import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientWithQueueInfo,
    PatientSearch
)
from app.services.patient_service import patient_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientResponse)
def create_patient(
        patient: PatientCreate,
        db: Session = Depends(get_db)
):
    """
    Crear un nuevo paciente
    """
    try:
        # Detectar intentos de SQL injection
        if any(char in patient.document_number for char in [';', '--', 'DROP', 'DELETE']):
            raise HTTPException(
                status_code=400,
                detail="Caracteres no permitidos en el documento"
            )

        created = patient_service.create_patient(db, patient)
        return PatientResponse.from_orm(created)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[PatientResponse])
def get_patients(
        skip: int = Query(0, ge=0, description="Número de registros a saltar"),
        limit: int = Query(100, ge=1, le=100, description="Límite de registros a retornar"),
        search: Optional[str] = Query(None, description="Búsqueda por nombre o documento"),
        is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
        db: Session = Depends(get_db)
):
    """
    Obtener lista de pacientes con paginación y filtros
    """
    patients = patient_service.get_patients(db, skip, limit, search, is_active)
    return [PatientResponse.from_orm(p) for p in patients]


@router.get("/search", response_model=List[PatientSearch])
def search_patients(
        q: str = Query(..., min_length=2, description="Término de búsqueda"),
        limit: int = Query(10, ge=1, le=50, description="Límite de resultados"),
        db: Session = Depends(get_db)
):
    """
    Búsqueda rápida de pacientes para autocompletado
    """
    patients = patient_service.search_patients(db, q, limit)
    return [PatientSearch.from_orm(p) for p in patients]


@router.get("/document/{document_number}", response_model=PatientResponse)
async def get_patient_by_document(
        document_number: str,
        db: Session = Depends(get_db)
):
    """
    Obtener paciente por número de documento.
    Primero busca en BD local, si no encuentra consulta el servicio externo de DNI.
    """
    try:
        patient = await patient_service.get_or_create_by_document(db, document_number)
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró información para el documento {document_number}"
            )
        return PatientResponse.from_orm(patient)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error al procesar la solicitud: {str(e)}"
        )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
        patient_id: str,  # Cambiado a str porque usa GUID
        db: Session = Depends(get_db)
):
    # Validar formato UUID
    try:
        uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Paciente con ID {patient_id} no encontrado"
        )

    """
    Obtener un paciente específico por ID
    """
    patient = patient_service.get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f"Paciente con ID {patient_id} no encontrado"
        )
    return PatientResponse.from_orm(patient)


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
        patient_id: str,  # Cambiado a str porque usa GUID
        patient_update: PatientUpdate,
        db: Session = Depends(get_db)
):
    """
    Actualizar información de un paciente
    """
    try:
        updated = patient_service.update_patient(db, patient_id, patient_update)
        return PatientResponse.from_orm(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=400 if "documento" in str(e).lower() else 404,
            detail=str(e)
        )


@router.delete("/{patient_id}")
def delete_patient(
        patient_id: str,  # Cambiado a str porque usa GUID
        db: Session = Depends(get_db)
):
    """
    Eliminar un paciente (soft delete)
    """
    if not patient_service.delete_patient(db, patient_id):
        raise HTTPException(
            status_code=404,
            detail=f"Paciente con ID {patient_id} no encontrado"
        )

    return {"message": f"Paciente {patient_id} eliminado exitosamente"}


def get_patient_queue_stats(
        self,
        db: Session,
        patient_id: str,
        include_history: bool = False
) -> dict:
    """
    Obtiene estadísticas de cola del paciente

    Args:
        db: Sesión de base de datos
        patient_id: ID del paciente (GUID)
        include_history: Si incluir historial completo

    Returns:
        Diccionario con estadísticas
    """
    from app.models.ticket import Ticket
    from app.models.service_type import ServiceType
    from app.schemas.ticket import TicketStatus
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload

    patient = crud_patient.get(db, patient_id)
    if not patient:
        raise ValueError(f"Paciente con ID {patient_id} no encontrado")

    # Obtener tickets activos con la relación service_type cargada
    active_tickets = db.query(Ticket).options(
        joinedload(Ticket.service_type)  # Cargar la relación ServiceType
    ).filter(
        Ticket.PatientId == patient_id,
        Ticket.Status.in_(['Waiting', 'Called', 'InProgress'])
    ).all()

    stats = {
        "patient": patient,
        "active_tickets_count": len(active_tickets),
        "active_tickets": active_tickets,
        "current_ticket": None
    }

    # Obtener el ticket más reciente si existe
    if active_tickets:
        # Ordenar por fecha de creación y tomar el más reciente
        stats["current_ticket"] = max(
            active_tickets,
            key=lambda x: x.CreatedAt if hasattr(x, 'CreatedAt') else x.created_at
        )

    if include_history:
        # Obtener historial de tickets (últimos 30)
        recent_tickets = db.query(Ticket).options(
            joinedload(Ticket.service_type)
        ).filter(
            Ticket.PatientId == patient_id
        ).order_by(
            Ticket.CreatedAt.desc()
        ).limit(30).all()

        stats["history"] = recent_tickets[:10]
        stats["total_visits"] = db.query(func.count(Ticket.Id)).filter(
            Ticket.PatientId == patient_id
        ).scalar()

    return stats


