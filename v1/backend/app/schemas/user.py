"""
Schemas de Pydantic para gestión de usuarios
Corregido para coincidir exactamente con la tabla SQL Server
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

# ========================================
# ENUMS BÁSICOS
# ========================================

class UserStatus(str, Enum):
    """Estados de usuario"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class ActivityType(str, Enum):
    """Tipos de actividad de usuario"""
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PROFILE_UPDATE = "profile_update"
    STATION_ASSIGNMENT = "station_assignment"
    ROLE_CHANGE = "role_change"


# ========================================
# SCHEMAS BÁSICOS
# ========================================

class UserBase(BaseModel):
    """Schema base para usuario - solo campos que existen en la BD"""
    Username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    Email: EmailStr = Field(..., description="Email único del usuario")
    FullName: str = Field(..., min_length=2, max_length=200, description="Nombre completo")

    @field_validator('Username')
    @classmethod
    def validate_username(cls, v):
        """Normaliza el username a lowercase"""
        if v:
            return v.strip().lower()
        return v

    @field_validator('Email')
    @classmethod
    def validate_email(cls, v):
        """Normaliza el email a lowercase"""
        if v:
            return v.strip().lower()
        return v

    @field_validator('FullName')
    @classmethod
    def validate_fullname(cls, v):
        """Capitaliza cada palabra del nombre"""
        if v:
            return ' '.join(word.capitalize() for word in v.strip().split())
        return v

    model_config = {
        "str_strip_whitespace": True
    }


class UserCreate(UserBase):
    """Schema para crear usuario - campos requeridos para creación"""
    Password: str = Field(..., min_length=8, max_length=128, description="Contraseña del usuario")
    RoleId: int = Field(..., description="ID del rol a asignar")
    StationId: Optional[int] = Field(None, description="ID de estación inicial (opcional)")
    IsActive: bool = Field(True, description="Usuario activo por defecto")


class UserUpdate(BaseModel):
    """Schema para actualizar usuario - todos los campos son opcionales"""
    Email: Optional[EmailStr] = Field(None, description="Nuevo email")
    FullName: Optional[str] = Field(None, min_length=2, max_length=200, description="Nuevo nombre completo")
    RoleId: Optional[int] = Field(None, description="Nuevo rol")
    StationId: Optional[int] = Field(None, description="Nueva estación asignada")
    IsActive: Optional[bool] = Field(None, description="Estado activo/inactivo")

    @field_validator('Email')
    @classmethod
    def validate_email(cls, v):
        """Normaliza el email a lowercase"""
        if v:
            return v.strip().lower()
        return v

    @field_validator('FullName')
    @classmethod
    def validate_fullname(cls, v):
        """Capitaliza cada palabra del nombre"""
        if v:
            return ' '.join(word.capitalize() for word in v.strip().split())
        return v


# ========================================
# SCHEMAS DE RESPUESTA
# ========================================

class UserResponse(BaseModel):
    """Schema de respuesta para usuario - mapea campos reales de BD"""
    Id: str = Field(..., description="ID único del usuario")
    Username: str = Field(..., description="Nombre de usuario")
    Email: str = Field(..., description="Email del usuario")
    FullName: str = Field(..., description="Nombre completo")
    IsActive: bool = Field(..., description="Estado activo")

    # Información de rol
    RoleId: int = Field(..., description="ID del rol")
    role_name: Optional[str] = Field(None, description="Nombre del rol")

    # Información de estación
    StationId: Optional[int] = Field(None, description="ID de estación asignada")
    station_name: Optional[str] = Field(None, description="Nombre de la estación")
    station_code: Optional[str] = Field(None, description="Código de la estación")

    # Timestamps
    CreatedAt: datetime = Field(..., description="Fecha de creación")
    UpdatedAt: datetime = Field(..., description="Fecha de última actualización")
    LastLogin: Optional[datetime] = Field(None, description="Último login")

    # Campos calculados (vienen del modelo)
    permissions: List[str] = Field(default_factory=list, description="Lista de permisos")
    is_admin: bool = Field(False, description="Es administrador")
    is_supervisor: bool = Field(False, description="Es supervisor")
    is_agente: bool = Field(False, description="Es agente")
    can_attend_patients: bool = Field(False, description="Puede atender pacientes")
    days_since_last_login: Optional[int] = Field(None, description="Días desde último login")
    is_recently_active: bool = Field(False, description="Activo en últimos 7 días")

    model_config = {
        "from_attributes": True
    }


class UserListResponse(BaseModel):
    """Schema para respuesta de lista de usuarios"""
    users: List[UserResponse]
    total: int
    page: int = Field(1)
    size: int = Field(10)
    has_more: bool


# ========================================
# SCHEMAS DE BÚSQUEDA Y FILTROS
# ========================================

class UserSearchFilters(BaseModel):
    """Schema para filtros de búsqueda de usuarios"""
    search_term: Optional[str] = Field(None, max_length=100, description="Buscar en username, email o nombre")
    role_id: Optional[int] = Field(None, description="Filtrar por rol")
    is_active: Optional[bool] = Field(None, description="Filtrar por estado activo")
    station_id: Optional[int] = Field(None, description="Filtrar por estación")
    has_station: Optional[bool] = Field(None, description="Usuarios con/sin estación")
    created_from: Optional[date] = Field(None, description="Creados desde fecha")
    created_to: Optional[date] = Field(None, description="Creados hasta fecha")
    last_login_from: Optional[datetime] = Field(None, description="Login desde fecha")
    last_login_to: Optional[datetime] = Field(None, description="Login hasta fecha")


