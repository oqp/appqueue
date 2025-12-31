"""
API endpoints para gestión de estaciones/ventanillas del laboratorio clínico
Versión simplificada y corregida para funcionar con la estructura real de BD
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.api.dependencies.auth import (
    get_current_user,
    require_admin,
    require_supervisor_or_admin
)
from app.models.station import Station
from app.models.user import User
from app.schemas.station import (
    StationCreate, StationUpdate, StationResponse, StationListResponse
)
from app.crud.station import station_crud

# ========================================
# CONFIGURACIÓN DEL ROUTER
# ========================================

router = APIRouter(prefix="/stations", tags=["stations"])
logger = logging.getLogger(__name__)


# ========================================
# ENDPOINTS CRUD BÁSICOS
# ========================================

# IMPORTANTE: Rutas específicas ANTES que rutas con parámetros

@router.get("/available", response_model=List[StationResponse])
async def get_available_stations(
        service_type_id: Optional[int] = Query(None, description="Filtrar por tipo de servicio"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las estaciones disponibles
    """
    try:
        stations = Station.get_available_stations(db, service_type_id)

        return [_station_to_response(station) for station in stations]

    except Exception as e:
        logger.error(f"Error obteniendo estaciones disponibles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo estaciones disponibles"
        )


@router.get("/by-code/{code}", response_model=StationResponse)
async def get_station_by_code(
        code: str = Path(..., description="Código de la estación"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene una estación por su código
    """
    try:
        station = Station.get_by_code(db, code)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Estación con código {code} no encontrada"
            )

        return _station_to_response(station)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estación por código {code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo estación"
        )


@router.post("", response_model=StationResponse, status_code=status.HTTP_201_CREATED)
async def create_station(
        station_data: StationCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Crea una nueva estación/ventanilla

    - Requiere permisos de administrador
    - Validación de código único
    """
    try:
        logger.info(f"Creando estación: {station_data.Name} por {current_user.Username}")

        # Verificar si el código ya existe
        existing = db.query(Station).filter(Station.Code == station_data.Code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El código {station_data.Code} ya está en uso"
            )

        # Crear la estación
        station = station_crud.create(db, obj_in=station_data)

        # Convertir a respuesta
        return _station_to_response(station)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando estación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno creando estación"
        )


@router.get("", response_model=StationListResponse)
async def list_stations(
        skip: int = Query(0, ge=0, description="Registros a saltar"),
        limit: int = Query(100, ge=1, le=100, description="Límite de registros"),
        only_active: bool = Query(False, description="Solo estaciones activas"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Lista todas las estaciones con filtros opcionales

    - Paginación incluida
    - Filtros por estado activo
    """
    try:
        # Construir query base
        query = db.query(Station)

        # Aplicar filtro de activos si es necesario
        if only_active:
            query = query.filter(Station.IsActive == True)

        # Obtener total antes de paginar
        total = query.count()

        # Aplicar ordenamiento (requerido por SQL Server para paginación)
        query = query.order_by(Station.Id.desc())

        # Aplicar paginación
        stations = query.offset(skip).limit(limit).all()

        # Convertir estaciones a respuesta
        station_responses = [_station_to_response(station) for station in stations]

        # Calcular valores de paginación
        current_page = (skip // limit) + 1 if limit > 0 else 1
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        return StationListResponse(
            Stations=station_responses,
            Total=total,
            Page=current_page,
            PageSize=limit,
            TotalPages=total_pages,
            HasNext=(skip + limit) < total,
            HasPrev=skip > 0
        )

    except Exception as e:
        logger.error(f"Error listando estaciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno listando estaciones"
        )


@router.get("/{station_id}", response_model=StationResponse)
async def get_station(
        station_id: int = Path(..., description="ID de la estación"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene información detallada de una estación
    """
    try:
        station = station_crud.get(db, id=station_id)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estación no encontrada"
            )

        return _station_to_response(station)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estación {station_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo estación"
        )


@router.put("/{station_id}", response_model=StationResponse)
async def update_station(
        station_id: int = Path(..., description="ID de la estación"),
        station_update: StationUpdate = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Actualiza una estación existente

    - Requiere permisos de supervisor o administrador
    """
    try:
        station = station_crud.get(db, id=station_id)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estación no encontrada"
            )

        # Actualizar la estación
        station = station_crud.update(db, db_obj=station, obj_in=station_update)

        logger.info(f"Estación {station.Code} actualizada por {current_user.Username}")

        return _station_to_response(station)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando estación {station_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno actualizando estación"
        )


@router.delete("/{station_id}")
async def delete_station(
        station_id: int = Path(..., description="ID de la estación"),
        soft_delete: bool = Query(True, description="Eliminación lógica"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Elimina una estación (lógica o físicamente)

    - Requiere permisos de administrador
    - Por defecto hace eliminación lógica (IsActive = False)
    """
    try:
        station = station_crud.get(db, id=station_id)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estación no encontrada"
            )

        if soft_delete:
            # Eliminación lógica
            station.IsActive = False
            db.commit()
            message = f"Estación {station.Code} desactivada"
        else:
            # Eliminación física
            station_crud.remove(db, id=station_id)
            message = f"Estación {station.Code} eliminada permanentemente"

        logger.info(f"{message} por {current_user.Username}")

        return {"message": message, "success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando estación {station_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno eliminando estación"
        )


@router.patch("/{station_id}/status")
async def update_station_status(
        station_id: int = Path(..., description="ID de la estación"),
        new_status: str = Body(..., embed=True),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Actualiza el estado de una estación

    Estados válidos: Available, Busy, Break, Maintenance, Offline
    """
    try:
        valid_statuses = ['Available', 'Busy', 'Break', 'Maintenance', 'Offline']

        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido. Estados válidos: {', '.join(valid_statuses)}"
            )

        station = station_crud.get(db, id=station_id)
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Estación no encontrada"
            )

        # Actualizar estado
        station.Status = new_status
        station.UpdatedAt = datetime.utcnow()
        db.commit()
        db.refresh(station)

        logger.info(f"Estado de estación {station.Code} cambiado a {new_status} por {current_user.Username}")

        return _station_to_response(station)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando estado de estación {station_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno actualizando estado"
        )


# ========================================
# FUNCIONES AUXILIARES
# ========================================

def _station_to_response(station: Station) -> StationResponse:
    """
    Convierte un modelo Station a StationResponse
    """
    try:
        # Preparar datos básicos que coinciden con la BD
        response_data = {
            "Id": station.Id,
            "Name": station.Name,
            "Code": station.Code,
            "Description": station.Description,
            "ServiceTypeId": station.ServiceTypeId,
            "Location": station.Location,
            "Status": station.Status,
            "CurrentTicketId": str(station.CurrentTicketId) if station.CurrentTicketId else None,
            "IsActive": station.IsActive,
            "CreatedAt": station.CreatedAt,
            "UpdatedAt": station.UpdatedAt
        }

        # Agregar información del tipo de servicio si existe y está cargada
        if hasattr(station, 'service_type') and station.service_type:
            response_data["ServiceTypeName"] = station.service_type.Name
        else:
            response_data["ServiceTypeName"] = None

        # Agregar información del ticket actual si existe y está cargado
        if hasattr(station, 'current_ticket') and station.current_ticket:
            response_data["CurrentTicketNumber"] = station.current_ticket.TicketNumber
        else:
            response_data["CurrentTicketNumber"] = None

        # Agregar usuarios asignados si la relación está cargada
        if hasattr(station, 'users'):
            try:
                users = station.users.all() if hasattr(station.users, 'all') else []
                response_data["AssignedUsers"] = [
                    {"Id": str(user.Id), "Username": user.Username, "FullName": user.FullName}
                    for user in users
                ]
            except:
                response_data["AssignedUsers"] = []
        else:
            response_data["AssignedUsers"] = []

        return StationResponse(**response_data)

    except Exception as e:
        logger.error(f"Error convirtiendo station a response: {e}")
        logger.error(f"Station data: {station.__dict__ if station else 'None'}")
        raise