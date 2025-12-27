"""
API endpoints para gestión de tickets/turnos del laboratorio clínico
Compatible con todos los modelos, schemas y CRUD existentes
CORREGIDO PARA PYDANTIC V2
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import logging

from app.core.database import get_db
from app.api.dependencies.auth import (
    get_current_user,
    require_permissions,
    get_current_agente,
    require_supervisor_or_admin
)
from app.models import ServiceType
from app.models.ticket import Ticket
from app.models.patient import Patient
from app.models.user import User
from app.schemas.ticket import (
    TicketCreate, TicketQuickCreate, TicketUpdate, TicketStatusUpdate,
    TicketResponse, TicketListResponse, TicketSearchFilters,
    CallTicketRequest, TransferTicketRequest, QueuePosition,
    TicketStats, QueueOverview, DailyTicketSummary
)
from app.crud.ticket import ticket_crud
from app.crud.patient import patient as patient_crud
from app.core.redis import cache_manager
from app.models.queue_state import QueueState
from app.services.queue_service import QueueService
from app.websocket.connection_manager import websocket_manager

# Importar WebSocket manager para broadcasts
try:
    from app.websocket.connection_manager import websocket_manager, MessageType
except ImportError:
    websocket_manager = None
    MessageType = None


# ========================================
# CONFIGURACIÓN DEL ROUTER
# ========================================

router = APIRouter(prefix="/tickets", tags=["tickets"])
logger = logging.getLogger(__name__)

# ========================================
# HELPER FUNCTIONS PARA WEBSOCKET
# ========================================

async def notify_new_ticket(ticket, patient, service_type) -> int:
    """
    Notifica via WebSocket la creación de un nuevo ticket
    """
    try:
        ticket_data = {
            "id": str(ticket.Id),
            "ticket_number": ticket.TicketNumber,
            "patient_name": patient.FullName if patient else "Desconocido",
            "patient_document": patient.DocumentNumber if patient else None,
            "service_type_id": ticket.ServiceTypeId,
            "service_name": service_type.Name if service_type else "Servicio",
            "service_code": service_type.Code if service_type else None,
            "position": ticket.Position,
            "estimated_wait_time": ticket.EstimatedWaitTime,
            "status": ticket.Status,
            "created_at": ticket.CreatedAt.isoformat() if ticket.CreatedAt else datetime.now().isoformat()
        }

        sent_count = await websocket_manager.broadcast_new_ticket(ticket_data)
        logger.info(f"WebSocket: Nuevo ticket {ticket.TicketNumber} notificado a {sent_count} clientes")
        return sent_count

    except Exception as e:
        logger.error(f"Error enviando notificación WebSocket de nuevo ticket: {e}")
        return 0


async def notify_ticket_called(ticket, station, patient=None, service_type=None) -> int:
    """
    Notifica via WebSocket cuando se llama un ticket
    """
    try:
        ticket_data = {
            "id": str(ticket.Id),
            "ticket_number": ticket.TicketNumber,
            "patient_name": patient.FullName if patient else "Paciente",
            "service_name": service_type.Name if service_type else "Servicio"
        }

        station_data = {
            "id": station.Id if station else None,
            "name": station.Name if station else "Estación",
            "code": station.Code if station else None
        }

        sent_count = await websocket_manager.broadcast_ticket_called(ticket_data, station_data)
        logger.info(f"WebSocket: Ticket {ticket.TicketNumber} llamado - notificado a {sent_count} clientes")
        return sent_count

    except Exception as e:
        logger.error(f"Error enviando notificación WebSocket de ticket llamado: {e}")
        return 0


async def notify_ticket_status_change(ticket, old_status: str, new_status: str) -> int:
    """
    Notifica via WebSocket cuando cambia el estado de un ticket
    """
    try:
        ticket_data = {
            "id": str(ticket.Id),
            "ticket_number": ticket.TicketNumber,
            "service_type_id": ticket.ServiceTypeId
        }

        sent_count = await websocket_manager.broadcast_ticket_status_change(ticket_data, old_status, new_status)
        logger.info(f"WebSocket: Cambio de estado {ticket.TicketNumber} {old_status}->{new_status}")
        return sent_count

    except Exception as e:
        logger.error(f"Error enviando notificación WebSocket de cambio de estado: {e}")
        return 0


# ========================================
# ENDPOINTS DE CREACIÓN DE TICKETS
# ========================================
# app/api/v1/endpoints/tickets.py
# VERSIÓN DE DIAGNÓSTICO - Agregar logging detallado


@router.post("", response_model=TicketResponse)
async def create_ticket(
        ticket_data: TicketCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permissions(["tickets.create", "queue.manage"]))
):
    """
    Crea un nuevo ticket/turno

    - Requiere permisos de creación de tickets
    - Genera número automático y posición en cola
    - Calcula tiempo estimado de espera
    - Crea código QR automáticamente
    - Notifica via WebSocket a todos los displays
    """
    try:
        logger.info(f"Creando ticket para paciente {ticket_data.PatientId}")

        # Verificar que el paciente existe
        patient = patient_crud.get(db, patient_id=ticket_data.PatientId)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente no encontrado"
            )

        # Verificar que el paciente esté activo
        if not patient.IsActive:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El paciente está inactivo"
            )

        # Obtener el tipo de servicio para la notificación
        service_type = db.query(ServiceType).filter(ServiceType.Id == ticket_data.ServiceTypeId).first()
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de servicio no encontrado"
            )

        # Crear ticket usando el CRUD
        ticket = ticket_crud.create_ticket(
            db,
            patient_id=ticket_data.PatientId,
            service_type_id=ticket_data.ServiceTypeId,
            station_id=ticket_data.StationId,
            notes=ticket_data.Notes
        )

        # Limpiar cache relacionado
        if cache_manager:
            cache_manager.delete(f"queue_stats")
            cache_manager.delete(f"service_queue:{ticket_data.ServiceTypeId}")

        logger.info(f"Ticket creado exitosamente: {ticket.TicketNumber}")

        # ========================================
        # NOTIFICAR VIA WEBSOCKET
        # ========================================
        await notify_new_ticket(ticket, patient, service_type)

        return TicketResponse.model_validate(ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear ticket"
        )



@router.post("/quick", response_model=TicketResponse)
async def create_quick_ticket(
        ticket_data: TicketQuickCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permissions(["tickets.create"]))
):
    """
    Crea un ticket rápido usando número de documento del paciente

    - Busca automáticamente al paciente por documento
    - Si no existe, retorna error
    - Notifica via WebSocket a todos los displays
    """
    try:
        logger.info(f"Creación rápida de ticket para documento {ticket_data.PatientDocumentNumber}")

        # Buscar paciente por documento
        patient = patient_crud.get_by_document(db, document_number=ticket_data.PatientDocumentNumber)

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paciente con documento {ticket_data.PatientDocumentNumber} no encontrado. Por favor, registre primero al paciente."
            )

        # Obtener el tipo de servicio
        service_type = db.query(ServiceType).filter(ServiceType.Id == ticket_data.ServiceTypeId).first()
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de servicio no encontrado"
            )

        # Crear ticket
        ticket = ticket_crud.create_ticket(
            db,
            patient_id=str(patient.Id),
            service_type_id=ticket_data.ServiceTypeId,
            notes=ticket_data.Notes
        )

        # Limpiar cache
        if cache_manager:
            cache_manager.delete(f"queue_stats")
            cache_manager.delete(f"service_queue:{ticket_data.ServiceTypeId}")

        logger.info(f"Ticket rápido creado: {ticket.TicketNumber} para {patient.FullName}")

        # ========================================
        # NOTIFICAR VIA WEBSOCKET
        # ========================================
        await notify_new_ticket(ticket, patient, service_type)

        return TicketResponse.model_validate(ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en creación rápida de ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno en creación rápida"
        )



# ========================================
# ENDPOINTS DE CONSULTA DE TICKETS
# ========================================

@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
        ticket_id: str = Path(..., description="ID del ticket"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene un ticket por su ID
    """
    ticket = ticket_crud.get(db, id=ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado"
        )

    return TicketResponse.model_validate(ticket)


