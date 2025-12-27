"""
API endpoints para autenticación del sistema de gestión de colas
Compatible 100% con toda la estructura existente
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.core.database import get_db
from app.api.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    get_auth_info
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    ChangePasswordRequest, ResetPasswordRequest, UserInfo, TokenInfo,
    LogoutResponse
)
from app.services.auth_service import AuthService
from app.core.security import verify_token, check_password_strength
from app.core.redis import session_manager, cache_manager

# ========================================
# CONFIGURACIÓN DEL ROUTER
# ========================================

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# Inicializar servicio de autenticación
auth_service = AuthService()

# Configurar esquema de autenticación
security = HTTPBearer()


# ========================================
# ENDPOINTS DE AUTENTICACIÓN
# ========================================

@router.post("/login", response_model=LoginResponse)
async def login(
        request: Request,
        login_data: LoginRequest,
        db: Session = Depends(get_db)
):
    """
    Autentica un usuario y genera tokens de acceso

    - Valida credenciales (username/email + password)
    - Genera access_token y refresh_token
    - Registra sesión del usuario
    - Retorna información del usuario autenticado
    """
    try:
        logger.info(f"Intento de login para: {login_data.username}")

        # Obtener información del cliente
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Procesar login - NO await porque el método no es async
        login_response = auth_service.login(
            db=db,
            login_data=login_data,
            ip_address=client_ip,
            user_agent=user_agent
        )

        if not login_response:
            logger.warning(f"Login fallido para: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"Login exitoso para: {login_response.user['Username']}")
        return login_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
        refresh_data: RefreshTokenRequest,
        db: Session = Depends(get_db)
):
    """
    Renueva el token de acceso usando un refresh token válido

    - Valida el refresh token
    - Genera nuevo access token
    - Mantiene la sesión activa
    """
    try:
        logger.debug("Procesando renovación de token")

        # Renovar token usando el servicio - CORREGIDO
        refresh_response = auth_service.refresh_access_token(
            db=db,
            refresh_token=refresh_data.refresh_token  # Pasar el token directamente
        )

        if not refresh_response:
            logger.warning("Refresh token inválido o expirado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug("Token renovado exitosamente")
        return refresh_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renovando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
        current_user: User = Depends(get_current_user),
        credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Cierra la sesión del usuario actual

    - Invalida tokens de acceso y refresh
    - Limpia cache del usuario
    - Registra el logout
    """
    try:
        logger.info(f"Logout para usuario: {current_user.Username}")

        # Obtener el token actual
        access_token = credentials.credentials if credentials else None

        # Procesar logout usando el servicio - CORREGIDO
        success = auth_service.logout(
            user_id=str(current_user.Id),
            access_token=access_token
        )

        if success:
            logger.info(f"Logout exitoso para: {current_user.Username}")
            return LogoutResponse(
                message="Sesión cerrada correctamente",
                logged_out_at=datetime.utcnow()
            )
        else:
            logger.warning(f"Problema en logout para: {current_user.Username}")
            return LogoutResponse(
                message="Sesión cerrada (con advertencias)",
                logged_out_at=datetime.utcnow()
            )

    except Exception as e:
        logger.error(f"Error en logout: {e}")
        # Aún si hay error, consideramos exitoso el logout del lado del cliente
        return LogoutResponse(
            message="Sesión cerrada localmente",
            logged_out_at=datetime.utcnow()
        )


# ========================================
# GESTIÓN DE CONTRASEÑAS
# ========================================

