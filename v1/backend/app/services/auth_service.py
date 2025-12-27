"""
Servicio de autenticación para el sistema de gestión de colas
Compatible con toda la estructura existente de seguridad, CRUD y modelos
"""

from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import secrets

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, verify_token,
    create_password_hash, verify_password, generate_password,
    check_password_strength
)
from app.crud.user import user_crud
from app.crud.role import role_crud
from app.models.user import User
from app.models.role import Role
from app.schemas.auth import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    ChangePasswordRequest, ResetPasswordRequest, UserInfo, TokenInfo
)
from app.core.redis import session_manager, cache_manager

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)


# ========================================
# CLASE PRINCIPAL DEL SERVICIO
# ========================================

class AuthService:
    """
    Servicio principal de autenticación
    Maneja login, logout, tokens, permisos y sesiones
    """

    def __init__(self):
        """
        Inicializa el servicio de autenticación
        """
        self.token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def login(
            self,
            db: Session,
            login_data: LoginRequest,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None
    ) -> Optional[LoginResponse]:
        """
        Autentica un usuario y genera tokens de acceso

        Args:
            db: Sesión de base de datos
            login_data: Datos de login (username/email y password)
            ip_address: IP del cliente (opcional)
            user_agent: User agent del cliente (opcional)

        Returns:
            LoginResponse: Respuesta con tokens y datos del usuario, o None si falla
        """
        try:
            logger.info(f"Intento de login para: {login_data.username}")

            # Autenticar usuario
            user = user_crud.authenticate(
                db,
                username=login_data.username,
                password=login_data.password
            )

            if not user:
                logger.warning(f"Autenticación fallida para: {login_data.username}")
                return None

            # Verificar que el usuario esté activo
            if not user.IsActive:
                logger.warning(f"Usuario inactivo intentó login: {user.Username}")
                return None

            # Generar tokens
            access_token = create_access_token(
                data={
                    "sub": str(user.Id),
                    "username": user.Username,
                    "role": user.role.Name if user.role else None
                }
            )

            refresh_token = create_refresh_token(
                data={"sub": str(user.Id)}
            )

            # Actualizar último login
            user.LastLogin = datetime.utcnow()
            db.commit()

            # Crear sesión en Redis si está disponible
            if session_manager:
                try:
                    # Ajustado: create_session solo necesita user_id y metadata
                    session_data = {
                        "user_id": str(user.Id),
                        "username": user.Username,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    session_manager.create_session(
                        user_id=str(user.Id),
                        session_data=session_data
                    )
                except Exception as e:
                    logger.error(f"Error creando sesión en Redis: {e}")
                    # Continuar sin Redis

            # Limpiar cache del usuario
            if cache_manager:
                cache_key = f"user:{user.Id}"
                cache_manager.delete(cache_key)

            # Preparar respuesta - convertir UserInfo a dict
            user_info = self.user_to_info(user)

            return LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=self.token_expire_minutes * 60,
                user=user_info.model_dump()  # Convertir a diccionario
            )

        except Exception as e:
            logger.error(f"Error en login: {e}")
            return None

    def logout(
            self,
            user_id: str,
            access_token: str
    ) -> bool:
        """
        Cierra la sesión de un usuario

        Args:
            user_id: ID del usuario
            access_token: Token de acceso actual

        Returns:
            bool: True si el logout fue exitoso
        """
        try:
            # Invalidar sesión en Redis
            if session_manager:
                try:
                    # Intentar invalidar la sesión del usuario
                    session_manager.delete(f"session:{user_id}")
                except Exception as e:
                    logger.error(f"Error invalidando sesión en Redis: {e}")

            # Limpiar cache del usuario
            if cache_manager:
                try:
                    cache_key = f"user:{user_id}"
                    cache_manager.delete(cache_key)
                except Exception as e:
                    logger.error(f"Error limpiando cache: {e}")

            logger.info(f"Logout exitoso para usuario: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error en logout: {e}")
            return False

    def refresh_access_token(
            self,
            db: Session,
            refresh_token: str
    ) -> Optional[RefreshTokenResponse]:
        """
        Genera un nuevo access token usando el refresh token

        Args:
            db: Sesión de base de datos
            refresh_token: Refresh token válido

        Returns:
            RefreshTokenResponse: Nuevo access token o None si falla
        """
        try:
            # Verificar refresh token
            payload = verify_token(refresh_token, token_type="refresh")
            if not payload:
                return None

            user_id = payload.get("sub")
            if not user_id:
                return None

            # Buscar usuario
            user = user_crud.get(db, id=user_id)
            if not user or not user.IsActive:
                return None

            # Generar nuevo access token
            new_access_token = create_access_token(
                data={
                    "sub": str(user.Id),
                    "username": user.Username,
                    "role": user.role.Name if user.role else None
                }
            )

            # Actualizar sesión en Redis si está disponible
            if session_manager:
                try:
                    # Actualizar datos de sesión
                    session_data = {
                        "user_id": str(user.Id),
                        "username": user.Username,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    session_manager.set(f"session:{user.Id}", session_data, expire=3600)
                except Exception as e:
                    logger.error(f"Error actualizando sesión en Redis: {e}")

            return RefreshTokenResponse(
                access_token=new_access_token,
                token_type="bearer",
                expires_in=self.token_expire_minutes * 60
            )

        except Exception as e:
            logger.error(f"Error refrescando token: {e}")
            return None

    def change_password(
            self,
            db: Session,
            user: User,
            change_data: ChangePasswordRequest
    ) -> bool:
        """
        Cambia la contraseña de un usuario

        Args:
            db: Sesión de base de datos
            user: Usuario que cambia la contraseña
            change_data: Datos del cambio (contraseña actual y nueva)

        Returns:
            bool: True si el cambio fue exitoso
        """
        try:
            # Verificar contraseña actual
            if not verify_password(change_data.current_password, user.PasswordHash):
                logger.warning(f"Contraseña actual incorrecta para: {user.Username}")
                return False

            # Verificar que la nueva contraseña sea diferente
            if change_data.current_password == change_data.new_password:
                logger.warning(f"Nueva contraseña igual a la actual para: {user.Username}")
                return False

            # Verificar fortaleza de la nueva contraseña
            strength = check_password_strength(change_data.new_password)
            if not strength.get("is_strong", False):
                logger.warning(f"Contraseña débil rechazada para: {user.Username}")
                return False

            # Actualizar contraseña
            user.PasswordHash = create_password_hash(change_data.new_password)
            db.commit()

            # Invalidar todas las sesiones del usuario
            if session_manager:
                try:
                    session_manager.delete(f"session:{user.Id}")
                except Exception as e:
                    logger.error(f"Error invalidando sesiones: {e}")

            logger.info(f"Contraseña cambiada exitosamente para: {user.Username}")
            return True

        except Exception as e:
            logger.error(f"Error cambiando contraseña: {e}")
            db.rollback()
            return False

    def reset_password(
            self,
            db: Session,
            username: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Resetea la contraseña de un usuario

        Args:
            db: Sesión de base de datos
            username: Username o email del usuario

        Returns:
            Tuple[bool, Optional[str]]: (éxito, nueva_contraseña_temporal)
        """
        try:
            # Buscar usuario por username o email
            user = user_crud.get_by_username(db, username=username)
            if not user:
                user = user_crud.get_by_email(db, email=username)

            if not user:
                logger.warning(f"Usuario no encontrado para reset: {username}")
                return False, None

            # Generar nueva contraseña temporal
            new_password = generate_password()

            # Actualizar contraseña
            user.PasswordHash = create_password_hash(new_password)
            db.commit()

            # Invalidar todas las sesiones del usuario
            if session_manager:
                try:
                    session_manager.delete(f"session:{user.Id}")
                except Exception as e:
                    logger.error(f"Error invalidando sesiones: {e}")

            logger.info(f"Contraseña reseteada para usuario: {user.Username}")
            return True, new_password

        except Exception as e:
            logger.error(f"Error reseteando contraseña: {e}")
            db.rollback()
            return False, None

    def verify_token_info(
            self,
            token: str,
            token_type: str = "access"
    ) -> Optional[TokenInfo]:
        """
        Verifica y obtiene información de un token

        Args:
            token: Token a verificar
            token_type: Tipo de token (access/refresh)

        Returns:
            TokenInfo: Información del token o None si es inválido
        """
        try:
            payload = verify_token(token, token_type=token_type)
            if not payload:
                return None

            # Calcular tiempos
            iat = payload.get("iat", 0)
            exp = payload.get("exp", 0)
            issued_at = datetime.fromtimestamp(iat) if iat else None
            expires_at = datetime.fromtimestamp(exp) if exp else None
            is_expired = datetime.utcnow() > expires_at if expires_at else True

            return TokenInfo(
                token_type=token_type,
                user_id=payload.get("sub", ""),
                username=payload.get("username", ""),
                issued_at=issued_at,
                expires_at=expires_at,
                is_expired=is_expired,
                permissions=payload.get("permissions", [])
            )

        except Exception as e:
            logger.error(f"Error verificando token: {e}")
            return None

    def user_to_info(self, user: User) -> UserInfo:
        """
        Convierte un modelo User a UserInfo schema

        Args:
            user: Modelo User de SQLAlchemy

        Returns:
            UserInfo: Schema con información del usuario
        """
        try:
            # Calcular días desde último login
            days_since_login = 0
            if user.LastLogin:
                delta = datetime.utcnow() - user.LastLogin
                days_since_login = delta.days

            return UserInfo(
                Id=str(user.Id),
                Username=user.Username,
                FullName=user.FullName,
                Email=user.Email,
                role_name=user.role.Name if user.role else None,
                station_name=user.station.Name if user.station else None,
                station_code=user.station.Code if user.station else None,
                permissions=user.role.permissions_list if user.role else [],
                IsActive=user.IsActive,
                LastLogin=user.LastLogin,
                is_admin=user.role.Name == "Admin" if user.role else False,
                is_supervisor=user.role.Name == "Supervisor" if user.role else False,
                is_agente=user.role.Name == "Agente" if user.role else False,
                can_attend_patients=True if user.role and user.role.Name in ["Admin", "Agente"] else False,
                days_since_last_login=days_since_login
            )

        except Exception as e:
            logger.error(f"Error convirtiendo usuario a info: {e}")
            # Retornar información mínima en caso de error
            return UserInfo(
                Id=str(user.Id),
                Username=user.Username,
                FullName=user.FullName or user.Username,
                Email=user.Email,
                role_name="Unknown",
                permissions=[],
                IsActive=user.IsActive,
                is_admin=False,
                is_supervisor=False,
                is_agente=False,
                can_attend_patients=False,
                days_since_last_login=0
            )

    def create_default_admin(self, db: Session) -> Optional[User]:
        """
        Crea el usuario administrador por defecto

        Args:
            db: Sesión de base de datos

        Returns:
            User: Usuario admin creado o existente
        """
        try:
            # Verificar si ya existe un admin
            existing_admin = user_crud.get_by_username(db, username="admin")
            if existing_admin:
                logger.info("Usuario admin ya existe")
                return existing_admin

            # Buscar rol de admin
            admin_role = role_crud.get_by_name(db, name="Admin")
            if not admin_role:
                logger.error("Rol Admin no encontrado - creándolo")
                admin_role = role_crud.create_default_roles(db).get("Admin")

            if not admin_role:
                logger.error("No se pudo crear el rol Admin")
                return None

            # Crear usuario admin
            admin_data = {
                "Username": "admin",
                "Email": "admin@laboratorio.com",
                "PasswordHash": create_password_hash("admin123"),
                "FullName": "Administrador del Sistema",
                "RoleId": admin_role.Id,
                "IsActive": True
            }

            admin_user = User(**admin_data)
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

            logger.info("Usuario admin creado exitosamente")
            return admin_user

        except Exception as e:
            logger.error(f"Error creando usuario admin: {e}")
            db.rollback()
            return None

    def validate_system_setup(self, db: Session) -> Dict[str, Any]:
        """
        Valida que el sistema de autenticación esté configurado correctamente

        Args:
            db: Sesión de base de datos

        Returns:
            Dict[str, Any]: Resultado de la validación
        """
        try:
            issues = []
            warnings = []

            # Verificar que existan roles
            roles = db.query(Role).all()
            if not roles:
                issues.append("No hay roles creados en el sistema")
            else:
                # Verificar roles básicos
                role_names = [r.Name for r in roles]
                required_roles = ["Admin", "Supervisor", "Agente", "Receptionist"]
                missing_roles = [r for r in required_roles if r not in role_names]
                if missing_roles:
                    warnings.append(f"Roles faltantes: {', '.join(missing_roles)}")

            # Verificar que exista al menos un admin
            admin_users = db.query(User).join(Role).filter(Role.Name == "Admin").all()
            if not admin_users:
                issues.append("No hay usuarios administradores en el sistema")

            # Verificar configuración de seguridad
            if len(settings.SECRET_KEY) < 32:
                warnings.append("La clave secreta es muy corta (recomendado mínimo 32 caracteres)")

            # Verificar Redis
            redis_available = session_manager is not None
            if not redis_available:
                warnings.append("Redis no disponible - sin cache de sesiones")

            return {
                "is_valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "roles_count": len(roles),
                "admin_count": len(admin_users),
                "redis_available": redis_available
            }

        except Exception as e:
            logger.error(f"Error validando setup de auth: {e}")
            return {
                "is_valid": False,
                "issues": [f"Error de validación: {str(e)}"],
                "warnings": [],
                "roles_count": 0,
                "admin_count": 0,
                "redis_available": False
            }


# ========================================
# INSTANCIA GLOBAL DEL SERVICIO
# ========================================

auth_service = AuthService()


# ========================================
# FUNCIONES DE UTILIDAD
# ========================================

def get_auth_service() -> AuthService:
    """
    Obtiene la instancia del servicio de autenticación

    Returns:
        AuthService: Instancia del servicio
    """
    return auth_service


def initialize_auth_system(db: Session) -> Dict[str, Any]:
    """
    Inicializa el sistema de autenticación

    Args:
        db: Sesión de base de datos

    Returns:
        Dict[str, Any]: Resultado de la inicialización
    """
    try:
        logger.info("Inicializando sistema de autenticación...")

        # Crear roles por defecto
        roles = role_crud.create_default_roles(db)
        logger.info(f"Roles por defecto: {list(roles.keys())}")

        # Crear admin por defecto
        admin_user = auth_service.create_default_admin(db)

        # Validar configuración
        validation = auth_service.validate_system_setup(db)

        result = {
            "success": True,
            "created_roles": list(roles.keys()),
            "admin_created": admin_user is not None,
            "validation": validation
        }

        logger.info("Sistema de autenticación inicializado correctamente")
        return result

    except Exception as e:
        logger.error(f"Error inicializando sistema de auth: {e}")
        return {
            "success": False,
            "error": str(e),
            "created_roles": [],
            "admin_created": False,
            "validation": {"is_valid": False}
        }