from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func, text
from datetime import datetime
from typing import Optional, List, Dict
import uuid
import json
from .base import BaseModel, TimestampMixin


class NotificationLog(BaseModel, TimestampMixin):
    """
    Modelo para el registro de notificaciones enviadas
    """
    __tablename__ = 'NotificationLog'

    # Campos principales
    Id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        server_default=text('newid()'),
        comment="ID único del log de notificación"
    )

    TicketId = Column(
        UNIQUEIDENTIFIER,
        ForeignKey('Tickets.Id', ondelete='CASCADE'),
        nullable=False,
        comment="ID del ticket relacionado"
    )

    Type = Column(
        String(20),
        nullable=False,
        comment="Tipo de notificación (SMS, Email, Audio, Push)"
    )

    Recipient = Column(
        String(100),
        nullable=False,
        comment="Destinatario de la notificación"
    )

    Message = Column(
        Text,
        nullable=False,
        comment="Contenido del mensaje enviado"
    )

    Status = Column(
        String(20),
        nullable=False,
        default='Pending',
        comment="Estado de la notificación"
    )

    ErrorMessage = Column(
        String(500),
        nullable=True,
        comment="Mensaje de error si falló el envío"
    )

    SentAt = Column(
        DateTime,
        nullable=True,
        comment="Fecha y hora de envío exitoso"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "Type IN ('SMS', 'Email', 'Audio', 'Push')",
            name='chk_notification_type'
        ),
        CheckConstraint(
            "Status IN ('Pending', 'Sent', 'Failed', 'Delivered')",
            name='chk_notification_status'
        ),
    )

    # Relaciones
    ticket = relationship(
        "Ticket",
        back_populates="notifications"
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo NotificationLog
        """
        super().__init__(**kwargs)

    @validates('Type')
    def validate_type(self, key, notification_type):
        """
        Valida el tipo de notificación
        """
        valid_types = ['SMS', 'Email', 'Audio', 'Push']
        if notification_type and notification_type not in valid_types:
            raise ValueError(f"Tipo inválido. Debe ser uno de: {', '.join(valid_types)}")
        return notification_type

    @validates('Status')
    def validate_status(self, key, status):
        """
        Valida el estado de la notificación
        """
        valid_statuses = ['Pending', 'Sent', 'Failed', 'Delivered']
        if status and status not in valid_statuses:
            raise ValueError(f"Estado inválido. Debe ser uno de: {', '.join(valid_statuses)}")
        return status

    @validates('Recipient')
    def validate_recipient(self, key, recipient):
        """
        Valida el destinatario según el tipo
        """
        if recipient:
            recipient = recipient.strip()

            # Validaciones básicas según tipo común
            if self.Type == 'Email':
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, recipient):
                    raise ValueError("Formato de email inválido")

            elif self.Type == 'SMS':
                import re
                # Permitir números con +, espacios, guiones
                phone_pattern = r'^[\+]?[1-9][\d\s\-\(\)]{7,15}$'
                cleaned_phone = re.sub(r'[\s\-\(\)]', '', recipient)
                if not re.match(phone_pattern, cleaned_phone):
                    raise ValueError("Formato de teléfono inválido")

            return recipient
        return recipient

    @property
    def type_display(self) -> str:
        """
        Obtiene el nombre descriptivo del tipo

        Returns:
            str: Tipo en formato legible
        """
        type_map = {
            'SMS': 'Mensaje de texto',
            'Email': 'Correo electrónico',
            'Audio': 'Anuncio de audio',
            'Push': 'Notificación push'
        }
        return type_map.get(self.Type, 'Desconocido')

    @property
    def status_display(self) -> str:
        """
        Obtiene el nombre descriptivo del estado

        Returns:
            str: Estado en formato legible
        """
        status_map = {
            'Pending': 'Pendiente',
            'Sent': 'Enviado',
            'Failed': 'Falló',
            'Delivered': 'Entregado'
        }
        return status_map.get(self.Status, 'Desconocido')

    @property
    def is_successful(self) -> bool:
        """
        Verifica si la notificación fue exitosa

        Returns:
            bool: True si fue enviada o entregada
        """
        return self.Status in ['Sent', 'Delivered']

    @property
    def is_failed(self) -> bool:
        """
        Verifica si la notificación falló

        Returns:
            bool: True si falló
        """
        return self.Status == 'Failed'

    @property
    def is_pending(self) -> bool:
        """
        Verifica si la notificación está pendiente

        Returns:
            bool: True si está pendiente
        """
        return self.Status == 'Pending'

    @property
    def delivery_time(self) -> Optional[int]:
        """
        Calcula el tiempo de entrega en segundos

        Returns:
            int: Tiempo de entrega en segundos
        """
        if not self.SentAt:
            return None

        return int((self.SentAt - self.CreatedAt).total_seconds())

    @property
    def ticket_number(self) -> Optional[str]:
        """
        Obtiene el número del ticket relacionado

        Returns:
            str: Número del ticket
        """
        return self.ticket.TicketNumber if self.ticket else None

    @property
    def patient_name(self) -> Optional[str]:
        """
        Obtiene el nombre del paciente del ticket relacionado

        Returns:
            str: Nombre del paciente
        """
        return self.ticket.patient_name if self.ticket else None

    def mark_as_sent(self, sent_at: Optional[datetime] = None) -> bool:
        """
        Marca la notificación como enviada

        Args:
            sent_at: Fecha de envío (por defecto ahora)

        Returns:
            bool: True si se marcó exitosamente
        """
        if self.Status != 'Pending':
            return False

        self.Status = 'Sent'
        self.SentAt = sent_at or func.getdate()
        self.ErrorMessage = None

        return True

    def mark_as_delivered(self) -> bool:
        """
        Marca la notificación como entregada

        Returns:
            bool: True si se marcó exitosamente
        """
        if self.Status not in ['Sent', 'Pending']:
            return False

        self.Status = 'Delivered'
        if not self.SentAt:
            self.SentAt = func.getdate()

        return True

    def mark_as_failed(self, error_message: str) -> bool:
        """
        Marca la notificación como fallida

        Args:
            error_message: Mensaje de error

        Returns:
            bool: True si se marcó exitosamente
        """
        if self.Status not in ['Pending', 'Sent']:
            return False

        self.Status = 'Failed'
        self.ErrorMessage = error_message

        return True

    def retry(self) -> bool:
        """
        Prepara la notificación para reintento

        Returns:
            bool: True si se puede reintentar
        """
        if self.Status != 'Failed':
            return False

        self.Status = 'Pending'
        self.ErrorMessage = None
        self.SentAt = None

        return True

    @classmethod
    def create_notification(cls, ticket_id: str, notification_type: str,
                            recipient: str, message: str) -> 'NotificationLog':
        """
        Crea una nueva notificación

        Args:
            ticket_id: ID del ticket
            notification_type: Tipo de notificación
            recipient: Destinatario
            message: Mensaje a enviar

        Returns:
            NotificationLog: Nueva instancia de notificación
        """
        return cls(
            TicketId=ticket_id,
            Type=notification_type,
            Recipient=recipient,
            Message=message,
            Status='Pending'
        )

    @classmethod
    def get_failed_notifications(cls, hours: int = 24):
        """
        Obtiene notificaciones fallidas en las últimas horas

        Args:
            hours: Horas hacia atrás para buscar

        Returns:
            Query: Query de notificaciones fallidas
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        pass

    @classmethod
    def get_statistics(cls, days: int = 7) -> Dict[str, int]:
        """
        Obtiene estadísticas de notificaciones

        Args:
            days: Días para el cálculo

        Returns:
            Dict[str, int]: Estadísticas de notificaciones
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        return {
            'total': 0,
            'sent': 0,
            'failed': 0,
            'pending': 0,
            'success_rate': 0
        }

    def get_retry_count(self) -> int:
        """
        Obtiene el número de reintentos basado en logs

        Returns:
            int: Número de reintentos
        """
        # Esta lógica se puede expandir con un campo específico
        # Por ahora, asumimos que se puede inferir de los logs
        return 0

    def can_retry(self, max_retries: int = 3) -> bool:
        """
        Verifica si se puede reintentar la notificación

        Args:
            max_retries: Número máximo de reintentos

        Returns:
            bool: True si se puede reintentar
        """
        return (self.is_failed and
                self.get_retry_count() < max_retries)

    def get_notification_context(self) -> Dict[str, any]:
        """
        Obtiene el contexto de datos para la notificación

        Returns:
            Dict[str, any]: Contexto con datos del ticket y paciente
        """
        if not self.ticket:
            return {}

        return {
            'ticket_number': self.ticket.TicketNumber,
            'patient_name': self.ticket.patient_name,
            'patient_document': self.ticket.patient_document,
            'service_name': self.ticket.service_name,
            'service_code': self.ticket.service_code,
            'station_name': self.ticket.station_name,
            'station_code': self.ticket.station_code,
            'position': self.ticket.Position,
            'estimated_wait_time': self.ticket.EstimatedWaitTime,
            'status': self.ticket.status_display,
            'created_at': self.ticket.created_at.strftime('%H:%M') if self.ticket.created_at else None,
            'current_time': datetime.now().strftime('%H:%M'),
            'date': datetime.now().strftime('%Y-%m-%d')
        }

    def to_dict(self, include_context: bool = False) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_context: Si incluir contexto del ticket

        Returns:
            dict: Diccionario con los datos de la notificación
        """
        result = super().to_dict()

        # Agregar propiedades calculadas
        result['type_display'] = self.type_display
        result['status_display'] = self.status_display
        result['is_successful'] = self.is_successful
        result['is_failed'] = self.is_failed
        result['is_pending'] = self.is_pending
        result['delivery_time'] = self.delivery_time
        result['ticket_number'] = self.ticket_number
        result['patient_name'] = self.patient_name
        result['retry_count'] = self.get_retry_count()
        result['can_retry'] = self.can_retry()

        if include_context:
            result['context'] = self.get_notification_context()

        return result

    def __repr__(self) -> str:
        return f"<NotificationLog(Id={self.Id}, Type='{self.Type}', Status='{self.Status}')>"