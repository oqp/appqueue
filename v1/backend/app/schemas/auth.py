"""
Schemas Pydantic para autenticación y autorización
100% compatibles con el modelo SQLAlchemy User y sistema de security existente
ACTUALIZADO PARA PYDANTIC V2
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


# ========================================
# SCHEMAS PARA LOGIN
# ========================================

class LoginRequest(BaseModel):
    """Schema para request de login"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Nombre de usuario o email"
    )

    password: str = Field(
        ...,
        min_length=4,
        max_length=100,
        description="Contraseña del usuario"
    )

    remember_me: bool = Field(
        False,
        description="Mantener sesión activa por más tiempo"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Valida el formato del username"""
        if v:
            v = v.strip().lower()
            # Permitir username o email
            if '@' in v:
                # Validar como email
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, v):
                    raise ValueError('Formato de email inválido')
            else:
                # Validar como username
                if not re.match(r'^[a-zA-Z0-9_]{3,50}$', v):
                    raise ValueError('Username debe tener 3-50 caracteres (letras, números y _)')
            return v
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Valida que la contraseña no esté vacía"""
        if v:
            return v.strip()
        raise ValueError('La contraseña es requerida')

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "admin",
                "password": "admin123",
                "remember_me": False
            }
        }
    }


class LoginResponse(BaseModel):
    """Schema para respuesta de login exitoso"""

    access_token: str = Field(..., description="Token JWT de acceso")
    refresh_token: str = Field(..., description="Token JWT para renovar acceso")
    token_type: str = Field("bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")

    # Información del usuario
    user: dict = Field(..., description="Información básica del usuario")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "Id": "123e4567-e89b-12d3-a456-426614174000",
                    "Username": "admin",
                    "FullName": "Administrador del Sistema",
                    "Email": "admin@laboratorio.com",
                    "role_name": "Admin",
                    "station_name": None,
                    "permissions": ["users.create", "users.read", "users.update"]
                }
            }
        }
    }


# ========================================
# SCHEMAS PARA REFRESH TOKEN
# ========================================

class RefreshTokenRequest(BaseModel):
    """Schema para renovar token de acceso"""

    refresh_token: str = Field(..., description="Token de refresh válido")

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }


class RefreshTokenResponse(BaseModel):
    """Schema para respuesta de refresh token"""

    access_token: str = Field(..., description="Nuevo token JWT de acceso")
    token_type: str = Field("bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
    }


# ========================================
# SCHEMAS PARA CAMBIO DE CONTRASEÑA
# ========================================

class ChangePasswordRequest(BaseModel):
    """Schema para cambiar contraseña"""

    current_password: str = Field(..., description="Contraseña actual")
    new_password: str = Field(..., min_length=6, description="Nueva contraseña")
    confirm_password: str = Field(..., description="Confirmación de nueva contraseña")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """Valida fortaleza de la nueva contraseña"""
        if len(v) < 6:
            raise ValueError('La nueva contraseña debe tener al menos 6 caracteres')

        # Verificar que tenga al menos una letra y un número
        if not re.search(r'[a-zA-Z]', v) or not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos una letra y un número')

        return v

    def model_post_init(self, __context):
        """Validación después de inicialización"""
        if self.new_password != self.confirm_password:
            raise ValueError('Las contraseñas no coinciden')

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_password": "oldpass123",
                "new_password": "newpass456",
                "confirm_password": "newpass456"
            }
        }
    }


class ResetPasswordRequest(BaseModel):
    """Schema para solicitar reset de contraseña"""

    username_or_email: str = Field(..., description="Username o email del usuario")

    @field_validator('username_or_email')
    @classmethod
    def validate_username_or_email(cls, v):
        if v:
            return v.strip().lower()
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "username_or_email": "admin@laboratorio.com"
            }
        }
    }


# ========================================
# SCHEMAS DE INFORMACIÓN DE USUARIO
# ========================================

class UserInfo(BaseModel):
    """Schema para información del usuario actual"""

    Id: str = Field(..., description="ID único del usuario")
    Username: str = Field(..., description="Nombre de usuario")
    FullName: str = Field(..., description="Nombre completo")
    Email: str = Field(..., description="Correo electrónico")
    role_name: Optional[str] = Field(None, description="Nombre del rol")
    station_name: Optional[str] = Field(None, description="Nombre de estación asignada")
    station_code: Optional[str] = Field(None, description="Código de estación asignada")
    permissions: List[str] = Field([], description="Lista de permisos")
    IsActive: bool = Field(True, description="Estado activo")
    LastLogin: Optional[datetime] = Field(None, description="Último login")

    # Propiedades calculadas
    is_admin: bool = Field(False, description="Es administrador")
    is_supervisor: bool = Field(False, description="Es supervisor")
    is_agente: bool = Field(False, description="Es agente")
    can_attend_patients: bool = Field(False, description="Puede atender pacientes")
    days_since_last_login: Optional[int] = Field(None, description="Días desde último login")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "Id": "123e4567-e89b-12d3-a456-426614174000",
                "Username": "admin",
                "FullName": "Administrador del Sistema",
                "Email": "admin@laboratorio.com",
                "role_name": "Admin",
                "station_name": None,
                "station_code": None,
                "permissions": ["users.create", "users.read", "tickets.create"],
                "IsActive": True,
                "LastLogin": "2024-03-15T10:30:00",
                "is_admin": True,
                "is_supervisor": False,
                "is_agente": False,
                "can_attend_patients": True,
                "days_since_last_login": 0
            }
        }
    }


