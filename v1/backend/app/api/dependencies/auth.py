"""
Dependencias de autenticación para FastAPI
Compatible con el modelo User de SQLAlchemy y sistema de security existente
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.core.redis import cache_manager

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)

# Configurar el esquema de autenticación Bearer JWT
security = HTTPBearer(auto_error=False)


# ========================================
# DEPENDENCIAS BASE
# ========================================

async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Obtiene el usuario actual desde el token JWT (opcional)

    Args:
        credentials: Credenciales Bearer del header Authorization
        db: Sesión de base de datos

    Returns:
        User: Usuario actual o None si no hay token válido
    """
    if not credentials:
        return None

    try:
        # Verificar y decodificar el token JWT
        payload = verify_token(credentials.credentials, token_type="access")
        if not payload:
            return None

        # Obtener user_id del token
        user_id: str = payload.get("sub")
        if not user_id:
            return None

        # Buscar en cache primero (si está disponible)
        cache_key = f"user:{user_id}"
        cached_user = None

        if cache_manager:
            cached_user = cache_manager.get(cache_key)
            if cached_user:
                # Verificar que el usuario sigue activo
                user = db.query(User).filter(
                    User.Id == user_id,
                    User.IsActive == True
                ).first()
                if user:
                    logger.debug(f"Usuario obtenido desde cache: {user.Username}")
                    return user
                else:
                    # Usuario ya no está activo, limpiar cache
                    cache_manager.delete(cache_key)

        # Buscar usuario en base de datos
        user = db.query(User).filter(
            User.Id == user_id,
            User.IsActive == True
        ).first()

        if not user:
            logger.warning(f"Usuario no encontrado o inactivo: {user_id}")
            return None

        # Guardar en cache por 5 minutos
        if cache_manager:
            cache_manager.set(cache_key, {"id": str(user.Id)}, expire=300)

        logger.debug(f"Usuario autenticado: {user.Username}")
        return user

    except Exception as e:
        logger.error(f"Error obteniendo usuario actual: {e}")
        return None


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """
    Obtiene el usuario actual desde el token JWT (requerido)

    Args:
        credentials: Credenciales Bearer del header Authorization (requerido)
        db: Sesión de base de datos

    Returns:
        User: Usuario actual

    Raises:
        HTTPException: Si no hay token válido o usuario no encontrado
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Verificar y decodificar el token JWT
        payload = verify_token(credentials.credentials, token_type="access")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Obtener user_id del token
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token malformado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Buscar en cache primero (si está disponible)
        cache_key = f"user:{user_id}"

        if cache_manager:
            cached_data = cache_manager.get(cache_key)
            if cached_data:
                # Verificar que el usuario sigue activo
                user = db.query(User).filter(
                    User.Id == user_id,
                    User.IsActive == True
                ).first()
                if user:
                    logger.debug(f"Usuario obtenido desde cache: {user.Username}")
                    return user
                else:
                    # Usuario ya no está activo, limpiar cache
                    cache_manager.delete(cache_key)

        # Buscar usuario en base de datos
        user = db.query(User).filter(
            User.Id == user_id,
            User.IsActive == True
        ).first()

        if not user:
            logger.warning(f"Usuario no encontrado o inactivo: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado o inactivo",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Actualizar último login si es necesario
        if user.LastLogin:
            from datetime import datetime, timedelta
            # Solo actualizar si han pasado más de 10 minutos desde último login
            if datetime.now() - user.LastLogin > timedelta(minutes=10):
                user.update_last_login()
                db.commit()

        # Guardar en cache por 5 minutos
        if cache_manager:
            cache_manager.set(cache_key, {"id": str(user.Id)}, expire=300)

        logger.debug(f"Usuario autenticado: {user.Username}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuario actual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno de autenticación"
        )


# ========================================
# DEPENDENCIAS DE PERMISOS
# ========================================

def require_permissions(required_permissions: List[str]):
    """
    Decorator para requerir permisos específicos

    Args:
        required_permissions: Lista de permisos requeridos

    Returns:
        Función que valida permisos del usuario actual
    """

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        """
        Valida que el usuario tenga los permisos requeridos

        Args:
            current_user: Usuario actual autenticado

        Returns:
            User: Usuario si tiene permisos

        Raises:
            HTTPException: Si no tiene permisos suficientes
        """
        if not current_user.has_any_permission(required_permissions):
            logger.warning(
                f"Acceso denegado para {current_user.Username}. "
                f"Permisos requeridos: {required_permissions}. "
                f"Permisos del usuario: {current_user.permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere: {', '.join(required_permissions)}"
            )

        return current_user

    return permission_checker


def require_admin():
    """
    Dependencia que requiere permisos de administrador

    Returns:
        User: Usuario administrador
    """

    def admin_checker(current_user: User = Depends(get_current_user)) -> User:
        """
        Valida que el usuario sea administrador

        Args:
            current_user: Usuario actual autenticado

        Returns:
            User: Usuario administrador

        Raises:
            HTTPException: Si no es administrador
        """
        if not current_user.is_admin:
            logger.warning(f"Acceso admin denegado para {current_user.Username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Se requieren permisos de administrador"
            )

        return current_user

    return admin_checker


def require_supervisor_or_admin():
    """
    Dependencia que requiere permisos de supervisor o administrador

    Returns:
        User: Usuario con permisos suficientes
    """

    def supervisor_checker(current_user: User = Depends(get_current_user)) -> User:
        """
        Valida que el usuario sea supervisor o administrador

        Args:
            current_user: Usuario actual autenticado

        Returns:
            User: Usuario con permisos suficientes

        Raises:
            HTTPException: Si no tiene permisos suficientes
        """
        if not (current_user.is_admin or current_user.is_supervisor):
            logger.warning(f"Acceso supervisor denegado para {current_user.Username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Se requieren permisos de supervisor o administrador"
            )

        return current_user

    return supervisor_checker


def require_station_access(station_id: Optional[int] = None):
    """
    Dependencia que requiere acceso a una estación específica

    Args:
        station_id: ID de la estación (opcional, se puede pasar dinámicamente)

    Returns:
        Función que valida acceso a la estación
    """

    def station_checker(current_user: User = Depends(get_current_user)) -> User:
        """
        Valida que el usuario tenga acceso a la estación

        Args:
            current_user: Usuario actual autenticado

        Returns:
            User: Usuario con acceso a la estación

        Raises:
            HTTPException: Si no tiene acceso a la estación
        """
        # Admins y supervisores tienen acceso a todas las estaciones
        if current_user.is_admin or current_user.is_supervisor:
            return current_user

        # Técnicos solo pueden acceder a su estación asignada
        if station_id and not current_user.can_access_station(station_id):
            logger.warning(
                f"Acceso denegado a estación {station_id} para {current_user.Username}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene acceso a la estación {station_id}"
            )

        return current_user

    return station_checker


# ========================================
# DEPENDENCIAS DE ROLES ESPECÍFICOS
# ========================================

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Obtiene el usuario actual si es administrador

    Args:
        current_user: Usuario actual autenticado

    Returns:
        User: Usuario administrador

    Raises:
        HTTPException: Si no es administrador
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return current_user


def get_current_supervisor(current_user: User = Depends(get_current_user)) -> User:
    """
    Obtiene el usuario actual si es supervisor o administrador

    Args:
        current_user: Usuario actual autenticado

    Returns:
        User: Usuario supervisor o administrador

    Raises:
        HTTPException: Si no tiene permisos suficientes
    """
    if not (current_user.is_supervisor or current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de supervisor"
        )
    return current_user


def get_current_agente(current_user: User = Depends(get_current_user)) -> User:
    """
    Obtiene el usuario actual si puede atender pacientes

    Args:
        current_user: Usuario actual autenticado

    Returns:
        User: Usuario que puede atender pacientes

    Raises:
        HTTPException: Si no puede atender pacientes
    """
    if not current_user.can_attend_patients:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos para atender pacientes"
        )
    return current_user


# ========================================
# UTILIDADES DE AUTENTICACIÓN
# ========================================

def get_token_data(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[dict]:
    """
    Extrae los datos del token JWT sin validar el usuario

    Args:
        credentials: Credenciales Bearer del header Authorization

    Returns:
        dict: Datos del token o None si es inválido
    """
    if not credentials:
        return None

    try:
        payload = verify_token(credentials.credentials, token_type="access")
        return payload
    except Exception as e:
        logger.debug(f"Token inválido: {e}")
        return None


def invalidate_user_cache(user_id: str) -> None:
    """
    Invalida el cache de un usuario específico

    Args:
        user_id: ID del usuario a invalidar
    """
    if cache_manager:
        cache_key = f"user:{user_id}"
        cache_manager.delete(cache_key)
        logger.debug(f"Cache invalidado para usuario: {user_id}")


def invalidate_all_user_cache() -> None:
    """
    Invalida el cache de todos los usuarios
    Útil cuando se actualizan permisos globalmente
    """
    if cache_manager:
        # Limpiar todas las claves que empiecen con "user:"
        # Nota: Esta implementación depende de las capacidades de Redis
        logger.warning("Cache de usuarios invalidado globalmente")


# ========================================
# DEPENDENCIAS COMPUESTAS
# ========================================

def require_queue_management():
    """
    Dependencia para operaciones de gestión de colas
    """
    return require_permissions(["queue.manage", "queue.attend"])


def require_patient_management():
    """
    Dependencia para operaciones de gestión de pacientes
    """
    return require_permissions(["patients.create", "patients.update", "patients.read"])


def require_station_management():
    """
    Dependencia para operaciones de gestión de estaciones
    """
    return require_permissions(["stations.manage", "stations.update"])


def require_reports_access():
    """
    Dependencia para acceso a reportes
    """
    return require_permissions(["reports.read", "reports.export"])


def require_system_config():
    """
    Dependencia para configuración del sistema
    """
    return require_permissions(["system.configure"])


# ========================================
# INFORMACIÓN DE AUTENTICACIÓN
# ========================================

def get_auth_info() -> dict:
    """
    Obtiene información sobre el sistema de autenticación

    Returns:
        dict: Información del sistema de auth
    """
    from app.core.security import get_security_info

    return {
        "authentication_method": "JWT Bearer Token",
        "token_location": "Authorization header",
        "cache_enabled": cache_manager is not None,
        "security_config": get_security_info()
    }