@router.get("/number/{ticket_number}", response_model=TicketResponse)
async def get_ticket_by_number(
        ticket_number: str = Path(..., description="Número del ticket (ej: A001)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene un ticket por su número
    """
    ticket = ticket_crud.get_by_ticket_number(db, ticket_number=ticket_number)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_number} no encontrado"
        )

    return TicketResponse.model_validate(ticket)


@router.get("/", response_model=TicketListResponse)
async def list_tickets(
        skip: int = Query(0, ge=0, description="Registros a omitir"),
        limit: int = Query(20, ge=1, le=100, description="Límite de registros"),
        service_type_id: Optional[int] = Query(None, description="Filtrar por tipo de servicio"),
        station_id: Optional[int] = Query(None, description="Filtrar por estación"),
        status: Optional[str] = Query(None, description="Filtrar por estado"),
        active_only: bool = Query(True, description="Solo tickets activos"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Lista tickets con paginación y filtros
    """
    try:
        # Obtener tickets según filtros
        if active_only:
            tickets = ticket_crud.get_active_tickets(db, skip=skip, limit=limit)
        else:
            tickets = ticket_crud.get_multi(db, skip=skip, limit=limit)

        # Aplicar filtros adicionales si es necesario
        if service_type_id:
            tickets = [t for t in tickets if t.ServiceTypeId == service_type_id]
        if station_id:
            tickets = [t for t in tickets if t.StationId == station_id]
        if status:
            tickets = [t for t in tickets if t.Status == status]

        total = len(tickets)

        # Obtener estadísticas de cola
        queue_stats = ticket_crud.get_queue_statistics(db)

        return TicketListResponse(
            tickets=[TicketResponse.model_validate(t) for t in tickets],
            total=total,
            skip=skip,
            limit=limit,
            has_more=total > (skip + limit),
            queue_stats=queue_stats
        )

    except Exception as e:
        logger.error(f"Error listando tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener lista de tickets"
        )


# ========================================
# ENDPOINTS DE BÚSQUEDA
# ========================================

@router.post("/search", response_model=List[TicketResponse])
async def search_tickets(
        filters: TicketSearchFilters,
        limit: int = Query(50, ge=1, le=100, description="Límite de resultados"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Búsqueda avanzada de tickets con múltiples filtros
    """
    try:
        # Buscar tickets con filtros
        tickets = ticket_crud.search_tickets(
            db,
            patient_document=filters.patient_document,
            patient_name=filters.patient_name,
            service_type_id=filters.service_type_id,
            station_id=filters.station_id,
            status=filters.status,
            date_from=filters.date_from,
            date_to=filters.date_to,
            limit=limit
        )

        return [TicketResponse.model_validate(ticket) for ticket in tickets]

    except Exception as e:
        logger.error(f"Error en búsqueda de tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno en búsqueda"
        )


# ========================================
# ENDPOINTS DE GESTIÓN DE COLA
# ========================================

@router.get("/queue/{service_type_id}", response_model=List[TicketResponse])
async def get_service_queue(
        service_type_id: int = Path(..., description="ID del tipo de servicio"),
        limit: int = Query(50, ge=1, le=100, description="Límite de tickets en cola"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene la cola de tickets para un tipo de servicio específico
    """
    try:
        tickets = ticket_crud.get_queue_by_service(
            db,
            service_type_id=service_type_id,
            limit=limit
        )

        return [TicketResponse.model_validate(ticket) for ticket in tickets]

    except Exception as e:
        logger.error(f"Error obteniendo cola del servicio {service_type_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener cola"
        )


@router.get("/queue/{service_type_id}/next", response_model=Optional[TicketResponse])
async def get_next_ticket(
        service_type_id: int = Path(..., description="ID del tipo de servicio"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_agente)
):
    """
    Obtiene el siguiente ticket en la cola para atender

    - Requiere permisos de técnico
    - Retorna el ticket con menor posición en estado Waiting
    """
    try:
        next_ticket = ticket_crud.get_next_in_queue(db, service_type_id=service_type_id)

        if not next_ticket:
            return None

        return TicketResponse.model_validate(next_ticket)

    except Exception as e:
        logger.error(f"Error obteniendo siguiente ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener siguiente ticket"
        )


# ========================================
# ENDPOINTS DE ACTUALIZACIÓN DE TICKETS
# ========================================

@router.patch("/{ticket_id}/call", response_model=TicketResponse)
async def call_ticket(
        ticket_id: str = Path(..., description="ID del ticket"),
        call_data: CallTicketRequest = ...,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_agente)
):
    """
    Llama a un ticket para atención

    - Requiere permisos de técnico o superior
    - Cambia el estado a Called
    - Registra la estación que llama
    - Notifica via WebSocket a los displays
    """
    try:
        ticket = ticket_crud.call_ticket(
            db,
            ticket_id=ticket_id,
            station_id=call_data.station_id,
            user_id=str(current_user.Id)
        )

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo llamar el ticket. Verifique el estado."
            )

        # Agregar notas si se proporcionaron
        if call_data.notes:
            current_notes = ticket.Notes or ""
            ticket.Notes = f"{current_notes} | Llamado: {call_data.notes}".strip(" |")
            db.commit()
            db.refresh(ticket)

        # Obtener información relacionada para la notificación
        from app.models.station import Station
        station = db.query(Station).filter(Station.Id == call_data.station_id).first()
        patient = patient_crud.get(db, patient_id=str(ticket.PatientId))
        service_type = db.query(ServiceType).filter(ServiceType.Id == ticket.ServiceTypeId).first()

        logger.info(f"Ticket llamado: {ticket.TicketNumber} por {current_user.Username}")

        # ========================================
        # NOTIFICAR VIA WEBSOCKET
        # ========================================
        await notify_ticket_called(ticket, station, patient, service_type)

        return TicketResponse.model_validate(ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error llamando ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al llamar ticket"
        )



@router.patch("/number/{ticket_number}/call", response_model=TicketResponse)
async def call_ticket_by_number(
        ticket_number: str = Path(..., description="Número del ticket (ej: A001)"),
        station_id: int = Query(..., description="ID de la estación que llama"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_agente)
):
    """
    Llama a un ticket por su número (ej: A001)

    - Más práctico que usar el UUID
    - Requiere permisos de técnico o superior
    """
    try:
        # Buscar ticket por número
        ticket = ticket_crud.get_by_ticket_number(db, ticket_number=ticket_number)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_number} no encontrado"
            )

        # Llamar el ticket
        ticket = ticket_crud.call_ticket(
            db,
            ticket_id=str(ticket.Id),
            station_id=station_id,
            user_id=str(current_user.Id)
        )

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo llamar el ticket. Verifique el estado."
            )

        logger.info(f"Ticket llamado por número: {ticket.TicketNumber} por {current_user.Username}")

        # Broadcast de ticket llamado
        if websocket_manager:
            try:
                from app.crud.station import station_crud
                station = station_crud.get(db, id=station_id)
                station_name = station.Name if station else f"Ventanilla {station_id}"
                station_code = station.Code if station else None

                from app.crud.service_type import service_type_crud
                service = service_type_crud.get(db, id=ticket.ServiceTypeId) if ticket.ServiceTypeId else None
                service_name = service.Name if service else ""

                # Llamar con dos argumentos separados
                ticket_data = {
                    "id": str(ticket.Id),
                    "ticket_number": ticket.TicketNumber,
                    "patient_name": "Paciente",
                    "service_name": service_name
                }
                station_data = {
                    "id": station_id,
                    "name": station_name,
                    "code": station_code
                }

                await websocket_manager.broadcast_ticket_called(ticket_data, station_data)
                logger.info(f"Broadcast enviado: {ticket.TicketNumber} -> {station_name}")
            except Exception as ws_error:
                logger.warning(f"Error en broadcast: {ws_error}")

        return TicketResponse.model_validate(ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error llamando ticket {ticket_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al llamar ticket"
        )




@router.patch("/{ticket_id}/attend", response_model=TicketResponse)
async def start_attention(
        ticket_id: str = Path(..., description="ID del ticket"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_agente)
):
    """
    Inicia la atención de un ticket

    - Requiere permisos de técnico o superior
    - Cambia el estado a InProgress
    - Registra hora de inicio
    - Notifica via WebSocket
    """
    try:
        # Guardar estado anterior
        ticket_before = ticket_crud.get(db, id=ticket_id)
        old_status = ticket_before.Status if ticket_before else "Unknown"

        ticket = ticket_crud.start_attention(
            db,
            ticket_id=ticket_id,
            user_id=str(current_user.Id)
        )

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo iniciar la atención. Verifique el estado del ticket."
            )

        logger.info(f"Atención iniciada: {ticket.TicketNumber} por {current_user.Username}")

        # ========================================
        # NOTIFICAR VIA WEBSOCKET
        # ========================================
        await notify_ticket_status_change(ticket, old_status, "InProgress")

        return TicketResponse.model_validate(ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error iniciando atención de ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al iniciar atención"
        )