# ========================================
# SCHEMAS DE GESTIÓN DE CONTRASEÑAS
# ========================================

class ChangePasswordRequest(BaseModel):
    """Schema para cambio de contraseña"""
    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=8, max_length=128, description="Nueva contraseña")
    confirm_password: str = Field(..., description="Confirmar nueva contraseña")

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        """Valida que las contraseñas coincidan"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v


class ResetPasswordRequest(BaseModel):
    """Schema para reset de contraseña"""
    username_or_email: str = Field(..., description="Username o email del usuario")
    new_password: Optional[str] = Field(None, min_length=8, description="Nueva contraseña (si no se genera automática)")
    send_email: bool = Field(True, description="Enviar contraseña por email")


# ========================================
# SCHEMAS DE ASIGNACIONES
# ========================================

class UserStationAssignment(BaseModel):
    """Schema para asignar estación a usuario"""
    station_id: Optional[int] = Field(None, description="ID de estación (None para desasignar)")
    reason: Optional[str] = Field(None, max_length=200, description="Razón del cambio")


class UserRoleAssignment(BaseModel):
    """Schema para asignación de rol"""
    role_id: int = Field(..., description="ID del nuevo rol")
    reason: Optional[str] = Field(None, max_length=200, description="Razón del cambio")


# ========================================
# SCHEMAS DE ESTADÍSTICAS Y REPORTES
# ========================================

class UserStats(BaseModel):
    """Schema para estadísticas de usuarios"""
    total_users: int = Field(0, description="Total de usuarios")
    active_users: int = Field(0, description="Usuarios activos")
    inactive_users: int = Field(0, description="Usuarios inactivos")
    users_by_role: Dict[str, int] = Field(default_factory=dict, description="Usuarios por rol")
    users_with_stations: int = Field(0, description="Usuarios con estación asignada")
    users_without_stations: int = Field(0, description="Usuarios sin estación")
    recent_logins_7d: int = Field(0, description="Logins en últimos 7 días")
    recent_logins_30d: int = Field(0, description="Logins en últimos 30 días")
    average_session_time: float = Field(0.0, description="Tiempo promedio de sesión (minutos)")
    last_updated: datetime = Field(default_factory=datetime.now)


class UserDashboard(BaseModel):
    """Schema para dashboard de usuarios"""
    stats: UserStats
    top_active_users: List[Dict[str, Any]] = Field(default_factory=list, description="Usuarios más activos")
    recent_registrations: List[Dict[str, Any]] = Field(default_factory=list, description="Registros recientes")
    inactive_alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Usuarios inactivos por mucho tiempo")
    role_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribución por roles")
    station_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribución por estaciones")


class UserActivityLog(BaseModel):
    """Schema para log de actividad de usuario"""
    id: str
    user_id: str
    username: str
    activity_type: ActivityType
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: datetime


# ========================================
# SCHEMAS DE CREACIÓN MASIVA
# ========================================

class BulkUserCreate(BaseModel):
    """Schema para creación masiva de usuarios"""
    users: List[UserCreate] = Field(..., min_items=1, max_items=100, description="Lista de usuarios a crear")
    default_role_id: Optional[int] = Field(None, description="Rol por defecto si no se especifica")
    default_password: Optional[str] = Field(None, min_length=8, description="Contraseña por defecto")
    send_welcome_emails: bool = Field(True, description="Enviar emails de bienvenida")


class BulkUserResponse(BaseModel):
    """Schema para respuesta de creación masiva"""
    success_count: int = Field(0, description="Usuarios creados exitosamente")
    failed_count: int = Field(0, description="Usuarios que fallaron")
    created_users: List[UserResponse] = Field(default_factory=list, description="Usuarios creados")
    failed_users: List[Dict[str, str]] = Field(default_factory=list, description="Errores por usuario")


# ========================================
# SCHEMAS DE IMPORTACIÓN/EXPORTACIÓN
# ========================================

class UserExportRequest(BaseModel):
    """Schema para solicitud de exportación"""
    format: str = Field("csv", pattern="^(csv|excel|json)$", description="Formato de exportación")
    include_inactive: bool = Field(False, description="Incluir usuarios inactivos")
    role_ids: Optional[List[int]] = Field(None, description="Filtrar por roles")
    station_ids: Optional[List[int]] = Field(None, description="Filtrar por estaciones")


class UserImportRequest(BaseModel):
    """Schema para importación de usuarios"""
    file_format: str = Field(..., pattern="^(csv|excel|json)$", description="Formato del archivo")
    skip_errors: bool = Field(True, description="Continuar si hay errores")
    update_existing: bool = Field(False, description="Actualizar usuarios existentes")
    default_role_id: int = Field(..., description="Rol por defecto para nuevos usuarios")
    default_password: Optional[str] = Field(None, min_length=8, description="Contraseña por defecto")