@router.get("/{patient_id}/queue-info", response_model=PatientWithQueueInfo)
def get_patient_with_queue_info(
        patient_id: str,  # GUID string
        include_history: bool = Query(False, description="Incluir historial de visitas"),
        db: Session = Depends(get_db)
):
    """
    Obtener información del paciente con datos de su posición en cola

    Retorna:
    - Información completa del paciente
    - Cantidad de tickets activos
    - Información del ticket actual si existe
    - Historial de visitas (opcional)
    """
    try:
        # Obtener estadísticas del paciente
        stats = patient_service.get_patient_queue_stats(db, patient_id, include_history)

        # Construir respuesta
        patient = stats["patient"]

        # Extraer nombres del FullName
        full_name_parts = patient.FullName.split() if patient.FullName else []
        first_name = full_name_parts[0] if full_name_parts else ""
        last_name = " ".join(full_name_parts[1:]) if len(full_name_parts) > 1 else ""

        response_dict = {
            "id": str(patient.Id),
            "document_type": "DNI",
            "document_number": patient.DocumentNumber,
            "full_name": patient.FullName,
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": patient.BirthDate,
            "gender": patient.Gender,
            "email": patient.Email,
            "phone": patient.Phone,
            "age": getattr(patient, 'Age', None),
            "is_active": patient.IsActive,
            "created_at": getattr(patient, 'created_at', getattr(patient, 'CreatedAt', None)),
            "updated_at": getattr(patient, 'updated_at', getattr(patient, 'UpdatedAt', None)),
            "active_tickets": stats["active_tickets_count"],
            "current_ticket": None
        }

        # Agregar información del ticket actual si existe
        if stats["current_ticket"]:
            ticket = stats["current_ticket"]

            # Extraer información del ServiceType de forma segura
            service_name = None
            service_code = None
            if hasattr(ticket, 'service_type') and ticket.service_type:
                service_name = getattr(ticket.service_type, 'Name', None)
                service_code = getattr(ticket.service_type, 'Code', None)

            response_dict["current_ticket"] = {
                "ticket_number": getattr(ticket, 'TicketNumber', None),
                "status": getattr(ticket, 'Status', None),
                "service_name": service_name,
                "service_code": service_code,
                "created_at": getattr(ticket, 'CreatedAt', getattr(ticket, 'created_at', None))
            }

        # Agregar historial si se solicitó
        if include_history and "total_visits" in stats:
            response_dict["total_visits"] = stats["total_visits"]

            # Obtener última visita del historial
            if "history" in stats and stats["history"]:
                last_ticket = stats["history"][0]
                response_dict["last_visit"] = getattr(
                    last_ticket,
                    'CreatedAt',
                    getattr(last_ticket, 'created_at', None)
                )

        return PatientWithQueueInfo(**response_dict)

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error en queue-info para paciente {patient_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error interno al obtener información del paciente"
        )

@router.post("/bulk-create", response_model=List[PatientResponse])
def bulk_create_patients(
        patients: List[PatientCreate] = Body(..., description="Lista de pacientes a crear"),
        db: Session = Depends(get_db)
):
    """
    Crear múltiples pacientes en una sola operación
    """
    created_patients, errors = patient_service.bulk_create_patients(db, patients)

    if errors:
        raise HTTPException(
            status_code=207,  # Multi-Status
            detail={
                "created": len(created_patients),
                "errors": errors
            }
        )

    return [PatientResponse.from_orm(p) for p in created_patients]