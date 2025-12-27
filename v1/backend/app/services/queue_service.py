"""
Servicio de lógica de negocio para gestión de colas del laboratorio clínico
Compatible 100% con toda la estructura existente del proyecto
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta, time, date
import logging
import asyncio
from enum import Enum
import json
import qrcode
import io
import base64

from app.crud.ticket import ticket_crud
from app.crud.station import station_crud
from app.crud.patient import patient as patient_crud
from app.crud.service_type import service_type_crud
from app.models.ticket import Ticket
from app.models.station import Station
from app.schemas.ticket import (
    TicketResponse, TicketStatus, TicketStats,
    QueuePosition, DailyTicketSummary
)
from app.schemas.station import CallNextPatientResponse
from app.websocket.connection_manager import websocket_manager

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)


class QueuePriority(str, Enum):
    """Niveles de prioridad para colas"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class QueueStrategy(str, Enum):
    """Estrategias de gestión de colas"""
    FIFO = "fifo"  # First In, First Out
    PRIORITY = "priority"  # Por prioridad
    SERVICE_TIME = "service_time"  # Por tiempo de servicio
    BALANCED = "balanced"  # Estrategia balanceada
    SMART = "smart"  # Algoritmo inteligente


# ========================================
# CLASE PRINCIPAL DEL SERVICIO
# ========================================

