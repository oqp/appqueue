from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint, Text, Computed
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func, text
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
from .base import BaseModel, TimestampMixin


class Ticket(BaseModel, TimestampMixin):
    """
    Modelo para tickets/turnos del sistema de gestión de colas
    """
    __tablename__ = 'Tickets'

    # Campos principales
    Id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        server_default=text('newid()'),
        comment="ID único del ticket"
    )

    TicketNumber = Column(
        String(20),
        nullable=False,
        comment="Número del ticket (ej: A001, LAB-001)"
    )

    PatientId = Column(
        UNIQUEIDENTIFIER,
        ForeignKey('Patients.Id', ondelete='RESTRICT'),
        nullable=False,
        comment="ID del paciente"
    )

    ServiceTypeId = Column(
        Integer,
        ForeignKey('ServiceTypes.Id', ondelete='RESTRICT'),
        nullable=False,
        comment="ID del tipo de servicio"
    )

    StationId = Column(
        Integer,
        ForeignKey('Stations.Id', ondelete='SET NULL'),
        nullable=True,
        comment="ID de la estación asignada"
    )

    Status = Column(
        String(20),
        nullable=False,
        default='Waiting',
        comment="Estado actual del ticket"
    )

    Position = Column(
        Integer,
        nullable=False,
        comment="Posición en la cola"
    )

    EstimatedWaitTime = Column(
        Integer,
        nullable=True,
        comment="Tiempo estimado de espera en minutos"
    )

    QrCode = Column(
        Text,
        nullable=True,
        comment="Código QR para el ticket"
    )

    Notes = Column(
        String(500),
        nullable=True,
        comment="Notas adicionales del ticket"
    )

    CalledAt = Column(
        DateTime,
        nullable=True,
        comment="Fecha y hora de llamada"
    )

    AttendedAt = Column(
        DateTime,
        nullable=True,
        comment="Fecha y hora de inicio de atención"
    )

    CompletedAt = Column(
        DateTime,
        nullable=True,
        comment="Fecha y hora de finalización"
    )

    # Columnas calculadas (como en SQL Server)
    ActualWaitTime = Column(
        Integer,
        Computed("datediff(minute, [CreatedAt], isnull([AttendedAt], getdate()))"),
        comment="Tiempo real de espera calculado automáticamente"
    )

    ServiceTime = Column(
        Integer,
        Computed("datediff(minute, [AttendedAt], [CompletedAt])"),
        comment="Tiempo de servicio calculado automáticamente"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "Status IN ('Waiting', 'Called', 'InProgress', 'Completed', 'Cancelled', 'NoShow')",
            name='chk_ticket_status'
        ),
        CheckConstraint(
            "Position > 0",
            name='chk_ticket_position'
        ),
    )

    # Relaciones
    patient = relationship(
        "Patient",
        back_populates="tickets"
    )

    service_type = relationship(
        "ServiceType",
        back_populates="tickets"
    )

    station = relationship(
        "Station",
        back_populates="tickets"
    )

    notifications = relationship(
        "NotificationLog",
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    activity_logs = relationship(
        "ActivityLog",
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo Ticket
        """
        super().__init__(**kwargs)

    @validates('Status')
    def validate_status(self, key, status):
        """
        Valida el estado del ticket
        """
        valid_statuses = ['Waiting', 'Called', 'InProgress', 'Completed', 'Cancelled', 'NoShow']
        if status and status not in valid_statuses:
            raise ValueError(f"Estado inválido. Debe ser uno de: {', '.join(valid_statuses)}")
        return status

    @validates('Position')
    def validate_position(self, key, position):
        """
        Valida la posición en la cola
        """
        if position is not None and position <= 0:
            raise ValueError("La posición debe ser mayor a 0")
        return position

    @validates('EstimatedWaitTime')
    def validate_estimated_wait_time(self, key, wait_time):
        """
        Valida el tiempo estimado de espera
        """
        if wait_time is not None and wait_time < 0:
            raise ValueError("El tiempo estimado no puede ser negativo")
        return wait_time

    @property
    def status_display(self) -> str:
        """
        Obtiene el nombre descriptivo del estado

        Returns:
            str: Estado en formato legible
        """
        status_map = {
            'Waiting': 'En espera',
            'Called': 'Llamado',
            'InProgress': 'En atención',
            'Completed': 'Completado',
            'Cancelled': 'Cancelado',
            'NoShow': 'No se presentó'
        }
        return status_map.get(self.Status, 'Estado desconocido')

    @property
    def is_active(self) -> bool:
        """
        Verifica si el ticket está activo (no completado ni cancelado)

        Returns:
            bool: True si está activo
        """
        return self.Status in ['Waiting', 'Called', 'InProgress']

    @property
    def is_completed(self) -> bool:
        """
        Verifica si el ticket está completado

        Returns:
            bool: True si está completado
        """
        return self.Status == 'Completed'

    @property
    def is_cancelled(self) -> bool:
        """
        Verifica si el ticket fue cancelado

        Returns:
            bool: True si fue cancelado
        """
        return self.Status in ['Cancelled', 'NoShow']

    @property
    def can_be_called(self) -> bool:
        """
        Verifica si el ticket puede ser llamado

        Returns:
            bool: True si puede ser llamado
        """
        return self.Status == 'Waiting'

    @property
    def can_be_attended(self) -> bool:
        """
        Verifica si el ticket puede ser atendido

        Returns:
            bool: True si puede ser atendido
        """
        return self.Status in ['Called', 'InProgress']

    @property
    def patient_name(self) -> Optional[str]:
        """
        Obtiene el nombre del paciente

        Returns:
            str: Nombre del paciente
        """
        return self.patient.FullName if self.patient else None

    @property
    def patient_document(self) -> Optional[str]:
        """
        Obtiene el documento del paciente

        Returns:
            str: Documento del paciente
        """
        return self.patient.DocumentNumber if self.patient else None

    @property
    def service_name(self) -> Optional[str]:
        """
        Obtiene el nombre del servicio

        Returns:
            str: Nombre del servicio
        """
        return self.service_type.Name if self.service_type else None

    @property
    def service_code(self) -> Optional[str]:
        """
        Obtiene el código del servicio

        Returns:
            str: Código del servicio
        """
        return self.service_type.Code if self.service_type else None

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
    def actual_wait_time_minutes(self) -> Optional[int]:
        """
        Obtiene el tiempo real de espera desde la columna calculada

        Returns:
            int: Tiempo de espera en minutos
        """
        return self.ActualWaitTime

    @property
    def service_time_minutes(self) -> Optional[int]:
        """
        Obtiene el tiempo de servicio desde la columna calculada

        Returns:
            int: Tiempo de servicio en minutos
        """
        return self.ServiceTime

    @property
    def total_time_minutes(self) -> Optional[int]:
        """
        Calcula el tiempo total desde creación hasta finalización

        Returns:
            int: Tiempo total en minutos
        """
        end_time = self.CompletedAt or datetime.now()
        return int((end_time - self.CreatedAt).total_seconds() / 60)

    @property
    def is_overdue(self) -> bool:
        """
        Verifica si el ticket está retrasado respecto al tiempo estimado

        Returns:
            bool: True si está retrasado
        """
        if not self.EstimatedWaitTime or self.is_completed or self.is_cancelled:
            return False

        elapsed_minutes = int((datetime.now() - self.CreatedAt).total_seconds() / 60)
        return elapsed_minutes > self.EstimatedWaitTime

    @property
    def priority_score(self) -> int:
        """
        Calcula un puntaje de prioridad para ordenamiento

        Returns:
            int: Puntaje de prioridad (menor = mayor prioridad)
        """
        base_score = self.Position

        # Ajustar por prioridad del servicio
        if self.service_type:
            base_score -= (6 - self.service_type.Priority) * 100

        # Ajustar por tiempo de espera
        if self.actual_wait_time_minutes:
            base_score -= self.actual_wait_time_minutes

        # Prioridad por edad del paciente
        if self.patient and self.patient.requires_priority:
            base_score -= 500

        return base_score

    def call_ticket(self, station_id: Optional[int] = None) -> bool:
        """
        Llama al ticket para atención

        Args:
            station_id: ID de la estación que llama

        Returns:
            bool: True si se llamó exitosamente
        """
        if not self.can_be_called:
            return False

        self.Status = 'Called'
        self.CalledAt = func.getdate()

        if station_id:
            self.StationId = station_id

        return True

    def start_attention(self) -> bool:
        """
        Inicia la atención del ticket

        Returns:
            bool: True si se inició exitosamente
        """
        if not self.can_be_attended:
            return False

        self.Status = 'InProgress'
        self.AttendedAt = func.getdate()

        return True

    def complete_ticket(self, notes: Optional[str] = None) -> bool:
        """
        Completa la atención del ticket

        Args:
            notes: Notas adicionales

        Returns:
            bool: True si se completó exitosamente
        """
        if self.Status != 'InProgress':
            return False

        self.Status = 'Completed'
        self.CompletedAt = func.getdate()

        if notes:
            self.Notes = (self.Notes + ' | ' + notes) if self.Notes else notes

        return True

    def cancel_ticket(self, reason: str = 'Cancelled') -> bool:
        """
        Cancela el ticket

        Args:
            reason: Razón de cancelación

        Returns:
            bool: True si se canceló exitosamente
        """
        if not self.is_active:
            return False

        self.Status = 'NoShow' if reason == 'NoShow' else 'Cancelled'
        self.Notes = (self.Notes + ' | ' + reason) if self.Notes else reason

        return True

    def transfer_to_station(self, new_station_id: int) -> bool:
        """
        Transfiere el ticket a otra estación

        Args:
            new_station_id: ID de la nueva estación

        Returns:
            bool: True si se transfirió exitosamente
        """
        if not self.is_active:
            return False

        old_station_id = self.StationId
        self.StationId = new_station_id

        # Resetear estado si estaba en progreso
        if self.Status == 'InProgress':
            self.Status = 'Called'
            self.AttendedAt = None

        return True

    def update_estimated_wait_time(self) -> None:
        """
        Actualiza el tiempo estimado de espera basado en la cola actual
        """
        if not self.service_type or self.is_completed or self.is_cancelled:
            return

        # Calcular basado en posición y tiempo promedio del servicio
        queue_length = max(0, self.Position - 1)  # Tickets antes que este
        avg_time = self.service_type.AverageTimeMinutes
        active_stations = self.service_type.active_station_count

        if active_stations > 0:
            estimated_time = (queue_length * avg_time) // active_stations
        else:
            estimated_time = queue_length * avg_time

        self.EstimatedWaitTime = max(1, estimated_time)  # Mínimo 1 minuto

    def generate_qr_code(self) -> str:
        """
        Genera el código QR para el ticket

        Returns:
            str: Datos para el código QR
        """
        qr_data = {
            'ticket_id': str(self.Id),
            'ticket_number': self.TicketNumber,
            'service_code': self.service_code,
            'CreatedAt': self.CreatedAt.isoformat() if self.CreatedAt else None
        }

        import json
        return json.dumps(qr_data)

    def get_notification_recipients(self) -> List[str]:
        """
        Obtiene los destinatarios para notificaciones

        Returns:
            List[str]: Lista de teléfonos/emails para notificar
        """
        recipients = []

        if self.patient:
            if self.patient.Phone:
                recipients.append(self.patient.Phone)
            if self.patient.Email:
                recipients.append(self.patient.Email)

        return recipients

    @classmethod
    def generate_ticket_number(cls, service_type, daily_counter: int) -> str:
        """
        Genera un número de ticket

        Args:
            service_type: Tipo de servicio
            daily_counter: Contador diario

        Returns:
            str: Número de ticket generado
        """
        prefix = service_type.TicketPrefix if service_type else 'T'
        return f"{prefix}{daily_counter:03d}"

    def to_dict(self, include_patient: bool = True, include_service: bool = True) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_patient: Si incluir datos del paciente
            include_service: Si incluir datos del servicio

        Returns:
            dict: Diccionario con los datos del ticket
        """
        result = super().to_dict()

        # Agregar propiedades calculadas
        result['status_display'] = self.status_display
        result['is_active'] = self.is_active
        result['is_completed'] = self.is_completed
        result['is_cancelled'] = self.is_cancelled
        result['can_be_called'] = self.can_be_called
        result['can_be_attended'] = self.can_be_attended
        result['actual_wait_time_minutes'] = self.actual_wait_time_minutes
        result['service_time_minutes'] = self.service_time_minutes
        result['total_time_minutes'] = self.total_time_minutes
        result['is_overdue'] = self.is_overdue
        result['priority_score'] = self.priority_score

        if include_patient:
            result['patient_name'] = self.patient_name
            result['patient_document'] = self.patient_document

        if include_service:
            result['service_name'] = self.service_name
            result['service_code'] = self.service_code
            result['station_name'] = self.station_name
            result['station_code'] = self.station_code

        return result

    def __repr__(self) -> str:
        return f"<Ticket(Id={self.Id}, Number='{self.TicketNumber}', Status='{self.Status}')>"