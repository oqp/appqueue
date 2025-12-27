"""
Schemas Pydantic para validación y serialización de datos de tickets
100% compatibles con el modelo SQLAlchemy Ticket
ACTUALIZADO PARA PYDANTIC V2
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date  # <-- ASEGÚRATE DE QUE date ESTÉ AQUÍ
from enum import Enum
import uuid
from datetime import date as DateType  # Agregar esta línea

# ========================================
# ENUMS Y CONSTANTES
# ========================================

class TicketStatus(str, Enum):
    """Estados válidos de ticket - Compatible con constraint del modelo SQLAlchemy"""
    WAITING = "Waiting"
    CALLED = "Called"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    NO_SHOW = "NoShow"


# ========================================
# SCHEMAS BASE
# ========================================

class TicketBase(BaseModel):
    """Schema base para campos comunes de ticket"""

    PatientId: Union[str, uuid.UUID] = Field(
        ...,
        description="ID del paciente (UNIQUEIDENTIFIER)"
    )

    ServiceTypeId: int = Field(
        ...,
        ge=1,
        description="ID del tipo de servicio"
    )

    StationId: Optional[int] = Field(
        None,
        ge=1,
        description="ID de la estación asignada (opcional)"
    )

    Notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Notas adicionales del ticket"
    )

    # Serializar UUIDs como strings automáticamente
    @field_serializer('PatientId')
    def serialize_patient_id(self, value: Union[str, uuid.UUID]) -> str:
        """Convierte UUID a string para serialización"""
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    @field_validator('PatientId', mode='before')
    @classmethod
    def validate_patient_id(cls, v):
        """Valida y convierte el PatientId"""
        if isinstance(v, uuid.UUID):
            return str(v)
        if isinstance(v, str):
            try:
                # Validar que sea un UUID válido
                uuid.UUID(v)
                return v
            except ValueError:
                raise ValueError('PatientId debe ser un UUID válido')
        return v

    @field_validator('Notes')
    @classmethod
    def validate_notes(cls, v):
        """Valida y limpia las notas"""
        if v:
            return v.strip()
        return v


# ========================================
# SCHEMAS PARA CREAR TICKETS
# ========================================

class TicketCreate(TicketBase):
    """Schema para crear un nuevo ticket"""
    model_config = {
        "json_schema_extra": {
            "example": {
                "PatientId": "123e4567-e89b-12d3-a456-426614174000",
                "ServiceTypeId": 1,
                "StationId": None,
                "Notes": "Paciente requiere atención prioritaria"
            }
        }
    }


class TicketQuickCreate(BaseModel):
    """Schema para creación rápida de ticket"""
    PatientDocumentNumber: str = Field(
        ...,
        min_length=5,
        max_length=20,
        description="Número de documento del paciente"
    )
    ServiceTypeId: int = Field(
        ...,
        ge=1,
        description="ID del tipo de servicio"
    )
    Notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Notas adicionales"
    )


class TicketUpdate(BaseModel):
    """Schema para actualizar datos de ticket existente"""
    StationId: Optional[int] = Field(None, ge=1)
    Status: Optional[TicketStatus] = None
    Notes: Optional[str] = Field(None, max_length=500)
    EstimatedWaitTime: Optional[int] = Field(None, ge=0)

    @field_validator('Notes')
    @classmethod
    def validate_notes(cls, v):
        if v is not None:
            return v.strip()
        return v


class TicketStatusUpdate(BaseModel):
    """Schema específico para actualizar solo el estado del ticket"""
    Status: TicketStatus = Field(..., description="Nuevo estado del ticket")
    Notes: Optional[str] = Field(
        None,
        max_length=200,
        description="Notas sobre el cambio de estado"
    )


# ========================================
# SCHEMAS PARA RESPUESTAS
# ========================================

class TicketResponse(TicketBase):
    """Schema para respuestas - COMPATIBLE CON SQLALCHEMY"""

    # Configuración que permite el mapeo automático desde SQLAlchemy
    model_config = ConfigDict(
        from_attributes=True,  # Permite leer desde objetos SQLAlchemy
        populate_by_name=True,  # Permite múltiples nombres para campos
        alias_generator=None,  # No generar aliases automáticos
        validate_assignment=True
    )

    # Campos principales con soporte para UUID
    Id: Union[str, uuid.UUID] = Field(..., description="ID único del ticket")
    TicketNumber: str = Field(..., description="Número del ticket")
    Status: TicketStatus = Field(..., description="Estado actual")
    Position: int = Field(..., description="Posición en la cola")
    EstimatedWaitTime: Optional[int] = Field(None, description="Tiempo estimado de espera")
    QrCode: Optional[str] = Field(None, description="Código QR del ticket")

    # Campos de timestamp - Acepta ambos nombres
    CreatedAt: Optional[datetime] = Field(None, alias="created_at", description="Fecha de creación")
    UpdatedAt: Optional[datetime] = Field(None, alias="updated_at", description="Última actualización")
    CalledAt: Optional[datetime] = Field(None, description="Fecha y hora de llamada")
    AttendedAt: Optional[datetime] = Field(None, description="Fecha y hora de inicio de atención")
    CompletedAt: Optional[datetime] = Field(None, description="Fecha y hora de finalización")

    # Campos calculados
    ActualWaitTime: Optional[int] = Field(None, description="Tiempo real de espera")
    ServiceTime: Optional[int] = Field(None, description="Tiempo de servicio")

    # Propiedades calculadas opcionales
    status_display: Optional[str] = Field(None, description="Estado en formato legible")
    is_active: Optional[bool] = Field(None, description="Si el ticket está activo")
    is_completed: Optional[bool] = Field(None, description="Si el ticket está completado")
    is_cancelled: Optional[bool] = Field(None, description="Si el ticket fue cancelado")
    can_be_called: Optional[bool] = Field(None, description="Si puede ser llamado")
    can_be_attended: Optional[bool] = Field(None, description="Si puede ser atendido")
    is_overdue: Optional[bool] = Field(None, description="Si está retrasado")
    priority_score: Optional[int] = Field(None, description="Puntaje de prioridad")

    # Datos relacionados opcionales
    patient_name: Optional[str] = Field(None, description="Nombre del paciente")
    patient_document: Optional[str] = Field(None, description="Documento del paciente")
    service_name: Optional[str] = Field(None, description="Nombre del servicio")
    service_code: Optional[str] = Field(None, description="Código del servicio")
    station_name: Optional[str] = Field(None, description="Nombre de la estación")
    station_code: Optional[str] = Field(None, description="Código de la estación")

    # Serializar el ID como string
    @field_serializer('Id')
    def serialize_id(self, value: Union[str, uuid.UUID]) -> str:
        """Convierte UUID a string para serialización"""
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    # Validadores para manejar los campos de timestamp
    @field_validator('CreatedAt', 'UpdatedAt', mode='before')
    @classmethod
    def validate_timestamps(cls, v, info):
        """Maneja los timestamps que vienen del modelo SQLAlchemy"""
        if v is None and info.field_name == 'CreatedAt':
            # Si CreatedAt es None, intentar obtenerlo de created_at
            if hasattr(info.data, 'created_at'):
                return info.data.get('created_at')
        if v is None and info.field_name == 'UpdatedAt':
            # Si UpdatedAt es None, intentar obtenerlo de updated_at
            if hasattr(info.data, 'updated_at'):
                return info.data.get('updated_at')
        return v

    @classmethod
    def from_orm_with_fallback(cls, obj):
        """
        Método auxiliar para crear desde objeto ORM con manejo de campos
        """
        # Crear diccionario con los datos del objeto
        data = {}

        # Mapear campos básicos
        for field in cls.model_fields:
            # Intentar obtener el valor del objeto
            if hasattr(obj, field):
                data[field] = getattr(obj, field)
            # Casos especiales de mapeo
            elif field == 'CreatedAt' and hasattr(obj, 'created_at'):
                data['CreatedAt'] = obj.created_at
            elif field == 'UpdatedAt' and hasattr(obj, 'updated_at'):
                data['UpdatedAt'] = obj.updated_at

        # Convertir UUIDs a strings
        if 'Id' in data and isinstance(data['Id'], uuid.UUID):
            data['Id'] = str(data['Id'])
        if 'PatientId' in data and isinstance(data['PatientId'], uuid.UUID):
            data['PatientId'] = str(data['PatientId'])

        # Si el objeto tiene el método to_dict, usar sus propiedades calculadas
        if hasattr(obj, 'to_dict'):
            obj_dict = obj.to_dict(include_patient=True, include_service=True)
            # Agregar propiedades calculadas si existen
            for prop in ['status_display', 'is_active', 'is_completed', 'is_cancelled',
                         'can_be_called', 'can_be_attended', 'is_overdue', 'priority_score',
                         'patient_name', 'patient_document', 'service_name', 'service_code',
                         'station_name', 'station_code']:
                if prop in obj_dict:
                    data[prop] = obj_dict[prop]

        return cls.model_validate(data)


# ========================================
# SCHEMAS PARA LISTAS Y BÚSQUEDAS
# ========================================

class TicketListResponse(BaseModel):
    """Schema para respuestas de listas de tickets con paginación"""

    tickets: List[TicketResponse] = Field(..., description="Lista de tickets")
    total: int = Field(..., description="Total de registros")
    skip: int = Field(..., description="Registros omitidos")
    limit: int = Field(..., description="Límite de registros por página")
    has_more: bool = Field(..., description="Hay más registros disponibles")
    queue_stats: Optional[dict] = Field(None, description="Estadísticas de la cola")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tickets": [
                    {
                        "Id": "123e4567-e89b-12d3-a456-426614174000",
                        "TicketNumber": "A001",
                        "Status": "Waiting",
                        "Position": 1,
                        "patient_name": "Juan Pérez",
                        "service_name": "Análisis de Laboratorio"
                    }
                ],
                "total": 150,
                "skip": 0,
                "limit": 20,
                "has_more": True,
                "queue_stats": {
                    "waiting": 45,
                    "in_progress": 8,
                    "completed_today": 97
                }
            }
        }
    }


class TicketSearchFilters(BaseModel):
    """Schema para filtros de búsqueda de tickets"""

    patient_document: Optional[str] = Field(None, description="Documento del paciente")
    patient_name: Optional[str] = Field(None, description="Nombre del paciente")
    service_type_id: Optional[int] = Field(None, description="ID del tipo de servicio")
    station_id: Optional[int] = Field(None, description="ID de la estación")
    status: Optional[TicketStatus] = Field(None, description="Estado del ticket")
    date_from: Optional[date] = Field(None, description="Fecha desde")
    date_to: Optional[date] = Field(None, description="Fecha hasta")
    ticket_number: Optional[str] = Field(None, description="Número de ticket")
    include_cancelled: bool = Field(False, description="Incluir tickets cancelados")

    model_config = {
        "json_schema_extra": {
            "example": {
                "patient_document": "12345678",
                "service_type_id": 1,
                "status": "Waiting",
                "date_from": "2024-03-01",
                "date_to": "2024-03-15",
                "include_cancelled": False
            }
        }
    }

# ========================================
# SCHEMAS PARA OPERACIONES DE COLA
# ========================================
class QueuePosition(BaseModel):
    """Schema para posición en cola"""
    ticket_id: str = Field(..., description="ID del ticket")
    ticket_number: str = Field(..., description="Número del ticket")
    current_position: int = Field(..., description="Posición actual en cola")
    ahead_count: int = Field(..., description="Tickets por delante")
    estimated_wait_time: int = Field(..., description="Tiempo estimado de espera en minutos")
    service_name: str = Field(..., description="Nombre del servicio")


class CallTicketRequest(BaseModel):
    """Schema para llamar un ticket específico"""

    station_id: int = Field(..., ge=1, description="ID de la estación que llama")
    notes: Optional[str] = Field(None, max_length=200, description="Notas de la llamada")

    model_config = {
        "json_schema_extra": {
            "example": {
                "station_id": 2,
                "notes": "Llamada desde ventanilla 2"
            }
        }
    }


class TransferTicketRequest(BaseModel):
    """Schema para transferir ticket a otra estación"""

    new_station_id: int = Field(..., ge=1, description="ID de la nueva estación")
    reason: Optional[str] = Field(None, max_length=200, description="Razón de la transferencia")

    model_config = {
        "json_schema_extra": {
            "example": {
                "new_station_id": 3,
                "reason": "Especialización requerida"
            }
        }
    }


# ========================================
# SCHEMAS PARA ESTADÍSTICAS
# ========================================
class TicketStats(BaseModel):
    """Schema para estadísticas generales de tickets"""
    total_tickets: int = Field(0, description="Total de tickets del día")
    waiting_tickets: int = Field(0, description="Tickets en espera")
    called_tickets: int = Field(0, description="Tickets llamados")
    in_progress_tickets: int = Field(0, description="Tickets en progreso")
    completed_tickets: int = Field(0, description="Tickets completados")
    cancelled_tickets: int = Field(0, description="Tickets cancelados")
    no_show_tickets: int = Field(0, description="Tickets no-show")
    average_wait_time: float = Field(0.0, description="Tiempo promedio de espera en minutos")
    average_service_time: float = Field(0.0, description="Tiempo promedio de servicio en minutos")

class QueueOverview(BaseModel):
    """Schema para vista general de colas"""
    service_queues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Estado de las colas por servicio"
    )
    total_waiting: int = Field(0, description="Total de tickets en espera")
    active_stations: int = Field(0, description="Número de estaciones activas")
    estimated_next_calls: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Próximas llamadas estimadas"
    )


# ========================================
# SCHEMAS PARA CREACIÓN MASIVA
# ========================================

class BulkTicketCreate(BaseModel):
    """Schema para crear múltiples tickets"""

    tickets: List[TicketCreate] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Lista de tickets a crear (máximo 50)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tickets": [
                    {
                        "PatientId": "123e4567-e89b-12d3-a456-426614174000",
                        "ServiceTypeId": 1
                    },
                    {
                        "PatientId": "456e7890-e89b-12d3-a456-426614174000",
                        "ServiceTypeId": 2
                    }
                ]
            }
        }
    }


class BulkTicketResponse(BaseModel):
    """Schema para respuesta de creación masiva"""

    created_tickets: List[TicketResponse] = Field(..., description="Tickets creados exitosamente")
    failed_tickets: List[dict] = Field(..., description="Tickets que fallaron al crear")
    success_count: int = Field(..., description="Cantidad de tickets creados")
    error_count: int = Field(..., description="Cantidad de errores")

    model_config = {
        "json_schema_extra": {
            "example": {
                "created_tickets": [
                    {
                        "Id": "123e4567-e89b-12d3-a456-426614174000",
                        "TicketNumber": "A001",
                        "Status": "Waiting"
                    }
                ],
                "failed_tickets": [
                    {
                        "index": 1,
                        "error": "Paciente no encontrado"
                    }
                ],
                "success_count": 1,
                "error_count": 1
            }
        }
    }


# ========================================
# SCHEMAS PARA REPORTES RÁPIDOS
# ========================================

class DailyTicketSummary(BaseModel):
    """Schema para resumen diario de tickets"""
    summary_date: DateType = Field(..., description="Fecha del resumen")  # Renombrar campo y usar alias
    total_tickets: int = Field(default=0, description="Total de tickets creados")
    tickets_by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Tickets agrupados por estado"
    )
    tickets_by_service: Dict[str, int] = Field(
        default_factory=dict,
        description="Tickets agrupados por servicio"
    )
    average_wait_time: float = Field(default=0.0, description="Tiempo promedio de espera")
    average_service_time: float = Field(default=0.0, description="Tiempo promedio de servicio")
    peak_hour: str = Field(default="N/A", description="Hora pico del día")

    model_config = {
        "json_schema_extra": {
            "example": {
                "summary_date": "2024-03-15",
                "total_tickets": 150,
                "tickets_by_status": {
                    "Waiting": 10,
                    "InProgress": 5,
                    "Completed": 130,
                    "Cancelled": 5
                },
                "tickets_by_service": {
                    "Análisis": 80,
                    "Entrega de Resultados": 50,
                    "Consultas": 20
                },
                "average_wait_time": 25.5,
                "average_service_time": 15.3,
                "peak_hour": "10:00-11:00"
            }
        }
    }