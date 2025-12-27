"""
Schemas Pydantic para validación y serialización de datos de tipos de servicios
100% compatibles con el modelo SQLAlchemy ServiceType
ACTUALIZADO PARA PYDANTIC V2
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


# ========================================
# SCHEMAS BASE
# ========================================

class ServiceTypeBase(BaseModel):
    """Schema base para campos comunes de tipo de servicio - Compatible con modelo SQLAlchemy"""

    Code: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Código único del servicio (ej: LAB, RES, MUE)"
    )

    Name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nombre del tipo de servicio"
    )

    Description: Optional[str] = Field(
        None,
        max_length=500,
        description="Descripción detallada del servicio"
    )

    Priority: int = Field(
        1,
        ge=1,
        le=5,
        description="Prioridad del servicio (1=máxima, 5=mínima)"
    )

    AverageTimeMinutes: int = Field(
        10,
        gt=0,
        le=1440,  # Máximo 24 horas
        description="Tiempo promedio de atención en minutos"
    )

    TicketPrefix: str = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Prefijo para los números de ticket (ej: A, B, LAB)"
    )

    Color: str = Field(
        "#007bff",
        pattern=r"^#[0-9A-Fa-f]{6}$",  # Validar formato hexadecimal
        description="Color hexadecimal para la interfaz"
    )

    @field_validator('Code')
    @classmethod
    def validate_code(cls, v):
        """Valida y normaliza el código del servicio - Compatible con modelo SQLAlchemy"""
        if v:
            # Mismo procesamiento que en el modelo SQLAlchemy
            normalized_code = v.upper().strip()

            # Validar formato (solo letras, números y guiones)
            if not re.match(r'^[A-Z0-9\-_]{1,10}$', normalized_code):
                raise ValueError("El código debe contener solo letras, números, guiones y underscore")

            return normalized_code
        return v

    @field_validator('Name')
    @classmethod
    def validate_name(cls, v):
        """Valida el nombre del servicio"""
        if v:
            name = v.strip()
            if len(name) < 1:
                raise ValueError("El nombre es requerido")
            return name
        return v

    @field_validator('Description')
    @classmethod
    def validate_description(cls, v):
        """Valida y limpia la descripción"""
        if v:
            return v.strip()
        return v

    @field_validator('TicketPrefix')
    @classmethod
    def validate_ticket_prefix(cls, v):
        """Valida y normaliza el prefijo del ticket - Compatible con modelo SQLAlchemy"""
        if v:
            # Mismo procesamiento que en el modelo SQLAlchemy
            normalized_prefix = v.upper().strip()

            # Validar formato
            if not re.match(r'^[A-Z0-9]{1,5}$', normalized_prefix):
                raise ValueError("El prefijo debe contener solo letras y números (máximo 5 caracteres)")

            return normalized_prefix
        return v

    @field_validator('Color')
    @classmethod
    def validate_color(cls, v):
        """Valida que el color sea un código hexadecimal válido - Compatible con modelo SQLAlchemy"""
        if v:
            if not (v.startswith('#') and len(v) == 7):
                raise ValueError("El color debe ser un código hexadecimal válido (#RRGGBB)")

            # Validar que los caracteres sean hexadecimales válidos
            hex_part = v[1:]
            if not re.match(r'^[0-9A-Fa-f]{6}$', hex_part):
                raise ValueError("El color debe contener solo caracteres hexadecimales válidos")

            return v.upper()  # Normalizar a mayúsculas
        return v


# ========================================
# SCHEMAS PARA CREAR TIPOS DE SERVICIOS
# ========================================

class ServiceTypeCreate(ServiceTypeBase):
    """Schema para crear un nuevo tipo de servicio"""

    # Hereda todos los campos de ServiceTypeBase
    # Todos los campos requeridos están definidos en la base

    model_config = {
        "json_schema_extra": {
            "example": {
                "Code": "LAB",
                "Name": "Análisis de Laboratorio",
                "Description": "Toma de muestras y análisis clínicos generales",
                "Priority": 2,
                "AverageTimeMinutes": 15,
                "TicketPrefix": "A",
                "Color": "#007BFF"
            }
        }
    }


# ========================================
# SCHEMAS PARA ACTUALIZAR TIPOS DE SERVICIOS
# ========================================

class ServiceTypeUpdate(BaseModel):
    """Schema para actualizar datos de tipo de servicio existente"""

    # Todos los campos opcionales para updates parciales
    Code: Optional[str] = Field(None, min_length=1, max_length=10)
    Name: Optional[str] = Field(None, min_length=1, max_length=100)
    Description: Optional[str] = Field(None, max_length=500)
    Priority: Optional[int] = Field(None, ge=1, le=5)
    AverageTimeMinutes: Optional[int] = Field(None, gt=0, le=1440)
    TicketPrefix: Optional[str] = Field(None, min_length=1, max_length=5)
    Color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")

    # Usar los mismos validadores que ServiceTypeBase
    @field_validator('Code')
    @classmethod
    def validate_code(cls, v):
        if v:
            normalized_code = v.upper().strip()
            if not re.match(r'^[A-Z0-9\-_]{1,10}$', normalized_code):
                raise ValueError("El código debe contener solo letras, números, guiones y underscore")
            return normalized_code
        return v

    @field_validator('Name')
    @classmethod
    def validate_name(cls, v):
        if v:
            name = v.strip()
            if len(name) < 1:
                raise ValueError("El nombre es requerido")
            return name
        return v

    @field_validator('Description')
    @classmethod
    def validate_description(cls, v):
        if v:
            return v.strip()
        return v

    @field_validator('TicketPrefix')
    @classmethod
    def validate_ticket_prefix(cls, v):
        if v:
            normalized_prefix = v.upper().strip()
            if not re.match(r'^[A-Z0-9]{1,5}$', normalized_prefix):
                raise ValueError("El prefijo debe contener solo letras y números (máximo 5 caracteres)")
            return normalized_prefix
        return v

    @field_validator('Color')
    @classmethod
    def validate_color(cls, v):
        if v:
            if not (v.startswith('#') and len(v) == 7):
                raise ValueError("El color debe ser un código hexadecimal válido (#RRGGBB)")
            hex_part = v[1:]
            if not re.match(r'^[0-9A-Fa-f]{6}$', hex_part):
                raise ValueError("El color debe contener solo caracteres hexadecimales válidos")
            return v.upper()
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "Name": "Análisis de Laboratorio Actualizado",
                "Description": "Descripción actualizada del servicio",
                "Priority": 1,
                "AverageTimeMinutes": 12,
                "Color": "#28A745"
            }
        }
    }


# ========================================
# SCHEMAS PARA RESPUESTAS
# ========================================

class ServiceTypeResponse(ServiceTypeBase):
    """Schema para respuestas que incluyen datos completos de tipo de servicio"""

    Id: int = Field(..., description="ID único del tipo de servicio")

    # Campos de ActiveMixin
    IsActive: bool = Field(True, description="Estado activo/inactivo")

    # Campos de TimestampMixin (NOMBRES EXACTOS del modelo SQLAlchemy)
    CreatedAt: datetime = Field(..., description="Fecha de creación")
    UpdatedAt: Optional[datetime] = Field(None, description="Fecha de última actualización")

    # Propiedades calculadas adicionales (del modelo SQLAlchemy)
    priority_name: Optional[str] = Field(None, description="Nombre de la prioridad")
    is_high_priority: Optional[bool] = Field(None, description="Es prioridad alta (1 o 2)")
    station_count: Optional[int] = Field(None, description="Cantidad de estaciones asignadas")
    active_station_count: Optional[int] = Field(None, description="Estaciones activas")
    current_queue_count: Optional[int] = Field(None, description="Tickets en cola actualmente")

    model_config = {
        "from_attributes": True,  # Para usar con SQLAlchemy models
        "json_schema_extra": {
            "example": {
                "Id": 1,
                "Code": "LAB",
                "Name": "Análisis de Laboratorio",
                "Description": "Toma de muestras y análisis clínicos generales",
                "Priority": 2,
                "AverageTimeMinutes": 15,
                "TicketPrefix": "A",
                "Color": "#007BFF",
                "IsActive": True,
                "CreatedAt": "2024-03-15T10:00:00",
                "UpdatedAt": "2024-03-15T10:00:00",
                "priority_name": "Alta",
                "is_high_priority": True,
                "station_count": 3,
                "active_station_count": 2,
                "current_queue_count": 8
            }
        }
    }


# ========================================
# SCHEMAS PARA BÚSQUEDA Y FILTROS
# ========================================

class ServiceTypeSearchFilters(BaseModel):
    """Schema para filtros de búsqueda de tipos de servicios"""

    query: Optional[str] = Field(None, description="Búsqueda por texto libre")
    priority: Optional[int] = Field(None, ge=1, le=5, description="Filtrar por prioridad")
    is_active: Optional[bool] = Field(True, description="Filtrar por estado activo")
    has_stations: Optional[bool] = Field(None, description="Filtrar por asignación de estaciones")
    min_time: Optional[int] = Field(None, description="Tiempo mínimo de atención")
    max_time: Optional[int] = Field(None, description="Tiempo máximo de atención")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "análisis",
                "priority": 2,
                "is_active": True,
                "has_stations": True,
                "min_time": 5,
                "max_time": 30
            }
        }
    }


class ServiceTypeListResponse(BaseModel):
    """Schema para respuesta de lista de tipos de servicios"""

    services: List[ServiceTypeResponse] = Field(..., description="Lista de servicios")
    total: int = Field(..., description="Total de servicios")
    active_count: int = Field(..., description="Total de servicios activos")
    inactive_count: int = Field(..., description="Total de servicios inactivos")

    model_config = {
        "json_schema_extra": {
            "example": {
                "services": [
                    {
                        "Id": 1,
                        "Code": "LAB",
                        "Name": "Análisis de Laboratorio",
                        "IsActive": True
                    }
                ],
                "total": 1,
                "active_count": 1,
                "inactive_count": 0
            }
        }
    }


# ========================================
# SCHEMAS PARA ESTADÍSTICAS
# ========================================

class ServiceTypeStats(BaseModel):
    """Schema para estadísticas de un tipo de servicio"""

    service_id: int = Field(..., description="ID del servicio")
    service_name: str = Field(..., description="Nombre del servicio")
    service_code: str = Field(..., description="Código del servicio")
    total_tickets: int = Field(0, description="Total de tickets generados")
    attended_tickets: int = Field(0, description="Tickets atendidos")
    pending_tickets: int = Field(0, description="Tickets pendientes")
    average_wait_time: float = Field(0.0, description="Tiempo promedio de espera (minutos)")
    average_service_time: float = Field(0.0, description="Tiempo promedio de servicio (minutos)")
    completion_rate: float = Field(0.0, description="Tasa de completitud (%)")
    stations_assigned: int = Field(0, description="Estaciones asignadas")
    peak_hour: Optional[str] = Field(None, description="Hora pico de demanda")

    model_config = {
        "json_schema_extra": {
            "example": {
                "service_id": 1,
                "service_name": "Análisis de Laboratorio",
                "service_code": "LAB",
                "total_tickets": 150,
                "attended_tickets": 120,
                "pending_tickets": 30,
                "average_wait_time": 12.5,
                "average_service_time": 15.0,
                "completion_rate": 80.0,
                "stations_assigned": 3,
                "peak_hour": "10:00-11:00"
            }
        }
    }


# ========================================
# SCHEMAS PARA DASHBOARD
# ========================================

class ServiceTypeDashboard(BaseModel):
    """Schema para dashboard de tipos de servicios"""

    total_services: int = Field(0, description="Total de tipos de servicios")
    priority_distribution: dict = Field({}, description="Distribución por prioridad")
    average_service_time: float = Field(0.0, description="Tiempo promedio general")
    total_stations: int = Field(0, description="Total de estaciones")
    active_stations: int = Field(0, description="Estaciones activas")
    services_with_high_priority: int = Field(0, description="Servicios de alta prioridad")
    utilization_rate: float = Field(0.0, description="Tasa de utilización (%)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_services": 5,
                "priority_distribution": {
                    "priority_1": 1,
                    "priority_2": 2,
                    "priority_3": 1,
                    "priority_4": 1,
                    "priority_5": 0
                },
                "average_service_time": 13.2,
                "total_stations": 8,
                "active_stations": 6,
                "services_with_high_priority": 3,
                "utilization_rate": 75.0
            }
        }
    }


# ========================================
# SCHEMAS PARA CONFIGURACIÓN RÁPIDA
# ========================================

class ServiceTypeQuickSetup(BaseModel):
    """Schema para configuración rápida de servicios básicos"""

    include_default_services: bool = Field(True, description="Incluir servicios por defecto")
    custom_services: Optional[List[ServiceTypeCreate]] = Field(None, description="Servicios personalizados adicionales")

    model_config = {
        "json_schema_extra": {
            "example": {
                "include_default_services": True,
                "custom_services": [
                    {
                        "Code": "ESP",
                        "Name": "Servicios Especializados",
                        "Description": "Análisis especializados",
                        "Priority": 3,
                        "AverageTimeMinutes": 20,
                        "TicketPrefix": "E",
                        "Color": "#9C27B0"
                    }
                ]
            }
        }
    }


class ServiceTypeValidation(BaseModel):
    """Schema para validación de campos únicos"""

    is_valid: bool = Field(..., description="Si la validación es exitosa")
    field: str = Field(..., description="Campo validado (code/prefix)")
    value: str = Field(..., description="Valor validado")
    message: str = Field(..., description="Mensaje de validación")

    model_config = {
        "json_schema_extra": {
            "example": {
                "is_valid": True,
                "field": "code",
                "value": "LAB",
                "message": "El código está disponible"
            }
        }
    }


# ========================================
# SCHEMAS PARA BULK OPERATIONS
# ========================================

class BulkServiceTypeCreate(BaseModel):
    """Schema para crear múltiples tipos de servicios"""

    service_types: List[ServiceTypeCreate] = Field(
        ...,
        min_items=1,
        max_items=20,
        description="Lista de servicios a crear (máximo 20)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "service_types": [
                    {
                        "Code": "LAB",
                        "Name": "Análisis de Laboratorio",
                        "Priority": 2,
                        "AverageTimeMinutes": 15,
                        "TicketPrefix": "A",
                        "Color": "#007BFF"
                    },
                    {
                        "Code": "RES",
                        "Name": "Entrega de Resultados",
                        "Priority": 3,
                        "AverageTimeMinutes": 5,
                        "TicketPrefix": "R",
                        "Color": "#28A745"
                    }
                ]
            }
        }
    }


class BulkServiceTypeResponse(BaseModel):
    """Schema para respuesta de operaciones masivas"""

    created_services: List[ServiceTypeResponse] = Field(..., description="Servicios creados exitosamente")
    failed_services: List[dict] = Field(..., description="Servicios que fallaron al crear")
    success_count: int = Field(..., description="Cantidad de servicios creados")
    error_count: int = Field(..., description="Cantidad de errores")

    model_config = {
        "json_schema_extra": {
            "example": {
                "created_services": [
                    {
                        "Id": 1,
                        "Code": "LAB",
                        "Name": "Análisis de Laboratorio",
                        "IsActive": True
                    }
                ],
                "failed_services": [
                    {
                        "index": 1,
                        "error": "El código RES ya está en uso"
                    }
                ],
                "success_count": 1,
                "error_count": 1
            }
        }
    }