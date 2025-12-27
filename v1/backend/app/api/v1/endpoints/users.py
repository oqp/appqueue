"""
API endpoints para gestión de usuarios del sistema de gestión de colas
Compatible 100% con toda la estructura existente del proyecto
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Path, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.crud.user import user_crud
from datetime import datetime, date, timedelta
import logging

from app.core.database import get_db
from app.api.dependencies.auth import (
    get_current_user,
    require_permissions,
    require_admin,
    require_supervisor_or_admin,
    invalidate_user_cache
)
from app.models.user import User
from app.models.role import Role
from app.models.station import Station
from app.models.activity_log import ActivityLog
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, UserSearchFilters,
    UserStats, UserDashboard, ChangePasswordRequest, UserStationAssignment,
    UserRoleAssignment, UserActivityLog, BulkUserCreate, BulkUserResponse,
    UserExportRequest, UserImportRequest
)
from app.schemas.auth import UserInfo

from app.crud.role import role_crud
from app.crud.station import station_crud
from app.services.auth_service import AuthService
from app.core.security import (
    check_password_strength,
    create_password_hash,
    generate_password,
    verify_password
)
from app.core.redis import cache_manager

# ========================================
# CONFIGURACIÓN DEL ROUTER
# ========================================

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)

# Inicializar servicio de autenticación
auth_service = AuthService()


# ========================================
# FUNCIONES AUXILIARES
# ========================================

def _user_to_response(user: User) -> UserResponse:
    """
    Convierte un modelo User a UserResponse

    Args:
        user: Modelo User de SQLAlchemy

    Returns:
        UserResponse: Schema de respuesta
    """
    return UserResponse(
        Id=str(user.Id),
        Username=user.Username,
        Email=user.Email,
        FullName=user.FullName,
        IsActive=user.IsActive,
        RoleId=user.RoleId,
        role_name=user.role_name,
        StationId=user.StationId,
        station_name=user.station_name,
        station_code=user.station_code,
        CreatedAt=user.CreatedAt,
        UpdatedAt=user.UpdatedAt,
        LastLogin=user.LastLogin,
        permissions=user.permissions,
        is_admin=user.is_admin,
        is_supervisor=user.is_supervisor,
        is_agente=user.is_agente,
        can_attend_patients=user.can_attend_patients,
        days_since_last_login=user.days_since_last_login,
        is_recently_active=user.is_recently_active
    )


def _log_user_activity(
        db: Session,
        user_id: str,
        action: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
):
    """
    Registra actividad del usuario

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        action: Acción realizada
        details: Detalles adicionales
        ip_address: IP del usuario
    """
    try:
        activity_log = ActivityLog.create_log(
            action=action,
            user_id=user_id,
            details={"description": details} if details else None,
            ip_address=ip_address
        )
        db.add(activity_log)
        db.commit()
    except Exception as e:
        logger.error(f"Error registrando actividad: {e}")


# ========================================
# ENDPOINTS CRUD BÁSICOS
# ========================================

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
        user_data: UserCreate,
        auto_generate_password: bool = Query(False, description="Generar contraseña automática"),
        send_welcome_email: bool = Query(True, description="Enviar email de bienvenida"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permissions(["users.create"]))
):
    """
    Crea un nuevo usuario

    - Requiere permisos de creación de usuarios
    - Validación de username y email únicos
    - Generación opcional de contraseña automática
    - Envío opcional de email de bienvenida
    """
    try:
        logger.info(f"Creando usuario {user_data.Username} por {current_user.Username}")

        # Verificar que username no exista
        if user_crud.get_by_username(db, username=user_data.Username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya existe"
            )

        # Verificar que email no exista
        if user_crud.get_by_email(db, email=user_data.Email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )

        # Verificar que el rol exista
        role = role_crud.get(db, id=user_data.RoleId)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado"
            )

        # Verificar estación si se proporciona
        if user_data.StationId:
            station = station_crud.get(db, id=user_data.StationId)
            if not station:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Estación no encontrada"
                )

        # Generar contraseña si es necesario
        password = user_data.Password
        if auto_generate_password:
            password = generate_password()
            logger.info(f"Contraseña generada automáticamente para {user_data.Username}")

        # Validar fortaleza de contraseña
        if not auto_generate_password:
            password_strength = check_password_strength(password)
            if not password_strength["is_strong"]:
                # Construir errores basados en checks fallidos
                failed_checks = [k for k, v in password_strength["checks"].items() if not v]
                # ... generar mensajes apropiados

        # Crear usuario
        new_user = user_crud.create_user(
            db,
            username=user_data.Username,
            email=user_data.Email,
            password=password,
            full_name=user_data.FullName,
            role_id=user_data.RoleId,
            station_id=user_data.StationId
        )

        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creando usuario"
            )

        # Enviar email de bienvenida si es necesario
        if send_welcome_email:
            # TODO: Implementar envío de email
            logger.info(f"Email de bienvenida enviado a {new_user.Email}")

        # Registrar actividad
        _log_user_activity(
            db,
            str(current_user.Id),
            "user.created",
            f"Usuario {new_user.Username} creado",
            None
        )

        return _user_to_response(new_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno creando usuario"
        )


@router.get("/", response_model=UserListResponse)
async def list_users(
        skip: int = Query(0, ge=0, description="Registros a saltar"),
        limit: int = Query(10, ge=1, le=100, description="Límite de registros"),
        search: Optional[str] = Query(None, description="Búsqueda general"),
        role_id: Optional[int] = Query(None, description="Filtrar por rol"),
        station_id: Optional[int] = Query(None, description="Filtrar por estación"),
        is_active: Optional[bool] = Query(None, description="Filtrar por estado"),
        sort_by: str = Query("FullName", description="Campo de ordenamiento"),
        sort_desc: bool = Query(False, description="Orden descendente"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permissions(["users.read"]))
):
    """
    Lista usuarios con filtros y paginación

    - Búsqueda por username, email o nombre completo
    - Filtros por rol, estación y estado
    - Paginación y ordenamiento
    """
    try:
        logger.debug(f"Listando usuarios - skip: {skip}, limit: {limit}")

        # Construir query base
        query = db.query(User)

        # Aplicar filtros
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                db.or_(
                    User.Username.like(search_term),
                    User.Email.like(search_term),
                    User.FullName.like(search_term)
                )
            )

        if role_id is not None:
            query = query.filter(User.RoleId == role_id)

        if station_id is not None:
            query = query.filter(User.StationId == station_id)

        if is_active is not None:
            query = query.filter(User.IsActive == is_active)

        # Total antes de paginación
        total = query.count()

        # Ordenamiento
        order_field = getattr(User, sort_by, User.FullName)
        if sort_desc:
            query = query.order_by(order_field.desc())
        else:
            query = query.order_by(order_field)

        # Paginación
        users = query.offset(skip).limit(limit).all()

        return UserListResponse(
            users=[_user_to_response(user) for user in users],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
            has_more=(skip + limit) < total
        )

    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno listando usuarios"
        )


@router.get("/search", response_model=List[UserResponse])
async def search_users(
        q: str = Query(..., min_length=2, description="Término de búsqueda"),
        limit: int = Query(20, ge=1, le=50, description="Límite de resultados"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Búsqueda rápida de usuarios

    - Búsqueda por username, email o nombre
    - Retorna máximo 20 resultados por defecto
    """
    try:
        users = user_crud.search_users(db, query=q, limit=limit)
        return [_user_to_response(user) for user in users]

    except Exception as e:
        logger.error(f"Error buscando usuarios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno buscando usuarios"
        )


