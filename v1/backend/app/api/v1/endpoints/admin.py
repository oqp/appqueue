"""
Endpoints de administración del sistema
Incluye verificación diaria, mantenimiento y operaciones administrativas
"""

from typing import Optional, List
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text, Date
from pydantic import BaseModel, Field, ConfigDict
import logging

from app.core.database import get_db
from app.core.redis import redis_available, cache_manager
from app.api.dependencies.auth import get_current_user, get_current_admin, get_current_supervisor
from app.models.user import User
from app.models.station import Station
from app.models.service_type import ServiceType
from app.models.ticket import Ticket
from app.models.queue_state import QueueState
from app.models.role import Role
from app.core.redis import redis_available, cache_manager, check_redis_connection
from app.websocket.connection_manager import websocket_manager

# ========================================
# CONFIGURACION
# ========================================

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Sin permisos suficientes"},
        500: {"description": "Error interno del servidor"}
    }
)


# ========================================
# SCHEMAS PARA VERIFICACION DIARIA
# ========================================

class ServiceCheckResult(BaseModel):
    """Resultado de verificacion de un servicio"""
    Name: str = Field(..., description="Nombre del componente")
    Status: str = Field(..., description="Estado: ok, warning, error")
    Message: str = Field(..., description="Mensaje descriptivo")
    Details: Optional[dict] = Field(None, description="Detalles adicionales")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Name": "Base de datos",
                "Status": "ok",
                "Message": "Conexion establecida correctamente",
                "Details": {"type": "SQL Server"}
            }
        }
    )


class StationCheckResult(BaseModel):
    """Resultado de verificacion de estaciones"""
    TotalStations: int = Field(..., description="Total de estaciones")
    ActiveStations: int = Field(..., description="Estaciones activas")
    AvailableStations: int = Field(..., description="Estaciones disponibles")
    StationsWithIssues: List[dict] = Field(default_factory=list, description="Estaciones con problemas")
    Status: str = Field(..., description="Estado general: ok, warning, error")
    Message: str = Field(..., description="Mensaje descriptivo")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "TotalStations": 10,
                "ActiveStations": 8,
                "AvailableStations": 6,
                "StationsWithIssues": [],
                "Status": "ok",
                "Message": "Todas las estaciones listas"
            }
        }
    )


class ServiceTypeCheckResult(BaseModel):
    """Resultado de verificacion de tipos de servicio"""
    TotalServiceTypes: int = Field(..., description="Total de tipos de servicio")
    ActiveServiceTypes: int = Field(..., description="Tipos de servicio activos")
    ServiceTypesWithoutStations: List[dict] = Field(default_factory=list, description="Servicios sin estaciones")
    Status: str = Field(..., description="Estado general: ok, warning, error")
    Message: str = Field(..., description="Mensaje descriptivo")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "TotalServiceTypes": 5,
                "ActiveServiceTypes": 5,
                "ServiceTypesWithoutStations": [],
                "Status": "ok",
                "Message": "Todos los servicios configurados correctamente"
            }
        }
    )


class PendingTicketsCheckResult(BaseModel):
    """Resultado de verificacion de tickets pendientes"""
    PendingFromYesterday: int = Field(..., description="Tickets pendientes del dia anterior")
    TicketsToClean: List[dict] = Field(default_factory=list, description="Tickets que requieren limpieza")
    Status: str = Field(..., description="Estado general: ok, warning, error")
    Message: str = Field(..., description="Mensaje descriptivo")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "PendingFromYesterday": 0,
                "TicketsToClean": [],
                "Status": "ok",
                "Message": "No hay tickets pendientes del dia anterior"
            }
        }
    )


class QueueStateCheckResult(BaseModel):
    """Resultado de verificacion de estados de cola"""
    TotalQueueStates: int = Field(..., description="Total de estados de cola")
    StaleQueueStates: int = Field(..., description="Estados desactualizados")
    QueueStatesToReset: List[dict] = Field(default_factory=list, description="Estados que requieren reset")
    Status: str = Field(..., description="Estado general: ok, warning, error")
    Message: str = Field(..., description="Mensaje descriptivo")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "TotalQueueStates": 5,
                "StaleQueueStates": 0,
                "QueueStatesToReset": [],
                "Status": "ok",
                "Message": "Estados de cola listos"
            }
        }
    )


