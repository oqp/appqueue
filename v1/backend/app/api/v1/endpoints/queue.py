"""
API endpoints para gestión de estados de cola (QueueState)
Compatible con toda la estructura del proyecto existente
VERSIÓN CORREGIDA CON PASCALCASE - Coincide con BD, modelos y schemas
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging
import uuid

from app.core.database import get_db
from app.api.dependencies.auth import (
    get_current_user,
    require_permissions,
    get_current_agente,
    require_supervisor_or_admin,
    require_admin
)
from app.models.queue_state import QueueState
from app.models.user import User
from app.models.service_type import ServiceType
from app.models.station import Station
from app.models.ticket import Ticket

from sqlalchemy import func
from typing import Dict, Any

# Importar schemas de queue con PascalCase
from app.schemas.queue import (
    QueueStateCreate,
    QueueStateUpdate,
    QueueStateResponse,
    QueueStateWithTickets,
    AdvanceQueueRequest,
    ResetQueueRequest,
    UpdateWaitTimeRequest,
    QueueSummary,
    QueueFilters,
    BatchQueueUpdate,
    QueueStateChangeNotification
)

# Importar los CRUDs necesarios
from app.crud.queue import queue_crud
from app.crud.service_type import service_type_crud
from app.crud.station import station_crud
from app.crud.ticket import ticket_crud

# Servicios y utilidades - Con manejo de importaciones opcionales
try:
    from app.core.redis import cache_manager
except ImportError:
    cache_manager = None

try:
    from app.websocket.connection_manager import websocket_manager
except ImportError:
    websocket_manager = None

try:
    from app.services.notification_service import notification_service
except ImportError:
    notification_service = None

# ========================================
# CONFIGURACIÓN DEL ROUTER
# ========================================

router = APIRouter(prefix="/queue-states", tags=["queue-states"])
logger = logging.getLogger(__name__)


# ========================================
# FUNCIONES AUXILIARES
# ========================================

def _convert_queue_to_response(
    queue_state: QueueState,
    db: Session
) -> QueueStateResponse:
    """
    Convierte un modelo QueueState a QueueStateResponse
    Enriquece con información adicional de servicio y estación
    Usa PascalCase para coincidir con schemas corregidos
    """
    response_data = {
        "Id": queue_state.Id,
        "ServiceTypeId": queue_state.ServiceTypeId,
        "StationId": queue_state.StationId,
        "CurrentTicketId": str(queue_state.CurrentTicketId) if queue_state.CurrentTicketId else None,
        "NextTicketId": str(queue_state.NextTicketId) if queue_state.NextTicketId else None,
        "QueueLength": queue_state.QueueLength,
        "AverageWaitTime": queue_state.AverageWaitTime,
        "LastUpdateAt": queue_state.LastUpdateAt,
        "IsActive": True  # Por defecto activo
    }

    # Agregar información del servicio si existe la relación
    if hasattr(queue_state, 'service_type') and queue_state.service_type:
        response_data["ServiceName"] = queue_state.service_type.Name
        response_data["ServiceCode"] = queue_state.service_type.Code
    else:
        # Obtener manualmente si no está cargado
        service = service_type_crud.get(db, id=queue_state.ServiceTypeId)
        if service:
            response_data["ServiceName"] = service.Name
            response_data["ServiceCode"] = service.Code

    # Agregar información de la estación si existe
    if queue_state.StationId:
        if hasattr(queue_state, 'station') and queue_state.station:
            response_data["StationName"] = queue_state.station.Name
            response_data["StationCode"] = queue_state.station.Code
        else:
            # Obtener manualmente si no está cargado
            station = station_crud.get(db, id=queue_state.StationId)
            if station:
                response_data["StationName"] = station.Name
                response_data["StationCode"] = station.Code

    # Calcular tiempo estimado
    response_data["EstimatedWaitTime"] = queue_state.QueueLength * queue_state.AverageWaitTime

    return QueueStateResponse(**response_data)


async def _send_queue_notification(
    queue_state_id: int,
    change_type: str,
    db: Session
):
    """
    Envía notificación de cambio en estado de cola
    Solo si el servicio de WebSocket está disponible
    """
    if not websocket_manager:
        logger.debug("WebSocket manager no disponible, omitiendo notificación")
        return

    try:
        queue_state = queue_crud.get(db, id=queue_state_id)
        if not queue_state:
            return

        # Obtener información de tickets
        current_ticket = None
        next_ticket = None

        if queue_state.CurrentTicketId:
            current = ticket_crud.get(db, id=str(queue_state.CurrentTicketId))
            if current:
                current_ticket = current.TicketNumber

        if queue_state.NextTicketId:
            next = ticket_crud.get(db, id=str(queue_state.NextTicketId))
            if next:
                next_ticket = next.TicketNumber

        # Crear notificación con PascalCase
        notification = QueueStateChangeNotification(
            QueueStateId=queue_state_id,
            ChangeType=change_type,
            CurrentTicket=current_ticket,
            NextTicket=next_ticket,
            Timestamp=datetime.now()
        )

        # Enviar por WebSocket
        await websocket_manager.broadcast_json(
            notification.model_dump(mode='json')
        )

    except Exception as e:
        logger.error(f"Error enviando notificación de cola: {e}")


# ========================================
# ENDPOINTS DE CONSULTA
# ========================================

@router.get("/", response_model=List[QueueStateResponse])
async def get_queue_states(
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=100, description="Límite de registros"),
    service_type_id: Optional[int] = Query(None, description="Filtrar por tipo de servicio"),
    station_id: Optional[int] = Query(None, description="Filtrar por estación"),
    include_empty: bool = Query(True, description="Incluir colas vacías"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene lista de estados de cola con filtros opcionales

    Permisos: Usuario autenticado
    """
    try:
        query = db.query(QueueState)

        # Aplicar filtros
        if service_type_id:
            query = query.filter(QueueState.ServiceTypeId == service_type_id)

        if station_id:
            query = query.filter(QueueState.StationId == station_id)

        if not include_empty:
            query = query.filter(QueueState.QueueLength > 0)

        # Paginación
        # SQL Server requiere ORDER BY para OFFSET/LIMIT
        queue_states = query.order_by(QueueState.Id.asc()).offset(skip).limit(limit).all()

        return [_convert_queue_to_response(q, db) for q in queue_states]

    except Exception as e:
        logger.error(f"Error obteniendo estados de cola: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estados de cola"
        )


