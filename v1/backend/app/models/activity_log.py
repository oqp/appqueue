from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func, text
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import uuid
import json
from .base import BaseModel, TimestampMixin


class ActivityLog(BaseModel, TimestampMixin):
    """
    Modelo para el registro de actividades del sistema
    """
    __tablename__ = 'ActivityLog'

    # Campos principales
    Id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        server_default=text('newid()'),
        comment="ID único del log de actividad"
    )

    UserId = Column(
        UNIQUEIDENTIFIER,
        ForeignKey('Users.Id', ondelete='SET NULL'),
        nullable=True,
        comment="ID del usuario que realizó la acción"
    )

    TicketId = Column(
        UNIQUEIDENTIFIER,
        ForeignKey('Tickets.Id', ondelete='SET NULL'),
        nullable=True,
        comment="ID del ticket relacionado"
    )

    StationId = Column(
        Integer,
        ForeignKey('Stations.Id', ondelete='SET NULL'),
        nullable=True,
        comment="ID de la estación donde ocurrió la actividad"
    )

    Action = Column(
        String(50),
        nullable=False,
        comment="Acción realizada"
    )

    Details = Column(
        Text,
        nullable=True,
        comment="Detalles adicionales de la actividad en formato JSON"
    )

    IpAddress = Column(
        String(45),
        nullable=True,
        comment="Dirección IP del usuario"
    )

    UserAgent = Column(
        String(500),
        nullable=True,
        comment="User agent del navegador"
    )

    # Relaciones
    user = relationship(
        "User",
        back_populates="activity_logs"
    )

    ticket = relationship(
        "Ticket",
        back_populates="activity_logs"
    )

    station = relationship(
        "Station",
        back_populates="activity_logs"
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo ActivityLog
        """
        super().__init__(**kwargs)

    @validates('Action')
    def validate_action(self, key, action):
        """
        Valida y normaliza la acción
        """
        if action:
            # Normalizar la acción a snake_case
            action = action.strip().lower().replace(' ', '_').replace('-', '_')

            if len(action) < 2:
                raise ValueError("La acción debe tener al menos 2 caracteres")

            return action
        return action

    @validates('IpAddress')
    def validate_ip_address(self, key, ip_address):
        """
        Valida el formato de la dirección IP
        """
        if ip_address:
            import re
            # Patrón básico para IPv4 e IPv6
            ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'

            if not (re.match(ipv4_pattern, ip_address) or re.match(ipv6_pattern, ip_address)):
                # Si no es una IP válida, solo advertir pero no fallar
                pass

            return ip_address
        return ip_address

    @property
    def action_display(self) -> str:
        """
        Obtiene el nombre descriptivo de la acción

        Returns:
            str: Acción en formato legible
        """
        action_map = {
            'user_login': 'Inicio de sesión',
            'user_logout': 'Cierre de sesión',
            'ticket_created': 'Ticket creado',
            'ticket_called': 'Ticket llamado',
            'ticket_attended': 'Ticket atendido',
            'ticket_completed': 'Ticket completado',
            'ticket_cancelled': 'Ticket cancelado',
            'ticket_transferred': 'Ticket transferido',
            'station_status_changed': 'Estado de estación cambiado',
            'station_assigned': 'Estación asignada',
            'queue_reset': 'Cola reiniciada',
            'service_configured': 'Servicio configurado',
            'user_created': 'Usuario creado',
            'user_updated': 'Usuario actualizado',
            'user_deactivated': 'Usuario desactivado',
            'report_generated': 'Reporte generado',
            'system_backup': 'Respaldo del sistema',
            'configuration_updated': 'Configuración actualizada'
        }
        return action_map.get(self.Action, self.Action.replace('_', ' ').title())

    @property
    def details_dict(self) -> Dict[str, any]:
        """
        Obtiene los detalles como diccionario

        Returns:
            Dict[str, any]: Detalles parseados
        """
        if not self.Details:
            return {}

        try:
            return json.loads(self.Details)
        except (json.JSONDecodeError, TypeError):
            return {'raw_details': self.Details}

    @details_dict.setter
    def details_dict(self, details: Dict[str, any]):
        """
        Establece los detalles desde un diccionario

        Args:
            details: Diccionario con detalles
        """
        if isinstance(details, dict):
            self.Details = json.dumps(details, default=str)
        else:
            self.Details = str(details) if details else None

    @property
    def user_name(self) -> Optional[str]:
        """
        Obtiene el nombre del usuario

        Returns:
            str: Nombre del usuario
        """
        return self.user.FullName if self.user else None

    @property
    def user_username(self) -> Optional[str]:
        """
        Obtiene el username del usuario

        Returns:
            str: Username del usuario
        """
        return self.user.Username if self.user else None

    @property
    def ticket_number(self) -> Optional[str]:
        """
        Obtiene el número del ticket

        Returns:
            str: Número del ticket
        """
        return self.ticket.TicketNumber if self.ticket else None

    @property
    def station_name(self) -> Optional[str]:
        """
        Obtiene el nombre de la estación

        Returns:
            str: Nombre de la estación
        """
        return self.station.Name if self.station else None

    @property
    def station_code(self) -> Optional[str]:
        """
        Obtiene el código de la estación

        Returns:
            str: Código de la estación
        """
        return self.station.Code if self.station else None

    @property
    def is_system_action(self) -> bool:
        """
        Verifica si es una acción del sistema (sin usuario)

        Returns:
            bool: True si es acción del sistema
        """
        return self.UserId is None

    @property
    def is_user_action(self) -> bool:
        """
        Verifica si es una acción de usuario

        Returns:
            bool: True si es acción de usuario
        """
        return self.UserId is not None

    @property
    def is_ticket_action(self) -> bool:
        """
        Verifica si la acción está relacionada con un ticket

        Returns:
            bool: True si involucra un ticket
        """
        return self.TicketId is not None

    @property
    def is_station_action(self) -> bool:
        """
        Verifica si la acción está relacionada con una estación

        Returns:
            bool: True si involucra una estación
        """
        return self.StationId is not None

    @property
    def browser_info(self) -> Dict[str, str]:
        """
        Extrae información del navegador del User-Agent

        Returns:
            Dict[str, str]: Información del navegador
        """
        if not self.UserAgent:
            return {'browser': 'Desconocido', 'os': 'Desconocido'}

        user_agent = self.UserAgent.lower()

        # Detectar navegador
        if 'chrome' in user_agent:
            browser = 'Chrome'
        elif 'firefox' in user_agent:
            browser = 'Firefox'
        elif 'safari' in user_agent:
            browser = 'Safari'
        elif 'edge' in user_agent:
            browser = 'Edge'
        elif 'opera' in user_agent:
            browser = 'Opera'
        else:
            browser = 'Otro'

        # Detectar OS
        if 'windows' in user_agent:
            os = 'Windows'
        elif 'mac' in user_agent:
            os = 'macOS'
        elif 'linux' in user_agent:
            os = 'Linux'
        elif 'android' in user_agent:
            os = 'Android'
        elif 'ios' in user_agent:
            os = 'iOS'
        else:
            os = 'Otro'

        return {'browser': browser, 'os': os}

    def add_detail(self, key: str, value: any) -> None:
        """
        Agrega un detalle al log

        Args:
            key: Clave del detalle
            value: Valor del detalle
        """
        details = self.details_dict
        details[key] = value
        self.details_dict = details

    def get_detail(self, key: str, default: any = None) -> any:
        """
        Obtiene un detalle específico

        Args:
            key: Clave del detalle
            default: Valor por defecto

        Returns:
            any: Valor del detalle
        """
        return self.details_dict.get(key, default)

    @classmethod
    def log_action(cls, action: str, user_id: Optional[str] = None,
                   ticket_id: Optional[str] = None, station_id: Optional[int] = None,
                   details: Optional[Dict[str, any]] = None,
                   ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> 'ActivityLog':
        """
        Crea un log de actividad

        Args:
            action: Acción realizada
            user_id: ID del usuario (opcional)
            ticket_id: ID del ticket (opcional)  
            station_id: ID de la estación (opcional)
            details: Detalles adicionales (opcional)
            ip_address: IP del usuario (opcional)
            user_agent: User agent (opcional)

        Returns:
            ActivityLog: Nueva instancia de log
        """
        log = cls(
            Action=action,
            UserId=user_id,
            TicketId=ticket_id,
            StationId=station_id,
            IpAddress=ip_address,
            UserAgent=user_agent
        )

        if details:
            log.details_dict = details

        return log

    @classmethod
    def get_action_types(cls) -> List[str]:
        """
        Obtiene los tipos de acciones más comunes

        Returns:
            List[str]: Lista de tipos de acciones
        """
        return [
            'user_login', 'user_logout',
            'ticket_created', 'ticket_called', 'ticket_attended', 'ticket_completed', 'ticket_cancelled',
            'station_status_changed', 'station_assigned',
            'queue_reset', 'service_configured',
            'user_created', 'user_updated', 'user_deactivated',
            'report_generated', 'system_backup', 'configuration_updated'
        ]

    @classmethod
    def get_recent_activity(cls, hours: int = 24, limit: int = 100):
        """
        Obtiene actividad reciente

        Args:
            hours: Horas hacia atrás
            limit: Límite de registros

        Returns:
            Query: Query de actividad reciente
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        pass

    @classmethod
    def get_user_activity(cls, user_id: str, days: int = 7):
        """
        Obtiene actividad de un usuario específico

        Args:
            user_id: ID del usuario
            days: Días hacia atrás

        Returns:
            Query: Query de actividad del usuario
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        pass

    @classmethod
    def get_ticket_activity(cls, ticket_id: str):
        """
        Obtiene toda la actividad de un ticket

        Args:
            ticket_id: ID del ticket

        Returns:
            Query: Query de actividad del ticket
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        pass

    @classmethod
    def get_station_activity(cls, station_id: int, days: int = 7):
        """
        Obtiene actividad de una estación

        Args:
            station_id: ID de la estación
            days: Días hacia atrás

        Returns:
            Query: Query de actividad de la estación
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        pass

    def to_dict(self, include_relations: bool = True) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_relations: Si incluir datos de relaciones

        Returns:
            dict: Diccionario con los datos del log
        """
        result = super().to_dict()

        # Agregar propiedades calculadas
        result['action_display'] = self.action_display
        result['details_dict'] = self.details_dict
        result['is_system_action'] = self.is_system_action
        result['is_user_action'] = self.is_user_action
        result['is_ticket_action'] = self.is_ticket_action
        result['is_station_action'] = self.is_station_action
        result['browser_info'] = self.browser_info

        if include_relations:
            result['user_name'] = self.user_name
            result['user_username'] = self.user_username
            result['ticket_number'] = self.ticket_number
            result['station_name'] = self.station_name
            result['station_code'] = self.station_code

        return result

    def __repr__(self) -> str:
        return f"<ActivityLog(Id={self.Id}, Action='{self.Action}', User='{self.user_username}')>"