@router.get("/stats", response_model=UserStats)
async def get_user_stats(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin)
):
    """
    Obtiene estadísticas generales de usuarios

    - Total de usuarios activos/inactivos
    - Distribución por roles
    - Usuarios con/sin estación
    - Actividad reciente
    """
    try:
        stats_data = user_crud.get_dashboard_stats(db)

        # Complementar con estadísticas adicionales
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.IsActive == True).count()
        inactive_users = total_users - active_users

        # Usuarios por rol
        users_by_role = {}
        roles = db.query(Role).filter(Role.IsActive == True).all()
        for role in roles:
            count = db.query(User).filter(
                User.RoleId == role.Id,
                User.IsActive == True
            ).count()
            users_by_role[role.Name] = count

        # Usuarios con/sin estación
        with_station = db.query(User).filter(
            User.StationId.isnot(None),
            User.IsActive == True
        ).count()

        without_station = db.query(User).filter(
            User.StationId.is_(None),
            User.IsActive == True
        ).count()

        return UserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            users_by_role=users_by_role,
            users_with_stations=with_station,
            users_without_stations=without_station,
            recent_logins_7d=stats_data.get("recent_logins_7d", 0),
            recent_logins_30d=0,  # TODO: Implementar
            average_session_time=0.0,  # TODO: Implementar
            last_updated=datetime.now()
        )

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo estadísticas"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
        user_id: str = Path(..., description="ID del usuario"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permissions(["users.read"]))
):
    """
    Obtiene un usuario por ID

    - Información completa del usuario
    - Incluye rol y estación asignada
    """
    try:
        user = user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        return _user_to_response(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo usuario"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
        user_id: str = Path(..., description="ID del usuario"),
        user_update: UserUpdate = ...,
        invalidate_cache: bool = Query(True, description="Invalidar cache del usuario"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permissions(["users.update"]))
):
    """
    Actualiza un usuario existente

    - Validación de datos únicos
    - Control de permisos según rol
    - Invalidación de cache automática
    """
    try:
        logger.info(f"Actualizando usuario {user_id} por {current_user.Username}")

        # Obtener usuario existente
        user = user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        # Verificar permisos especiales
        if user_id == str(current_user.Id):
            # Usuario actualizando su propio perfil - solo campos básicos
            allowed_fields = {"Email", "FullName"}
            update_data = {
                k: v for k, v in user_update.model_dump(exclude_unset=True).items()
                if k in allowed_fields
            }
        else:
            # Admin/Supervisor actualizando otro usuario
            if not (current_user.is_admin or current_user.is_supervisor):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permisos para actualizar otros usuarios"
                )
            update_data = user_update.model_dump(exclude_unset=True)

        # Validar email único si se está cambiando
        if "Email" in update_data and update_data["Email"] != user.Email:
            existing = user_crud.get_by_email(db, email=update_data["Email"])
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está registrado"
                )

        # Validar rol si se está cambiando
        if "RoleId" in update_data:
            role = role_crud.get(db, id=update_data["RoleId"])
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Rol no encontrado"
                )

        # Validar estación si se está cambiando
        if "StationId" in update_data and update_data["StationId"] is not None:
            station = station_crud.get(db, id=update_data["StationId"])
            if not station:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Estación no encontrada"
                )

        # Actualizar usuario
        updated_user = user_crud.update(db, db_obj=user, obj_in=update_data)

        # Invalidar cache si es necesario
        if invalidate_cache and cache_manager:
            invalidate_user_cache(user_id)

        # Registrar actividad
        _log_user_activity(
            db,
            str(current_user.Id),
            "user.updated",
            f"Usuario {user.Username} actualizado",
            None
        )

        return _user_to_response(updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno actualizando usuario"
        )