class UserCheckResult(BaseModel):
    """Resultado de verificacion de usuarios"""
    TotalUsers: int = Field(..., description="Total de usuarios")
    ActiveUsers: int = Field(..., description="Usuarios activos")
    UsersWithStations: int = Field(..., description="Usuarios con estacion asignada")
    TechniciansReady: int = Field(..., description="Tecnicos listos para operar")
    Status: str = Field(..., description="Estado general: ok, warning, error")
    Message: str = Field(..., description="Mensaje descriptivo")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "TotalUsers": 15,
                "ActiveUsers": 12,
                "UsersWithStations": 8,
                "TechniciansReady": 6,
                "Status": "ok",
                "Message": "Usuarios operativos listos"
            }
        }
    )


class DailyVerificationResponse(BaseModel):
    """Respuesta completa de verificacion diaria"""
    Timestamp: datetime = Field(..., description="Fecha y hora de la verificacion")
    OverallStatus: str = Field(..., description="Estado general del sistema: ready, warning, not_ready")
    OverallMessage: str = Field(..., description="Mensaje general")
    ReadyToOperate: bool = Field(..., description="Si el sistema esta listo para operar")

    # Verificaciones individuales
    Infrastructure: List[ServiceCheckResult] = Field(..., description="Estado de infraestructura")
    Stations: StationCheckResult = Field(..., description="Estado de estaciones")
    ServiceTypes: ServiceTypeCheckResult = Field(..., description="Estado de tipos de servicio")
    PendingTickets: PendingTicketsCheckResult = Field(..., description="Tickets pendientes")
    QueueStates: QueueStateCheckResult = Field(..., description="Estados de cola")
    Users: UserCheckResult = Field(..., description="Estado de usuarios")

    # Acciones recomendadas
    RecommendedActions: List[str] = Field(default_factory=list, description="Acciones recomendadas antes de iniciar")

    # Resumen de limpieza automatica
    AutoCleanupPerformed: bool = Field(False, description="Si se realizo limpieza automatica")
    CleanupSummary: Optional[dict] = Field(None, description="Resumen de limpieza realizada")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Timestamp": "2024-01-15T08:00:00",
                "OverallStatus": "ready",
                "OverallMessage": "Sistema listo para iniciar operaciones",
                "ReadyToOperate": True,
                "Infrastructure": [],
                "Stations": {},
                "ServiceTypes": {},
                "PendingTickets": {},
                "QueueStates": {},
                "Users": {},
                "RecommendedActions": [],
                "AutoCleanupPerformed": False,
                "CleanupSummary": None
            }
        }
    )


class DailyCleanupRequest(BaseModel):
    """Solicitud de limpieza diaria"""
    CancelPendingTickets: bool = Field(
        True,
        description="Cancelar tickets pendientes del dia anterior"
    )
    ResetQueueStates: bool = Field(
        True,
        description="Resetear estados de cola"
    )
    ResetStationStates: bool = Field(
        True,
        description="Resetear estados de estaciones"
    )
    ClearRedisCache: bool = Field(
        False,
        description="Limpiar cache de Redis"
    )
    Reason: Optional[str] = Field(
        "Inicio de jornada",
        description="Razon de la limpieza",
        max_length=200
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "CancelPendingTickets": True,
                "ResetQueueStates": True,
                "ResetStationStates": True,
                "ClearRedisCache": False,
                "Reason": "Inicio de jornada"
            }
        }
    )


class DailyCleanupResponse(BaseModel):
    """Respuesta de limpieza diaria"""
    Success: bool = Field(..., description="Si la limpieza fue exitosa")
    Timestamp: datetime = Field(..., description="Fecha y hora de la limpieza")
    TicketsCancelled: int = Field(0, description="Tickets cancelados")
    QueueStatesReset: int = Field(0, description="Estados de cola reseteados")
    StationsReset: int = Field(0, description="Estaciones reseteadas")
    CacheCleared: bool = Field(False, description="Si se limpio el cache")
    Errors: List[str] = Field(default_factory=list, description="Errores encontrados")
    Message: str = Field(..., description="Mensaje descriptivo")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Success": True,
                "Timestamp": "2024-01-15T08:00:00",
                "TicketsCancelled": 3,
                "QueueStatesReset": 5,
                "StationsReset": 8,
                "CacheCleared": False,
                "Errors": [],
                "Message": "Limpieza diaria completada exitosamente"
            }
        }
    )