@router.patch("/{ticket_id}/complete", response_model=TicketResponse)
@router.patch("/{ticket_id}/complete", response_model=TicketResponse)
async def complete_ticket(
        ticket_id: str = Path(..., description="ID del ticket"),
        completion_notes: Optional[str] = Body(None, description="Notas de finalización"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_agente)
):
    """
    Completa la atención de un ticket

    - Requiere permisos de técnico o superior
    - Cambia el estado a Completed
    - Registra hora de finalización
    - Notifica via WebSocket
    """
    try:
        # Guardar estado anterior
        ticket_before = ticket_crud.get(db, id=ticket_id)
        old_status = ticket_before.Status if ticket_before else "Unknown"

        ticket = ticket_crud.complete_ticket(
            db,
            ticket_id=ticket_id,
            notes=completion_notes,
            user_id=str(current_user.Id)
        )

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo completar el ticket. Verifique el estado."
            )

        # Limpiar cache
        if cache_manager:
            cache_manager.delete(f"queue_stats")
            cache_manager.delete(f"service_queue:{ticket.ServiceTypeId}")

        logger.info(f"Ticket completado: {ticket.TicketNumber} por {current_user.Username}")

        # ========================================
        # NOTIFICAR VIA WEBSOCKET
        # ========================================
        await notify_ticket_status_change(ticket, old_status, "Completed")

        return TicketResponse.model_validate(ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completando ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al completar ticket"
        )



