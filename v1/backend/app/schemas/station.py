"""
Schemas Pydantic para gestión de estaciones/ventanillas
Versión limpia que coincide exactamente con la estructura de la BD
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re


# ========================================
# ENUMS PARA ESTACIONES
# ========================================

class StationStatus(str, Enum):
    """Estados posibles de una estación según la BD"""
    AVAILABLE = "Available"
    BUSY = "Busy"
    BREAK = "Break"
    MAINTENANCE = "Maintenance"
    OFFLINE = "Offline"


# ========================================
# SCHEMAS BASE PARA ESTACIONES
# ========================================

class StationBase(BaseModel):
    """Schema base para estaciones"""

    Name: str = Field(..., min_length=2, max_length=100, description="Nombre de la estación")
    Code: str = Field(..., min_length=1, max_length=10, description="Código único de la estación")
    Description: Optional[str] = Field(None, max_length=200, description="Descripción de la estación")
    ServiceTypeId: Optional[int] = Field(None, description="ID del tipo de servicio principal")
    Location: Optional[str] = Field(None, max_length=100, description="Ubicación física")
    IsActive: bool = Field(True, description="Estado activo de la estación")

    @field_validator('Code')
    @classmethod
    def validate_code(cls, v):
        """Valida el formato del código de estación"""
        if v:
            # Normalizar código (mayúsculas, sin espacios)
            v = v.strip().upper()
            # Validar formato alfanumérico
            if not re.match(r'^[A-Z0-9]{1,10}$', v):
                raise ValueError('Código debe ser alfanumérico de 1-10 caracteres')
            return v
        return v

    @field_validator('Name')
    @classmethod
    def validate_name(cls, v):
        """Valida el nombre de la estación"""
        if v:
            v = v.strip()
            if len(v) < 2:
                raise ValueError('Nombre debe tener al menos 2 caracteres')
            return v
        return v


class StationCreate(StationBase):
    """Schema para crear nueva estación"""

    Status: Optional[str] = Field("Available", description="Estado inicial de la estación")

    model_config = {
        "json_schema_extra": {
            "example": {
                "Name": "Ventanilla Principal",
                "Code": "V001",
                "Description": "Ventanilla principal para análisis generales",
                "ServiceTypeId": 1,
                "Location": "Planta Baja",
                "IsActive": True,
                "Status": "Available"
            }
        }
    }


class StationUpdate(BaseModel):
    """Schema para actualizar estación existente"""

    Name: Optional[str] = Field(None, min_length=2, max_length=100)
    Description: Optional[str] = Field(None, max_length=200)
    ServiceTypeId: Optional[int] = Field(None)
    Location: Optional[str] = Field(None, max_length=100)
    IsActive: Optional[bool] = Field(None)
    Status: Optional[str] = Field(None)

    @field_validator('Name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError('Nombre debe tener al menos 2 caracteres')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "Name": "Ventanilla Actualizada",
                "Description": "Descripción actualizada",
                "Location": "Planta Alta",
                "Status": "Available"
            }
        }
    }


# ========================================
# SCHEMAS DE RESPUESTA
# ========================================

class StationResponse(BaseModel):
    """Schema de respuesta para una estación - coincide con BD real"""

    Id: int = Field(..., description="ID de la estación")
    Name: str = Field(..., description="Nombre de la estación")
    Code: str = Field(..., description="Código de la estación")
    Description: Optional[str] = Field(None, description="Descripción")
    ServiceTypeId: Optional[int] = Field(None, description="ID del tipo de servicio")
    Location: Optional[str] = Field(None, description="Ubicación física")
    Status: str = Field(..., description="Estado actual")
    CurrentTicketId: Optional[str] = Field(None, description="ID del ticket actual")
    IsActive: bool = Field(..., description="Si está activa")
    CreatedAt: Optional[datetime] = Field(None, description="Fecha de creación")
    UpdatedAt: Optional[datetime] = Field(None, description="Fecha de actualización")

    # Campos opcionales de relaciones (solo si se cargan)
    ServiceTypeName: Optional[str] = Field(None, description="Nombre del tipo de servicio")
    CurrentTicketNumber: Optional[str] = Field(None, description="Número del ticket actual")
    AssignedUsers: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Usuarios asignados")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "Id": 1,
                "Name": "Ventanilla Análisis 1",
                "Code": "VA01",
                "Description": "Toma de muestras - Análisis",
                "ServiceTypeId": 1,
                "Location": "Planta Baja",
                "Status": "Available",
                "CurrentTicketId": None,
                "IsActive": True,
                "CreatedAt": "2025-07-31T04:57:10.563",
                "UpdatedAt": "2025-07-31T04:57:10.563",
                "ServiceTypeName": "Análisis",
                "CurrentTicketNumber": None,
                "AssignedUsers": []
            }
        }
    }


class StationListResponse(BaseModel):
    """Schema para respuesta de lista de estaciones"""

    Stations: List[StationResponse] = Field(..., description="Lista de estaciones")
    Total: int = Field(..., description="Total de registros")
    Page: int = Field(..., description="Página actual")
    PageSize: int = Field(..., description="Tamaño de página")
    TotalPages: int = Field(..., description="Total de páginas")
    HasNext: bool = Field(..., description="Tiene página siguiente")
    HasPrev: bool = Field(..., description="Tiene página anterior")

    model_config = {
        "json_schema_extra": {
            "example": {
                "Stations": [],
                "Total": 6,
                "Page": 1,
                "PageSize": 100,
                "TotalPages": 1,
                "HasNext": False,
                "HasPrev": False
            }
        }
    }


# ========================================
# SCHEMAS PARA ESTADÍSTICAS (OPCIONALES)
# ========================================

class StationStats(BaseModel):
    """Schema para estadísticas de una estación"""

    StationId: int = Field(..., description="ID de la estación")
    QueueLength: int = Field(0, description="Longitud actual de la cola")
    TotalTicketsToday: int = Field(0, description="Total de tickets atendidos hoy")
    AverageWaitTime: float = Field(0.0, description="Tiempo promedio de espera en minutos")
    CurrentStatus: str = Field(..., description="Estado actual")
    LastActivityTime: Optional[datetime] = Field(None, description="Última actividad")

    model_config = {
        "json_schema_extra": {
            "example": {
                "StationId": 1,
                "QueueLength": 5,
                "TotalTicketsToday": 23,
                "AverageWaitTime": 15.5,
                "CurrentStatus": "Busy",
                "LastActivityTime": "2024-03-15T14:30:00"
            }
        }
    }


class StationStatusUpdate(BaseModel):
    """Schema para cambiar el estado de una estación"""

    Status: str = Field(..., description="Nuevo estado de la estación")
    Reason: Optional[str] = Field(None, max_length=200, description="Razón del cambio de estado")

    @field_validator('Status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ['Available', 'Busy', 'Break', 'Maintenance', 'Offline']
        if v not in valid_statuses:
            raise ValueError(f'Estado debe ser uno de: {", ".join(valid_statuses)}')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "Status": "Break",
                "Reason": "Descanso programado"
            }
        }
    }


# ========================================
# SCHEMAS PARA OPERACIONES DE COLA
# ========================================

class CallNextPatientRequest(BaseModel):
    """Schema para solicitud de llamar siguiente paciente"""

    ServiceTypeId: Optional[int] = Field(None, description="Tipo de servicio específico")
    Priority: Optional[int] = Field(None, ge=1, le=5, description="Nivel de prioridad mínima")
    Notes: Optional[str] = Field(None, max_length=200, description="Notas de la llamada")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ServiceTypeId": 1,
                "Priority": 3,
                "Notes": "Llamada desde ventanilla principal"
            }
        }
    }


class CallNextPatientResponse(BaseModel):
    """Schema para respuesta de llamar siguiente paciente"""

    success: bool = Field(..., description="Si se pudo llamar un paciente")
    message: str = Field(..., description="Mensaje descriptivo")
    ticket: Optional[Dict[str, Any]] = Field(None, description="Información del ticket llamado")
    queue_length: int = Field(0, description="Longitud actual de la cola")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Paciente A001 llamado exitosamente",
                "ticket": {
                    "id": "uuid",
                    "ticket_number": "A001",
                    "patient_name": "Juan Pérez"
                },
                "queue_length": 5
            }
        }
    }


class TransferPatientsRequest(BaseModel):
    """Schema para transferir pacientes entre estaciones"""

    SourceStationId: int = Field(..., description="ID de estación origen")
    TargetStationId: int = Field(..., description="ID de estación destino")
    TicketIds: Optional[List[str]] = Field(None, description="IDs específicos de tickets a transferir")
    TransferAll: bool = Field(False, description="Transferir todos los tickets en cola")
    Reason: str = Field(..., max_length=200, description="Razón de la transferencia")

    model_config = {
        "json_schema_extra": {
            "example": {
                "SourceStationId": 1,
                "TargetStationId": 2,
                "TicketIds": ["uuid1", "uuid2"],
                "TransferAll": False,
                "Reason": "Mantenimiento de ventanilla"
            }
        }
    }


class StationPerformanceReport(BaseModel):
    """Schema para reporte de rendimiento de estación"""

    StationId: int = Field(..., description="ID de la estación")
    StationName: str = Field(..., description="Nombre de la estación")
    Period: str = Field(..., description="Período del reporte")
    TotalTickets: int = Field(0, description="Total de tickets atendidos")
    AverageServiceTime: float = Field(0.0, description="Tiempo promedio de servicio")
    AverageWaitTime: float = Field(0.0, description="Tiempo promedio de espera")
    SatisfactionScore: Optional[float] = Field(None, description="Puntuación de satisfacción")
    UtilizationRate: float = Field(0.0, description="Tasa de utilización (%)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "StationId": 1,
                "StationName": "Ventanilla 1",
                "Period": "2024-03",
                "TotalTickets": 450,
                "AverageServiceTime": 12.5,
                "AverageWaitTime": 8.3,
                "SatisfactionScore": 4.2,
                "UtilizationRate": 78.5
            }
        }
    }


class StationAssignUser(BaseModel):
    """Schema para asignar usuario a estación"""

    UserId: str = Field(..., description="ID del usuario a asignar")
    StartTime: Optional[datetime] = Field(None, description="Hora de inicio de turno")
    EndTime: Optional[datetime] = Field(None, description="Hora de fin de turno")
    Notes: Optional[str] = Field(None, max_length=200, description="Notas de la asignación")

    model_config = {
        "json_schema_extra": {
            "example": {
                "UserId": "123e4567-e89b-12d3-a456-426614174000",
                "StartTime": "2024-03-15T08:00:00",
                "EndTime": "2024-03-15T17:00:00",
                "Notes": "Turno matutino"
            }
        }
    }


# ========================================
# SCHEMAS PARA OPERACIONES ESPECÍFICAS
# ========================================

class StationSearchFilters(BaseModel):
    """Schema para filtros de búsqueda de estaciones"""

    Query: Optional[str] = Field(None, max_length=100, description="Texto de búsqueda")
    Status: Optional[str] = Field(None, description="Filtrar por estado")
    IsActive: Optional[bool] = Field(None, description="Filtrar por estado activo")
    ServiceTypeId: Optional[int] = Field(None, description="Filtrar por tipo de servicio")
    Location: Optional[str] = Field(None, description="Filtrar por ubicación")

    model_config = {
        "json_schema_extra": {
            "example": {
                "Query": "ventanilla",
                "Status": "Available",
                "IsActive": True,
                "ServiceTypeId": 1,
                "Location": "Planta Baja"
            }
        }
    }


class StationDashboard(BaseModel):
    """Schema para dashboard de estaciones"""

    TotalStations: int = Field(0, description="Total de estaciones")
    ActiveStations: int = Field(0, description="Estaciones activas")
    AvailableStations: int = Field(0, description="Estaciones disponibles")
    BusyStations: int = Field(0, description="Estaciones ocupadas")
    InMaintenanceStations: int = Field(0, description="Estaciones en mantenimiento")

    # Estadísticas del día
    TotalTicketsToday: int = Field(0, description="Total tickets hoy")
    AverageWaitTimeToday: float = Field(0.0, description="Tiempo promedio de espera hoy")

    # Lista de estaciones con su estado
    StationsSummary: List[Dict[str, Any]] = Field(default_factory=list, description="Resumen de estaciones")

    model_config = {
        "json_schema_extra": {
            "example": {
                "TotalStations": 6,
                "ActiveStations": 6,
                "AvailableStations": 4,
                "BusyStations": 2,
                "InMaintenanceStations": 0,
                "TotalTicketsToday": 150,
                "AverageWaitTimeToday": 12.5,
                "StationsSummary": []
            }
        }
    }