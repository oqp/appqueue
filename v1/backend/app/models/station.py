"""
Modelo SQLAlchemy para estaciones/ventanillas de atención del laboratorio
Compatible con SQL Server y estructura real de la base de datos
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
from app.models.base import BaseModel, TimestampMixin, ActiveMixin
import uuid


class Station(BaseModel, TimestampMixin, ActiveMixin):
    """
    Modelo para estaciones/ventanillas de atención del laboratorio
    Coincide exactamente con la estructura de la tabla en SQL Server
    """
    __tablename__ = 'Stations'

    # ========================================
    # CAMPOS PRINCIPALES (REALES EN BD)
    # ========================================

    Id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="ID único de la estación"
    )

    Name = Column(
        String(100),
        nullable=False,
        comment="Nombre de la estación"
    )

    Code = Column(
        String(10),
        nullable=False,
        unique=True,
        comment="Código único de la estación (VA01, VR01, etc.)"
    )

    Description = Column(
        String(200),
        nullable=True,
        comment="Descripción de la estación"
    )

    ServiceTypeId = Column(
        Integer,
        ForeignKey('ServiceTypes.Id'),
        nullable=True,
        comment="ID del tipo de servicio asociado"
    )

    Location = Column(
        String(100),
        nullable=True,
        comment="Ubicación física de la estación"
    )

    Status = Column(
        String(20),
        nullable=False,
        default='Available',
        comment="Estado actual de la estación"
    )

    CurrentTicketId = Column(
        UNIQUEIDENTIFIER,
        nullable=True,
        comment="ID del ticket actualmente siendo atendido"
    )

    # Los campos CreatedAt, UpdatedAt e IsActive ya vienen de las mixins

    # ========================================
    # RELACIONES
    # ========================================

    # Relación con ServiceType
    service_type = relationship(
        "ServiceType",
        back_populates="stations",
        lazy="joined"
    )

    # Relación con usuarios asignados (uno a muchos a través de User.StationId)
    users = relationship(
        "User",
        back_populates="station",
        foreign_keys="User.StationId",
        lazy="dynamic"
    )

    # Relación con tickets atendidos
    tickets = relationship(
        "Ticket",
        foreign_keys="Ticket.StationId",
        back_populates="station",
        lazy="dynamic"
    )

    # Relación con el ticket actual
    current_ticket = relationship(
        "Ticket",
        foreign_keys=[CurrentTicketId],
        primaryjoin="Station.CurrentTicketId == Ticket.Id",
        post_update=True,
        lazy="joined"
    )

    # Relación con logs de actividad
    activity_logs = relationship(
        "ActivityLog",
        back_populates="station",
        foreign_keys="ActivityLog.StationId",
        lazy="dynamic"
    )

    # Relación con métricas diarias
    daily_metrics = relationship(
        "DailyMetrics",
        back_populates="station",
        foreign_keys="DailyMetrics.StationId",
        lazy="dynamic"
    )

    # Relación con estados de cola
    queue_states = relationship(
        "QueueState",
        back_populates="station",
        foreign_keys="QueueState.StationId",
        lazy="dynamic"
    )

    # ========================================
    # CONSTRAINTS Y VALIDACIONES
    # ========================================

    __table_args__ = (
        CheckConstraint(
            "Status IN ('Available', 'Busy', 'Break', 'Maintenance', 'Offline')",
            name='CK_Station_Status'
        ),
        Index('IX_Station_Code', 'Code'),
        Index('IX_Station_ServiceTypeId', 'ServiceTypeId'),
        Index('IX_Station_Status', 'Status'),
        Index('IX_Station_IsActive', 'IsActive'),
    )

    # ========================================
    # VALIDADORES
    # ========================================

    @validates('Code')
    def validate_code(self, key, value):
        """Valida el código de la estación"""
        if value:
            value = value.strip().upper()
            if len(value) > 10:
                raise ValueError("El código no puede tener más de 10 caracteres")
        return value

    @validates('Status')
    def validate_status(self, key, value):
        """Valida el estado de la estación"""
        valid_statuses = ['Available', 'Busy', 'Break', 'Maintenance', 'Offline']
        if value not in valid_statuses:
            raise ValueError(f"Estado inválido. Debe ser uno de: {', '.join(valid_statuses)}")
        return value

    # ========================================
    # PROPIEDADES CALCULADAS
    # ========================================

    @property
    def is_available(self) -> bool:
        """Verifica si la estación está disponible para atender"""
        return self.IsActive and self.Status == 'Available'

    @property
    def is_busy(self) -> bool:
        """Verifica si la estación está ocupada"""
        return self.Status == 'Busy'

    @property
    def can_receive_patients(self) -> bool:
        """Verifica si puede recibir pacientes"""
        return self.is_available and not self.CurrentTicketId

    @property
    def display_name(self) -> str:
        """Nombre para mostrar"""
        return f"{self.Name} ({self.Code})"

    @property
    def status_display(self) -> str:
        """Estado en español para mostrar"""
        status_map = {
            'Available': 'Disponible',
            'Busy': 'Ocupada',
            'Break': 'En descanso',
            'Maintenance': 'Mantenimiento',
            'Offline': 'Fuera de línea'
        }
        return status_map.get(self.Status, self.Status)

    # ========================================
    # MÉTODOS DE INSTANCIA
    # ========================================

    def set_status(self, status: str) -> None:
        """Cambia el estado de la estación"""
        self.Status = status
        self.UpdatedAt = datetime.utcnow()

    def set_busy(self, ticket_id: Optional[str] = None) -> None:
        """Marca la estación como ocupada"""
        self.Status = 'Busy'
        if ticket_id:
            self.CurrentTicketId = ticket_id
        self.UpdatedAt = datetime.utcnow()

    def set_available(self) -> None:
        """Marca la estación como disponible"""
        self.Status = 'Available'
        self.CurrentTicketId = None
        self.UpdatedAt = datetime.utcnow()

    def set_break(self) -> None:
        """Marca la estación en descanso"""
        self.Status = 'Break'
        self.CurrentTicketId = None
        self.UpdatedAt = datetime.utcnow()

    def set_maintenance(self) -> None:
        """Marca la estación en mantenimiento"""
        self.Status = 'Maintenance'
        self.CurrentTicketId = None
        self.UpdatedAt = datetime.utcnow()

    def set_offline(self) -> None:
        """Marca la estación fuera de línea"""
        self.Status = 'Offline'
        self.CurrentTicketId = None
        self.UpdatedAt = datetime.utcnow()

    def assign_ticket(self, ticket) -> None:
        """Asigna un ticket a la estación"""
        self.CurrentTicketId = ticket.Id
        self.Status = 'Busy'
        self.UpdatedAt = datetime.utcnow()

    def release_ticket(self) -> None:
        """Libera el ticket actual"""
        self.CurrentTicketId = None
        self.Status = 'Available'
        self.UpdatedAt = datetime.utcnow()

    # ========================================
    # MÉTODOS DE CLASE
    # ========================================

    @classmethod
    def get_available_stations(cls, db_session, service_type_id: Optional[int] = None):
        """Obtiene todas las estaciones disponibles"""
        query = db_session.query(cls).filter(
            cls.IsActive == True,
            cls.Status == 'Available'
        )

        if service_type_id:
            query = query.filter(cls.ServiceTypeId == service_type_id)

        return query.all()

    @classmethod
    def get_by_code(cls, db_session, code: str):
        """Obtiene una estación por su código"""
        return db_session.query(cls).filter(
            cls.Code == code.upper(),
            cls.IsActive == True
        ).first()

    # ========================================
    # REPRESENTACIÓN
    # ========================================

    def __repr__(self):
        return f"<Station(Id={self.Id}, Code={self.Code}, Name={self.Name}, Status={self.Status})>"

    def __str__(self):
        return self.display_name

    def to_dict(self, include_relations: bool = False) -> dict:
        """Convierte la estación a diccionario"""
        data = {
            'Id': self.Id,
            'Name': self.Name,
            'Code': self.Code,
            'Description': self.Description,
            'ServiceTypeId': self.ServiceTypeId,
            'Location': self.Location,
            'Status': self.Status,
            'StatusDisplay': self.status_display,
            'CurrentTicketId': str(self.CurrentTicketId) if self.CurrentTicketId else None,
            'IsActive': self.IsActive,
            'IsAvailable': self.is_available,
            'CanReceivePatients': self.can_receive_patients,
            'CreatedAt': self.CreatedAt.isoformat() if self.CreatedAt else None,
            'UpdatedAt': self.UpdatedAt.isoformat() if self.UpdatedAt else None
        }

        if include_relations:
            if hasattr(self, 'service_type') and self.service_type:
                data['ServiceType'] = {
                    'Id': self.service_type.Id,
                    'Name': self.service_type.Name,
                    'Code': self.service_type.Code
                }
            if hasattr(self, 'current_ticket') and self.current_ticket:
                data['CurrentTicket'] = {
                    'Id': str(self.current_ticket.Id),
                    'TicketNumber': self.current_ticket.TicketNumber,
                    'Status': self.current_ticket.Status
                }

        return data