@router.patch("/{ticket_id}/cancel", response_model=TicketResponse)
async def cancel_ticket(
        ticket_id: str = Path(..., description="ID del ticket"),
        reason: Optional[str] = Body(None, description="Razón de cancelación"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Cancela un ticket

    - El usuario puede cancelar sus propios tickets
    - Supervisores pueden cancelar cualquier ticket
    - Notifica via WebSocket
    """
    try:
        ticket = ticket_crud.get(db, id=ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket no encontrado"
            )

        old_status = ticket.Status

        # Verificar permisos
        is_own_ticket = str(ticket.PatientId) == str(current_user.Id)
        is_supervisor = current_user.role and current_user.role.Name in ["Admin", "Supervisor"]

        if not (is_own_ticket or is_supervisor):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para cancelar este ticket"
            )

        # Cancelar ticket
        ticket = ticket_crud.cancel_ticket(
            db,
            ticket_id=ticket_id,
            reason=reason,
            user_id=str(current_user.Id)
        )

        # Limpiar cache
        if cache_manager:
            cache_manager.delete(f"queue_stats")
            cache_manager.delete(f"service_queue:{ticket.ServiceTypeId}")

        logger.info(f"Ticket cancelado: {ticket.TicketNumber} por {current_user.Username}")

        # ========================================
        # NOTIFICAR VIA WEBSOCKET
        # ========================================
        await notify_ticket_status_change(ticket, old_status, "Cancelled")

        return TicketResponse.model_validate(ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelando ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al cancelar ticket"
        )



@router.patch("/{ticket_id}/transfer", response_model=TicketResponse)
async def transfer_ticket(
        ticket_id: str = Path(..., description="ID del ticket"),
        transfer_data: TransferTicketRequest = ...,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_agente)
):
    """
    Transfiere un ticket a otra estación

    - Requiere permisos de técnico o superior
    - Mantiene el estado actual del ticket
    - Registra la transferencia en las notas
    """
    try:
        ticket = ticket_crud.transfer_ticket(
            db,
            ticket_id=ticket_id,
            new_station_id=transfer_data.new_station_id,
            reason=transfer_data.reason,
            user_id=str(current_user.Id)
        )

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo transferir el ticket"
            )

        logger.info(f"Ticket transferido: {ticket.TicketNumber} a estación {transfer_data.new_station_id}")
        return TicketResponse.model_validate(ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transfiriendo ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al transferir ticket"
        )


# ========================================
# ENDPOINTS DE ESTADÍSTICAS
# ========================================

@router.get("/stats/general", response_model=TicketStats)
async def get_general_stats(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene estadísticas generales de tickets
    """
    try:
        stats = ticket_crud.get_queue_statistics(db)

        return TicketStats(
            total_tickets=stats.get("total_tickets_today", 0),
            waiting_tickets=stats.get("waiting_tickets", 0),
            called_tickets=stats.get("called_tickets", 0),
            in_progress_tickets=stats.get("in_progress_tickets", 0),
            completed_tickets=stats.get("completed_tickets", 0),
            cancelled_tickets=stats.get("cancelled_tickets", 0),
            no_show_tickets=stats.get("no_show_tickets", 0),
            average_wait_time=stats.get("average_wait_time", 0.0),
            average_service_time=stats.get("average_service_time", 0.0)
        )

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas generales: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener estadísticas"
        )


@router.get("/stats/queue-overview", response_model=QueueOverview)
async def get_queue_overview(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene vista general del estado de todas las colas
    """
    try:
        stats = ticket_crud.get_queue_statistics(db)

        # Procesar datos para la vista general
        service_queues = stats.get("services_breakdown", [])

        return QueueOverview(
            service_queues=service_queues,
            total_waiting=stats.get("waiting_tickets", 0),
            active_stations=stats.get("active_stations", 0),
            estimated_next_calls=[]  # TODO: Implementar estimaciones
        )

    except Exception as e:
        logger.error(f"Error obteniendo vista general de colas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener vista general"
        )


# ========================================
# ENDPOINTS DE UTILIDAD
# ========================================

@router.get("/{ticket_id}/position", response_model=QueuePosition)
async def get_ticket_position(
        ticket_id: str = Path(..., description="ID del ticket"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene la posición actual de un ticket en la cola
    """
    try:
        ticket = ticket_crud.get(db, id=ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket no encontrado"
            )

        # Calcular posición actual
        position_info = ticket_crud.get_ticket_position(db, ticket_id=ticket_id)

        return QueuePosition(
            ticket_id=str(ticket.Id),
            ticket_number=ticket.TicketNumber,
            current_position=position_info.get("position", 0),
            estimated_wait_time=position_info.get("estimated_wait", 0),
            ahead_count=position_info.get("ahead_count", 0),
            service_name=position_info.get("service_name", "Servicio")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo posición de ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener posición"
        )


@router.post("/reset-positions")
async def reset_daily_positions(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Reinicia las posiciones de los tickets para un nuevo día

    - Requiere permisos de supervisor o administrador
    - Resetea contadores diarios
    - Útil para inicio de jornada
    """
    try:
        updated_count = ticket_crud.reset_daily_positions(db)

        logger.info(f"Posiciones reiniciadas: {updated_count} tickets actualizados por {current_user.Username}")

        return {
            "message": "Posiciones reiniciadas correctamente",
            "updated_tickets": updated_count,
            "timestamp": datetime.utcnow()
        }

    except Exception as e:
        logger.error(f"Error reiniciando posiciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al reiniciar posiciones"
        )

@router.patch("/number/{ticket_number}/reset-status")
async def reset_ticket_status(
        ticket_number: str = Path(..., description="Número del ticket (ej: A001)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Resetea el estado de un ticket a 'Waiting' (solo para desarrollo/pruebas)

    - Útil para probar el flujo de llamadas
    - Requiere permisos de supervisor o administrador
    """
    try:
        ticket = ticket_crud.get_by_ticket_number(db, ticket_number=ticket_number)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket {ticket_number} no encontrado"
            )

        old_status = ticket.Status
        ticket.Status = 'Waiting'
        ticket.CalledAt = None
        ticket.AttendedAt = None
        ticket.StationId = None
        db.commit()
        db.refresh(ticket)

        logger.info(f"Ticket {ticket_number} reseteado: {old_status} -> Waiting por {current_user.Username}")

        return {
            "message": f"Ticket {ticket_number} reseteado a estado Waiting",
            "ticket_number": ticket.TicketNumber,
            "old_status": old_status,
            "new_status": ticket.Status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reseteando ticket {ticket_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al resetear ticket"
        )
