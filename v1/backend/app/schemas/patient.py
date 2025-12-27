from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime, date
from enum import Enum


class GenderEnum(str, Enum):
    """Enumeración para género"""
    MALE = "M"
    FEMALE = "F"
    OTHER = "Otro"


class DocumentTypeEnum(str, Enum):
    """Enumeración para tipos de documento"""
    DNI = "DNI"
    PASSPORT = "PASSPORT"
    CE = "CE"  # Carnet de Extranjería
    OTHER = "OTHER"


class PatientBase(BaseModel):
    """Schema base para paciente"""
    document_type: DocumentTypeEnum = Field(default=DocumentTypeEnum.DNI, description="Tipo de documento")
    document_number: str = Field(..., min_length=1, max_length=20, description="Número de documento")
    first_name: str = Field(..., min_length=1, max_length=100, description="Nombres")
    last_name: str = Field(..., min_length=1, max_length=100, description="Apellidos")
    birth_date: Optional[date] = Field(None, description="Fecha de nacimiento")
    gender: Optional[GenderEnum] = Field(None, description="Género")
    email: Optional[EmailStr] = Field(None, description="Correo electrónico")
    phone: Optional[str] = Field(None, max_length=20, description="Teléfono")
    address: Optional[str] = Field(None, max_length=255, description="Dirección")

    model_config = {
        "str_strip_whitespace": True,
    }


class PatientCreate(PatientBase):
    """Schema para crear paciente"""
    # Para crear, la fecha de nacimiento podría ser requerida dependiendo del negocio
    # Por ahora la dejamos opcional para que funcione con el servicio DNI
    birth_date: Optional[date] = None


class PatientUpdate(BaseModel):
    """Schema para actualizar paciente"""
    document_type: Optional[DocumentTypeEnum] = None
    document_number: Optional[str] = Field(None, min_length=1, max_length=20)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    birth_date: Optional[date] = None
    gender: Optional[GenderEnum] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class PatientResponse(BaseModel):
    """Schema para respuesta de paciente - mapea desde el modelo con campos mixtos"""
    id: str = Field(..., description="ID único del paciente")
    document_type: str = Field(default="DNI", description="Tipo de documento")
    document_number: str = Field(..., description="Número de documento")
    full_name: str = Field(..., description="Nombre completo")
    first_name: Optional[str] = Field(None, description="Nombres")
    last_name: Optional[str] = Field(None, description="Apellidos")
    birth_date: Optional[date] = Field(None, description="Fecha de nacimiento")
    gender: Optional[str] = Field(None, description="Género")
    email: Optional[str] = Field(None, description="Email")
    phone: Optional[str] = Field(None, description="Teléfono")
    age: Optional[int] = Field(None, description="Edad")
    is_active: bool = Field(True, description="Estado activo")
    CreatedAt: datetime = Field(..., description="Fecha de creación")
    UpdatedAt: datetime = Field(..., description="Fecha de actualización")

    class Config:
        orm_mode = True

    @classmethod
    def from_orm(cls, obj):
        """
        Crear desde objeto ORM con campos mixtos (PascalCase y snake_case)
        El modelo tiene:
        - Campos PascalCase: Id, DocumentNumber, FullName, BirthDate, Gender, Phone, Email, IsActive, Age
        - Campos snake_case: CreatedAt, UpdatedAt (por los mixins)
        """
        # Extraer nombres del FullName
        full_name_parts = obj.FullName.split() if obj.FullName else []
        first_name = full_name_parts[0] if full_name_parts else ""
        last_name = " ".join(full_name_parts[1:]) if len(full_name_parts) > 1 else ""

        return cls(
            id=str(obj.Id),  # Convertir GUID a string
            document_type="DNI",  # Por defecto DNI
            document_number=obj.DocumentNumber,
            full_name=obj.FullName,
            first_name=first_name,
            last_name=last_name,
            birth_date=obj.BirthDate,
            gender=obj.Gender,
            email=obj.Email,
            phone=obj.Phone,
            age=obj.Age or obj.current_age if hasattr(obj, 'current_age') else None,
            is_active=obj.IsActive,
            CreatedAt=obj.CreatedAt,  # snake_case por el mixin
            UpdatedAt=obj.UpdatedAt  # snake_case por el mixin
        )


class PatientSearch(BaseModel):
    """Schema para resultados de búsqueda rápida"""
    id: str
    document_number: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        orm_mode = True

    @classmethod
    def from_orm(cls, obj):
        """Crear desde objeto ORM con campos PascalCase"""
        return cls(
            id=str(obj.Id),
            document_number=obj.DocumentNumber,
            full_name=obj.FullName,
            email=obj.Email,
            phone=obj.Phone
        )


class CurrentTicketInfo(BaseModel):
    """Schema para información del ticket actual"""
    ticket_number: Optional[str] = Field(None, description="Número del ticket")
    status: Optional[str] = Field(None, description="Estado del ticket")
    service_name: Optional[str] = Field(None, description="Nombre del servicio")
    service_code: Optional[str] = Field(None, description="Código del servicio")
    CreatedAt: Optional[datetime] = Field(None, description="Fecha de creación")

    class Config:
        orm_mode = False  # No es un modelo ORM directo


class PatientWithQueueInfo(PatientResponse):
    """Schema para paciente con información de cola"""
    active_tickets: int = Field(0, description="Cantidad de tickets activos")
    current_ticket: Optional[CurrentTicketInfo] = Field(None, description="Información del ticket actual")
    total_visits: Optional[int] = Field(None, description="Total de visitas")
    last_visit: Optional[datetime] = Field(None, description="Última visita")

    class Config:
        orm_mode = True


class PatientStatistics(BaseModel):
    """Schema para estadísticas de pacientes"""
    total_patients: int = Field(..., description="Total de pacientes registrados")
    active_patients: int = Field(..., description="Pacientes activos")
    new_today: int = Field(..., description="Pacientes registrados hoy")
    with_tickets_today: int = Field(..., description="Pacientes con tickets hoy")