@router.get("/summary", response_model=QueueSummary)
async def get_queue_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene resumen del estado global de las colas

    Permisos: Usuario autenticado
    CORREGIDO: Ahora cuenta tickets reales desde la tabla Ticket
    """
    try:
        summary = queue_crud.get_queue_summary(db)

        # Convertir a PascalCase para el response
        return QueueSummary(
            TotalQueues=summary['total_queues'],
            ActiveQueues=summary['active_queues'],
            TotalWaiting=summary['total_waiting'],
            InAttention=summary.get('in_attention', 0),
            StationsBusy=summary['stations_busy'],
            AverageWaitTime=summary['average_wait_time'],
            CompletedToday=summary.get('completed_today', 0)
        )

    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener resumen de colas"
        )




@router.get("/consistency-check", response_model=Dict[str, Any])
async def check_queue_consistency(
        fix_issues: bool = Query(False, description="Corregir automáticamente las inconsistencias"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Verifica la consistencia entre Tickets y QueueState.
    Opcionalmente corrige las inconsistencias encontradas.

    Permisos: Cualquier usuario autenticado
    """
    try:
        inconsistencies = []
        fixed = []

        # Obtener todos los QueueStates
        queue_states = db.query(QueueState).filter(
            QueueState.StationId == None  # Solo colas generales
        ).all()

        for queue_state in queue_states:
            # Contar tickets reales en espera
            actual_count = db.query(func.count(Ticket.Id)).filter(
                Ticket.ServiceTypeId == queue_state.ServiceTypeId,
                Ticket.Status == 'Waiting'
            ).scalar() or 0

            # Verificar si hay discrepancia
            if queue_state.QueueLength != actual_count:
                service = db.query(ServiceType).filter(
                    ServiceType.Id == queue_state.ServiceTypeId
                ).first()

                inconsistency = {
                    "service_id": queue_state.ServiceTypeId,
                    "service_name": service.Name if service else "Unknown",
                    "queue_state_count": queue_state.QueueLength,
                    "actual_ticket_count": actual_count,
                    "difference": actual_count - queue_state.QueueLength
                }

                inconsistencies.append(inconsistency)

                # Corregir si se solicitó
                if fix_issues:
                    queue_state.QueueLength = actual_count
                    queue_state.LastUpdateAt = datetime.now()

                    # Actualizar NextTicketId
                    if actual_count > 0:
                        next_ticket = db.query(Ticket).filter(
                            Ticket.ServiceTypeId == queue_state.ServiceTypeId,
                            Ticket.Status == 'Waiting'
                        ).order_by(Ticket.Position).first()

                        queue_state.NextTicketId = next_ticket.Id if next_ticket else None
                    else:
                        queue_state.NextTicketId = None

                    fixed.append({
                        "service_id": queue_state.ServiceTypeId,
                        "old_count": inconsistency["queue_state_count"],
                        "new_count": actual_count
                    })

            # Verificar NextTicketId válido
            if queue_state.NextTicketId:
                next_ticket_exists = db.query(Ticket).filter(
                    Ticket.Id == queue_state.NextTicketId,
                    Ticket.Status == 'Waiting'
                ).first()

                if not next_ticket_exists:
                    inconsistencies.append({
                        "service_id": queue_state.ServiceTypeId,
                        "issue": "NextTicketId apunta a un ticket inválido",
                        "invalid_ticket_id": str(queue_state.NextTicketId)
                    })

                    if fix_issues:
                        # Buscar el siguiente ticket válido
                        valid_next = db.query(Ticket).filter(
                            Ticket.ServiceTypeId == queue_state.ServiceTypeId,
                            Ticket.Status == 'Waiting'
                        ).order_by(Ticket.Position).first()

                        queue_state.NextTicketId = valid_next.Id if valid_next else None
                        fixed.append({
                            "service_id": queue_state.ServiceTypeId,
                            "issue_fixed": "NextTicketId corregido"
                        })

        # Buscar servicios sin QueueState
        services_without_queue = db.query(ServiceType).filter(
            ServiceType.IsActive == True,
            ~ServiceType.Id.in_(
                db.query(QueueState.ServiceTypeId).filter(
                    QueueState.StationId == None
                )
            )
        ).all()

        for service in services_without_queue:
            ticket_count = db.query(func.count(Ticket.Id)).filter(
                Ticket.ServiceTypeId == service.Id,
                Ticket.Status == 'Waiting'
            ).scalar() or 0

            inconsistencies.append({
                "service_id": service.Id,
                "service_name": service.Name,
                "issue": "Sin QueueState",
                "waiting_tickets": ticket_count
            })

            if fix_issues:
                # Crear QueueState faltante
                new_queue = QueueState(
                    ServiceTypeId=service.Id,
                    StationId=None,
                    QueueLength=ticket_count,
                    AverageWaitTime=service.AverageTimeMinutes or 15,
                    LastUpdateAt=datetime.now()
                )

                if ticket_count > 0:
                    next_ticket = db.query(Ticket).filter(
                        Ticket.ServiceTypeId == service.Id,
                        Ticket.Status == 'Waiting'
                    ).order_by(Ticket.Position).first()

                    if next_ticket:
                        new_queue.NextTicketId = next_ticket.Id

                db.add(new_queue)
                fixed.append({
                    "service_id": service.Id,
                    "action": "QueueState creado",
                    "queue_length": ticket_count
                })

        # Commit si se corrigieron problemas
        if fix_issues and fixed:
            db.commit()

        # Preparar resultado
        is_consistent = len(inconsistencies) == 0

        result = {
            "is_consistent": is_consistent,
            "message": "Sistema consistente" if is_consistent else f"Se encontraron {len(inconsistencies)} inconsistencias",
            "inconsistencies": inconsistencies,
            "fixed": fixed if fix_issues else [],
            "checked_at": datetime.now().isoformat()
        }

        if fix_issues and fixed:
            result["message"] = f"Se corrigieron {len(fixed)} inconsistencias"

        return result

    except Exception as e:
        logger.error(f"Error verificando consistencia: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar consistencia: {str(e)}"
        )