@router.delete("/{user_id}")
async def delete_user(
        user_id: str = Path(..., description="ID del usuario"),
        soft_delete: bool = Query(True, description="Desactivar en lugar de eliminar"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Elimina o desactiva un usuario

    - Solo administradores pueden eliminar usuarios
    - Por defecto realiza soft delete (desactivación)
    - No se puede eliminar el propio usuario
    """
    try:
        if user_id == str(current_user.Id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede eliminar su propio usuario"
            )

        user = user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        if soft_delete:
            # Desactivar usuario
            user.IsActive = False
            user.UpdatedAt = datetime.now()
            db.commit()

            message = f"Usuario {user.Username} desactivado"
            action = "user.deactivated"
        else:
            # Eliminar permanentemente
            db.delete(user)
            db.commit()

            message = f"Usuario {user.Username} eliminado permanentemente"
            action = "user.deleted"

        # Invalidar cache
        if cache_manager:
            invalidate_user_cache(user_id)

        # Registrar actividad
        _log_user_activity(
            db,
            str(current_user.Id),
            action,
            message,
            None
        )

        return {"message": message}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno eliminando usuario"
        )


# ========================================
# ENDPOINTS DE GESTIÓN DE CONTRASEÑAS
# ========================================

@router.post("/{user_id}/change-password")
async def change_user_password(
        user_id: str = Path(..., description="ID del usuario"),
        password_data: ChangePasswordRequest = ...,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Cambia la contraseña de un usuario

    - Usuarios pueden cambiar su propia contraseña
    - Admins pueden cambiar cualquier contraseña
    - Requiere contraseña actual para usuarios normales
    """
    try:
        # Verificar permisos
        if user_id != str(current_user.Id) and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede cambiar su propia contraseña"
            )

        user = user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        # Verificar contraseña actual si no es admin
        if user_id == str(current_user.Id):
            if not verify_password(password_data.current_password, user.PasswordHash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Contraseña actual incorrecta"
                )

        # Validar nueva contraseña
        password_strength = check_password_strength(password_data.new_password)
        if not password_strength["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Contraseña débil: {', '.join(password_strength['errors'])}"
            )

        # Actualizar contraseña
        success = user_crud.update_password(
            db,
            user_id=user_id,
            new_password=password_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error actualizando contraseña"
            )

        # Registrar actividad
        _log_user_activity(
            db,
            str(current_user.Id),
            "password.changed",
            f"Contraseña cambiada para usuario {user.Username}",
            None
        )

        return {"message": "Contraseña actualizada correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno cambiando contraseña"
        )




# ========================================
# ENDPOINTS DE ASIGNACIONES
# ========================================

@router.put("/{user_id}/assign-station")
async def assign_station_to_user(
        user_id: str = Path(..., description="ID del usuario"),
        assignment: UserStationAssignment = ...,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_supervisor_or_admin)
):
    """
    Asigna o desasigna una estación a un usuario

    - Solo supervisores y admins pueden asignar estaciones
    - StationId null desasigna la estación actual
    """
    try:
        user = user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        # Validar estación si se proporciona
        if assignment.station_id:
            station = station_crud.get(db, id=assignment.station_id)
            if not station:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Estación no encontrada"
                )

            # Verificar que la estación esté disponible
            if not station.IsActive:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La estación no está activa"
                )

        # Asignar estación
        old_station = user.station_name if user.StationId else "Sin estación"
        user.StationId = assignment.station_id
        user.UpdatedAt = datetime.now()
        db.commit()
        db.refresh(user)

        new_station = user.station_name if user.StationId else "Sin estación"

        # Registrar actividad
        _log_user_activity(
            db,
            str(current_user.Id),
            "station.assigned",
            f"Usuario {user.Username}: {old_station} -> {new_station}",
            None
        )

        return {
            "message": "Estación asignada correctamente",
            "user_id": user_id,
            "station_id": assignment.station_id,
            "station_name": new_station
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error asignando estación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno asignando estación"
        )