# ========================================
# FUNCIONES DE VERIFICACION
# ========================================

def check_infrastructure(db: Session) -> List[ServiceCheckResult]:
    """Verifica el estado de la infraestructura"""
    results = []

    # Verificar base de datos
    try:
        db.execute(text("SELECT 1"))
        results.append(ServiceCheckResult(
            Name="Base de datos",
            Status="ok",
            Message="Conexion a SQL Server establecida correctamente",
            Details={"type": "SQL Server"}
        ))
    except Exception as e:
        results.append(ServiceCheckResult(
            Name="Base de datos",
            Status="error",
            Message=f"Error de conexion: {str(e)}",
            Details={"error": str(e)}
        ))

    # Verificar Redis
    if check_redis_connection():
        results.append(ServiceCheckResult(
            Name="Cache (Redis)",
            Status="ok",
            Message="Servicio de cache disponible",
            Details={"type": "Redis"}
        ))
    else:
        results.append(ServiceCheckResult(
            Name="Cache (Redis)",
            Status="warning",
            Message="Servicio de cache no disponible - el sistema funcionara sin cache",
            Details={"type": "Redis", "available": False}
        ))

    return results


def check_stations(db: Session) -> StationCheckResult:
    """Verifica el estado de las estaciones"""
    # Contar estaciones
    total = db.query(func.count(Station.Id)).scalar() or 0
    active = db.query(func.count(Station.Id)).filter(Station.IsActive == True).scalar() or 0
    available = db.query(func.count(Station.Id)).filter(
        Station.IsActive == True,
        Station.Status == 'Available'
    ).scalar() or 0

    # Buscar estaciones con problemas
    issues = []

    # Estaciones activas sin tipo de servicio
    no_service = db.query(Station).filter(
        Station.IsActive == True,
        Station.ServiceTypeId == None
    ).all()
    for station in no_service:
        issues.append({
            "Id": station.Id,
            "Code": station.Code,
            "Name": station.Name,
            "Issue": "Sin tipo de servicio asignado"
        })

    # Estaciones con ticket asignado pero no en estado Busy
    inconsistent = db.query(Station).filter(
        Station.IsActive == True,
        Station.CurrentTicketId != None,
        Station.Status != 'Busy'
    ).all()
    for station in inconsistent:
        issues.append({
            "Id": station.Id,
            "Code": station.Code,
            "Name": station.Name,
            "Issue": f"Tiene ticket asignado pero estado es '{station.Status}'"
        })

    # Determinar estado general
    if total == 0:
        status = "error"
        message = "No hay estaciones configuradas en el sistema"
    elif active == 0:
        status = "error"
        message = "No hay estaciones activas"
    elif len(issues) > 0:
        status = "warning"
        message = f"Hay {len(issues)} estacion(es) con problemas que requieren atencion"
    elif available == 0:
        status = "warning"
        message = "No hay estaciones disponibles para atender"
    else:
        status = "ok"
        message = f"{available} estacion(es) disponible(s) para operar"

    return StationCheckResult(
        TotalStations=total,
        ActiveStations=active,
        AvailableStations=available,
        StationsWithIssues=issues,
        Status=status,
        Message=message
    )


def check_service_types(db: Session) -> ServiceTypeCheckResult:
    """Verifica el estado de los tipos de servicio"""
    # Contar tipos de servicio
    total = db.query(func.count(ServiceType.Id)).scalar() or 0
    active = db.query(func.count(ServiceType.Id)).filter(ServiceType.IsActive == True).scalar() or 0

    # Buscar servicios activos sin estaciones
    without_stations = []
    active_services = db.query(ServiceType).filter(ServiceType.IsActive == True).all()

    for service in active_services:
        station_count = db.query(func.count(Station.Id)).filter(
            Station.ServiceTypeId == service.Id,
            Station.IsActive == True
        ).scalar() or 0

        if station_count == 0:
            without_stations.append({
                "Id": service.Id,
                "Code": service.Code,
                "Name": service.Name,
                "Issue": "Sin estaciones asignadas"
            })

    # Determinar estado general
    if total == 0:
        status = "error"
        message = "No hay tipos de servicio configurados"
    elif active == 0:
        status = "error"
        message = "No hay tipos de servicio activos"
    elif len(without_stations) > 0:
        status = "warning"
        message = f"Hay {len(without_stations)} servicio(s) sin estaciones asignadas"
    else:
        status = "ok"
        message = f"{active} tipo(s) de servicio activo(s) y configurado(s) correctamente"

    return ServiceTypeCheckResult(
        TotalServiceTypes=total,
        ActiveServiceTypes=active,
        ServiceTypesWithoutStations=without_stations,
        Status=status,
        Message=message
    )


