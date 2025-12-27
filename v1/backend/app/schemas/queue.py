"""
Schemas Pydantic v2 para gestión de estados de cola (QueueState)
Compatible con FastAPI y validación de datos
VERSIÓN CORREGIDA CON PASCALCASE - Coincide con BD y modelos SQLAlchemy
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from uuid import UUID


# ========================================
# SCHEMAS BASE
# ========================================

class QueueStateBase(BaseModel):
    """
    Schema base para QueueState con campos comunes
    Usa PascalCase para coincidir con el modelo SQLAlchemy y la BD
    """
    ServiceTypeId: int = Field(
        ...,
        description="ID del tipo de servicio",
        gt=0
    )
    StationId: Optional[int] = Field(
        None,
        description="ID de la estación (opcional para colas globales)",
        gt=0
    )
    QueueLength: int = Field(
        0,
        description="Longitud actual de la cola",
        ge=0
    )
    AverageWaitTime: int = Field(
        0,
        description="Tiempo promedio de espera en minutos",
        ge=0
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True  # Acepta tanto PascalCase como snake_case para compatibilidad
    )


# ========================================
# SCHEMAS DE CREACIÓN
# ========================================

class QueueStateCreate(BaseModel):
    """
    Schema para crear un nuevo estado de cola
    Usa PascalCase para coincidir con el modelo SQLAlchemy
    """
    ServiceTypeId: int = Field(
        ...,
        description="ID del tipo de servicio",
        gt=0
    )
    StationId: Optional[int] = Field(
        None,
        description="ID de la estación",
        gt=0
    )
    CurrentTicketId: Optional[str] = Field(
        None,
        description="ID del ticket actualmente siendo atendido"
    )
    NextTicketId: Optional[str] = Field(
        None,
        description="ID del próximo ticket en la cola"
    )
    QueueLength: int = Field(
        0,
        description="Longitud inicial de la cola",
        ge=0
    )
    AverageWaitTime: int = Field(
        0,
        description="Tiempo promedio inicial de espera",
        ge=0
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "ServiceTypeId": 1,
                "StationId": 2,
                "CurrentTicketId": "550e8400-e29b-41d4-a716-446655440000",
                "NextTicketId": "550e8400-e29b-41d4-a716-446655440001",
                "QueueLength": 0,
                "AverageWaitTime": 0
            }
        }
    )


# ========================================
# SCHEMAS DE ACTUALIZACIÓN
# ========================================

class QueueStateUpdate(BaseModel):
    """
    Schema para actualizar un estado de cola existente
    Todos los campos son opcionales
    """
    StationId: Optional[int] = Field(
        None,
        description="ID de la estación",
        gt=0
    )
    CurrentTicketId: Optional[str] = Field(
        None,
        description="ID del ticket actualmente siendo atendido"
    )
    NextTicketId: Optional[str] = Field(
        None,
        description="ID del próximo ticket en la cola"
    )
    QueueLength: Optional[int] = Field(
        None,
        description="Longitud actual de la cola",
        ge=0
    )
    AverageWaitTime: Optional[int] = Field(
        None,
        description="Tiempo promedio de espera en minutos",
        ge=0,
        le=480  # Máximo 8 horas
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "CurrentTicketId": "550e8400-e29b-41d4-a716-446655440000",
                "QueueLength": 10,
                "AverageWaitTime": 15
            }
        }
    )


# ========================================
# SCHEMAS DE RESPUESTA
# ========================================

class QueueStateResponse(BaseModel):
    """
    Schema para respuesta de API con información completa de QueueState
    Incluye información adicional del servicio y estación
    """
    Id: int = Field(..., description="ID único del estado de cola")
    ServiceTypeId: int = Field(..., description="ID del tipo de servicio")
    StationId: Optional[int] = Field(None, description="ID de la estación")
    CurrentTicketId: Optional[str] = Field(None, description="ID del ticket actual")
    NextTicketId: Optional[str] = Field(None, description="ID del próximo ticket")
    QueueLength: int = Field(..., description="Longitud actual de la cola")
    AverageWaitTime: int = Field(..., description="Tiempo promedio de espera")
    LastUpdateAt: datetime = Field(..., description="Última actualización")

    # Campos adicionales enriquecidos
    ServiceName: Optional[str] = Field(None, description="Nombre del servicio")
    ServiceCode: Optional[str] = Field(None, description="Código del servicio")
    StationName: Optional[str] = Field(None, description="Nombre de la estación")
    StationCode: Optional[str] = Field(None, description="Código de la estación")
    IsActive: bool = Field(True, description="Si la cola está activa")
    EstimatedWaitTime: Optional[int] = Field(None, description="Tiempo estimado para nuevos tickets")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "Id": 1,
                "ServiceTypeId": 1,
                "StationId": 2,
                "CurrentTicketId": "550e8400-e29b-41d4-a716-446655440000",
                "NextTicketId": "550e8400-e29b-41d4-a716-446655440001",
                "QueueLength": 5,
                "AverageWaitTime": 10,
                "LastUpdateAt": "2024-01-15T10:30:00",
                "ServiceName": "Análisis de Sangre",
                "ServiceCode": "LAB",
                "StationName": "Ventanilla 2",
                "StationCode": "V02",
                "IsActive": True,
                "EstimatedWaitTime": 50
            }
        }
    )


class QueueStateInDB(QueueStateBase):
    """
    Schema para QueueState tal como está en la base de datos
    """
    Id: int = Field(...)
    CurrentTicketId: Optional[str] = Field(None)
    NextTicketId: Optional[str] = Field(None)
    LastUpdateAt: datetime = Field(...)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


# ========================================
# SCHEMAS DE OPERACIONES
# ========================================

class AdvanceQueueRequest(BaseModel):
    """
    Schema para solicitud de avanzar la cola
    """
    ServiceTypeId: int = Field(
        ...,
        description="ID del tipo de servicio",
        gt=0
    )
    StationId: Optional[int] = Field(
        None,
        description="ID de la estación",
        gt=0
    )
    MarkCompleted: bool = Field(
        True,
        description="Si marcar el ticket actual como completado"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "ServiceTypeId": 1,
                "StationId": 2,
                "MarkCompleted": True
            }
        }
    )


class ResetQueueRequest(BaseModel):
    """
    Schema para solicitud de resetear cola
    """
    ServiceTypeId: int = Field(
        ...,
        description="ID del tipo de servicio",
        gt=0
    )
    StationId: Optional[int] = Field(
        None,
        description="ID de la estación",
        gt=0
    )
    Reason: Optional[str] = Field(
        None,
        description="Razón del reset",
        max_length=200
    )
    CancelPendingTickets: bool = Field(
        False,
        description="Si cancelar tickets pendientes"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "ServiceTypeId": 1,
                "StationId": None,
                "Reason": "Fin de jornada",
                "CancelPendingTickets": True
            }
        }
    )


class UpdateWaitTimeRequest(BaseModel):
    """
    Schema para solicitud de actualizar tiempo de espera
    """
    QueueStateId: int = Field(
        ...,
        description="ID del estado de cola",
        gt=0
    )
    Recalculate: bool = Field(
        True,
        description="Si recalcular basado en tiempos reales"
    )
    ManualTime: Optional[int] = Field(
        None,
        description="Tiempo manual en minutos",
        gt=0
    )

    @model_validator(mode='after')
    def validate_manual_time(self) -> 'UpdateWaitTimeRequest':
        """Valida que se proporcione ManualTime si no se recalcula"""
        if not self.Recalculate and self.ManualTime is None:
            raise ValueError('Debe proporcionar ManualTime si Recalculate es False')
        return self

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "QueueStateId": 1,
                "Recalculate": False,
                "ManualTime": 15
            }
        }
    )


# ========================================
# SCHEMAS DE CONSULTA Y ESTADÍSTICAS
# ========================================

class QueueSummary(BaseModel):
    """
    Schema para resumen de colas del sistema
    CORREGIDO: Ahora cuenta tickets reales, no QueueState.QueueLength
    """
    TotalQueues: int = Field(..., description="Total de colas en el sistema")
    ActiveQueues: int = Field(..., description="Colas con tickets esperando")
    TotalWaiting: int = Field(..., description="Total de tickets en espera")
    InAttention: int = Field(0, description="Tickets siendo atendidos")
    StationsBusy: int = Field(..., description="Estaciones ocupadas")
    AverageWaitTime: float = Field(..., description="Tiempo promedio global de espera")
    CompletedToday: int = Field(0, description="Tickets completados hoy")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "TotalQueues": 10,
                "ActiveQueues": 7,
                "TotalWaiting": 45,
                "InAttention": 3,
                "StationsBusy": 6,
                "AverageWaitTime": 12.5,
                "CompletedToday": 15
            }
        }
    )



class QueueStateWithTickets(QueueStateResponse):
    """
    Schema para QueueState con lista de tickets pendientes
    """
    PendingTickets: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Lista de tickets pendientes en la cola"
    )
    RecentlyCompleted: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tickets recientemente completados"
    )


class QueueFilters(BaseModel):
    """
    Schema para filtros de búsqueda de colas
    """
    ServiceTypeId: Optional[int] = Field(None, gt=0)
    StationId: Optional[int] = Field(None, gt=0)
    IsActive: Optional[bool] = Field(None)
    MinQueueLength: Optional[int] = Field(None, ge=0)
    MaxQueueLength: Optional[int] = Field(None, ge=0)
    HasCurrentTicket: Optional[bool] = Field(None)

    @model_validator(mode='after')
    def validate_queue_length_range(self) -> 'QueueFilters':
        """Valida que el rango de longitud sea válido"""
        if self.MinQueueLength is not None and self.MaxQueueLength is not None:
            if self.MinQueueLength > self.MaxQueueLength:
                raise ValueError('MinQueueLength debe ser menor o igual a MaxQueueLength')
        return self

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "ServiceTypeId": 1,
                "IsActive": True,
                "MinQueueLength": 5,
                "MaxQueueLength": 20
            }
        }
    )


# ========================================
# SCHEMAS DE ACTUALIZACIÓN MASIVA
# ========================================

class BatchQueueUpdate(BaseModel):
    """
    Schema para actualización masiva de colas
    """
    QueueIds: List[int] = Field(
        ...,
        description="IDs de colas a actualizar",
        min_length=1
    )
    Action: str = Field(
        ...,
        description="Acción a realizar",
        pattern="^(reset|refresh|cleanup)$"
    )
    Reason: Optional[str] = Field(
        None,
        description="Razón de la acción",
        max_length=200
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "QueueIds": [1, 2, 3],
                "Action": "reset",
                "Reason": "Cierre de jornada"
            }
        }
    )


# ========================================
# SCHEMAS DE NOTIFICACIÓN
# ========================================

class QueueStateChangeNotification(BaseModel):
    """
    Schema para notificación de cambio en estado de cola
    """
    QueueStateId: int = Field(..., description="ID del estado de cola")
    ChangeType: str = Field(
        ...,
        description="Tipo de cambio",
        pattern="^(advanced|reset|updated|created)$"
    )
    PreviousTicket: Optional[str] = Field(None, description="Ticket anterior")
    CurrentTicket: Optional[str] = Field(None, description="Ticket actual")
    NextTicket: Optional[str] = Field(None, description="Próximo ticket")
    Timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "QueueStateId": 1,
                "ChangeType": "advanced",
                "PreviousTicket": "A044",
                "CurrentTicket": "A045",
                "NextTicket": "A046",
                "Timestamp": "2024-01-15T10:30:00"
            }
        }
    )


# ========================================
# EXPORTS
# ========================================

__all__ = [
    # Base
    "QueueStateBase",
    "QueueStateInDB",

    # CRUD
    "QueueStateCreate",
    "QueueStateUpdate",
    "QueueStateResponse",

    # Operations
    "AdvanceQueueRequest",
    "ResetQueueRequest",
    "UpdateWaitTimeRequest",

    # Query & Stats
    "QueueSummary",
    "QueueStateWithTickets",
    "QueueFilters",
    "BatchQueueUpdate",

    # Notifications
    "QueueStateChangeNotification"
]