@router.post("/change-password")
async def change_password(
        password_data: ChangePasswordRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Cambia la contraseña del usuario actual

    - Valida contraseña actual
    - Verifica fortaleza de nueva contraseña
    - Actualiza contraseña en base de datos
    - Invalida sesiones activas
    """
    try:
        logger.info(f"Cambio de contraseña para: {current_user.Username}")

        # Cambiar contraseña usando el servicio - CORREGIDO
        success = auth_service.change_password(
            db=db,
            user=current_user,
            change_data=password_data  # Cambiado de password_data a change_data
        )

        if success:
            logger.info(f"Contraseña cambiada para: {current_user.Username}")
            return {
                "message": "Contraseña actualizada correctamente",
                "success": True,
                "timestamp": datetime.utcnow()
            }
        else:
            logger.warning(f"Fallo cambio de contraseña para: {current_user.Username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual es incorrecta o la nueva contraseña no cumple los requisitos"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post("/reset-password")
async def reset_password(
        reset_data: ResetPasswordRequest,
        db: Session = Depends(get_db)
):
    """
    Resetea la contraseña de un usuario

    - Genera nueva contraseña temporal
    - Solo para usuarios que olvidaron su contraseña
    - Requiere cambio en próximo login
    """
    try:
        logger.info(f"Reset de contraseña solicitado para: {reset_data.username_or_email}")

        # Resetear contraseña usando el servicio - YA ESTÁ CORRECTO
        success, new_password = auth_service.reset_password(
            db=db,
            username=reset_data.username_or_email
        )

        if success:
            logger.info(f"Contraseña reseteada para: {reset_data.username_or_email}")
            return {
                "message": "Contraseña reseteada correctamente",
                "success": True,
                "temporary_password": new_password if new_password else None,
                "timestamp": datetime.utcnow()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reseteando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )



@router.post("/check-password-strength")
async def check_password_strength_endpoint(
        password: str = Body(..., embed=True)
):
    """
    Verifica la fortaleza de una contraseña

    - Analiza longitud, complejidad y patrones
    - Retorna score y recomendaciones
    - No almacena la contraseña
    """
    try:
        from app.core.security import check_password_strength

        strength_info = check_password_strength(password)

        return {
            "score": strength_info["score"],
            "max_score": strength_info["max_score"],
            "strength": strength_info["strength"],
            "is_strong": strength_info["is_strong"],
            "checks": strength_info["checks"],
            "recommendations": []  # Se puede agregar lógica para recomendaciones
        }

    except Exception as e:
        logger.error(f"Error verificando fortaleza de contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verificando contraseña"
        )


# ========================================
# INFORMACIÓN DEL USUARIO Y TOKENS
# ========================================

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene información del usuario actual

    - Datos básicos del perfil
    - Permisos y roles
    - Estación asignada
    - Última actividad
    """
    try:
        # Convertir usuario a UserInfo usando el servicio
        user_info = auth_service.user_to_info(current_user)
        return user_info

    except Exception as e:
        logger.error(f"Error obteniendo información del usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo información del usuario"
        )


@router.post("/verify-token")
async def verify_token_endpoint(
        token: str = Body(..., embed=True),
        token_type: str = Body("access", embed=True)
):
    """
    Verifica la validez de un token

    - Decodifica y valida el token
    - Retorna información del token
    - Útil para debugging y validación
    """
    try:
        # Verificar token usando el servicio
        token_info = auth_service.verify_token_info(token, token_type)

        if not token_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )

        return token_info.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verificando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verificando token"
        )


# ========================================
# INFORMACIÓN DEL SISTEMA DE AUTENTICACIÓN
# ========================================

@router.get("/info")
async def get_authentication_info(
        current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Obtiene información sobre el sistema de autenticación

    - Métodos disponibles
    - Estado del sistema
    - Información de sesión (si está autenticado)
    """
    try:
        # Obtener información básica del sistema
        auth_info = get_auth_info()

        # Agregar información de usuario si está autenticado
        if current_user:
            auth_info.update({
                "user_authenticated": True,
                "username": current_user.Username,
                "role": current_user.role.Name if current_user.role else None,
                "session_active": True
            })

            # Agregar estadísticas de sesiones activas si Redis está disponible
            if session_manager:
                try:
                    # Intentar obtener información de sesiones
                    session_key = f"session:{current_user.Id}"
                    session_exists = session_manager.exists(session_key)
                    auth_info["session_exists"] = session_exists
                except Exception as e:
                    logger.debug(f"Error obteniendo info de sesión: {e}")

        else:
            auth_info.update({
                "user_authenticated": False,
                "session_active": False
            })

        return auth_info

    except Exception as e:
        logger.error(f"Error obteniendo info del sistema de auth: {e}")
        # Retornar información básica en caso de error
        return {
            "authentication_method": "JWT Bearer Token",
            "system_status": "operational",
            "error": "Información limitada disponible"
        }


# ========================================
# ENDPOINTS DE MANTENIMIENTO
# ========================================

@router.post("/invalidate-cache")
async def invalidate_user_cache_endpoint(
        user_id: Optional[str] = Body(None, embed=True),
        current_user: User = Depends(require_admin)
):
    """
    Invalida el cache de usuario(s)

    - Solo administradores pueden usarlo
    - Si user_id es None, limpia todo el cache de usuarios
    - Útil para forzar recarga de permisos
    """
    try:
        logger.info(f"Invalidación de cache solicitada por: {current_user.Username}")

        # Importar función de invalidación
        from app.api.dependencies.auth import invalidate_user_cache, invalidate_all_user_cache

        if user_id:
            invalidate_user_cache(user_id)
            message = f"Cache invalidado para usuario: {user_id}"
        else:
            invalidate_all_user_cache()
            message = "Cache invalidado para todos los usuarios"

        logger.info(message)
        return {
            "message": message,
            "success": True,
            "timestamp": datetime.utcnow()
        }

    except Exception as e:
        logger.error(f"Error invalidando cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error invalidando cache"
        )


# ========================================
# ENDPOINT DE SALUD
# ========================================

@router.get("/health")
async def health_check():
    """
    Verifica el estado del servicio de autenticación

    - Estado del servicio
    - Disponibilidad de Redis
    - Versión del sistema
    """
    try:
        health_status = {
            "status": "healthy",
            "service": "authentication",
            "timestamp": datetime.utcnow(),
            "redis_available": session_manager is not None,
            "cache_available": cache_manager is not None
        }

        # Verificar conexión a Redis si está disponible
        if session_manager:
            try:
                session_manager.ping()
                health_status["redis_status"] = "connected"
            except Exception:
                health_status["redis_status"] = "disconnected"

        return health_status

    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return {
            "status": "degraded",
            "service": "authentication",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }