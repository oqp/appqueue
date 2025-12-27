"""
Operaciones CRUD específicas para el modelo Role
100% compatible con SQLAlchemy Role model y schemas Pydantic
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import logging

from app.crud.base import CRUDBase
from app.models.role import Role
from app.models.user import User

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)


# ========================================
# CLASE CRUD ROLE
# ========================================

class CRUDRole(CRUDBase[Role, dict, dict]):
    """
    Operaciones CRUD específicas para roles
    Hereda operaciones básicas de CRUDBase y agrega funcionalidades específicas
    """

    def get_by_name(self, db: Session, *, name: str) -> Optional[Role]:
        """
        Busca un rol por nombre

        Args:
            db: Sesión de base de datos
            name: Nombre del rol a buscar

        Returns:
            Role: Rol encontrado o None
        """
        try:
            # Normalizar nombre (case insensitive)
            normalized_name = name.strip().lower()

            return db.query(Role).filter(
                and_(
                    func.lower(Role.Name) == normalized_name,
                    Role.IsActive == True
                )
            ).first()

        except Exception as e:
            logger.error(f"Error buscando rol por nombre {name}: {e}")
            return None

    def create_role(
            self,
            db: Session,
            *,
            name: str,
            description: Optional[str] = None,
            permissions: Optional[List[str]] = None
    ) -> Optional[Role]:
        """
        Crea un nuevo rol

        Args:
            db: Sesión de base de datos
            name: Nombre único del rol
            description: Descripción del rol
            permissions: Lista de permisos del rol

        Returns:
            Role: Rol creado o None si hay error
        """
        try:
            # Verificar que el nombre no exista
            existing_role = self.get_by_name(db, name=name)
            if existing_role:
                logger.warning(f"Rol ya existe: {name}")
                return None

            # Crear rol
            role_data = {
                "Name": name.strip(),
                "Description": description.strip() if description else None,
                "IsActive": True
            }

            role = Role(**role_data)

            # Asignar permisos si se proporcionaron
            if permissions:
                role.permissions_list = permissions

            db.add(role)
            db.commit()
            db.refresh(role)

            logger.info(f"Rol creado exitosamente: {name}")
            return role

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando rol: {e}")
            return None

    def update_permissions(
            self,
            db: Session,
            *,
            role_id: int,
            permissions: List[str]
    ) -> Optional[Role]:
        """
        Actualiza los permisos de un rol

        Args:
            db: Sesión de base de datos
            role_id: ID del rol
            permissions: Nueva lista de permisos

        Returns:
            Role: Rol actualizado o None
        """
        try:
            role = self.get(db, id=role_id)
            if not role:
                return None

            # Actualizar permisos usando la propiedad del modelo
            role.permissions_list = permissions
            role.UpdatedAt = func.getdate()

            db.add(role)
            db.commit()
            db.refresh(role)

            logger.info(f"Permisos actualizados para rol {role.Name}: {len(permissions)} permisos")
            return role

        except Exception as e:
            db.rollback()
            logger.error(f"Error actualizando permisos del rol {role_id}: {e}")
            return None

    def add_permission(
            self,
            db: Session,
            *,
            role_id: int,
            permission: str
    ) -> Optional[Role]:
        """
        Agrega un permiso a un rol

        Args:
            db: Sesión de base de datos
            role_id: ID del rol
            permission: Permiso a agregar

        Returns:
            Role: Rol actualizado o None
        """
        try:
            role = self.get(db, id=role_id)
            if not role:
                return None

            # Usar método del modelo para agregar permiso
            if role.add_permission(permission):
                role.UpdatedAt = func.getdate()
                db.add(role)
                db.commit()
                db.refresh(role)

                logger.info(f"Permiso '{permission}' agregado al rol {role.Name}")
                return role
            else:
                logger.info(f"Permiso '{permission}' ya existe en rol {role.Name}")
                return role

        except Exception as e:
            db.rollback()
            logger.error(f"Error agregando permiso al rol {role_id}: {e}")
            return None

    def remove_permission(
            self,
            db: Session,
            *,
            role_id: int,
            permission: str
    ) -> Optional[Role]:
        """
        Remueve un permiso de un rol

        Args:
            db: Sesión de base de datos
            role_id: ID del rol
            permission: Permiso a remover

        Returns:
            Role: Rol actualizado o None
        """
        try:
            role = self.get(db, id=role_id)
            if not role:
                return None

            # Usar método del modelo para remover permiso
            if role.remove_permission(permission):
                role.UpdatedAt = func.getdate()
                db.add(role)
                db.commit()
                db.refresh(role)

                logger.info(f"Permiso '{permission}' removido del rol {role.Name}")
                return role
            else:
                logger.info(f"Permiso '{permission}' no existe en rol {role.Name}")
                return role

        except Exception as e:
            db.rollback()
            logger.error(f"Error removiendo permiso del rol {role_id}: {e}")
            return None

    def get_users_with_role(self, db: Session, *, role_id: int) -> List[User]:
        """
        Obtiene todos los usuarios que tienen un rol específico

        Args:
            db: Sesión de base de datos
            role_id: ID del rol

        Returns:
            List[User]: Lista de usuarios con ese rol
        """
        try:
            return db.query(User).filter(
                and_(
                    User.RoleId == role_id,
                    User.IsActive == True
                )
            ).order_by(User.FullName).all()

        except Exception as e:
            logger.error(f"Error obteniendo usuarios con rol {role_id}: {e}")
            return []

    def get_role_statistics(self, db: Session, *, role_id: int) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un rol específico

        Args:
            db: Sesión de base de datos
            role_id: ID del rol

        Returns:
            Dict[str, Any]: Estadísticas del rol
        """
        try:
            role = self.get(db, id=role_id)
            if not role:
                return {}

            # Obtener usuarios con este rol
            users_with_role = self.get_users_with_role(db, role_id=role_id)

            # Contar usuarios activos vs inactivos
            active_users = len([u for u in users_with_role if u.IsActive])

            # Obtener permisos
            permissions = role.permissions_list

            return {
                "role_id": role_id,
                "role_name": role.Name,
                "description": role.Description,
                "total_users": len(users_with_role),
                "active_users": active_users,
                "total_permissions": len(permissions),
                "permissions": permissions,
                "is_active": role.IsActive,
                "created_at": role.CreatedAt,
                "updated_at": role.UpdatedAt
            }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del rol {role_id}: {e}")
            return {"error": str(e)}

    def search_roles(
            self,
            db: Session,
            *,
            query: str,
            limit: int = 20
    ) -> List[Role]:
        """
        Búsqueda de roles por nombre o descripción

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            limit: Límite de resultados

        Returns:
            List[Role]: Lista de roles encontrados
        """
        try:
            search_term = f"%{query.strip()}%"

            return db.query(Role).filter(
                and_(
                    Role.IsActive == True,
                    or_(
                        Role.Name.like(search_term),
                        Role.Description.like(search_term)
                    )
                )
            ).order_by(Role.Name).limit(limit).all()

        except Exception as e:
            logger.error(f"Error en búsqueda de roles '{query}': {e}")
            return []

    def get_available_permissions(self) -> List[str]:
        """
        Obtiene la lista de permisos disponibles en el sistema

        Returns:
            List[str]: Lista de permisos disponibles
        """
        try:
            # Usar los permisos por defecto del modelo Role
            default_permissions = Role.get_default_permissions()

            # Recopilar todos los permisos únicos
            all_permissions = set()
            for role_permissions in default_permissions.values():
                all_permissions.update(role_permissions)

            return sorted(list(all_permissions))

        except Exception as e:
            logger.error(f"Error obteniendo permisos disponibles: {e}")
            return []

    def get_permissions_by_category(self) -> Dict[str, List[str]]:
        """
        Obtiene permisos organizados por categoría

        Returns:
            Dict[str, List[str]]: Permisos organizados por categoría
        """
        try:
            all_permissions = self.get_available_permissions()

            # Organizar por categoría (basado en el prefijo antes del punto)
            categories = {}

            for permission in all_permissions:
                if '.' in permission:
                    category, action = permission.split('.', 1)
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(permission)
                else:
                    # Permisos sin categoría
                    if 'general' not in categories:
                        categories['general'] = []
                    categories['general'].append(permission)

            # Ordenar cada categoría
            for category in categories:
                categories[category].sort()

            return categories

        except Exception as e:
            logger.error(f"Error organizando permisos por categoría: {e}")
            return {}

    def create_default_roles(self, db: Session) -> Dict[str, Role]:
        """
        Crea los roles por defecto del sistema

        Args:
            db: Sesión de base de datos

        Returns:
            Dict[str, Role]: Diccionario con los roles creados
        """
        try:
            default_permissions = Role.get_default_permissions()
            created_roles = {}

            for role_name, permissions in default_permissions.items():
                # Verificar si el rol ya existe
                existing_role = self.get_by_name(db, name=role_name)

                if not existing_role:
                    # Crear el rol
                    role = self.create_role(
                        db,
                        name=role_name.title(),  # Capitalizar
                        description=f"Rol {role_name} del sistema",
                        permissions=permissions
                    )

                    if role:
                        created_roles[role_name] = role
                        logger.info(f"Rol por defecto creado: {role_name}")
                else:
                    created_roles[role_name] = existing_role
                    logger.info(f"Rol por defecto ya existe: {role_name}")

            return created_roles

        except Exception as e:
            logger.error(f"Error creando roles por defecto: {e}")
            return {}

    def get_roles_summary(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene un resumen de todos los roles

        Args:
            db: Sesión de base de datos

        Returns:
            Dict[str, Any]: Resumen de roles
        """
        try:
            # Obtener todos los roles activos
            roles = self.get_active(db)

            roles_summary = []
            total_users = 0

            for role in roles:
                role_stats = self.get_role_statistics(db, role_id=role.Id)
                roles_summary.append({
                    "id": role.Id,
                    "name": role.Name,
                    "description": role.Description,
                    "user_count": role_stats.get("total_users", 0),
                    "permission_count": role_stats.get("total_permissions", 0)
                })
                total_users += role_stats.get("total_users", 0)

            return {
                "total_roles": len(roles),
                "total_users_assigned": total_users,
                "roles": roles_summary,
                "available_permissions_count": len(self.get_available_permissions())
            }

        except Exception as e:
            logger.error(f"Error obteniendo resumen de roles: {e}")
            return {
                "total_roles": 0,
                "total_users_assigned": 0,
                "roles": [],
                "available_permissions_count": 0
            }

    def validate_permissions(self, permissions: List[str]) -> Dict[str, List[str]]:
        """
        Valida una lista de permisos contra los permisos disponibles

        Args:
            permissions: Lista de permisos a validar

        Returns:
            Dict[str, List[str]]: Resultado de validación
        """
        try:
            available_permissions = set(self.get_available_permissions())
            provided_permissions = set(permissions)

            valid_permissions = list(provided_permissions.intersection(available_permissions))
            invalid_permissions = list(provided_permissions.difference(available_permissions))

            return {
                "valid": valid_permissions,
                "invalid": invalid_permissions,
                "is_valid": len(invalid_permissions) == 0
            }

        except Exception as e:
            logger.error(f"Error validando permisos: {e}")
            return {
                "valid": [],
                "invalid": permissions,
                "is_valid": False
            }

    def clone_role(
            self,
            db: Session,
            *,
            source_role_id: int,
            new_name: str,
            new_description: Optional[str] = None
    ) -> Optional[Role]:
        """
        Clona un rol existente con un nuevo nombre

        Args:
            db: Sesión de base de datos
            source_role_id: ID del rol a clonar
            new_name: Nombre del nuevo rol
            new_description: Descripción del nuevo rol

        Returns:
            Role: Rol clonado o None
        """
        try:
            source_role = self.get(db, id=source_role_id)
            if not source_role:
                logger.error(f"Rol fuente no encontrado: {source_role_id}")
                return None

            # Crear el nuevo rol con los mismos permisos
            cloned_role = self.create_role(
                db,
                name=new_name,
                description=new_description or f"Copia de {source_role.Name}",
                permissions=source_role.permissions_list
            )

            if cloned_role:
                logger.info(f"Rol clonado: {source_role.Name} -> {new_name}")

            return cloned_role

        except Exception as e:
            logger.error(f"Error clonando rol {source_role_id}: {e}")
            return None


# ========================================
# INSTANCIA GLOBAL
# ========================================

role_crud = CRUDRole(Role)