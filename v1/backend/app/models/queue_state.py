"""
Modelo SQLAlchemy para el estado de colas del sistema
Compatible con schemas y CRUD de queue
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func, text
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
from .base import BaseModel


class QueueState(BaseModel):
    """
    Modelo para el estado actual de las colas del sistema
    Compatible con schemas/queue.py y crud/queue.py
    """
    __tablename__ = 'QueueState'

    # ========================================
    # CAMPOS PRINCIPALES
    # ========================================

    Id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="ID único del estado de cola"
    )

    ServiceTypeId = Column(
        Integer,
        ForeignKey('ServiceTypes.Id', ondelete='CASCADE'),
        nullable=False,
        comment="ID del tipo de servicio"
    )

    StationId = Column(
        Integer,
        ForeignKey('Stations.Id', ondelete='SET NULL'),
        nullable=True,
        comment="ID de la estación (opcional para estados globales)"
    )

    CurrentTicketId = Column(
        UNIQUEIDENTIFIER,
        ForeignKey('Tickets.Id', ondelete='SET NULL'),
        nullable=True,
        comment="ID del ticket actualmente siendo atendido"
    )

    NextTicketId = Column(
        UNIQUEIDENTIFIER,
        ForeignKey('Tickets.Id', ondelete='SET NULL'),
        nullable=True,
        comment="ID del próximo ticket en la cola"
    )

    QueueLength = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Longitud actual de la cola"
    )

    AverageWaitTime = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Tiempo promedio de espera actual en minutos"
    )

    LastUpdateAt = Column(
        DateTime,
        nullable=False,
        server_default=func.getdate(),
        onupdate=func.getdate(),
        comment="Última actualización del estado"
    )

    # ========================================
    # CONSTRAINTS
    # ========================================

    __table_args__ = (
        CheckConstraint(
            'QueueLength >= 0',
            name='chk_queue_length_non_negative'
        ),
        CheckConstraint(
            'AverageWaitTime >= 0',
            name='chk_average_wait_time_non_negative'
        ),
    )

    # ========================================
    # RELACIONES
    # ========================================

    service_type = relationship(
        "ServiceType",
        back_populates="queue_states",
        lazy="joined"  # Cargar automáticamente para propiedades
    )

    station = relationship(
        "Station",
        back_populates="queue_states",
        lazy="joined"
    )

    current_ticket = relationship(
        "Ticket",
        foreign_keys=[CurrentTicketId],
        post_update=True,
        lazy="joined"
    )

    next_ticket = relationship(
        "Ticket",
        foreign_keys=[NextTicketId],
        post_update=True,
        lazy="joined"
    )

    # ========================================
    # CONSTRUCTOR
    # ========================================

    def __init__(self, **kwargs):
        """
        Constructor del modelo QueueState
        """
        # Establecer valores por defecto si no se proporcionan
        if 'LastUpdateAt' not in kwargs:
            kwargs['LastUpdateAt'] = datetime.now()

        super().__init__(**kwargs)

    # ========================================
    # VALIDADORES
    # ========================================

    @validates('QueueLength')
    def validate_queue_length(self, key, length):
        """Valida que la longitud de la cola sea no negativa"""
        if length is not None and length < 0:
            raise ValueError("La longitud de la cola no puede ser negativa")
        return length

    @validates('AverageWaitTime')
    def validate_average_wait_time(self, key, wait_time):
        """Valida que el tiempo de espera promedio sea no negativo"""
        if wait_time is not None and wait_time < 0:
            raise ValueError("El tiempo promedio de espera no puede ser negativo")
        return wait_time

    @validates('ServiceTypeId')
    def validate_service_type_id(self, key, service_type_id):
        """Valida que el ID del tipo de servicio sea positivo"""
        if service_type_id is not None and service_type_id <= 0:
            raise ValueError("El ID del tipo de servicio debe ser mayor que 0")
        return service_type_id

    # ========================================
    # PROPIEDADES - INFORMACIÓN RELACIONADA
    # ========================================

    @property
    def service_name(self) -> Optional[str]:
        """Obtiene el nombre del tipo de servicio"""
        return self.service_type.Name if self.service_type else None

    @property
    def service_code(self) -> Optional[str]:
        """Obtiene el código del tipo de servicio"""
        return self.service_type.Code if self.service_type else None

    @property
    def station_name(self) -> Optional[str]:
        """Obtiene el nombre de la estación"""
        return self.station.Name if self.station else None

    @property
    def station_code(self) -> Optional[str]:
        """Obtiene el código de la estación"""
        return self.station.Code if self.station else None

    @property
    def current_ticket_number(self) -> Optional[str]:
        """Obtiene el número del ticket actual"""
        return self.current_ticket.TicketNumber if self.current_ticket else None

    @property
    def next_ticket_number(self) -> Optional[str]:
        """Obtiene el número del próximo ticket"""
        return self.next_ticket.TicketNumber if self.next_ticket else None

    # ========================================
    # PROPIEDADES - ESTADO
    # ========================================

    @property
    def is_active(self) -> bool:
        """Verifica si la cola está activa (tiene tickets)"""
        return self.QueueLength > 0 or self.CurrentTicketId is not None

    @property
    def is_idle(self) -> bool:
        """Verifica si la cola está inactiva"""
        return self.QueueLength == 0 and self.CurrentTicketId is None

    @property
    def has_current_ticket(self) -> bool:
        """Verifica si hay un ticket siendo atendido"""
        return self.CurrentTicketId is not None

    @property
    def has_next_ticket(self) -> bool:
        """Verifica si hay un próximo ticket"""
        return self.NextTicketId is not None

    @property
    def queue_status(self) -> str:
        """Obtiene el estado descriptivo de la cola"""
        if self.is_idle:
            return "Vacía"
        elif self.QueueLength == 0:
            return "Último ticket"
        elif self.QueueLength <= 5:
            return "Baja"
        elif self.QueueLength <= 15:
            return "Media"
        elif self.QueueLength <= 30:
            return "Alta"
        else:
            return "Crítica"

    @property
    def priority_level(self) -> str:
        """Obtiene el nivel de prioridad basado en la carga"""
        if self.QueueLength <= 5:
            return "Baja"
        elif self.QueueLength <= 15:
            return "Media"
        elif self.QueueLength <= 30:
            return "Alta"
        else:
            return "Crítica"

    @property
    def time_since_last_update(self) -> int:
        """Calcula el tiempo transcurrido desde la última actualización en minutos"""
        if not self.LastUpdateAt:
            return 0
        return int((datetime.now() - self.LastUpdateAt).total_seconds() / 60)

    @property
    def is_stale(self) -> bool:
        """Verifica si el estado está desactualizado (más de 5 minutos)"""
        return self.time_since_last_update > 5

    @property
    def estimated_next_call_time(self) -> Optional[datetime]:
        """Estima cuándo se llamará al próximo ticket"""
        if not self.AverageWaitTime or not self.has_next_ticket:
            return None
        return datetime.now() + timedelta(minutes=self.AverageWaitTime)

    @property
    def estimated_wait_time(self) -> int:
        """Calcula el tiempo estimado de espera para nuevos tickets"""
        if self.QueueLength == 0:
            return 0
        return self.AverageWaitTime * (self.QueueLength + 1)

    # ========================================
    # MÉTODOS DE ACTUALIZACIÓN
    # ========================================

    def update_state(
            self,
            queue_length: Optional[int] = None,
            current_ticket_id: Optional[str] = None,
            next_ticket_id: Optional[str] = None,
            average_wait_time: Optional[int] = None
    ) -> None:
        """
        Actualiza el estado de la cola

        Args:
            queue_length: Nueva longitud de la cola
            current_ticket_id: ID del ticket actual
            next_ticket_id: ID del próximo ticket
            average_wait_time: Tiempo promedio de espera
        """
        if queue_length is not None:
            self.QueueLength = queue_length

        if current_ticket_id is not None:
            # Convertir a UUID si es string
            if isinstance(current_ticket_id, str) and current_ticket_id:
                try:
                    uuid.UUID(current_ticket_id)
                    self.CurrentTicketId = current_ticket_id
                except ValueError:
                    self.CurrentTicketId = None
            else:
                self.CurrentTicketId = current_ticket_id

        if next_ticket_id is not None:
            # Convertir a UUID si es string
            if isinstance(next_ticket_id, str) and next_ticket_id:
                try:
                    uuid.UUID(next_ticket_id)
                    self.NextTicketId = next_ticket_id
                except ValueError:
                    self.NextTicketId = None
            else:
                self.NextTicketId = next_ticket_id

        if average_wait_time is not None:
            self.AverageWaitTime = average_wait_time

        self.LastUpdateAt = datetime.now()

    def advance_queue(
            self,
            new_current_ticket_id: Optional[str] = None,
            new_next_ticket_id: Optional[str] = None
    ) -> None:
        """
        Avanza la cola al siguiente ticket

        Args:
            new_current_ticket_id: ID del nuevo ticket actual
            new_next_ticket_id: ID del nuevo próximo ticket
        """
        # El próximo ticket se convierte en el actual
        if new_current_ticket_id:
            self.CurrentTicketId = new_current_ticket_id
        else:
            self.CurrentTicketId = self.NextTicketId

        # Establecer el nuevo próximo ticket
        self.NextTicketId = new_next_ticket_id

        # Decrementar la longitud de la cola
        if self.QueueLength > 0:
            self.QueueLength -= 1

        self.LastUpdateAt = datetime.now()

    def clear_current_ticket(self) -> None:
        """Limpia el ticket actual (cuando se completa)"""
        self.CurrentTicketId = None
        self.LastUpdateAt = datetime.now()

    def reset_queue(self) -> None:
        """Reinicia el estado de la cola"""
        self.CurrentTicketId = None
        self.NextTicketId = None
        self.QueueLength = 0
        self.AverageWaitTime = 0
        self.LastUpdateAt = datetime.now()

    def calculate_average_wait_time(self, recent_tickets: List[Dict] = None) -> int:
        """
        Calcula el tiempo promedio de espera basado en tickets recientes

        Args:
            recent_tickets: Lista de tickets recientes con tiempos de espera

        Returns:
            int: Tiempo promedio en minutos
        """
        if not recent_tickets:
            # Usar tiempo base del servicio si no hay datos
            return self.service_type.AverageTimeMinutes if self.service_type else 10

        wait_times = [t.get('wait_time', 0) for t in recent_tickets if t.get('wait_time')]

        if not wait_times:
            return self.service_type.AverageTimeMinutes if self.service_type else 10

        avg_wait = sum(wait_times) / len(wait_times)

        # Ajustar por longitud de la cola
        if self.QueueLength > 0:
            queue_factor = min(2.0, 1 + (self.QueueLength * 0.1))
            avg_wait *= queue_factor

        return max(1, int(avg_wait))

    # ========================================
    # MÉTODOS DE CONVERSIÓN
    # ========================================

    def to_dict(self, include_estimates: bool = True) -> Dict[str, Any]:
        """
        Convierte el modelo a diccionario (compatible con schemas)

        Args:
            include_estimates: Si incluir estimaciones de tiempo

        Returns:
            dict: Diccionario con los datos del estado
        """
        result = {
            'id': self.Id,
            'service_type_id': self.ServiceTypeId,
            'station_id': self.StationId,
            'current_ticket_id': str(self.CurrentTicketId) if self.CurrentTicketId else None,
            'next_ticket_id': str(self.NextTicketId) if self.NextTicketId else None,
            'queue_length': self.QueueLength,
            'average_wait_time': self.AverageWaitTime,
            'last_update_at': self.LastUpdateAt.isoformat() if self.LastUpdateAt else None,

            # Propiedades calculadas
            'service_name': self.service_name,
            'service_code': self.service_code,
            'station_name': self.station_name,
            'station_code': self.station_code,
            'current_ticket_number': self.current_ticket_number,
            'next_ticket_number': self.next_ticket_number,
            'is_active': self.is_active,
            'is_idle': self.is_idle,
            'has_current_ticket': self.has_current_ticket,
            'has_next_ticket': self.has_next_ticket,
            'queue_status': self.queue_status,
            'priority_level': self.priority_level,
            'time_since_last_update': self.time_since_last_update,
            'is_stale': self.is_stale
        }

        if include_estimates:
            next_call_time = self.estimated_next_call_time
            result['estimated_next_call_time'] = next_call_time.isoformat() if next_call_time else None
            result['estimated_wait_time'] = self.estimated_wait_time

        return result

    def to_response(self) -> Dict[str, Any]:
        """
        Convierte a formato de respuesta para API (compatible con QueueStateResponse)

        Returns:
            dict: Datos formateados para respuesta
        """
        return {
            'id': self.Id,
            'service_type_id': self.ServiceTypeId,
            'station_id': self.StationId,
            'current_ticket_id': str(self.CurrentTicketId) if self.CurrentTicketId else None,
            'next_ticket_id': str(self.NextTicketId) if self.NextTicketId else None,
            'queue_length': self.QueueLength,
            'average_wait_time': self.AverageWaitTime,
            'last_update_at': self.LastUpdateAt,
            'service_name': self.service_name,
            'service_code': self.service_code,
            'station_name': self.station_name,
            'station_code': self.station_code,
            'is_active': self.is_active,
            'estimated_wait_time': self.estimated_wait_time
        }

    # ========================================
    # MÉTODOS ESPECIALES
    # ========================================

    def __repr__(self) -> str:
        """Representación en string del objeto"""
        return (
            f"<QueueState("
            f"Id={self.Id}, "
            f"Service='{self.service_code}', "
            f"Station='{self.station_code}', "
            f"Length={self.QueueLength}, "
            f"Current='{self.current_ticket_number}'"
            f")>"
        )

    def __str__(self) -> str:
        """Representación legible del objeto"""
        return f"Cola {self.service_name or 'Sin servicio'} - {self.QueueLength} en espera"