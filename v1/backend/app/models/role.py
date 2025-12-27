from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import json
from typing import List, Optional
from .base import BaseModel, TimestampMixin, ActiveMixin


class Role(BaseModel, TimestampMixin, ActiveMixin):
    """
    Modelo para roles de usuario del sistema
    """
    __tablename__ = 'Roles'

    # Campos principales
    Id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="ID único del rol"
    )

    Name = Column(
        String(50),
        nullable=False,
        unique=True,
        comment="Nombre único del rol"
    )

    Description = Column(
        String(200),
        nullable=True,
        comment="Descripción del rol"
    )

    Permissions = Column(
        Text,
        nullable=True,
        comment="Permisos del rol en formato JSON"
    )

    # Relaciones
    users = relationship(
        "User",
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo Role
        """
        super().__init__(**kwargs)

    @property
    def permissions_list(self) -> List[str]:
        """
        Obtiene la lista de permisos desde el campo JSON

        Returns:
            List[str]: Lista de permisos
        """
        if not self.Permissions:
            return []

        try:
            permissions = json.loads(self.Permissions)
            return permissions if isinstance(permissions, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @permissions_list.setter
    def permissions_list(self, permissions: List[str]):
        """
        Establece la lista de permisos en formato JSON

        Args:
            permissions: Lista de permisos
        """
        if isinstance(permissions, list):
            self.Permissions = json.dumps(permissions)
        else:
            self.Permissions = "[]"

    def has_permission(self, permission: str) -> bool:
        """
        Verifica si el rol tiene un permiso específico

        Args:
            permission: Permiso a verificar

        Returns:
            bool: True si tiene el permiso
        """
        return permission in self.permissions_list

    def add_permission(self, permission: str) -> bool:
        """
        Agrega un permiso al rol

        Args:
            permission: Permiso a agregar

        Returns:
            bool: True si se agregó correctamente
        """
        if not self.has_permission(permission):
            current_permissions = self.permissions_list
            current_permissions.append(permission)
            self.permissions_list = current_permissions
            return True
        return False

    def remove_permission(self, permission: str) -> bool:
        """
        Remueve un permiso del rol

        Args:
            permission: Permiso a remover

        Returns:
            bool: True si se removió correctamente
        """
        if self.has_permission(permission):
            current_permissions = self.permissions_list
            current_permissions.remove(permission)
            self.permissions_list = current_permissions
            return True
        return False

    @property
    def user_count(self) -> int:
        """
        Obtiene la cantidad de usuarios con este rol

        Returns:
            int: Cantidad de usuarios
        """
        return len(self.users) if self.users else 0

    @classmethod
    def get_default_permissions(cls) -> dict:
        """
        Obtiene los permisos por defecto para diferentes tipos de roles

        Returns:
            dict: Diccionario con permisos por tipo de rol
        """
        return {
            "admin": [
                "users.create", "users.read", "users.update", "users.delete",
                "roles.create", "roles.read", "roles.update", "roles.delete",
                "tickets.create", "tickets.read", "tickets.update", "tickets.delete",
                "stations.create", "stations.read", "stations.update", "stations.delete",
                "reports.read", "reports.export",
                "system.configure", "system.backup",
                "patients.create", "patients.read", "patients.update",
                "queue.manage"
            ],
            "supervisor": [
                "tickets.read", "tickets.update",
                "stations.read", "stations.update",
                "reports.read", "reports.export",
                "patients.read", "patients.update",
                "queue.manage"
            ],
            "agente": [
                "tickets.read", "tickets.update",
                "stations.read",
                "patients.read",
                "queue.attend"
            ],
            "receptionist": [
                "tickets.create", "tickets.read",
                "patients.create", "patients.read", "patients.update",
                "queue.view"
            ]
        }

    def to_dict(self, include_permissions: bool = True) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_permissions: Si incluir la lista de permisos

        Returns:
            dict: Diccionario con los datos del rol
        """
        result = super().to_dict()

        if include_permissions:
            result['permissions_list'] = self.permissions_list
            result['user_count'] = self.user_count

        return result

    def __repr__(self) -> str:
        return f"<Role(Id={self.Id}, Name='{self.Name}', Active={self.IsActive})>"