@router.put("/{user_id}/assign-role")
async def assign_role_to_user(
        user_id: str = Path(..., description="ID del usuario"),
        assignment: UserRoleAssignment = ...,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Cambia el rol de un usuario

    - Solo administradores pueden cambiar roles
    - No se puede cambiar el propio rol
    """
    try:
        if user_id == str(current_user.Id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede cambiar su propio rol"
            )

        user = user_crud.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        # Validar rol
        role = role_crud.get(db, id=assignment.role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado"
            )

        # Cambiar rol
        old_role = user.role_name
        user.RoleId = assignment.role_id
        user.UpdatedAt = datetime.now()
        db.commit()
        db.refresh(user)

        # Invalidar cache del usuario
        if cache_manager:
            invalidate_user_cache(user_id)

        # Registrar actividad
        _log_user_activity(
            db,
            str(current_user.Id),
            "role.changed",
            f"Usuario {user.Username}: {old_role} -> {role.Name}. Razón: {assignment.reason}",
            None
        )

        return {
            "message": "Rol asignado correctamente",
            "user_id": user_id,
            "role_id": assignment.role_id,
            "role_name": role.Name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error asignando rol: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno asignando rol"
        )


# ========================================
# ENDPOINTS DE PERFIL DE USUARIO
# ========================================

@router.get("/me", response_model=UserInfo)
async def get_my_profile(
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene el perfil del usuario actual

    - Información completa del usuario autenticado
    - Permisos y rol
    - Estación asignada
    """
    try:
        return user_crud.to_user_info(current_user)

    except Exception as e:
        logger.error(f"Error obteniendo perfil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo perfil"
        )


@router.put("/me")
async def update_my_profile(
        profile_update: UserUpdate = ...,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Actualiza el perfil del usuario actual

    - Solo puede actualizar Email y FullName
    - No puede cambiar rol, estación o estado
    """
    try:
        # Limitar campos que puede actualizar
        allowed_fields = {"Email", "FullName"}
        update_data = {
            k: v for k, v in profile_update.model_dump(exclude_unset=True).items()
            if k in allowed_fields
        }

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay campos válidos para actualizar"
            )

        # Validar email único si se está cambiando
        if "Email" in update_data and update_data["Email"] != current_user.Email:
            existing = user_crud.get_by_email(db, email=update_data["Email"])
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está registrado"
                )

        # Actualizar perfil
        updated_user = user_crud.update(
            db,
            db_obj=current_user,
            obj_in=update_data
        )

        # Invalidar cache
        if cache_manager:
            invalidate_user_cache(str(current_user.Id))

        return {
            "message": "Perfil actualizado correctamente",
            "updated_fields": list(update_data.keys())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando perfil: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno actualizando perfil"
        )


# ========================================
# ENDPOINTS DE OPERACIONES MASIVAS
# ========================================

@router.post("/bulk", response_model=BulkUserResponse)
async def create_bulk_users(
        bulk_data: BulkUserCreate = ...,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Crea múltiples usuarios de una vez

    - Solo administradores pueden crear usuarios masivamente
    - Máximo 100 usuarios por operación
    - Retorna resumen de éxitos y fallos
    """
    try:
        created_users = []
        failed_users = []

        for user_data in bulk_data.users:
            try:
                # Usar contraseña por defecto si no se proporciona
                if bulk_data.default_password:
                    user_data.Password = bulk_data.default_password

                # Usar rol por defecto si no se proporciona
                if bulk_data.default_role_id and not user_data.RoleId:
                    user_data.RoleId = bulk_data.default_role_id

                # Crear usuario
                new_user = user_crud.create_user(
                    db,
                    username=user_data.Username,
                    email=user_data.Email,
                    password=user_data.Password,
                    full_name=user_data.FullName,
                    role_id=user_data.RoleId,
                    station_id=user_data.StationId
                )

                if new_user:
                    created_users.append(_user_to_response(new_user))
                else:
                    failed_users.append({
                        "username": user_data.Username,
                        "error": "Error creando usuario"
                    })

            except Exception as e:
                failed_users.append({
                    "username": user_data.Username,
                    "error": str(e)
                })

        # Registrar actividad
        _log_user_activity(
            db,
            str(current_user.Id),
            "users.bulk_created",
            f"Creados {len(created_users)} usuarios, {len(failed_users)} fallos",
            None
        )

        return BulkUserResponse(
            success_count=len(created_users),
            failed_count=len(failed_users),
            created_users=created_users,
            failed_users=failed_users
        )

    except Exception as e:
        logger.error(f"Error en creación masiva: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno en creación masiva"
        )


@router.put("/bulk/deactivate")
async def deactivate_bulk_users(
        user_ids: List[str] = Body(..., description="IDs de usuarios a desactivar"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin())
):
    """
    Desactiva múltiples usuarios

    - Solo administradores pueden desactivar masivamente
    - No puede desactivar su propio usuario
    """
    try:
        if str(current_user.Id) in user_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puede desactivar su propio usuario"
            )

        # Desactivar usuarios
        count = user_crud.bulk_update(
            db,
            filters={"Id": user_ids},
            update_data={"IsActive": False}
        )

        # Invalidar cache de todos los usuarios
        if cache_manager:
            for user_id in user_ids:
                invalidate_user_cache(user_id)

        # Registrar actividad
        _log_user_activity(
            db,
            str(current_user.Id),
            "users.bulk_deactivated",
            f"Desactivados {count} usuarios",
            None
        )

        return {
            "message": f"{count} usuarios desactivados correctamente",
            "affected_count": count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en desactivación masiva: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno en desactivación masiva"
        )