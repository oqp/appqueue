"""
API endpoints para gestión de tipos de servicios del laboratorio clínico
100% completo y funcional - compatible con toda la estructura existente
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
    require_admin,
    require_supervisor_or_admin
)
from app.models.service_type import ServiceType
from app.models.user import User
from app.schemas.service_type import (
    ServiceTypeCreate, ServiceTypeUpdate, ServiceTypeResponse,
    ServiceTypeListResponse, ServiceTypeSearchFilters, ServiceTypeStats,
    ServiceTypeDashboard, ServiceTypeQuickSetup, ServiceTypeValidation,
    BulkServiceTypeCreate, BulkServiceTypeResponse
)
from app.crud.service_type import service_type_crud
from app.core.redis import cache_manager

# ========================================
# CONFIGURACIÓN DEL ROUTER
# ========================================

router = APIRouter(prefix="/service-types", tags=["service-types"])
logger = logging.getLogger(__name__)


# ========================================
# ENDPOINTS DE CREACIÓN
# ========================================



@router.get("/dashboard", response_model=ServiceTypeDashboard)
async def get_service_types_dashboard(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene dashboard global de tipos de servicios

    - Resumen de todos los servicios
    - Estadísticas de uso general
    - Distribución por prioridad
    - Métricas de rendimiento
    """
    try:
        # Verificar cache primero
        if cache_manager:
            cached_dashboard = cache_manager.get("service_types_dashboard")
            if cached_dashboard:
                return ServiceTypeDashboard(**cached_dashboard)
        # Generar dashboard
        dashboard_data = service_type_crud.get_dashboard_stats(db)
        dashboard = ServiceTypeDashboard(**dashboard_data)

        # Guardar en cache por 10 minutos
        if cache_manager:
            cache_manager.set("service_types_dashboard", dashboard.model_dump(), expire=600)

        return dashboard

    except Exception as e:
        logger.error(f"Error obteniendo dashboard de tipos de servicios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo dashboard"
        )