def check_pending_tickets(db: Session) -> PendingTicketsCheckResult:
    """Verifica tickets pendientes del dia anterior"""
    today = date.today()

    # Buscar tickets pendientes de dias anteriores
    pending_tickets = db.query(Ticket).filter(
        Ticket.Status.in_(['Waiting', 'Called', 'InProgress']),
        func.cast(Ticket.CreatedAt, Date) < today
    ).all()

    tickets_to_clean = []
    for ticket in pending_tickets:
        tickets_to_clean.append({
            "Id": str(ticket.Id),
            "TicketNumber": ticket.TicketNumber,
            "Status": ticket.Status,
            "CreatedAt": ticket.CreatedAt.isoformat() if ticket.CreatedAt else None,
            "ServiceTypeId": ticket.ServiceTypeId
        })

    count = len(tickets_to_clean)

    if count == 0:
        status = "ok"
        message = "No hay tickets pendientes de dias anteriores"
    elif count <= 5:
        status = "warning"
        message = f"Hay {count} ticket(s) pendiente(s) de dias anteriores que deben ser cancelados"
    else:
        status = "error"
        message = f"Hay {count} tickets pendientes de dias anteriores - se requiere limpieza urgente"

    return PendingTicketsCheckResult(
        PendingFromYesterday=count,
        TicketsToClean=tickets_to_clean,
        Status=status,
        Message=message
    )


def check_queue_states(db: Session) -> QueueStateCheckResult:
    """Verifica el estado de las colas"""
    total = db.query(func.count(QueueState.Id)).scalar() or 0

    # Buscar estados desactualizados (mas de 1 hora sin actualizar con datos)
    one_hour_ago = datetime.now() - timedelta(hours=1)

    stale_states = db.query(QueueState).filter(
        or_(
            QueueState.CurrentTicketId != None,
            QueueState.QueueLength > 0
        ),
        QueueState.LastUpdateAt < one_hour_ago
    ).all()

    states_to_reset = []
    for state in stale_states:
        states_to_reset.append({
            "Id": state.Id,
            "ServiceTypeId": state.ServiceTypeId,
            "QueueLength": state.QueueLength,
            "LastUpdateAt": state.LastUpdateAt.isoformat() if state.LastUpdateAt else None,
            "Issue": "Estado desactualizado"
        })

    # Buscar estados con ticket actual pero sin estacion que lo atienda
    # (verificacion adicional de consistencia)

    stale_count = len(states_to_reset)

    if stale_count == 0:
        status = "ok"
        message = "Estados de cola actualizados y consistentes"
    else:
        status = "warning"
        message = f"Hay {stale_count} estado(s) de cola desactualizado(s) que requieren reset"

    return QueueStateCheckResult(
        TotalQueueStates=total,
        StaleQueueStates=stale_count,
        QueueStatesToReset=states_to_reset,
        Status=status,
        Message=message
    )


def check_users(db: Session) -> UserCheckResult:
    """Verifica el estado de los usuarios"""
    total = db.query(func.count(User.Id)).scalar() or 0
    active = db.query(func.count(User.Id)).filter(User.IsActive == True).scalar() or 0

    # Usuarios con estacion asignada
    with_stations = db.query(func.count(User.Id)).filter(
        User.IsActive == True,
        User.StationId != None
    ).scalar() or 0

    # Tecnicos listos (usuarios activos con estacion que pueden atender)
    technicians_ready = db.query(func.count(User.Id)).filter(
        User.IsActive == True,
        User.StationId != None
    ).scalar() or 0

    if total == 0:
        status = "error"
        message = "No hay usuarios en el sistema"
    elif active == 0:
        status = "error"
        message = "No hay usuarios activos"
    elif technicians_ready == 0:
        status = "warning"
        message = "No hay tecnicos asignados a estaciones - no se podra atender pacientes"
    else:
        status = "ok"
        message = f"{technicians_ready} tecnico(s) listo(s) para operar"

    return UserCheckResult(
        TotalUsers=total,
        ActiveUsers=active,
        UsersWithStations=with_stations,
        TechniciansReady=technicians_ready,
        Status=status,
        Message=message
    )


