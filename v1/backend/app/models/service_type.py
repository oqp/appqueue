from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from typing import Optional, List
from .base import BaseModel, TimestampMixin, ActiveMixin


class ServiceType(BaseModel, TimestampMixin, ActiveMixin):
    """
    Modelo para tipos de servicios del laboratorio clínico
    """
    __tablename__ = 'ServiceTypes'

    # Campos principales
    Id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="ID único del tipo de servicio"
    )

    Code = Column(
        String(10),
        nullable=False,
        unique=True,
        comment="Código único del servicio (ej: LAB, RES, MUE)"
    )

    Name = Column(
        String(100),
        nullable=False,
        comment="Nombre del tipo de servicio"
    )

    Description = Column(
        String(500),
        nullable=True,
        comment="Descripción detallada del servicio"
    )

    Priority = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Prioridad del servicio (1=máxima, 5=mínima)"
    )

    AverageTimeMinutes = Column(
        Integer,
        nullable=False,
        default=10,
        comment="Tiempo promedio de atención en minutos"
    )

    TicketPrefix = Column(
        String(5),
        nullable=False,
        comment="Prefijo para los números de ticket (ej: A, B, LAB)"
    )

    Color = Column(
        String(7),
        nullable=False,
        default='#007bff',
        comment="Color hexadecimal para la interfaz"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            'Priority >= 1 AND Priority <= 5',
            name='chk_servicetype_priority'
        ),
        CheckConstraint(
            'AverageTimeMinutes > 0',
            name='chk_servicetype_avgtime'
        ),
    )

    # Relaciones
    stations = relationship(
        "Station",
        back_populates="service_type",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    tickets = relationship(
        "Ticket",
        back_populates="service_type",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    daily_metrics = relationship(
        "DailyMetrics",
        back_populates="service_type",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    queue_states = relationship(
        "QueueState",
        back_populates="service_type",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo ServiceType
        """
        super().__init__(**kwargs)

    @validates('Priority')
    def validate_priority(self, key, priority):
        """
        Valida que la prioridad esté en el rango correcto
        """
        if priority is not None and (priority < 1 or priority > 5):
            raise ValueError("La prioridad debe estar entre 1 y 5")
        return priority

    @validates('AverageTimeMinutes')
    def validate_average_time(self, key, minutes):
        """
        Valida que el tiempo promedio sea positivo
        """
        if minutes is not None and minutes <= 0:
            raise ValueError("El tiempo promedio debe ser mayor a 0")
        return minutes

    @validates('Color')
    def validate_color(self, key, color):
        """
        Valida que el color sea un código hexadecimal válido
        """
        if color and not (color.startswith('#') and len(color) == 7):
            raise ValueError("El color debe ser un código hexadecimal válido (#RRGGBB)")
        return color

    @validates('Code')
    def validate_code(self, key, code):
        """
        Valida y normaliza el código del servicio
        """
        if code:
            return code.upper().strip()
        return code

    @validates('TicketPrefix')
    def validate_ticket_prefix(self, key, prefix):
        """
        Valida y normaliza el prefijo del ticket
        """
        if prefix:
            return prefix.upper().strip()
        return prefix

    @property
    def priority_name(self) -> str:
        """
        Obtiene el nombre descriptivo de la prioridad

        Returns:
            str: Nombre de la prioridad
        """
        priority_names = {
            1: "Muy Alta",
            2: "Alta",
            3: "Media",
            4: "Baja",
            5: "Muy Baja"
        }
        return priority_names.get(self.Priority, "No definida")

    @property
    def is_high_priority(self) -> bool:
        """
        Verifica si es un servicio de alta prioridad

        Returns:
            bool: True si es alta prioridad (1 o 2)
        """
        return self.Priority <= 2

    @property
    def station_count(self) -> int:
        """
        Obtiene la cantidad de estaciones asignadas a este servicio

        Returns:
            int: Cantidad de estaciones
        """
        return len([s for s in self.stations if s.IsActive]) if self.stations else 0

    @property
    def active_station_count(self) -> int:
        """
        Obtiene la cantidad de estaciones activas para este servicio

        Returns:
            int: Cantidad de estaciones activas
        """
        if not self.stations:
            return 0
        return len([s for s in self.stations if s.IsActive and s.Status == 'Available'])

    def get_current_queue_length(self) -> int:
        """
        Obtiene la longitud actual de la cola para este servicio

        Returns:
            int: Longitud de la cola
        """
        if not self.queue_states:
            return 0

        total_length = sum(qs.QueueLength for qs in self.queue_states if qs.QueueLength)
        return total_length

    def get_estimated_wait_time(self) -> int:
        """
        Calcula el tiempo estimado de espera basado en la cola actual

        Returns:
            int: Tiempo estimado en minutos
        """
        queue_length = self.get_current_queue_length()
        active_stations = self.active_station_count

        if active_stations == 0:
            return queue_length * self.AverageTimeMinutes

        return (queue_length * self.AverageTimeMinutes) // active_stations

    @classmethod
    def get_default_service_types(cls) -> List[dict]:
        """
        Obtiene los tipos de servicio por defecto para un laboratorio clínico

        Returns:
            List[dict]: Lista de tipos de servicio por defecto
        """
        return [
            {
                "Code": "LAB",
                "Name": "Análisis de Laboratorio",
                "Description": "Toma de muestras y análisis clínicos generales",
                "Priority": 2,
                "AverageTimeMinutes": 15,
                "TicketPrefix": "A",
                "Color": "#007bff"
            },
            {
                "Code": "RES",
                "Name": "Entrega de Resultados",
                "Description": "Entrega de resultados de estudios completados",
                "Priority": 3,
                "AverageTimeMinutes": 5,
                "TicketPrefix": "R",
                "Color": "#28a745"
            },
            {
                "Code": "MUE",
                "Name": "Entrega de Muestras",
                "Description": "Entrega de muestras por parte del paciente",
                "Priority": 2,
                "AverageTimeMinutes": 8,
                "TicketPrefix": "M",
                "Color": "#ffc107"
            },
            {
                "Code": "CON",
                "Name": "Consultas",
                "Description": "Consultas médicas e informativas",
                "Priority": 4,
                "AverageTimeMinutes": 20,
                "TicketPrefix": "C",
                "Color": "#17a2b8"
            },
            {
                "Code": "PRI",
                "Name": "Servicios Prioritarios",
                "Description": "Atención prioritaria para embarazadas, adultos mayores, discapacitados",
                "Priority": 1,
                "AverageTimeMinutes": 12,
                "TicketPrefix": "P",
                "Color": "#dc3545"
            }
        ]

    def to_dict(self, include_stats: bool = False) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_stats: Si incluir estadísticas de colas y estaciones

        Returns:
            dict: Diccionario con los datos del servicio
        """
        result = super().to_dict()

        # Agregar propiedades calculadas
        result['priority_name'] = self.priority_name
        result['is_high_priority'] = self.is_high_priority

        if include_stats:
            result['station_count'] = self.station_count
            result['active_station_count'] = self.active_station_count
            result['current_queue_length'] = self.get_current_queue_length()
            result['estimated_wait_time'] = self.get_estimated_wait_time()

        return result

    def __repr__(self) -> str:
        return f"<ServiceType(Id={self.Id}, Code='{self.Code}', Name='{self.Name}')>"