# ========================================
# SCHEMAS PARA VERIFICACIÓN DE TOKENS
# ========================================

class TokenInfo(BaseModel):
    """Schema para información de un token"""

    token_type: str = Field(..., description="Tipo de token (access/refresh)")
    user_id: str = Field(..., description="ID del usuario")
    username: str = Field(..., description="Username del usuario")
    issued_at: datetime = Field(..., description="Fecha de emisión")
    expires_at: datetime = Field(..., description="Fecha de expiración")
    is_expired: bool = Field(..., description="Si el token está expirado")
    permissions: List[str] = Field([], description="Permisos del usuario")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token_type": "access",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "admin",
                "issued_at": "2024-03-15T10:30:00",
                "expires_at": "2024-03-15T11:30:00",
                "is_expired": False,
                "permissions": ["users.create", "users.read"]
            }
        }
    }


class VerifyTokenRequest(BaseModel):
    """Schema para verificar un token"""

    token: str = Field(..., description="Token a verificar")
    token_type: str = Field("access", description="Tipo de token esperado")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "access"
            }
        }
    }


# ========================================
# SCHEMAS PARA SESIONES
# ========================================

class SessionInfo(BaseModel):
    """Schema para información de sesión activa"""

    session_id: str = Field(..., description="ID de la sesión")
    user_id: str = Field(..., description="ID del usuario")
    username: str = Field(..., description="Username del usuario")
    ip_address: Optional[str] = Field(None, description="Dirección IP")
    user_agent: Optional[str] = Field(None, description="Navegador/dispositivo")
    created_at: datetime = Field(..., description="Fecha de creación")
    last_activity: datetime = Field(..., description="Última actividad")
    expires_at: datetime = Field(..., description="Fecha de expiración")
    is_active: bool = Field(True, description="Sesión activa")

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "sess_123456789",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "admin",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "created_at": "2024-03-15T10:30:00",
                "last_activity": "2024-03-15T10:45:00",
                "expires_at": "2024-03-15T18:30:00",
                "is_active": True
            }
        }
    }


# ========================================
# SCHEMAS PARA PERMISOS Y ROLES
# ========================================

class PermissionCheck(BaseModel):
    """Schema para verificar permisos"""

    permissions: List[str] = Field(..., description="Lista de permisos a verificar")
    require_all: bool = Field(False, description="Si requiere todos los permisos o solo uno")

    model_config = {
        "json_schema_extra": {
            "example": {
                "permissions": ["users.create", "users.update"],
                "require_all": False
            }
        }
    }


class PermissionCheckResponse(BaseModel):
    """Schema para respuesta de verificación de permisos"""

    has_permission: bool = Field(..., description="Si tiene los permisos requeridos")
    user_permissions: List[str] = Field(..., description="Permisos del usuario")
    required_permissions: List[str] = Field(..., description="Permisos requeridos")
    missing_permissions: List[str] = Field(..., description="Permisos faltantes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "has_permission": True,
                "user_permissions": ["users.create", "users.read", "users.update"],
                "required_permissions": ["users.create", "users.update"],
                "missing_permissions": []
            }
        }
    }


# ========================================
# SCHEMAS PARA RESPUESTAS GENERALES
# ========================================

class LogoutResponse(BaseModel):
    """Schema para respuesta de logout"""

    message: str = Field("Logout exitoso", description="Mensaje de confirmación")
    logged_out_at: datetime = Field(..., description="Fecha y hora del logout")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Logout exitoso",
                "logged_out_at": "2024-03-15T10:45:00"
            }
        }
    }


class AuthMessage(BaseModel):
    """Schema para mensajes generales de autenticación"""

    message: str = Field(..., description="Mensaje descriptivo")
    success: bool = Field(True, description="Si la operación fue exitosa")
    timestamp: datetime = Field(..., description="Fecha y hora del mensaje")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Contraseña actualizada correctamente",
                "success": True,
                "timestamp": "2024-03-15T10:45:00"
            }
        }
    }


# ========================================
# SCHEMAS PARA ERRORES DE AUTENTICACIÓN
# ========================================

class AuthError(BaseModel):
    """Schema para errores de autenticación"""

    error: str = Field(..., description="Tipo de error")
    message: str = Field(..., description="Mensaje descriptivo del error")
    timestamp: datetime = Field(..., description="Fecha y hora del error")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "invalid_credentials",
                "message": "Usuario o contraseña incorrectos",
                "timestamp": "2024-03-15T10:45:00"
            }
        }
    }