@router.get("/{queue_id}", response_model=QueueStateResponse)
async def get_queue_state(
    queue_id: int = Path(..., description="ID del estado de cola"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene un estado de cola específico por ID

    Permisos: Usuario autenticado
    """
    queue_state = queue_crud.get(db, id=queue_id)

    if not queue_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estado de cola no encontrado"
        )

    return _convert_queue_to_response(queue_state, db)


@router.get("/service/{service_id}", response_model=QueueStateResponse)
async def get_queue_by_service(
    service_id: int = Path(..., description="ID del tipo de servicio"),
    station_id: Optional[int] = Query(None, description="ID de estación opcional"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el estado de cola para un servicio específico

    Permisos: Usuario autenticado
    """
    # Verificar que existe el servicio
    service = service_type_crud.get(db, id=service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de servicio no encontrado"
        )

    # Usar get_or_create del CRUD
    queue_state = queue_crud.get_or_create(
        db,
        service_type_id=service_id,
        station_id=station_id
    )

    return _convert_queue_to_response(queue_state, db)


@router.get("/station/{station_id}/all", response_model=List[QueueStateResponse])
async def get_queues_by_station(
    station_id: int = Path(..., description="ID de la estación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las colas asociadas a una estación

    Permisos: Usuario autenticado
    """
    # Verificar que existe la estación
    station = station_crud.get(db, id=station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estación no encontrada"
        )

    # Usar método get_by_station del CRUD
    queue_states = queue_crud.get_by_station(
        db,
        station_id=station_id
    )

    return [_convert_queue_to_response(q, db) for q in queue_states]


# ========================================
# ENDPOINTS DE CREACIÓN Y ACTUALIZACIÓN
# ========================================

@router.post("", response_model=QueueStateResponse)
async def create_queue_state(
    queue_data: QueueStateCreate = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Crea un nuevo estado de cola

    Permisos: Supervisor o Admin
    """
    try:
        # Verificar que no exista ya
        existing = queue_crud.get_by_service_and_station(
            db,
            service_type_id=queue_data.ServiceTypeId,
            station_id=queue_data.StationId
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un estado de cola para este servicio y estación"
            )

        # Verificar que existe el servicio
        service = service_type_crud.get(db, id=queue_data.ServiceTypeId)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de servicio no encontrado"
            )

        # Verificar estación si se proporciona
        if queue_data.StationId:
            station = station_crud.get(db, id=queue_data.StationId)
            if not station:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Estación no encontrada"
                )

        # Crear estado de cola
        queue_state = queue_crud.create(db, obj_in=queue_data)

        # Enviar notificación
        background_tasks.add_task(
            _send_queue_notification,
            queue_state.Id,
            "created",
            db
        )

        logger.info(f"Estado de cola creado: {queue_state.Id} por usuario {current_user.Username}")

        return _convert_queue_to_response(queue_state, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando estado de cola: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear estado de cola"
        )


@router.patch("/{queue_id}", response_model=QueueStateResponse)
async def update_queue_state(
    queue_id: int = Path(..., description="ID del estado de cola"),
    queue_update: QueueStateUpdate = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_agente)
):
    """
    Actualiza un estado de cola existente

    Permisos: Técnico o superior
    """
    try:
        # Obtener estado actual
        queue_state = queue_crud.get(db, id=queue_id)
        if not queue_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estado de cola no encontrado"
            )

        # Actualizar usando CRUD
        queue_state = queue_crud.update(
            db,
            db_obj=queue_state,
            obj_in=queue_update
        )

        # Enviar notificación
        background_tasks.add_task(
            _send_queue_notification,
            queue_state.Id,
            "updated",
            db
        )

        # Invalidar caché si está disponible
        if cache_manager:
            await cache_manager.delete(f"queue:state:{queue_id}")

        logger.info(f"Estado de cola {queue_id} actualizado por {current_user.Username}")

        return _convert_queue_to_response(queue_state, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando estado de cola: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar estado de cola"
        )