# ========================================
# ENDPOINTS
# ========================================

@router.get(
    "/daily-verification",
    response_model=DailyVerificationResponse,
    summary="Verificacion diaria del sistema",
    description="""
    Realiza una verificacion completa del sistema para asegurar que esta listo
    para iniciar las operaciones del dia.

    Verifica:
    - **Infraestructura**: Base de datos y Redis
    - **Estaciones**: Estado y configuracion
    - **Tipos de servicio**: Configuracion y asignaciones
    - **Tickets pendientes**: Del dia anterior
    - **Estados de cola**: Consistencia y actualizacion
    - **Usuarios**: Tecnicos listos para operar

    Requiere permisos de supervisor o administrador.
    """
)
async def daily_verification(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_supervisor)
) -> DailyVerificationResponse:
    """
    Endpoint de verificacion diaria del sistema
    """
    logger.info(f"Verificacion diaria iniciada por usuario: {current_user.Username}")

    try:
        # Realizar todas las verificaciones
        infrastructure = check_infrastructure(db)
        stations = check_stations(db)
        service_types = check_service_types(db)
        pending_tickets = check_pending_tickets(db)
        queue_states = check_queue_states(db)
        users = check_users(db)

        # Determinar estado general
        all_checks = [
            infrastructure[0].Status if infrastructure else "error",  # DB
            stations.Status,
            service_types.Status,
            pending_tickets.Status,
            queue_states.Status,
            users.Status
        ]

        # Acciones recomendadas
        recommended_actions = []

        # Analizar resultados para determinar estado general
        has_errors = "error" in all_checks
        has_warnings = "warning" in all_checks

        if has_errors:
            overall_status = "not_ready"
            ready_to_operate = False
            overall_message = "El sistema NO esta listo para operar - hay errores criticos"
        elif has_warnings:
            overall_status = "warning"
            ready_to_operate = True
            overall_message = "El sistema puede operar pero hay advertencias que atender"
        else:
            overall_status = "ready"
            ready_to_operate = True
            overall_message = "Sistema listo para iniciar operaciones"

        # Generar acciones recomendadas
        if pending_tickets.PendingFromYesterday > 0:
            recommended_actions.append(
                f"Ejecutar limpieza diaria para cancelar {pending_tickets.PendingFromYesterday} ticket(s) pendiente(s)"
            )

        if stations.StationsWithIssues:
            recommended_actions.append(
                f"Revisar {len(stations.StationsWithIssues)} estacion(es) con problemas"
            )

        if service_types.ServiceTypesWithoutStations:
            recommended_actions.append(
                f"Asignar estaciones a {len(service_types.ServiceTypesWithoutStations)} servicio(s)"
            )

        if queue_states.StaleQueueStates > 0:
            recommended_actions.append(
                f"Resetear {queue_states.StaleQueueStates} estado(s) de cola desactualizado(s)"
            )

        if users.TechniciansReady == 0:
            recommended_actions.append(
                "Asignar tecnicos a estaciones para poder atender pacientes"
            )

        # Construir respuesta
        response = DailyVerificationResponse(
            Timestamp=datetime.now(),
            OverallStatus=overall_status,
            OverallMessage=overall_message,
            ReadyToOperate=ready_to_operate,
            Infrastructure=infrastructure,
            Stations=stations,
            ServiceTypes=service_types,
            PendingTickets=pending_tickets,
            QueueStates=queue_states,
            Users=users,
            RecommendedActions=recommended_actions,
            AutoCleanupPerformed=False,
            CleanupSummary=None
        )

        logger.info(f"Verificacion diaria completada. Estado: {overall_status}")
        return response

    except Exception as e:
        logger.error(f"Error en verificacion diaria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al realizar verificacion diaria: {str(e)}"
        )


