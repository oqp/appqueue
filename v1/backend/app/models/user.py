from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func, text
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import re
from .base import BaseModel, TimestampMixin, ActiveMixin


class User(BaseModel, TimestampMixin, ActiveMixin):
    """
    Modelo para usuarios del sistema de gestión de colas
    """
    __tablename__ = 'Users'

    # Campos principales
    Id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        server_default=text('newid()'),
        comment="ID único del usuario"
    )

    Username = Column(
        String(50),
        nullable=False,
        unique=True,
        comment="Nombre de usuario único"
    )

    Email = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Correo electrónico único"
    )

    PasswordHash = Column(
        String(255),
        nullable=False,
        comment="Hash de la contraseña"
    )

    FullName = Column(
        String(200),
        nullable=False,
        comment="Nombre completo del usuario"
    )

    RoleId = Column(
        Integer,
        ForeignKey('Roles.Id'),
        nullable=False,
        comment="ID del rol asignado"
    )

    StationId = Column(
        Integer,
        ForeignKey('Stations.Id', ondelete='SET NULL'),
        nullable=True,
        comment="ID de la estación asignada"
    )

    LastLogin = Column(
        DateTime,
        nullable=True,
        comment="Fecha y hora del último login"
    )

    # Relaciones
    role = relationship(
        "Role",
        back_populates="users"
    )

    station = relationship(
        "Station",
        back_populates="users"
    )

    activity_logs = relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo User
        """
        super().__init__(**kwargs)

    @validates('Username')
    def validate_username(self, key, username):
        """
        Valida el nombre de usuario
        """
        if username:
            username = username.strip().lower()

            # Validar formato (solo letras, números y underscore)
            if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
                raise ValueError("El username debe tener 3-50 caracteres (letras, números y _)")

            return username
        return username

    @validates('Email')
    def validate_email(self, key, email):
        """
        Valida el formato del email
        """
        if email:
            email = email.strip().lower()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

            if not re.match(email_pattern, email):
                raise ValueError("Formato de email inválido")

            return email
        return email

    @validates('FullName')
    def validate_full_name(self, key, name):
        """
        Valida y normaliza el nombre completo
        """
        if name:
            # Capitalizar cada palabra y remover espacios extra
            normalized_name = ' '.join(word.capitalize() for word in name.strip().split())

            if len(normalized_name) < 2:
                raise ValueError("El nombre completo debe tener al menos 2 caracteres")

            return normalized_name
        return name

    @property
    def role_name(self) -> Optional[str]:
        """
        Obtiene el nombre del rol asignado

        Returns:
            str: Nombre del rol
        """
        return self.role.Name if self.role else None

    @property
    def station_name(self) -> Optional[str]:
        """
        Obtiene el nombre de la estación asignada

        Returns:
            str: Nombre de la estación
        """
        return self.station.Name if self.station else None

    @property
    def station_code(self) -> Optional[str]:
        """
        Obtiene el código de la estación asignada

        Returns:
            str: Código de la estación
        """
        return self.station.Code if self.station else None

    @property
    def permissions(self) -> List[str]:
        """
        Obtiene la lista de permisos del usuario

        Returns:
            List[str]: Lista de permisos
        """
        return self.role.permissions_list if self.role else []

    @property
    def is_admin(self) -> bool:
        """
        Verifica si el usuario es administrador

        Returns:
            bool: True si es admin
        """
        return self.role_name and self.role_name.lower() == 'admin'

    @property
    def is_supervisor(self) -> bool:
        """
        Verifica si el usuario es supervisor

        Returns:
            bool: True si es supervisor
        """
        return self.role_name and self.role_name.lower() == 'supervisor'

    @property
    def is_agente(self) -> bool:
        """
        Verifica si el usuario es técnico

        Returns:
            bool: True si es técnico
        """
        return self.role_name and self.role_name.lower() == 'agente'

    @property
    def can_manage_stations(self) -> bool:
        """
        Verifica si puede gestionar estaciones

        Returns:
            bool: True si puede gestionar estaciones
        """
        return self.has_permission('stations.manage') or self.is_admin

    @property
    def can_attend_patients(self) -> bool:
        """
        Verifica si puede atender pacientes

        Returns:
            bool: True si puede atender pacientes
        """
        return (self.has_permission('queue.attend') or
                self.has_permission('queue.manage') or
                self.is_agente)

    @property
    def days_since_last_login(self) -> Optional[int]:
        """
        Obtiene los días desde el último login

        Returns:
            int: Días desde último login
        """
        if not self.LastLogin:
            return None

        return (datetime.now() - self.LastLogin).days

    @property
    def is_recently_active(self) -> bool:
        """
        Verifica si el usuario ha estado activo recientemente

        Returns:
            bool: True si estuvo activo en los últimos 7 días
        """
        if not self.LastLogin:
            return False

        return (datetime.now() - self.LastLogin).days <= 7

    def has_permission(self, permission: str) -> bool:
        """
        Verifica si el usuario tiene un permiso específico

        Args:
            permission: Permiso a verificar

        Returns:
            bool: True si tiene el permiso
        """
        if not self.IsActive:
            return False

        return permission in self.permissions or self.is_admin

    def has_any_permission(self, permissions: List[str]) -> bool:
        """
        Verifica si el usuario tiene alguno de los permisos especificados

        Args:
            permissions: Lista de permisos a verificar

        Returns:
            bool: True si tiene al menos uno de los permisos
        """
        return any(self.has_permission(perm) for perm in permissions)

    def has_all_permissions(self, permissions: List[str]) -> bool:
        """
        Verifica si el usuario tiene todos los permisos especificados

        Args:
            permissions: Lista de permisos a verificar

        Returns:
            bool: True si tiene todos los permisos
        """
        return all(self.has_permission(perm) for perm in permissions)

    def update_last_login(self):
        """
        Actualiza la fecha de último login
        """
        self.LastLogin = func.getdate()

    def can_access_station(self, station_id: int) -> bool:
        """
        Verifica si el usuario puede acceder a una estación específica

        Args:
            station_id: ID de la estación

        Returns:
            bool: True si puede acceder
        """
        if self.is_admin or self.is_supervisor:
            return True

        return self.StationId == station_id

    def get_recent_activity(self, days: int = 7) -> List:
        """
        Obtiene la actividad reciente del usuario

        Args:
            days: Número de días hacia atrás

        Returns:
            List: Lista de actividades recientes
        """
        if not self.activity_logs:
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        return [
            log for log in self.activity_logs
            if log.CreatedAt >= cutoff_date
        ]

    def get_daily_ticket_count(self, target_date: Optional[datetime] = None) -> int:
        """
        Obtiene la cantidad de tickets procesados en un día

        Args:
            target_date: Fecha objetivo (por defecto hoy)

        Returns:
            int: Cantidad de tickets procesados
        """
        if target_date is None:
            target_date = datetime.now().date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()

        if not self.activity_logs:
            return 0

        ticket_actions = ['ticket.attended', 'ticket.completed', 'ticket.called']
        daily_activities = [
            log for log in self.activity_logs
            if (log.CreatedAt.date() == target_date and
                log.Action in ticket_actions)
        ]

        # Contar tickets únicos
        unique_tickets = set(log.TicketId for log in daily_activities if log.TicketId)
        return len(unique_tickets)

    def get_performance_stats(self, days: int = 30) -> dict:
        """
        Obtiene estadísticas de rendimiento del usuario

        Args:
            days: Número de días para el cálculo

        Returns:
            dict: Estadísticas de rendimiento
        """
        recent_activities = self.get_recent_activity(days)

        ticket_activities = [
            log for log in recent_activities
            if log.Action and 'ticket' in log.Action.lower()
        ]

        return {
            'total_activities': len(recent_activities),
            'ticket_activities': len(ticket_activities),
            'unique_tickets_handled': len(set(
                log.TicketId for log in ticket_activities if log.TicketId
            )),
            'daily_average': len(ticket_activities) / days if days > 0 else 0,
            'last_activity': max(
                (log.CreatedAt for log in recent_activities),
                default=None
            )
        }

    def to_dict(self, include_sensitive: bool = False, include_stats: bool = False) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_sensitive: Si incluir datos sensibles
            include_stats: Si incluir estadísticas de rendimiento

        Returns:
            dict: Diccionario con los datos del usuario
        """
        exclude_fields = ['PasswordHash']
        if not include_sensitive:
            exclude_fields.extend(['Email'])

        result = super().to_dict(exclude_fields=exclude_fields)

        # Agregar propiedades calculadas
        result['role_name'] = self.role_name
        result['station_name'] = self.station_name
        result['station_code'] = self.station_code
        result['is_admin'] = self.is_admin
        result['is_supervisor'] = self.is_supervisor
        result['is_agente'] = self.is_agente
        result['days_since_last_login'] = self.days_since_last_login
        result['is_recently_active'] = self.is_recently_active

        if include_stats:
            result['performance_stats'] = self.get_performance_stats()
            result['recent_activities_count'] = len(self.get_recent_activity())

        return result

    def __repr__(self) -> str:
        return f"<User(Id={self.Id}, Username='{self.Username}', Role='{self.role_name}')>"