# ========================================
# ENDPOINTS DE OPERACIONES DE COLA
# ========================================

@router.post("/advance", response_model=QueueStateResponse)
async def advance_queue(
    request: AdvanceQueueRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_agente)
):
    """
    Avanza la cola al siguiente paciente

    Permisos: Técnico o superior
    """
    try:
        # Usar método advance_queue del CRUD
        queue_state = queue_crud.advance_queue(
            db,
            service_type_id=request.ServiceTypeId,
            station_id=request.StationId
        )

        if not queue_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay cola para avanzar o no hay más pacientes"
            )

        # Marcar ticket anterior como completado si se solicita
        if request.MarkCompleted and queue_state.CurrentTicketId:
            ticket_crud.update_ticket_status(
                db,
                ticket_id=str(queue_state.CurrentTicketId),
                new_status="Completed"
            )

        # Enviar notificación
        background_tasks.add_task(
            _send_queue_notification,
            queue_state.Id,
            "advanced",
            db
        )

        logger.info(f"Cola avanzada para servicio {request.ServiceTypeId}")

        return _convert_queue_to_response(queue_state, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error avanzando cola: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al avanzar la cola"
        )


@router.post("/reset", response_model=QueueStateResponse)
async def reset_queue(
    request: ResetQueueRequest = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Resetea una cola específica

    Permisos: Supervisor o Admin
    """
    try:
        # Usar método reset_queue del CRUD
        queue_state = queue_crud.reset_queue(
            db,
            service_type_id=request.ServiceTypeId,
            station_id=request.StationId
        )

        if not queue_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se pudo resetear la cola"
            )

        # Cancelar tickets pendientes si se solicita
        if request.CancelPendingTickets:
            pending_tickets = db.query(Ticket).filter(
                Ticket.ServiceTypeId == request.ServiceTypeId,
                Ticket.Status == 'Waiting'
            ).all()

            for ticket in pending_tickets:
                ticket.Status = 'Cancelled'

            db.commit()

        # Enviar notificación
        background_tasks.add_task(
            _send_queue_notification,
            queue_state.Id,
            "reset",
            db
        )

        logger.info(
            f"Cola reseteada para servicio {request.ServiceTypeId}. "
            f"Razón: {request.Reason}"
        )

        return _convert_queue_to_response(queue_state, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reseteando cola: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al resetear la cola"
        )


@router.post("/{queue_id}/update-wait-time", response_model=QueueStateResponse)
async def update_wait_time(
    queue_id: int = Path(..., description="ID del estado de cola"),
    request: UpdateWaitTimeRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_agente)
):
    """
    Actualiza el tiempo de espera promedio

    Permisos: Técnico o superior
    """
    try:
        queue_state = queue_crud.get(db, id=queue_id)
        if not queue_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estado de cola no encontrado"
            )

        if request.Recalculate:
            # Usar método calculate_and_update_wait_time del CRUD
            avg_time = queue_crud.calculate_and_update_wait_time(
                db,
                queue_state_id=queue_id
            )
            # Refrescar el objeto después de la actualización
            db.refresh(queue_state)
        else:
            # Actualizar manualmente con PascalCase
            avg_time = request.ManualTime
            update_data = QueueStateUpdate(AverageWaitTime=avg_time)
            queue_state = queue_crud.update(
                db,
                db_obj=queue_state,
                obj_in=update_data
            )

        logger.info(f"Tiempo de espera actualizado para cola {queue_id}: {avg_time} min")

        return _convert_queue_to_response(queue_state, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando tiempo de espera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar tiempo de espera"
        )


# ========================================
# ENDPOINTS DE OPERACIONES MASIVAS
# ========================================

@router.post("/batch-update", response_model=Dict[str, Any])
async def batch_update_queues(
    request: BatchQueueUpdate = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
):
    """
    Actualización masiva de estados de cola

    Permisos: Solo Admin
    """
    try:
        results = {
            "success": [],
            "failed": [],
            "total": len(request.QueueIds)
        }

        for queue_id in request.QueueIds:
            try:
                queue_state = queue_crud.get(db, id=queue_id)
                if not queue_state:
                    results["failed"].append({
                        "id": queue_id,
                        "error": "No encontrado"
                    })
                    continue

                if request.Action == "reset":
                    # Usar método reset_queue del CRUD
                    reset_result = queue_crud.reset_queue(
                        db,
                        service_type_id=queue_state.ServiceTypeId,
                        station_id=queue_state.StationId
                    )
                    if reset_result:
                        results["success"].append(queue_id)
                    else:
                        results["failed"].append({
                            "id": queue_id,
                            "error": "Error al resetear"
                        })

                elif request.Action == "refresh":
                    # Recalcular tiempo de espera
                    avg_time = queue_crud.calculate_and_update_wait_time(
                        db,
                        queue_state_id=queue_id
                    )
                    if avg_time is not None:
                        results["success"].append(queue_id)
                    else:
                        results["failed"].append({
                            "id": queue_id,
                            "error": "Error al refrescar"
                        })

                elif request.Action == "cleanup":
                    # Limpiar si está vacía y sin actividad
                    if queue_state.QueueLength == 0 and queue_state.CurrentTicketId is None:
                        db.delete(queue_state)
                        db.commit()
                        results["success"].append(queue_id)
                    else:
                        results["failed"].append({
                            "id": queue_id,
                            "error": "Cola no está vacía"
                        })

            except Exception as e:
                results["failed"].append({
                    "id": queue_id,
                    "error": str(e)
                })

        logger.info(
            f"Actualización masiva completada: {len(results['success'])} exitosas, "
            f"{len(results['failed'])} fallidas. Razón: {request.Reason}"
        )

        return results

    except Exception as e:
        logger.error(f"Error en actualización masiva: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en actualización masiva"
        )


@router.post("/refresh-all", response_model=Dict[str, int])
async def refresh_all_states(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Refresca todos los estados de cola desde los datos actuales

    Permisos: Supervisor o Admin
    """
    try:
        updated_count = queue_crud.refresh_all_states(db)

        logger.info(f"Refrescados {updated_count} estados de cola por {current_user.Username}")

        return {"updated_count": updated_count}

    except Exception as e:
        logger.error(f"Error refrescando estados: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al refrescar estados de cola"
        )


@router.delete("/cleanup-stale", response_model=Dict[str, Any])
async def cleanup_stale_states(
    minutes: int = Query(30, ge=1, le=1440, description="Minutos de inactividad"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
):
    """
    Limpia estados de cola obsoletos sin actividad reciente

    Permisos: Solo Admin
    """
    try:
        deleted_count = queue_crud.cleanup_stale_states(
            db,
            minutes=minutes
        )

        logger.info(
            f"Limpiados {deleted_count} estados obsoletos "
            f"(inactivos por {minutes} minutos) por {current_user.Username}"
        )

        return {
            "deleted_count": deleted_count,
            "criteria_minutes": minutes
        }

    except Exception as e:
        logger.error(f"Error limpiando estados obsoletos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al limpiar estados obsoletos"
        )


# ========================================
# ENDPOINTS DE ESTADÍSTICAS Y MONITOREO
# ========================================

@router.get("/active/all", response_model=List[QueueStateResponse])
async def get_active_queues(
        skip: int = Query(0, ge=0, description="Registros a omitir"),
        limit: int = Query(100, ge=1, le=100, description="Límite de registros"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las colas activas (con gente esperando o siendo atendida)

    Permisos: Usuario autenticado
    """
    try:
        # Obtener directamente con query para poder aplicar order_by
        query = db.query(QueueState).filter(
            or_(
                QueueState.QueueLength > 0,
                QueueState.CurrentTicketId != None
            )
        )

        # ORDER BY requerido para OFFSET/LIMIT en SQL Server
        query = query.order_by(QueueState.Id.asc())

        # Aplicar paginación
        active_queues = query.offset(skip).limit(limit).all()

        return [_convert_queue_to_response(q, db) for q in active_queues]

    except Exception as e:
        logger.error(f"Error obteniendo colas activas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener colas activas"
        )

@router.get("/{queue_id}/with-tickets", response_model=QueueStateWithTickets)
async def get_queue_with_tickets(
    queue_id: int = Path(..., description="ID del estado de cola"),
    include_completed: bool = Query(False, description="Incluir tickets completados"),
    limit: int = Query(10, ge=1, le=50, description="Límite de tickets"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene un estado de cola con lista de tickets pendientes

    Permisos: Usuario autenticado
    """
    try:
        queue_state = queue_crud.get(db, id=queue_id)
        if not queue_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estado de cola no encontrado"
            )

        # Obtener tickets pendientes
        pending_query = db.query(Ticket).filter(
            Ticket.ServiceTypeId == queue_state.ServiceTypeId,
            Ticket.Status == 'Waiting'
        ).order_by(Ticket.Position.asc()).limit(limit)

        pending_tickets = pending_query.all()

        # Formatear tickets para respuesta
        pending_list = [
            {
                "Id": str(t.Id),
                "TicketNumber": t.TicketNumber,
                "Position": t.Position,
                "EstimatedWaitTime": t.EstimatedWaitTime
            }
            for t in pending_tickets
        ]

        # Obtener tickets completados si se solicita
        recently_completed = []
        if include_completed:
            completed_query = db.query(Ticket).filter(
                Ticket.ServiceTypeId == queue_state.ServiceTypeId,
                Ticket.Status == 'Completed'
            ).order_by(Ticket.CompletedAt.desc()).limit(5)

            completed_tickets = completed_query.all()
            recently_completed = [
                {
                    "Id": str(t.Id),
                    "TicketNumber": t.TicketNumber,
                    "CompletedAt": t.CompletedAt
                }
                for t in completed_tickets
            ]

        # Crear respuesta con PascalCase
        response = _convert_queue_to_response(queue_state, db)
        response_dict = response.model_dump()
        response_dict["PendingTickets"] = pending_list
        response_dict["RecentlyCompleted"] = recently_completed

        return QueueStateWithTickets(**response_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo cola con tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener cola con tickets"
        )


# AGREGAR estos endpoints al archivo app/api/v1/endpoints/queue.py
# Colocar al final del archivo, antes del último comentario de cierre

# ========================================
# ENDPOINTS DE SINCRONIZACIÓN Y MANTENIMIENTO
# ========================================

@router.post("/initialize-all", response_model=Dict[str, Any])
async def initialize_all_queue_states(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Inicializa QueueState para todos los servicios activos.
    Útil para primera configuración o después de mantenimiento.

    Permisos: Cualquier usuario autenticado
    """
    try:
        logger.info("Iniciando inicialización de todos los QueueStates")

        created = 0
        updated = 0
        errors = []

        # Obtener todos los servicios activos
        services = db.query(ServiceType).filter(
            ServiceType.IsActive == True
        ).all()

        for service in services:
            try:
                # Verificar si ya existe QueueState
                queue_state = db.query(QueueState).filter(
                    QueueState.ServiceTypeId == service.Id,
                    QueueState.StationId == None  # Cola general
                ).first()

                # Contar tickets en espera para este servicio
                waiting_count = db.query(func.count(Ticket.Id)).filter(
                    Ticket.ServiceTypeId == service.Id,
                    Ticket.Status == 'Waiting'
                ).scalar() or 0

                if not queue_state:
                    # Crear nuevo QueueState
                    queue_state = QueueState(
                        ServiceTypeId=service.Id,
                        StationId=None,
                        QueueLength=waiting_count,
                        AverageWaitTime=service.AverageTimeMinutes or 15,
                        LastUpdateAt=datetime.now()
                    )

                    # Si hay tickets esperando, establecer el siguiente
                    if waiting_count > 0:
                        next_ticket = db.query(Ticket).filter(
                            Ticket.ServiceTypeId == service.Id,
                            Ticket.Status == 'Waiting'
                        ).order_by(Ticket.Position).first()

                        if next_ticket:
                            queue_state.NextTicketId = next_ticket.Id

                    db.add(queue_state)
                    created += 1
                    logger.info(f"QueueState creado para servicio {service.Name} con {waiting_count} tickets")

                else:
                    # Actualizar QueueState existente
                    if queue_state.QueueLength != waiting_count:
                        queue_state.QueueLength = waiting_count
                        queue_state.LastUpdateAt = datetime.now()

                        # Actualizar NextTicketId si es necesario
                        if waiting_count > 0 and not queue_state.NextTicketId:
                            next_ticket = db.query(Ticket).filter(
                                Ticket.ServiceTypeId == service.Id,
                                Ticket.Status == 'Waiting'
                            ).order_by(Ticket.Position).first()

                            if next_ticket:
                                queue_state.NextTicketId = next_ticket.Id

                        updated += 1
                        logger.info(f"QueueState actualizado para servicio {service.Name}: {waiting_count} tickets")

            except Exception as e:
                errors.append({
                    "service_id": service.Id,
                    "service_name": service.Name,
                    "error": str(e)
                })
                logger.error(f"Error procesando servicio {service.Name}: {e}")

        # Commit de todos los cambios
        db.commit()

        # Preparar resumen
        result = {
            "success": len(errors) == 0,
            "message": f"Inicialización completada: {created} creados, {updated} actualizados",
            "details": {
                "services_processed": len(services),
                "queues_created": created,
                "queues_updated": updated,
                "errors": errors
            },
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Inicialización completada: {result['message']}")
        return result

    except Exception as e:
        logger.error(f"Error en inicialización: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al inicializar colas: {str(e)}"
        )




@router.post("/refresh-all", response_model=Dict[str, Any])
async def refresh_all_queue_states(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Recalcula todos los QueueStates basándose en los tickets actuales.
    Útil para corregir cualquier desincronización.

    Permisos: Supervisor o Admin
    """
    try:
        refreshed = 0

        # Obtener todos los servicios con tickets en espera
        services_with_tickets = db.query(
            Ticket.ServiceTypeId,
            func.count(Ticket.Id).label('count')
        ).filter(
            Ticket.Status == 'Waiting'
        ).group_by(
            Ticket.ServiceTypeId
        ).all()

        # Actualizar cada QueueState
        for service_id, count in services_with_tickets:
            queue_state = db.query(QueueState).filter(
                QueueState.ServiceTypeId == service_id,
                QueueState.StationId == None
            ).first()

            if queue_state:
                queue_state.QueueLength = count

                # Actualizar NextTicketId
                next_ticket = db.query(Ticket).filter(
                    Ticket.ServiceTypeId == service_id,
                    Ticket.Status == 'Waiting'
                ).order_by(Ticket.Position).first()

                queue_state.NextTicketId = next_ticket.Id if next_ticket else None
                queue_state.LastUpdateAt = datetime.now()

                refreshed += 1

        # Limpiar QueueStates sin tickets
        empty_queues = db.query(QueueState).filter(
            QueueState.StationId == None,
            ~QueueState.ServiceTypeId.in_(
                db.query(Ticket.ServiceTypeId).filter(
                    Ticket.Status == 'Waiting'
                ).distinct()
            )
        ).all()

        for queue in empty_queues:
            queue.QueueLength = 0
            queue.NextTicketId = None
            queue.CurrentTicketId = None
            queue.LastUpdateAt = datetime.now()
            refreshed += 1

        db.commit()

        return {
            "success": True,
            "message": f"Se actualizaron {refreshed} colas",
            "refreshed_count": refreshed,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error refrescando colas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al refrescar colas: {str(e)}"
        )


# ========================================
# ENDPOINTS PÚBLICOS PARA DISPLAY
# ========================================

@router.get("/public/summary", response_model=QueueSummary)
async def get_public_queue_summary(
    db: Session = Depends(get_db)
):
    """
    Obtiene resumen del estado global de las colas - PÚBLICO

    Para uso en pantallas de display sin autenticación
    CORREGIDO: Ahora cuenta tickets reales desde la tabla Ticket
    """
    try:
        summary = queue_crud.get_queue_summary(db)

        return QueueSummary(
            TotalQueues=summary['total_queues'],
            ActiveQueues=summary['active_queues'],
            TotalWaiting=summary['total_waiting'],
            InAttention=summary.get('in_attention', 0),
            StationsBusy=summary['stations_busy'],
            AverageWaitTime=summary['average_wait_time'],
            CompletedToday=summary.get('completed_today', 0)
        )

    except Exception as e:
        logger.error(f"Error obteniendo resumen público: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener resumen de colas"
        )



@router.get("/public/waiting-tickets", response_model=List[Dict[str, Any]])
async def get_public_waiting_tickets(
    limit: int = Query(20, ge=1, le=50, description="Límite de tickets"),
    db: Session = Depends(get_db)
):
    """
    Obtiene lista de tickets en espera - PÚBLICO

    Para uso en pantallas de display sin autenticación
    """
    try:
        # Obtener tickets en espera ordenados por posición
        waiting_tickets = db.query(Ticket).filter(
            Ticket.Status == 'Waiting'
        ).order_by(Ticket.Position.asc()).limit(limit).all()

        result = []
        for ticket in waiting_tickets:
            # Obtener nombre del servicio
            service = service_type_crud.get(db, id=ticket.ServiceTypeId)

            result.append({
                "ticket_number": ticket.TicketNumber,
                "TicketNumber": ticket.TicketNumber,
                "position": ticket.Position,
                "service_name": service.Name if service else "",
                "service_code": service.Code if service else "",
                "estimated_wait": ticket.EstimatedWaitTime or 0
            })

        return result

    except Exception as e:
        logger.error(f"Error obteniendo tickets públicos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener tickets en espera"
        )


@router.get("/public/current-call", response_model=Dict[str, Any])
async def get_public_current_call(
    db: Session = Depends(get_db)
):
    """
    Obtiene el ticket actualmente siendo llamado - PÚBLICO

    Para uso en pantallas de display sin autenticación.
    Retorna el último ticket con estado 'Called' o 'InProgress'.
    """
    try:
        # Buscar el ticket más reciente que está siendo llamado o atendido
        current_ticket = db.query(Ticket).filter(
            Ticket.Status.in_(['Called', 'InProgress'])
        ).order_by(Ticket.CalledAt.desc()).first()

        if not current_ticket:
            return {
                "has_current": False,
                "ticket_id": None,
                "ticket_number": None,
                "station_name": None,
                "station_code": None,
                "service_name": None,
                "patient_name": None,
                "called_at": None
            }

        # Obtener información del servicio
        service = service_type_crud.get(db, id=current_ticket.ServiceTypeId)

        # Obtener información de la estación
        station_name = None
        station_code = None
        if current_ticket.StationId:
            station = station_crud.get(db, id=current_ticket.StationId)
            if station:
                station_name = station.Name
                station_code = station.Code

        # Obtener nombre del paciente (parcial por privacidad)
        patient_name = None
        if current_ticket.PatientId:
            from app.crud.patient import patient
            patient_obj = patient.get(db, patient_id=str(current_ticket.PatientId))
            if patient_obj and patient_obj.FullName:
                # Mostrar solo primer nombre + inicial del apellido
                names = patient_obj.FullName.split()
                if len(names) >= 2:
                    patient_name = f"{names[0]} {names[1][0]}."
                else:
                    patient_name = names[0] if names else None

        return {
            "has_current": True,
            "ticket_id": str(current_ticket.Id),
            "ticket_number": current_ticket.TicketNumber,
            "station_name": station_name,
            "station_code": station_code,
            "service_name": service.Name if service else None,
            "service_code": service.Code if service else None,
            "patient_name": patient_name,
            "status": current_ticket.Status,
            "called_at": current_ticket.CalledAt.isoformat() if current_ticket.CalledAt else None
        }

    except Exception as e:
        logger.error(f"Error obteniendo ticket actual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener ticket actual"
        )


# ========================================
# EXPORTS
# ========================================

__all__ = ["router"]