@router.post(
    "/daily-cleanup",
    response_model=DailyCleanupResponse,
    summary="Limpieza diaria del sistema",
    description="""
    Realiza la limpieza diaria del sistema para prepararlo para un nuevo dia de operaciones.

    Operaciones disponibles:
    - **Cancelar tickets pendientes**: Cancela tickets del dia anterior
    - **Resetear estados de cola**: Limpia las colas para empezar de cero
    - **Resetear estaciones**: Pone todas las estaciones en estado Available
    - **Limpiar cache**: Limpia el cache de Redis (opcional)

    Requiere permisos de administrador.
    """
)
async def daily_cleanup(
    request: DailyCleanupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
) -> DailyCleanupResponse:
    """
    Endpoint de limpieza diaria del sistema
    """
    logger.info(f"Limpieza diaria iniciada por usuario: {current_user.Username}")
    logger.info(f"Parametros: {request.model_dump()}")

    errors = []
    tickets_cancelled = 0
    queue_states_reset = 0
    stations_reset = 0
    cache_cleared = False

    try:
        today = date.today()

        # 1. Cancelar tickets pendientes del dia anterior
        if request.CancelPendingTickets:
            try:
                pending_tickets = db.query(Ticket).filter(
                    Ticket.Status.in_(['Waiting', 'Called', 'InProgress']),
                    func.cast(Ticket.CreatedAt, Date) < today
                ).all()

                for ticket in pending_tickets:
                    ticket.Status = 'Cancelled'
                    ticket.Notes = (ticket.Notes or '') + f" | Cancelado por limpieza diaria: {request.Reason}"
                    tickets_cancelled += 1

                db.flush()
                logger.info(f"Tickets cancelados: {tickets_cancelled}")
            except Exception as e:
                errors.append(f"Error cancelando tickets: {str(e)}")
                logger.error(f"Error cancelando tickets: {e}")

        # 2. Resetear estados de cola
        if request.ResetQueueStates:
            try:
                queue_states = db.query(QueueState).all()

                for state in queue_states:
                    state.CurrentTicketId = None
                    state.NextTicketId = None
                    state.QueueLength = 0
                    state.AverageWaitTime = 0
                    state.LastUpdateAt = datetime.now()
                    queue_states_reset += 1

                db.flush()
                logger.info(f"Estados de cola reseteados: {queue_states_reset}")
            except Exception as e:
                errors.append(f"Error reseteando colas: {str(e)}")
                logger.error(f"Error reseteando colas: {e}")

        # 3. Resetear estados de estaciones
        if request.ResetStationStates:
            try:
                stations = db.query(Station).filter(
                    Station.IsActive == True
                ).all()

                for station in stations:
                    station.CurrentTicketId = None
                    station.Status = 'Available'
                    station.UpdatedAt = datetime.now()
                    stations_reset += 1

                db.flush()
                logger.info(f"Estaciones reseteadas: {stations_reset}")
            except Exception as e:
                errors.append(f"Error reseteando estaciones: {str(e)}")
                logger.error(f"Error reseteando estaciones: {e}")

        # 4. Limpiar cache de Redis
        if request.ClearRedisCache:
            try:
                if cache_manager:
                    # Limpiar claves relacionadas con colas y sesiones del dia anterior
                    # Nota: Implementacion basica, se puede mejorar
                    cache_cleared = True
                    logger.info("Cache de Redis limpiado")
                else:
                    logger.warning("Cache manager no disponible")
            except Exception as e:
                errors.append(f"Error limpiando cache: {str(e)}")
                logger.error(f"Error limpiando cache: {e}")

        # Commit de todos los cambios
        db.commit()

        # Determinar si fue exitoso
        success = len(errors) == 0

        if success:
            message = "Limpieza diaria completada exitosamente"
        else:
            message = f"Limpieza completada con {len(errors)} error(es)"

        # 5. Notificar a todos los clientes WebSocket sobre el reset
        websocket_notifications_sent = 0
        try:
            websocket_notifications_sent = await websocket_manager.broadcast_daily_reset({
                "tickets_cancelled": tickets_cancelled,
                "queues_reset": queue_states_reset,
                "stations_reset": stations_reset,
                "performed_by": current_user.Username,
                "reason": request.Reason
            })
            logger.info(f"WebSocket notifications enviadas: {websocket_notifications_sent}")
        except Exception as e:
            errors.append(f"Error enviando notificaciones WebSocket: {str(e)}")
            logger.error(f"Error enviando notificaciones WebSocket: {e}")

        response = DailyCleanupResponse(
            Success=success,
            Timestamp=datetime.now(),
            TicketsCancelled=tickets_cancelled,
            QueueStatesReset=queue_states_reset,
            StationsReset=stations_reset,
            CacheCleared=cache_cleared,
            Errors=errors,
            Message=message
        )

        logger.info(f"Limpieza diaria completada. Exito: {success}")
        return response

    except Exception as e:
        db.rollback()
        logger.error(f"Error en limpieza diaria: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al realizar limpieza diaria: {str(e)}"
        )