class QueueService:
    """
    Servicio principal para gestión de colas
    Maneja lógica de negocio compleja, algoritmos de cola y optimización
    """

    def __init__(self):
        """Inicializa el servicio de colas"""
        self.queue_strategy = QueueStrategy.SMART
        self.max_wait_time_minutes = 120  # Tiempo máximo de espera
        self.priority_boost_minutes = 30  # Boost de prioridad después de X minutos
        self.auto_rebalance_enabled = True
        self.notification_enabled = True

    # ========================================
    # MÉTODOS DE GESTIÓN DE COLA
    # ========================================

    def get_queue_by_service(
        self,
        db: Session,
        service_type_id: int,
        include_completed: bool = False
    ) -> List[Ticket]:
        """
        Obtiene la cola completa de un servicio específico

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            include_completed: Incluir tickets completados

        Returns:
            List[Ticket]: Lista de tickets en la cola
        """
        try:
            # Construir query base
            from app.models.ticket import Ticket
            from sqlalchemy import text

            # Para SQL Server, usar una comparación de fecha más compatible
            today_start = datetime.combine(date.today(), time.min)
            today_end = datetime.combine(date.today(), time.max)

            query = db.query(Ticket).filter(
                Ticket.ServiceTypeId == service_type_id,
                text("CreatedAt >= :start AND CreatedAt <= :end")
            ).params(start=today_start, end=today_end)

            # Filtrar por estado si no incluimos completados
            if not include_completed:
                query = query.filter(
                    Ticket.Status.in_([
                        TicketStatus.WAITING.value,
                        TicketStatus.CALLED.value,
                        TicketStatus.IN_PROGRESS.value
                    ])
                )

            # Ordenar por posición y prioridad
            tickets = query.order_by(
                Ticket.Position.asc()
            ).all()

            return tickets

        except Exception as e:
            logger.error(f"Error obteniendo cola por servicio: {e}")
            return []

    async def get_next_in_queue(
        self,
        db: Session,
        station_id: int,
        skip_current: bool = True
    ) -> Optional[Ticket]:
        """
        Obtiene el siguiente ticket en la cola para una estación

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            skip_current: Omitir el ticket actual de la estación

        Returns:
            Optional[Ticket]: Siguiente ticket o None
        """
        try:
            # Obtener la estación
            station = station_crud.get(db, station_id)
            if not station:
                return None

            # Query base para tickets en espera
            today_start = datetime.combine(date.today(), time.min)
            today_end = datetime.combine(date.today(), time.max)

            query = db.query(Ticket).filter(
                Ticket.Status == TicketStatus.WAITING.value,
                text("CreatedAt >= :start AND CreatedAt <= :end")
            ).params(start=today_start, end=today_end)

            # Si la estación tiene servicio específico, filtrar
            if station.ServiceTypeId:
                query = query.filter(
                    Ticket.ServiceTypeId == station.ServiceTypeId
                )

            # Aplicar estrategia de cola
            if self.queue_strategy == QueueStrategy.SMART:
                # Estrategia inteligente: considera prioridad y tiempo de espera
                next_ticket = self._apply_smart_strategy(query)
            else:
                # Estrategia FIFO por defecto
                next_ticket = query.order_by(Ticket.Position.asc()).first()

            return next_ticket

        except Exception as e:
            logger.error(f"Error obteniendo siguiente en cola: {e}")
            return None

    def _apply_smart_strategy(self, query) -> Optional[Ticket]:
        """
        Aplica estrategia inteligente para selección de tickets

        Args:
            query: Query base de SQLAlchemy

        Returns:
            Optional[Ticket]: Ticket seleccionado
        """
        tickets = query.all()
        if not tickets:
            return None

        # Calcular score para cada ticket
        scored_tickets = []
        current_time = datetime.now()

        for ticket in tickets:
            score = 0

            # Factor de tiempo de espera (más tiempo = más prioridad)
            wait_minutes = (current_time - ticket.created_at).total_seconds() / 60
            score += min(wait_minutes / 5, 20)  # Máximo 20 puntos por espera

            # Factor de prioridad del servicio
            if ticket.service_type:
                score += (6 - ticket.service_type.Priority) * 5  # 5-25 puntos

            # Boost si excede tiempo de espera razonable
            if wait_minutes > self.priority_boost_minutes:
                score += 10

            # Penalización si fue llamado previamente (no show)
            if ticket.CalledAt:
                score -= 5

            scored_tickets.append((ticket, score))

        # Ordenar por score y devolver el mejor
        scored_tickets.sort(key=lambda x: x[1], reverse=True)
        return scored_tickets[0][0] if scored_tickets else None

    async def call_next_patient(
        self,
        db: Session,
        station_id: int,
        user_id: str
    ) -> CallNextPatientResponse:
        """
        Llama al siguiente paciente en la cola

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            user_id: ID del usuario que llama

        Returns:
            CallNextPatientResponse: Respuesta con información del paciente llamado
        """
        try:
            # Obtener siguiente ticket
            next_ticket = await self.get_next_in_queue(db, station_id)

            if not next_ticket:
                return CallNextPatientResponse(
                    success=False,
                    message="No hay pacientes en espera",
                    ticket=None,
                    patient=None
                )

            # Actualizar estado del ticket
            next_ticket.Status = TicketStatus.CALLED.value
            next_ticket.CalledAt = datetime.now()
            next_ticket.StationId = station_id

            # Actualizar estación
            station = station_crud.get(db, station_id)
            if station:
                station.CurrentTicketId = next_ticket.Id
                station.Status = "Busy"

            db.commit()

            # Notificar via WebSocket
            await self._notify_ticket_called(next_ticket, station)

            # Preparar respuesta
            patient = patient_crud.get(db, next_ticket.PatientId)

            return CallNextPatientResponse(
                success=True,
                message=f"Llamando a {patient.FullName}",
                ticket=TicketResponse.from_orm(next_ticket),
                patient=patient
            )

        except Exception as e:
            logger.error(f"Error llamando siguiente paciente: {e}")
            db.rollback()
            return CallNextPatientResponse(
                success=False,
                message=f"Error: {str(e)}",
                ticket=None,
                patient=None
            )

    async def transfer_ticket(
        self,
        db: Session,
        ticket_id: str,
        new_station_id: int,
        reason: Optional[str] = None
    ) -> bool:
        """
        Transfiere un ticket a otra estación

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket
            new_station_id: ID de la nueva estación
            reason: Razón de la transferencia

        Returns:
            bool: True si la transferencia fue exitosa
        """
        try:
            ticket = ticket_crud.get(db, ticket_id)
            if not ticket:
                return False

            old_station_id = ticket.StationId

            # Actualizar ticket
            ticket.StationId = new_station_id
            if reason:
                ticket.Notes = f"{ticket.Notes or ''}\nTransferido: {reason}"

            # Si estaba siendo atendido, volver a estado llamado
            if ticket.Status == TicketStatus.IN_PROGRESS.value:
                ticket.Status = TicketStatus.CALLED.value

            db.commit()

            # Notificar cambio
            await self._notify_ticket_transferred(ticket, old_station_id, new_station_id)

            return True

        except Exception as e:
            logger.error(f"Error transfiriendo ticket: {e}")
            db.rollback()
            return False

    async def mark_ticket_completed(
        self,
        db: Session,
        ticket_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Marca un ticket como completado

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket
            notes: Notas adicionales

        Returns:
            bool: True si se completó exitosamente
        """
        try:
            ticket = ticket_crud.get(db, ticket_id)
            if not ticket:
                return False

            # Actualizar ticket
            ticket.Status = TicketStatus.COMPLETED.value
            ticket.CompletedAt = datetime.now()

            if notes:
                ticket.Notes = f"{ticket.Notes or ''}\n{notes}"

            # Liberar estación si estaba asignada
            if ticket.StationId:
                station = station_crud.get(db, ticket.StationId)
                if station and station.CurrentTicketId == ticket.Id:
                    station.CurrentTicketId = None
                    station.Status = "Available"

            db.commit()

            # Notificar
            await self._notify_ticket_completed(ticket)

            return True

        except Exception as e:
            logger.error(f"Error completando ticket: {e}")
            db.rollback()
            return False

    async def mark_ticket_no_show(
        self,
        db: Session,
        ticket_id: str
    ) -> bool:
        """
        Marca un ticket como no show (paciente no se presentó)

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket

        Returns:
            bool: True si se marcó exitosamente
        """
        try:
            ticket = ticket_crud.get(db, ticket_id)
            if not ticket:
                return False

            # Actualizar ticket
            ticket.Status = TicketStatus.NO_SHOW.value

            # Liberar estación si estaba asignada
            if ticket.StationId:
                station = station_crud.get(db, ticket.StationId)
                if station and station.CurrentTicketId == ticket.Id:
                    station.CurrentTicketId = None
                    station.Status = "Available"

            db.commit()

            # Notificar
            await self._notify_ticket_no_show(ticket)

            return True

        except Exception as e:
            logger.error(f"Error marcando no show: {e}")
            db.rollback()
            return False

    # ========================================
    # MÉTODOS DE ESTADÍSTICAS
    # ========================================

    def get_queue_stats(
        self,
        db: Session,
        service_type_id: Optional[int] = None
    ) -> TicketStats:
        """
        Obtiene estadísticas de la cola

        Args:
            db: Sesión de base de datos
            service_type_id: ID del servicio (opcional)

        Returns:
            TicketStats: Estadísticas de la cola
        """
        try:
            # Query base para tickets del día
            today_start = datetime.combine(date.today(), time.min)
            today_end = datetime.combine(date.today(), time.max)

            query = db.query(Ticket).filter(
                text("CreatedAt >= :start AND CreatedAt <= :end")
            ).params(start=today_start, end=today_end)

            if service_type_id:
                query = query.filter(Ticket.ServiceTypeId == service_type_id)

            tickets = query.all()

            # Calcular estadísticas
            stats = {
                "total_tickets": len(tickets),
                "waiting_tickets": sum(1 for t in tickets if t.Status == TicketStatus.WAITING.value),
                "called_tickets": sum(1 for t in tickets if t.Status == TicketStatus.CALLED.value),
                "in_progress_tickets": sum(1 for t in tickets if t.Status == TicketStatus.IN_PROGRESS.value),
                "completed_tickets": sum(1 for t in tickets if t.Status == TicketStatus.COMPLETED.value),
                "cancelled_tickets": sum(1 for t in tickets if t.Status == TicketStatus.CANCELLED.value),
                "no_show_tickets": sum(1 for t in tickets if t.Status == TicketStatus.NO_SHOW.value),
            }

            # Calcular tiempos promedio
            wait_times = []
            service_times = []

            for ticket in tickets:
                if ticket.AttendedAt and ticket.created_at:
                    wait_time = (ticket.AttendedAt - ticket.created_at).total_seconds() / 60
                    wait_times.append(wait_time)

                if ticket.CompletedAt and ticket.AttendedAt:
                    service_time = (ticket.CompletedAt - ticket.AttendedAt).total_seconds() / 60
                    service_times.append(service_time)

            stats["average_wait_time"] = sum(wait_times) / len(wait_times) if wait_times else 0
            stats["average_service_time"] = sum(service_times) / len(service_times) if service_times else 0

            return TicketStats(**stats)

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return TicketStats()

    def get_estimated_wait_time(
        self,
        db: Session,
        ticket_id: str
    ) -> int:
        """
        Calcula el tiempo estimado de espera para un ticket

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket

        Returns:
            int: Tiempo estimado en minutos
        """
        try:
            ticket = ticket_crud.get(db, ticket_id)
            if not ticket or ticket.Status != TicketStatus.WAITING.value:
                return 0

            # Obtener tickets por delante
            today_start = datetime.combine(date.today(), time.min)
            today_end = datetime.combine(date.today(), time.max)

            tickets_ahead = db.query(Ticket).filter(
                Ticket.ServiceTypeId == ticket.ServiceTypeId,
                Ticket.Status.in_([TicketStatus.WAITING.value, TicketStatus.CALLED.value]),
                Ticket.Position < ticket.Position,
                text("CreatedAt >= :start AND CreatedAt <= :end")
            ).params(start=today_start, end=today_end).count()

            # Obtener tiempo promedio del servicio
            service_type = service_type_crud.get(db, ticket.ServiceTypeId)
            avg_time = service_type.AverageTimeMinutes if service_type else 10

            # Calcular estimado
            estimated_time = tickets_ahead * avg_time

            # Ajustar por estaciones activas
            active_stations = db.query(Station).filter(
                Station.ServiceTypeId == ticket.ServiceTypeId,
                Station.IsActive == True,
                Station.Status.in_(["Available", "Busy"])
            ).count()

            if active_stations > 1:
                estimated_time = estimated_time / active_stations

            return int(estimated_time)

        except Exception as e:
            logger.error(f"Error calculando tiempo estimado: {e}")
            return 0

    def get_queue_position(
        self,
        db: Session,
        ticket_id: str
    ) -> QueuePosition:
        """
        Obtiene la posición actual de un ticket en la cola

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket

        Returns:
            QueuePosition: Información de posición
        """
        try:
            ticket = ticket_crud.get(db, ticket_id)
            if not ticket:
                raise ValueError("Ticket no encontrado")

            # Contar tickets por delante
            today_start = datetime.combine(date.today(), time.min)
            today_end = datetime.combine(date.today(), time.max)

            ahead_count = db.query(Ticket).filter(
                Ticket.ServiceTypeId == ticket.ServiceTypeId,
                Ticket.Status == TicketStatus.WAITING.value,
                Ticket.Position < ticket.Position,
                text("CreatedAt >= :start AND CreatedAt <= :end")
            ).params(start=today_start, end=today_end).count()

            # Obtener tiempo estimado
            estimated_wait = self.get_estimated_wait_time(db, ticket_id)

            # Obtener nombre del servicio
            service = service_type_crud.get(db, ticket.ServiceTypeId)

            return QueuePosition(
                ticket_id=str(ticket.Id),
                ticket_number=ticket.TicketNumber,
                current_position=ticket.Position,
                ahead_count=ahead_count,
                estimated_wait_time=estimated_wait,
                service_name=service.Name if service else "Servicio"
            )

        except Exception as e:
            logger.error(f"Error obteniendo posición en cola: {e}")
            raise


    def get_daily_summary(
            self,
            db: Session,
            target_date: Optional[date] = None
    ) -> DailyTicketSummary:
        """
        Obtiene resumen diario de tickets

        Args:
            db: Sesión de base de datos
            target_date: Fecha objetivo (por defecto hoy)

        Returns:
            DailyTicketSummary: Resumen del día
        """
        try:
            if not target_date:
                target_date = date.today()

            # Query para tickets del día
            date_start = datetime.combine(target_date, time.min)
            date_end = datetime.combine(target_date, time.max)

            tickets = db.query(Ticket).filter(
                text("CreatedAt >= :start AND CreatedAt <= :end")
            ).params(start=date_start, end=date_end).all()

            # Agrupar por estado
            tickets_by_status = {}
            tickets_by_service = {}
            wait_times = []
            service_times = []
            hour_counts = {}

            for ticket in tickets:
                # Por estado
                status = ticket.Status
                tickets_by_status[status] = tickets_by_status.get(status, 0) + 1

                # Por servicio
                if ticket.service_type:
                    service_name = ticket.service_type.Name
                    tickets_by_service[service_name] = tickets_by_service.get(service_name, 0) + 1

                # Tiempos
                if hasattr(ticket, 'created_at') and ticket.created_at and ticket.AttendedAt:
                    wait_time = (ticket.AttendedAt - ticket.created_at).total_seconds() / 60
                    wait_times.append(wait_time)

                if ticket.AttendedAt and ticket.CompletedAt:
                    service_time = (ticket.CompletedAt - ticket.AttendedAt).total_seconds() / 60
                    service_times.append(service_time)

                # Por hora
                hour = 0
                if hasattr(ticket, 'created_at') and ticket.created_at:
                    hour = ticket.created_at.hour
                elif hasattr(ticket, 'CreatedAt') and ticket.CreatedAt:
                    hour = ticket.CreatedAt.hour

                hour_counts[hour] = hour_counts.get(hour, 0) + 1

            # Encontrar hora pico
            peak_hour_num = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 0
            peak_hour_str = f"{peak_hour_num:02d}:00-{(peak_hour_num + 1):02d}:00" if hour_counts else "N/A"

            # Calcular promedios
            avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0.0
            avg_service_time = sum(service_times) / len(service_times) if service_times else 0.0

            return DailyTicketSummary(
                summary_date=target_date,  # Usar summary_date, no date
                total_tickets=len(tickets),
                tickets_by_status=tickets_by_status,
                tickets_by_service=tickets_by_service,
                average_wait_time=avg_wait_time,
                average_service_time=avg_service_time,
                peak_hour=peak_hour_str  # Debe ser string
            )

        except Exception as e:
            logger.error(f"Error obteniendo resumen diario: {e}")
            raise


    def get_patient_queue_stats(
        self,
        db: Session,
        patient_id: str
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas de cola para un paciente específico

        Args:
            db: Sesión de base de datos
            patient_id: ID del paciente

        Returns:
            Dict: Estadísticas del paciente
        """
        try:
            # Obtener ticket activo del paciente
            today_start = datetime.combine(date.today(), time.min)
            today_end = datetime.combine(date.today(), time.max)

            active_ticket = db.query(Ticket).filter(
                Ticket.PatientId == patient_id,
                Ticket.Status.in_([
                    TicketStatus.WAITING.value,
                    TicketStatus.CALLED.value,
                    TicketStatus.IN_PROGRESS.value
                ]),
                text("CreatedAt >= :start AND CreatedAt <= :end")
            ).params(start=today_start, end=today_end).first()

            if not active_ticket:
                return {
                    "has_active_ticket": False,
                    "message": "No tiene turno activo"
                }

            # Obtener posición en cola
            position = self.get_queue_position(db, str(active_ticket.Id))

            # Obtener información de la estación si está asignado
            station_info = None
            if active_ticket.StationId:
                station = station_crud.get(db, active_ticket.StationId)
                if station:
                    station_info = {
                        "id": station.Id,
                        "name": station.Name,
                        "code": station.Code,
                        "location": station.Location
                    }

            return {
                "has_active_ticket": True,
                "ticket": {
                    "id": str(active_ticket.Id),
                    "number": active_ticket.TicketNumber,
                    "status": active_ticket.Status,
                    "created_at": active_ticket.created_at.isoformat(),
                    "called_at": active_ticket.CalledAt.isoformat() if active_ticket.CalledAt else None,
                    "service_type_id": active_ticket.ServiceTypeId,
                    "service_code": active_ticket.service_type.Code if active_ticket.service_type else None
                },
                "position": {
                    "current": position.current_position,
                    "ahead_count": position.ahead_count,
                    "estimated_wait_time": position.estimated_wait_time
                },
                "station": station_info
            }

        except Exception as e:
            logger.error(f"Error obteniendo stats de paciente: {e}")
            return {
                "has_active_ticket": False,
                "error": str(e)
            }

    # ========================================
    # MÉTODOS DE OPTIMIZACIÓN
    # ========================================

    async def rebalance_queues(
        self,
        db: Session
    ) -> Dict[str, Any]:
        """
        Rebalancea las colas entre estaciones disponibles

        Args:
            db: Sesión de base de datos

        Returns:
            Dict: Resultado del rebalanceo
        """
        try:
            if not self.auto_rebalance_enabled:
                return {"success": False, "message": "Rebalanceo automático deshabilitado"}

            # Obtener estaciones activas
            active_stations = db.query(Station).filter(
                Station.IsActive == True,
                Station.Status.in_(["Available", "Busy"])
            ).all()

            # Agrupar por servicio
            stations_by_service = {}
            for station in active_stations:
                service_id = station.ServiceTypeId
                if service_id not in stations_by_service:
                    stations_by_service[service_id] = []
                stations_by_service[service_id].append(station)

            transfers = []

            # Para cada servicio con múltiples estaciones
            for service_id, stations in stations_by_service.items():
                if len(stations) < 2:
                    continue

                # Obtener tickets en espera
                today_start = datetime.combine(date.today(), time.min)
                today_end = datetime.combine(date.today(), time.max)

                waiting_tickets = db.query(Ticket).filter(
                    Ticket.ServiceTypeId == service_id,
                    Ticket.Status == TicketStatus.WAITING.value,
                    text("CreatedAt >= :start AND CreatedAt <= :end")
                ).params(start=today_start, end=today_end).order_by(Ticket.Position.asc()).all()

                if not waiting_tickets:
                    continue

                # Distribuir equitativamente
                tickets_per_station = len(waiting_tickets) // len(stations)
                remainder = len(waiting_tickets) % len(stations)

                ticket_index = 0
                for i, station in enumerate(stations):
                    count = tickets_per_station + (1 if i < remainder else 0)

                    for j in range(count):
                        if ticket_index < len(waiting_tickets):
                            ticket = waiting_tickets[ticket_index]
                            if ticket.StationId != station.Id:
                                ticket.StationId = station.Id
                                transfers.append({
                                    "ticket": ticket.TicketNumber,
                                    "to_station": station.Name
                                })
                            ticket_index += 1

            if transfers:
                db.commit()

            return {
                "success": True,
                "transfers_count": len(transfers),
                "transfers": transfers[:10]  # Mostrar solo primeros 10
            }

        except Exception as e:
            logger.error(f"Error rebalanceando colas: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def optimize_service_times(
        self,
        db: Session
    ) -> Dict[str, Any]:
        """
        Optimiza los tiempos de servicio basado en datos históricos

        Args:
            db: Sesión de base de datos

        Returns:
            Dict: Resultado de la optimización
        """
        try:
            # Obtener tickets completados de los últimos 30 días
            thirty_days_ago = datetime.now() - timedelta(days=30)

            completed_tickets = db.query(
                Ticket.ServiceTypeId,
                func.avg(
                    func.datediff(
                        'minute',
                        Ticket.AttendedAt,
                        Ticket.CompletedAt
                    )
                ).label('avg_time')
            ).filter(
                Ticket.Status == TicketStatus.COMPLETED.value,
                Ticket.created_at >= thirty_days_ago,
                Ticket.AttendedAt.isnot(None),
                Ticket.CompletedAt.isnot(None)
            ).group_by(Ticket.ServiceTypeId).all()

            updates = []

            for service_id, avg_time in completed_tickets:
                if avg_time:
                    service = service_type_crud.get(db, service_id)
                    if service:
                        old_time = service.AverageTimeMinutes
                        new_time = int(avg_time)

                        # Solo actualizar si hay diferencia significativa (>20%)
                        if abs(old_time - new_time) / old_time > 0.2:
                            service.AverageTimeMinutes = new_time
                            updates.append({
                                "service": service.Name,
                                "old_time": old_time,
                                "new_time": new_time
                            })

            if updates:
                db.commit()

            return {
                "success": True,
                "updates_count": len(updates),
                "updates": updates
            }

        except Exception as e:
            logger.error(f"Error optimizando tiempos: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    # ========================================
    # MÉTODOS DE NOTIFICACIÓN
    # ========================================

    async def _notify_ticket_called(self, ticket: Ticket, station: Station):
        """Notifica cuando un ticket es llamado"""
        try:
            message = {
                "type": "ticket_called",
                "ticket_id": str(ticket.Id),
                "ticket_number": ticket.TicketNumber,
                "station_name": station.Name if station else "Ventanilla",
                "station_code": station.Code if station else "",
                "timestamp": datetime.now().isoformat()
            }

            # Enviar via WebSocket
            if websocket_manager:
                await websocket_manager.broadcast(json.dumps(message))

            # Log para debug
            logger.info(f"Notificación enviada: Ticket {ticket.TicketNumber} llamado")

        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")

    async def _notify_ticket_transferred(
        self,
        ticket: Ticket,
        old_station_id: int,
        new_station_id: int
    ):
        """Notifica cuando un ticket es transferido"""
        try:
            message = {
                "type": "ticket_transferred",
                "ticket_id": str(ticket.Id),
                "ticket_number": ticket.TicketNumber,
                "old_station_id": old_station_id,
                "new_station_id": new_station_id,
                "timestamp": datetime.now().isoformat()
            }

            if websocket_manager:
                await websocket_manager.broadcast(json.dumps(message))

        except Exception as e:
            logger.error(f"Error enviando notificación de transferencia: {e}")

    async def _notify_ticket_completed(self, ticket: Ticket):
        """Notifica cuando un ticket es completado"""
        try:
            message = {
                "type": "ticket_completed",
                "ticket_id": str(ticket.Id),
                "ticket_number": ticket.TicketNumber,
                "timestamp": datetime.now().isoformat()
            }

            if websocket_manager:
                await websocket_manager.broadcast(json.dumps(message))

        except Exception as e:
            logger.error(f"Error enviando notificación de completado: {e}")

    async def _notify_ticket_no_show(self, ticket: Ticket):
        """Notifica cuando un paciente no se presenta"""
        try:
            message = {
                "type": "ticket_no_show",
                "ticket_id": str(ticket.Id),
                "ticket_number": ticket.TicketNumber,
                "timestamp": datetime.now().isoformat()
            }

            if websocket_manager:
                await websocket_manager.broadcast(json.dumps(message))

        except Exception as e:
            logger.error(f"Error enviando notificación de no show: {e}")

    # ========================================
    # MÉTODOS AUXILIARES
    # ========================================

    def get_estimated_next_calls(
        self,
        db: Session,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las próximas llamadas estimadas

        Args:
            db: Sesión de base de datos
            limit: Límite de llamadas a estimar

        Returns:
            List[Dict]: Lista de próximas llamadas estimadas
        """
        try:
            # Obtener tickets en espera ordenados por posición
            today_start = datetime.combine(date.today(), time.min)
            today_end = datetime.combine(date.today(), time.max)

            waiting_tickets = db.query(Ticket).filter(
                Ticket.Status == TicketStatus.WAITING.value,
                text("CreatedAt >= :start AND CreatedAt <= :end")
            ).params(start=today_start, end=today_end).order_by(
                Ticket.Position.asc()
            ).limit(limit).all()

            estimated_calls = []
            accumulated_time = 0

            for ticket in waiting_tickets:
                # Obtener tiempo promedio del servicio
                service = service_type_crud.get(db, ticket.ServiceTypeId)
                avg_time = service.AverageTimeMinutes if service else 10

                accumulated_time += avg_time

                estimated_calls.append({
                    "ticket_number": ticket.TicketNumber,
                    "patient_id": str(ticket.PatientId),
                    "service_name": service.Name if service else "Servicio",
                    "estimated_time": accumulated_time,
                    "estimated_call": (
                        datetime.now() + timedelta(minutes=accumulated_time)
                    ).strftime("%H:%M")
                })

            return estimated_calls

        except Exception as e:
            logger.error(f"Error obteniendo próximas llamadas: {e}")
            return []

    def generate_qr_code(self, ticket_data: Dict[str, Any]) -> str:
        """
        Genera código QR para un ticket

        Args:
            ticket_data: Datos del ticket

        Returns:
            str: Código QR en base64
        """
        try:
            # Crear QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )

            # Agregar datos
            qr_content = json.dumps({
                "ticket_id": ticket_data.get("id"),
                "ticket_number": ticket_data.get("number"),
                "service": ticket_data.get("service"),
                "date": ticket_data.get("date")
            })

            qr.add_data(qr_content)
            qr.make(fit=True)

            # Crear imagen
            img = qr.make_image(fill_color="black", back_color="white")

            # Convertir a base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_str}"

        except Exception as e:
            logger.error(f"Error generando QR: {e}")
            return ""


# ========================================
# INSTANCIA GLOBAL DEL SERVICIO
# ========================================

queue_service = QueueService()