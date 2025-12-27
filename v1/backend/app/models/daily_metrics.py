from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func, text
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
import uuid
from .base import BaseModel, TimestampMixin


class DailyMetrics(BaseModel, TimestampMixin):
    """
    Modelo para métricas diarias del sistema de gestión de colas
    """
    __tablename__ = 'DailyMetrics'

    # Campos principales
    Id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        server_default=text('newid()'),
        comment="ID único de la métrica diaria"
    )

    Date = Column(
        Date,
        nullable=False,
        comment="Fecha de la métrica"
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
        comment="ID de la estación (opcional para métricas globales)"
    )

    TotalTickets = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total de tickets generados"
    )

    CompletedTickets = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Tickets completados"
    )

    CancelledTickets = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Tickets cancelados"
    )

    NoShowTickets = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Tickets donde el paciente no se presentó"
    )

    AverageWaitTime = Column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        comment="Tiempo promedio de espera en minutos"
    )

    AverageServiceTime = Column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        comment="Tiempo promedio de servicio en minutos"
    )

    PeakHour = Column(
        String(5),
        nullable=True,
        comment="Hora pico del día (formato HH:MM)"
    )

    # Relaciones
    service_type = relationship(
        "ServiceType",
        back_populates="daily_metrics"
    )

    station = relationship(
        "Station",
        back_populates="daily_metrics"
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo DailyMetrics
        """
        super().__init__(**kwargs)

    @validates('Date')
    def validate_date(self, key, metric_date):
        """
        Valida la fecha de la métrica
        """
        if metric_date:
            if isinstance(metric_date, str):
                try:
                    metric_date = datetime.strptime(metric_date, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError("Formato de fecha inválido (usar YYYY-MM-DD)")

            # No permitir fechas futuras
            if metric_date > date.today():
                raise ValueError("La fecha no puede ser futura")

            return metric_date
        return metric_date

    @validates('TotalTickets', 'CompletedTickets', 'CancelledTickets', 'NoShowTickets')
    def validate_ticket_counts(self, key, count):
        """
        Valida que los contadores sean no negativos
        """
        if count is not None and count < 0:
            raise ValueError(f"{key} no puede ser negativo")
        return count

    @validates('AverageWaitTime', 'AverageServiceTime')
    def validate_average_times(self, key, time_value):
        """
        Valida que los tiempos promedio sean no negativos
        """
        if time_value is not None and time_value < 0:
            raise ValueError(f"{key} no puede ser negativo")
        return time_value

    @validates('PeakHour')
    def validate_peak_hour(self, key, hour):
        """
        Valida el formato de la hora pico
        """
        if hour:
            import re
            if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', hour):
                raise ValueError("Formato de hora inválido (usar HH:MM)")
            return hour
        return hour

    @property
    def service_name(self) -> Optional[str]:
        """
        Obtiene el nombre del tipo de servicio

        Returns:
            str: Nombre del servicio
        """
        return self.service_type.Name if self.service_type else None

    @property
    def service_code(self) -> Optional[str]:
        """
        Obtiene el código del tipo de servicio

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
    def processed_tickets(self) -> int:
        """
        Obtiene el total de tickets procesados (completados + cancelados + no show)

        Returns:
            int: Tickets procesados
        """
        return self.CompletedTickets + self.CancelledTickets + self.NoShowTickets

    @property
    def pending_tickets(self) -> int:
        """
        Obtiene los tickets pendientes

        Returns:
            int: Tickets pendientes
        """
        return max(0, self.TotalTickets - self.processed_tickets)

    @property
    def completion_rate(self) -> float:
        """
        Calcula la tasa de completación

        Returns:
            float: Porcentaje de tickets completados
        """
        if self.TotalTickets == 0:
            return 0.0
        return (self.CompletedTickets / self.TotalTickets) * 100

    @property
    def cancellation_rate(self) -> float:
        """
        Calcula la tasa de cancelación

        Returns:
            float: Porcentaje de tickets cancelados
        """
        if self.TotalTickets == 0:
            return 0.0
        return (self.CancelledTickets / self.TotalTickets) * 100

    @property
    def no_show_rate(self) -> float:
        """
        Calcula la tasa de no presentación

        Returns:
            float: Porcentaje de no show
        """
        if self.TotalTickets == 0:
            return 0.0
        return (self.NoShowTickets / self.TotalTickets) * 100

    @property
    def efficiency_score(self) -> float:
        """
        Calcula un puntaje de eficiencia basado en múltiples factores

        Returns:
            float: Puntaje de eficiencia (0-100)
        """
        if self.TotalTickets == 0:
            return 0.0

        # Factores que contribuyen a la eficiencia
        completion_factor = self.completion_rate * 0.5  # 50% del peso
        wait_time_factor = max(0, 50 - float(self.AverageWaitTime or 0)) * 0.3  # 30% del peso
        service_time_factor = max(0, 30 - float(self.AverageServiceTime or 0)) * 0.2  # 20% del peso

        return min(100, completion_factor + wait_time_factor + service_time_factor)

    @property
    def is_peak_performance(self) -> bool:
        """
        Verifica si el día tuvo un rendimiento destacado

        Returns:
            bool: True si fue un día de alto rendimiento
        """
        return (self.completion_rate >= 90 and
                float(self.AverageWaitTime or 0) <= 15 and
                self.no_show_rate <= 5)

    @property
    def needs_attention(self) -> bool:
        """
        Verifica si las métricas indican problemas que requieren atención

        Returns:
            bool: True si necesita atención
        """
        return (self.completion_rate < 70 or
                float(self.AverageWaitTime or 0) > 30 or
                self.no_show_rate > 15)

    @property
    def date_display(self) -> str:
        """
        Obtiene la fecha en formato legible

        Returns:
            str: Fecha formateada
        """
        if not self.Date:
            return "Sin fecha"

        # Formato en español
        months = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]

        day = self.Date.day
        month = months[self.Date.month - 1]
        year = self.Date.year

        return f"{day} de {month} de {year}"

    def update_metrics(self, tickets_data: List[Dict]) -> None:
        """
        Actualiza las métricas basado en datos de tickets

        Args:
            tickets_data: Lista de datos de tickets del día
        """
        if not tickets_data:
            return

        # Contadores
        self.TotalTickets = len(tickets_data)
        self.CompletedTickets = sum(1 for t in tickets_data if t.get('status') == 'Completed')
        self.CancelledTickets = sum(1 for t in tickets_data if t.get('status') == 'Cancelled')
        self.NoShowTickets = sum(1 for t in tickets_data if t.get('status') == 'NoShow')

        # Tiempos promedio
        wait_times = [t.get('wait_time', 0) for t in tickets_data if t.get('wait_time')]
        service_times = [t.get('service_time', 0) for t in tickets_data if t.get('service_time')]

        self.AverageWaitTime = sum(wait_times) / len(wait_times) if wait_times else 0
        self.AverageServiceTime = sum(service_times) / len(service_times) if service_times else 0

        # Hora pico (hora con más tickets creados)
        hour_counts = {}
        for ticket in tickets_data:
            if ticket.get('created_at'):
                try:
                    hour = ticket['created_at'].strftime('%H:00')
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
                except:
                    continue

        if hour_counts:
            self.PeakHour = max(hour_counts, key=hour_counts.get)

    @classmethod
    def create_or_update(cls, date: date, service_type_id: int,
                         station_id: Optional[int] = None) -> 'DailyMetrics':
        """
        Crea o actualiza una métrica diaria

        Args:
            date: Fecha de la métrica
            service_type_id: ID del tipo de servicio
            station_id: ID de la estación (opcional)

        Returns:
            DailyMetrics: Instancia de la métrica
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        return cls(
            Date=date,
            ServiceTypeId=service_type_id,
            StationId=station_id
        )

    @classmethod
    def get_period_summary(cls, start_date: date, end_date: date,
                           service_type_id: Optional[int] = None) -> Dict[str, float]:
        """
        Obtiene un resumen de métricas para un período

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            service_type_id: ID del tipo de servicio (opcional)

        Returns:
            Dict[str, float]: Resumen de métricas
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        return {
            'total_tickets': 0,
            'avg_completion_rate': 0.0,
            'avg_wait_time': 0.0,
            'avg_service_time': 0.0,
            'total_days': (end_date - start_date).days + 1
        }

    @classmethod
    def get_comparative_analysis(cls, current_date: date,
                                 previous_period_days: int = 7) -> Dict[str, Dict]:
        """
        Obtiene análisis comparativo con período anterior

        Args:
            current_date: Fecha actual
            previous_period_days: Días del período anterior

        Returns:
            Dict[str, Dict]: Análisis comparativo
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        return {
            'current_period': {},
            'previous_period': {},
            'changes': {}
        }

    @classmethod
    def get_trends(cls, days: int = 30) -> List[Dict]:
        """
        Obtiene tendencias de métricas

        Args:
            days: Número de días para analizar

        Returns:
            List[Dict]: Datos de tendencias
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        return []

    def to_dict(self, include_calculations: bool = True) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_calculations: Si incluir cálculos derivados

        Returns:
            dict: Diccionario con los datos de la métrica
        """
        result = super().to_dict()

        # Agregar propiedades de relaciones
        result['service_name'] = self.service_name
        result['service_code'] = self.service_code
        result['station_name'] = self.station_name
        result['station_code'] = self.station_code
        result['date_display'] = self.date_display

        if include_calculations:
            result['processed_tickets'] = self.processed_tickets
            result['pending_tickets'] = self.pending_tickets
            result['completion_rate'] = round(self.completion_rate, 2)
            result['cancellation_rate'] = round(self.cancellation_rate, 2)
            result['no_show_rate'] = round(self.no_show_rate, 2)
            result['efficiency_score'] = round(self.efficiency_score, 2)
            result['is_peak_performance'] = self.is_peak_performance
            result['needs_attention'] = self.needs_attention

        return result

    def __repr__(self) -> str:
        return f"<DailyMetrics(Id={self.Id}, Date={self.Date}, Service='{self.service_code}')>"