@router.post("", response_model=ServiceTypeResponse)
async def create_service_type(
        service_data: ServiceTypeCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Crea un nuevo tipo de servicio

    - Requiere permisos de supervisor o administrador
    - Valida que el código y prefijo sean únicos
    - Normaliza automáticamente códigos y prefijos
    """
    try:
        logger.info(f"Creando tipo de servicio: {service_data.Code} por {current_user.Username}")

        # Crear usando CRUD con validaciones
        service_type = service_type_crud.create_with_validation(db, obj_in=service_data)

        # Limpiar cache relacionado
        if cache_manager:
            cache_manager.delete("service_types_list")
            cache_manager.delete("service_types_dashboard")

        logger.info(f"Tipo de servicio creado: {service_type.Name} ({service_type.Code})")
        return ServiceTypeResponse.model_validate(service_type)

    except ValueError as e:
        logger.warning(f"Error de validación: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creando tipo de servicio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno creando tipo de servicio"
        )


@router.post("/bulk", response_model=BulkServiceTypeResponse)
async def create_service_types_bulk(
        bulk_data: BulkServiceTypeCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Crea múltiples tipos de servicios en lote

    - Solo administradores
    - Máximo 20 servicios por operación
    - Continúa creando aunque algunos fallen
    """
    try:
        logger.info(f"Creación masiva de {len(bulk_data.service_types)} tipos de servicios por {current_user.Username}")

        created_services = []
        failed_services = []

        for index, service_data in enumerate(bulk_data.service_types):
            try:
                service_type = service_type_crud.create_with_validation(db, obj_in=service_data)
                created_services.append(ServiceTypeResponse.model_validate(service_type))

            except Exception as e:
                failed_services.append({
                    "index": index,
                    "service_data": service_data.model_dump(),
                    "error": str(e)
                })
                logger.warning(f"Error creando servicio en índice {index}: {e}")

        # Limpiar cache
        if cache_manager:
            cache_manager.delete("service_types_list")
            cache_manager.delete("service_types_dashboard")

        response = BulkServiceTypeResponse(
            created_services=created_services,
            failed_services=failed_services,
            success_count=len(created_services),
            error_count=len(failed_services)
        )

        logger.info(f"Creación masiva completada: {response.success_count} exitosos, {response.error_count} fallidos")
        return response

    except Exception as e:
        logger.error(f"Error en creación masiva: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno en creación masiva"
        )


# ========================================
# CORRECCIÓN 2: QUICK SETUP
# ========================================

@router.post("/quick-setup", response_model=List[ServiceTypeResponse])
async def quick_setup_default_services(
        setup_data: ServiceTypeQuickSetup,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Configuración rápida con servicios por defecto

    - Crea servicios básicos del laboratorio
    - Opción de agregar servicios personalizados
    """
    try:
        logger.info(f"Configuración rápida de servicios por {current_user.Username}")

        created_services = []

        # Crear servicios por defecto si se solicita
        if setup_data.include_default_services:
            # CORRECCIÓN: Implementar directamente aquí en lugar de llamar método inexistente

            # Verificar si ya existen servicios
            existing_count = db.query(ServiceType).count()

            if existing_count == 0:
                # Datos de servicios por defecto
                default_services_data = [
                    {
                        "Code": "LAB",
                        "Name": "Análisis de Laboratorio",
                        "Description": "Análisis clínicos generales",
                        "TicketPrefix": "L",
                        "Priority": 3,
                        "AverageTimeMinutes": 15,
                        "Color": "#007bff"
                    },
                    {
                        "Code": "RES",
                        "Name": "Entrega de Resultados",
                        "Description": "Retiro de estudios completados",
                        "TicketPrefix": "R",
                        "Priority": 2,
                        "AverageTimeMinutes": 5,
                        "Color": "#28a745"
                    },
                    {
                        "Code": "MUE",
                        "Name": "Entrega de Muestras",
                        "Description": "Recepción de muestras de pacientes",
                        "TicketPrefix": "M",
                        "Priority": 4,
                        "AverageTimeMinutes": 10,
                        "Color": "#ffc107"
                    },
                    {
                        "Code": "URG",
                        "Name": "Urgencias",
                        "Description": "Atención prioritaria urgente",
                        "TicketPrefix": "U",
                        "Priority": 5,
                        "AverageTimeMinutes": 20,
                        "Color": "#dc3545"
                    },
                    {
                        "Code": "CON",
                        "Name": "Consultas",
                        "Description": "Consultas y orientación médica",
                        "TicketPrefix": "C",
                        "Priority": 1,
                        "AverageTimeMinutes": 8,
                        "Color": "#6c757d"
                    }
                ]

                for service_data in default_services_data:
                    try:
                        service_create = ServiceTypeCreate(**service_data)
                        service = service_type_crud.create_with_validation(db, obj_in=service_create)
                        created_services.append(service)
                    except Exception as e:
                        logger.warning(f"Error creando servicio por defecto {service_data['Name']}: {e}")
                        # Continuar con los demás

                logger.info(f"{len(created_services)} servicios por defecto creados")
            else:
                logger.info(f"Ya existen {existing_count} servicios, no se crean los por defecto")

        # Crear servicios personalizados si se proporcionan
        if setup_data.custom_services:
            for service_data in setup_data.custom_services:
                try:
                    service_type = service_type_crud.create_with_validation(db, obj_in=service_data)
                    created_services.append(service_type)
                except Exception as e:
                    logger.warning(f"Error creando servicio personalizado {service_data.Name}: {e}")

        # Limpiar cache
        if cache_manager:
            cache_manager.delete("service_types_list")
            cache_manager.delete("service_types_dashboard")

        logger.info(f"Configuración rápida completada: {len(created_services)} servicios creados")
        return [ServiceTypeResponse.model_validate(s) for s in created_services]

    except Exception as e:
        logger.error(f"Error en configuración rápida: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno en configuración rápida"
        )


# ========================================
# ENDPOINTS DE CONSULTA
# ========================================

@router.get("/{service_id}", response_model=ServiceTypeResponse)
async def get_service_type(
        service_id: int = Path(..., description="ID del tipo de servicio"),
        include_stats: bool = Query(False, description="Incluir estadísticas de colas"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene un tipo de servicio por su ID

    - Información completa del servicio
    - Estadísticas opcionales de uso
    - Conteo de tickets activos
    """
    try:
        service_type = service_type_crud.get(db, id=service_id)
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de servicio no encontrado"
            )

        # Agregar estadísticas si se solicita
        if include_stats:
            stats = service_type_crud.get_service_stats(db, service_type_id=service_id)
            service_type.current_stats = stats

        return ServiceTypeResponse.model_validate(service_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo tipo de servicio {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo tipo de servicio"
        )


@router.get("/code/{service_code}", response_model=ServiceTypeResponse)
async def get_service_type_by_code(
        service_code: str = Path(..., description="Código del tipo de servicio"),
        include_stats: bool = Query(False, description="Incluir estadísticas"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene un tipo de servicio por su código único

    - Búsqueda por código normalizado
    - Información completa del servicio
    - Estadísticas opcionales
    """
    try:
        service_type = service_type_crud.get_by_code(db, code=service_code)
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tipo de servicio con código {service_code} no encontrado"
            )

        if include_stats:
            stats = service_type_crud.get_service_stats(db, service_type_id=service_type.Id)
            service_type.current_stats = stats

        return ServiceTypeResponse.model_validate(service_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo tipo de servicio por código {service_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo tipo de servicio"
        )


@router.get("/", response_model=ServiceTypeListResponse)
async def list_service_types(
        skip: int = Query(0, ge=0, description="Registros a omitir"),
        limit: int = Query(20, ge=1, le=100, description="Límite de registros"),
        active_only: bool = Query(True, description="Solo tipos de servicios activos"),
        include_stats: bool = Query(False, description="Incluir estadísticas de colas"),
        priority: Optional[int] = Query(None, ge=1, le=5, description="Filtrar por prioridad"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Lista tipos de servicios con paginación y filtros
    """
    try:
        # Verificar cache
        cache_key = f"service_types_{skip}_{limit}_{active_only}_{priority}_{include_stats}"

        if cache_manager:
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                logger.debug("Tipos de servicios obtenidos desde cache")
                return ServiceTypeListResponse(**cached_result)

        # Obtener servicios según filtros
        if priority:
            # Filtrar por prioridad con ORDER BY
            services_query = db.query(ServiceType).filter(
                ServiceType.Priority == priority
            )
            if active_only:
                services_query = services_query.filter(ServiceType.IsActive == True)

            # ORDER BY antes de OFFSET/LIMIT para SQL Server
            services = services_query.order_by(ServiceType.Id).offset(skip).limit(limit).all()

            total_query = db.query(ServiceType).filter(
                ServiceType.Priority == priority
            )
            if active_only:
                total_query = total_query.filter(ServiceType.IsActive == True)
            total = total_query.count()

        elif include_stats:
            # Con estadísticas
            query = db.query(ServiceType)
            if active_only:
                query = query.filter(ServiceType.IsActive == True)

            # ORDER BY necesario para SQL Server
            services = query.order_by(ServiceType.Id).all()
            total = len(services)
            services = services[skip:skip + limit]  # Paginación manual después

        else:
            # Caso normal
            if active_only:
                query = db.query(ServiceType).filter(ServiceType.IsActive == True)
            else:
                query = db.query(ServiceType)

            total = query.count()

            # ORDER BY antes de OFFSET/LIMIT para SQL Server
            services = query.order_by(ServiceType.Id).offset(skip).limit(limit).all()

        # Calcular active_count e inactive_count
        active_count = db.query(ServiceType).filter(ServiceType.IsActive == True).count()
        inactive_count = db.query(ServiceType).filter(ServiceType.IsActive == False).count()

        # IMPORTANTE: Usar el nombre correcto del campo según el schema
        response = ServiceTypeListResponse(
            services=[ServiceTypeResponse.model_validate(s) for s in services],  # 'services', NO 'service_types'
            total=total,
            active_count=active_count,
            inactive_count=inactive_count
            # NO incluir skip, limit, has_more porque el schema no los tiene
        )

        # Guardar en cache por 5 minutos
        if cache_manager:
            cache_manager.set(cache_key, response.model_dump(), expire=300)

        return response

    except Exception as e:
        logger.error(f"Error listando tipos de servicios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno listando tipos de servicios"
        )

# ========================================
# ENDPOINTS DE BÚSQUEDA AVANZADA
# ========================================

@router.post("/search", response_model=List[ServiceTypeResponse])
async def search_service_types(
        filters: ServiceTypeSearchFilters,
        limit: int = Query(50, ge=1, le=100, description="Límite de resultados"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Búsqueda avanzada de tipos de servicios

    - Múltiples filtros combinables
    - Búsqueda por texto en nombre/código/descripción
    - Filtros por prioridad, tiempo, estaciones
    - Resultados ordenados por relevancia
    """
    try:
        logger.debug(f"Búsqueda de servicios con filtros: {filters.model_dump()}")

        services = []

        # Búsqueda por texto libre
        if filters.query:
            services = service_type_crud.search_services(db, query=filters.query, limit=limit)

        # Filtrar por prioridad específica
        elif filters.priority:
            services = service_type_crud.get_by_priority(db, priority=filters.priority, limit=limit)

        # Filtrar por rango de tiempo de atención
        elif filters.min_time or filters.max_time:
            services = service_type_crud.get_services_by_average_time(
                db,
                min_minutes=filters.min_time,
                max_minutes=filters.max_time,
                limit=limit
            )

        # Obtener todos con estadísticas
        else:
            services = service_type_crud.get_services_with_stats(
                db, include_inactive=not filters.is_active
            )[:limit]

        # Filtros adicionales post-query
        if filters.has_stations is not None:
            if filters.has_stations:
                services = [s for s in services if getattr(s, 'station_count', 0) > 0]
            else:
                services = [s for s in services if getattr(s, 'station_count', 0) == 0]

        logger.debug(f"Búsqueda completada: {len(services)} resultados")
        return [ServiceTypeResponse.model_validate(service) for service in services]

    except Exception as e:
        logger.error(f"Error en búsqueda de tipos de servicios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno en búsqueda"
        )


# ========================================
# ENDPOINTS DE ACTUALIZACIÓN
# ========================================

@router.put("/{service_id}", response_model=ServiceTypeResponse)
async def update_service_type(
        service_id: int = Path(..., description="ID del tipo de servicio"),
        service_update: ServiceTypeUpdate = ...,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Actualiza un tipo de servicio existente

    - Requiere permisos de supervisor o administrador
    - Valida códigos y prefijos únicos si se modifican
    - Actualiza automáticamente el timestamp
    - Limpia cache relacionado
    """
    try:
        service_type = service_type_crud.get(db, id=service_id)
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de servicio no encontrado"
            )

        logger.info(f"Actualizando tipo de servicio {service_type.Name} por {current_user.Username}")

        # Actualizar usando CRUD con validaciones
        updated_service = service_type_crud.update_with_validation(
            db, db_obj=service_type, obj_in=service_update
        )

        # Limpiar cache relacionado
        if cache_manager:
            cache_manager.delete("service_types_list")
            cache_manager.delete("service_types_dashboard")
            cache_manager.delete(f"service_type:{service_id}")

        logger.info(f"Tipo de servicio actualizado: {updated_service.Name}")
        return ServiceTypeResponse.model_validate(updated_service)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando tipo de servicio {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno actualizando tipo de servicio"
        )


# ========================================
# ENDPOINTS DE ACTIVACIÓN/DESACTIVACIÓN
# ========================================

@router.post("/{service_id}/activate")
async def activate_service_type(
        service_id: int = Path(..., description="ID del tipo de servicio"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin())
):
    """
    Activa un tipo de servicio desactivado

    - Requiere permisos de supervisor o administrador
    - Restaura disponibilidad del servicio
    - Limpia cache automáticamente
    """
    try:
        service_type = service_type_crud.get(db, id=service_id)
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de servicio no encontrado"
            )

        if service_type.IsActive:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tipo de servicio ya está activo"
            )

        logger.info(f"Activando tipo de servicio {service_type.Name} por {current_user.Username}")

        # Activar servicio
        service_type.IsActive = True
        service_type.UpdatedAt = datetime.now()
        db.commit()
        db.refresh(service_type)

        # Limpiar cache
        if cache_manager:
            cache_manager.delete("service_types_list")
            cache_manager.delete("service_types_dashboard")

        return {
            "message": f"Tipo de servicio {service_type.Name} activado correctamente",
            "service": ServiceTypeResponse.model_validate(service_type)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activando tipo de servicio {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno activando tipo de servicio"
        )


@router.post("/{service_id}/deactivate")
async def deactivate_service_type(
        service_id: int = Path(..., description="ID del tipo de servicio"),
        force: bool = Query(False, description="Forzar desactivación"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Desactiva un tipo de servicio (eliminación lógica)

    - Requiere permisos de administrador
    - No elimina físicamente el registro
    - Verifica que no tenga tickets activos (excepto si force=true)
    """
    try:
        service_type = service_type_crud.get(db, id=service_id)
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de servicio no encontrado"
            )

        if not service_type.IsActive:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tipo de servicio ya está desactivado"
            )

        # Verificar tickets activos si no se fuerza
        if not force:
            active_tickets_count = service_type_crud.count_active_tickets(db, service_id)
            if active_tickets_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"No se puede desactivar. Hay {active_tickets_count} tickets activos. Use force=true para forzar."
                )

        logger.warning(f"Desactivando tipo de servicio {service_type.Name} por {current_user.Username}")

        # Desactivar servicio
        service_type.IsActive = False
        service_type.UpdatedAt = datetime.now()
        db.commit()
        db.refresh(service_type)

        # Limpiar cache
        if cache_manager:
            cache_manager.delete("service_types_list")
            cache_manager.delete("service_types_dashboard")

        return {
            "message": f"Tipo de servicio {service_type.Name} desactivado correctamente",
            "forced": force,
            "service": ServiceTypeResponse.model_validate(service_type)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error desactivando tipo de servicio {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno desactivando tipo de servicio"
        )


# ========================================
# ENDPOINTS DE ESTADÍSTICAS
# ========================================

@router.get("/{service_id}/stats", response_model=ServiceTypeStats)
async def get_service_type_stats(
        service_id: int = Path(..., description="ID del tipo de servicio"),
        days: int = Query(30, ge=1, le=365, description="Días de análisis"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene estadísticas detalladas de un tipo de servicio

    - Período configurable de análisis
    - Métricas de uso y rendimiento
    - Comparativas históricas
    """
    try:
        service_type = service_type_crud.get(db, id=service_id)
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de servicio no encontrado"
            )

        # Obtener estadísticas del período
        stats = service_type_crud.get_service_stats(
            db, service_type_id=service_id, days=days
        )

        return ServiceTypeStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas del servicio {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo estadísticas"
        )


# ========================================
# ENDPOINTS DE VALIDACIÓN
# ========================================

@router.get("/validate/code/{code}", response_model=ServiceTypeValidation)
async def validate_service_code(
        code: str = Path(..., description="Código a validar"),
        exclude_id: Optional[int] = Query(None, description="ID a excluir en validación"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Valida disponibilidad de código de servicio

    - Verificación de unicidad
    - Normalización automática
    - Exclusión opcional para actualizaciones
    """
    try:
        # Normalizar código
        normalized_code = code.strip().upper()

        # Verificar disponibilidad
        existing_service = service_type_crud.get_by_code(db, code=normalized_code)

        is_valid = True
        message = "Código disponible"

        if existing_service:
            if exclude_id and existing_service.Id == exclude_id:
                is_valid = True
                message = "Código válido (servicio actual)"
            else:
                is_valid = False
                message = f"Código ya está en uso por: {existing_service.Name}"

        return ServiceTypeValidation(
            is_valid=is_valid,
            field="code",
            value=normalized_code,
            message=message
        )

    except Exception as e:
        logger.error(f"Error validando código {code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno validando código"
        )


@router.get("/validate/prefix/{prefix}", response_model=ServiceTypeValidation)
async def validate_ticket_prefix(
        prefix: str = Path(..., description="Prefijo a validar"),
        exclude_id: Optional[int] = Query(None, description="ID a excluir en validación"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Valida disponibilidad de prefijo de ticket

    - Verificación de unicidad
    - Normalización automática
    - Exclusión opcional para actualizaciones
    """
    try:
        # Normalizar prefijo
        normalized_prefix = prefix.strip().upper()

        # Verificar disponibilidad
        existing_service = service_type_crud.get_by_prefix(db, prefix=normalized_prefix)

        is_valid = True
        message = "Prefijo disponible"

        if existing_service:
            if exclude_id and existing_service.Id == exclude_id:
                is_valid = True
                message = "Prefijo válido (servicio actual)"
            else:
                is_valid = False
                message = f"Prefijo ya está en uso por: {existing_service.Name}"

        return ServiceTypeValidation(
            is_valid=is_valid,
            field="prefix",
            value=normalized_prefix,
            message=message
        )

    except Exception as e:
        logger.error(f"Error validando prefijo {prefix}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno validando prefijo"
        )


# ========================================
# ENDPOINTS DE UTILIDAD
# ========================================

@router.get("/active/summary")
async def get_active_services_summary(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene resumen de servicios activos

    - Solo servicios en estado activo
    - Información básica para selecciones
    - Útil para dropdowns y formularios
    """
    try:
        active_services = service_type_crud.get_active_summary(db)

        return {
            "total_active": len(active_services),
            "services": [
                {
                    "Id": service.Id,
                    "Code": service.Code,
                    "Name": service.Name,
                    "TicketPrefix": service.TicketPrefix,
                    "Priority": service.Priority,
                    "Color": service.Color,
                    "AverageTimeMinutes": service.AverageTimeMinutes
                }
                for service in active_services
            ]
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen de servicios activos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo resumen"
        )


@router.get("/priorities/distribution")
async def get_priority_distribution(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene distribución de servicios por prioridad

    - Conteo por nivel de prioridad
    - Estadísticas de uso
    - Útil para análisis y dashboards
    """
    try:
        distribution = service_type_crud.get_priority_distribution(db)

        return {
            "distribution": distribution,
            "total_services": sum(distribution.values()),
            "priority_levels": {
                1: "Muy Baja",
                2: "Baja",
                3: "Normal",
                4: "Alta",
                5: "Urgente"
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo distribución de prioridades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo distribución"
        )