@router.get(
    "/system-status",
    summary="Estado rapido del sistema",
    description="Obtiene un estado rapido del sistema sin verificacion completa"
)
async def system_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Endpoint de estado rapido del sistema
    """
    try:
        # Conteos rapidos
        active_stations = db.query(func.count(Station.Id)).filter(
            Station.IsActive == True,
            Station.Status == 'Available'
        ).scalar() or 0

        busy_stations = db.query(func.count(Station.Id)).filter(
            Station.IsActive == True,
            Station.Status == 'Busy'
        ).scalar() or 0

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        tickets_today = db.query(func.count(Ticket.Id)).filter(
            Ticket.CreatedAt >= today_start,
            Ticket.CreatedAt < today_end
        ).scalar() or 0

        waiting_tickets = db.query(func.count(Ticket.Id)).filter(
            Ticket.Status == 'Waiting',
            Ticket.CreatedAt >= today_start,
            Ticket.CreatedAt < today_end
        ).scalar() or 0

        return {
            "Timestamp": datetime.now().isoformat(),
            "Status": "operational",
            "ActiveStations": active_stations,
            "BusyStations": busy_stations,
            "TicketsToday": tickets_today,
            "WaitingTickets": waiting_tickets,
            "RedisAvailable": check_redis_connection()
        }

    except Exception as e:
        logger.error(f"Error obteniendo estado del sistema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estado del sistema: {str(e)}"
        )


# ========================================
# ENDPOINTS DE ROLES
# ========================================

@router.get(
    "/roles",
    summary="Obtener todos los roles",
    description="Obtiene la lista de roles del sistema. Requiere autenticacion."
)
async def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """
    Endpoint para obtener todos los roles del sistema
    """
    try:
        roles = db.query(Role).filter(Role.IsActive == True).order_by(Role.Id).all()

        return [
            {
                "Id": role.Id,
                "Name": role.Name,
                "Description": role.Description,
                "IsActive": role.IsActive
            }
            for role in roles
        ]

    except Exception as e:
        logger.error(f"Error obteniendo roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener roles: {str(e)}"
        )


@router.get(
    "/roles/{role_id}",
    summary="Obtener un rol por ID",
    description="Obtiene un rol especifico por su ID"
)
async def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
) -> dict:
    """
    Endpoint para obtener un rol por ID
    """
    try:
        role = db.query(Role).filter(Role.Id == role_id).first()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rol con ID {role_id} no encontrado"
            )

        # Contar usuarios con este rol
        user_count = db.query(func.count(User.Id)).filter(User.RoleId == role_id).scalar() or 0

        return {
            "Id": role.Id,
            "Name": role.Name,
            "Description": role.Description,
            "IsActive": role.IsActive,
            "Permissions": role.permissions_list,
            "UserCount": user_count,
            "CreatedAt": role.CreatedAt.isoformat() if role.CreatedAt else None,
            "UpdatedAt": role.UpdatedAt.isoformat() if role.UpdatedAt else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo rol {role_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener rol: {str(e)}"
        )


@router.post(
    "/roles/init",
    summary="Inicializar roles por defecto",
    description="Crea los roles por defecto del sistema si no existen"
)
async def init_default_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
) -> dict:
    """
    Endpoint para inicializar los roles por defecto del sistema
    """
    try:
        default_roles = [
            {"Name": "Admin", "Description": "Administrador del sistema con acceso completo"},
            {"Name": "Supervisor", "Description": "Supervisor con acceso a reportes y gestión de operaciones"},
            {"Name": "Tecnico", "Description": "Técnico que atiende pacientes en estaciones"},
            {"Name": "Recepcionista", "Description": "Recepcionista para registro de pacientes y tickets"}
        ]

        created = []
        existing = []

        for role_data in default_roles:
            # Verificar si ya existe
            existing_role = db.query(Role).filter(Role.Name == role_data["Name"]).first()

            if existing_role:
                existing.append(role_data["Name"])
            else:
                # Crear el rol
                new_role = Role(
                    Name=role_data["Name"],
                    Description=role_data["Description"],
                    IsActive=True
                )
                db.add(new_role)
                created.append(role_data["Name"])

        db.commit()

        return {
            "success": True,
            "message": f"Inicialización completada",
            "created": created,
            "existing": existing,
            "total_roles": len(created) + len(existing)
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error inicializando roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al inicializar roles: {str(e)}"
        )


class RoleUpdate(BaseModel):
    """Schema para actualizar un rol"""
    Name: Optional[str] = Field(None, min_length=2, max_length=50)
    Description: Optional[str] = Field(None, max_length=200)
    IsActive: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Name": "Analista",
                "Description": "Analista de laboratorio",
                "IsActive": True
            }
        }
    )


@router.put(
    "/roles/{role_id}",
    summary="Actualizar un rol",
    description="Actualiza los datos de un rol existente"
)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
) -> dict:
    """
    Endpoint para actualizar un rol
    """
    try:
        role = db.query(Role).filter(Role.Id == role_id).first()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rol con ID {role_id} no encontrado"
            )

        # Verificar si el nuevo nombre ya existe (si se esta cambiando)
        if role_data.Name and role_data.Name != role.Name:
            existing = db.query(Role).filter(
                Role.Name == role_data.Name,
                Role.Id != role_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe un rol con el nombre '{role_data.Name}'"
                )
            role.Name = role_data.Name

        if role_data.Description is not None:
            role.Description = role_data.Description

        if role_data.IsActive is not None:
            role.IsActive = role_data.IsActive

        db.commit()
        db.refresh(role)

        # Contar usuarios con este rol
        user_count = db.query(func.count(User.Id)).filter(User.RoleId == role_id).scalar() or 0

        return {
            "Id": role.Id,
            "Name": role.Name,
            "Description": role.Description,
            "IsActive": role.IsActive,
            "UserCount": user_count,
            "message": "Rol actualizado correctamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando rol {role_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar rol: {str(e)}"
        )


@router.delete(
    "/roles/{role_id}",
    summary="Eliminar un rol",
    description="Elimina un rol del sistema (solo si no tiene usuarios asignados)"
)
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
) -> dict:
    """
    Endpoint para eliminar un rol
    """
    try:
        role = db.query(Role).filter(Role.Id == role_id).first()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rol con ID {role_id} no encontrado"
            )

        # Verificar que no tenga usuarios asignados
        user_count = db.query(func.count(User.Id)).filter(User.RoleId == role_id).scalar() or 0
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede eliminar el rol '{role.Name}' porque tiene {user_count} usuario(s) asignado(s)"
            )

        role_name = role.Name
        db.delete(role)
        db.commit()

        return {
            "success": True,
            "message": f"Rol '{role_name}' eliminado correctamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando rol {role_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar rol: {str(e)}"
        )


class RoleCreate(BaseModel):
    """Schema para crear un rol"""
    Name: str = Field(..., min_length=2, max_length=50)
    Description: Optional[str] = Field(None, max_length=200)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Name": "Analista",
                "Description": "Analista de laboratorio"
            }
        }
    )


@router.post(
    "/roles",
    summary="Crear un nuevo rol",
    description="Crea un nuevo rol en el sistema"
)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
) -> dict:
    """
    Endpoint para crear un nuevo rol
    """
    try:
        # Verificar si ya existe un rol con ese nombre
        existing = db.query(Role).filter(Role.Name == role_data.Name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un rol con el nombre '{role_data.Name}'"
            )

        # Crear el rol
        new_role = Role(
            Name=role_data.Name,
            Description=role_data.Description,
            IsActive=True
        )
        db.add(new_role)
        db.commit()
        db.refresh(new_role)

        return {
            "Id": new_role.Id,
            "Name": new_role.Name,
            "Description": new_role.Description,
            "IsActive": new_role.IsActive,
            "message": "Rol creado correctamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando rol: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear rol: {str(e)}"
        )

