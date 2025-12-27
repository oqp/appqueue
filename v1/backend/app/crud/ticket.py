"""
Operaciones CRUD específicas para el modelo Ticket
100% compatible con SQLAlchemy Ticket model y schemas Pydantic
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.sql import literal_column
from datetime import datetime, timedelta, date
import logging

from app.crud import service_type_crud
from app.crud.base import CRUDBase
from app.models.ticket import Ticket
from app.models.patient import Patient
from app.models.service_type import ServiceType
from app.models.station import Station
from app.schemas.ticket import TicketCreate, TicketUpdate

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)


# ========================================
# CLASE CRUD TICKET
# ========================================

class CRUDTicket(CRUDBase[Ticket, TicketCreate, TicketUpdate]):
    """
    Operaciones CRUD específicas para tickets
    Compatible con modelo SQLAlchemy y schemas Pydantic
    """

    def create_ticket(
            self,
            db: Session,
            *,
            patient_id: str,
            service_type_id: int,
            station_id: Optional[int] = None,
            notes: Optional[str] = None
    ) -> Ticket:
        """
        Crea un nuevo ticket con número automático y posición en cola

        Args:
            db: Sesión de base de datos
            patient_id: ID del paciente
            service_type_id: ID del tipo de servicio
            station_id: ID de la estación (opcional)
            notes: Notas adicionales

        Returns:
            Ticket: Ticket creado
        """
        try:
            # Obtener tipo de servicio para el prefijo
            service_type = db.query(ServiceType).filter(ServiceType.Id == service_type_id).first()
            if not service_type:
                raise ValueError(f"Tipo de servicio no encontrado: {service_type_id}")

            # Generar número de ticket
            ticket_number = self._generate_ticket_number(db, service_type)

            # Calcular posición en la cola
            position = self._get_next_position(db, service_type_id)

            # Calcular tiempo estimado de espera
            estimated_wait_time = self._calculate_estimated_wait_time(db, service_type_id, position)

            # Crear ticket
            ticket_data = {
                "TicketNumber": ticket_number,
                "PatientId": patient_id,
                "ServiceTypeId": service_type_id,
                "StationId": station_id,
                "Status": "Waiting",
                "Position": position,
                "EstimatedWaitTime": estimated_wait_time,
                "Notes": notes
            }

            ticket = Ticket(**ticket_data)
            db.add(ticket)
            db.commit()
            db.refresh(ticket)

            # Generar código QR
            qr_data = ticket.generate_qr_code()
            ticket.QrCode = qr_data
            db.commit()
            db.refresh(ticket)

            logger.info(f"Ticket creado: {ticket_number} para paciente {patient_id}")
            return ticket

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando ticket: {e}")
            raise

    def _generate_ticket_number(self, db: Session, service_type: ServiceType) -> str:
        """
        Genera el número de ticket para el día actual

        Args:
            db: Sesión de base de datos
            service_type: Tipo de servicio

        Returns:
            str: Número de ticket generado
        """
        try:
            today = date.today()

            # CORREGIDO: Usar CreatedAt en lugar de CreatedAt
            # Opción 1: Usar func.date para SQL Server
            daily_count = db.query(Ticket).filter(
                and_(
                    Ticket.ServiceTypeId == service_type.Id,
                    func.convert(literal_column('DATE'), Ticket.CreatedAt) == today  # CAMBIO: CreatedAt
                )
            ).count()

            # Siguiente número
            next_number = daily_count + 1

            # Formato del número: Prefijo + número del día (ej: A001, A002, etc.)
            ticket_number = f"{service_type.TicketPrefix}{next_number:03d}"

            logger.debug(f"Generado número de ticket: {ticket_number}")
            return ticket_number

        except Exception as e:
            logger.error(f"Error generando número de ticket: {e}")
            # Fallback con timestamp para garantizar unicidad
            import time
            fallback_number = f"{service_type.TicketPrefix}{int(time.time()) % 10000:04d}"
            logger.warning(f"Usando número de ticket fallback: {fallback_number}")
            return fallback_number




    def _get_next_position(self, db: Session, service_type_id: int) -> int:
        """
        Calcula la siguiente posición en la cola

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio

        Returns:
            int: Siguiente posición en la cola
        """
        try:
            # Contar tickets activos en la cola para este servicio
            active_tickets = db.query(Ticket).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.Status.in_(['Waiting', 'Called', 'InProgress'])
                )
            ).count()

            return active_tickets + 1

        except Exception as e:
            logger.error(f"Error calculando posición en cola: {e}")
            return 1

    def _calculate_estimated_wait_time(
            self,
            db: Session,
            service_type_id: int,
            position: int
    ) -> int:
        """
        Calcula el tiempo estimado de espera

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            position: Posición en la cola

        Returns:
            int: Tiempo estimado en minutos
        """
        try:
            # Obtener tipo de servicio
            service_type = db.query(ServiceType).filter(ServiceType.Id == service_type_id).first()
            if not service_type:
                return 10  # Fallback

            # Contar estaciones activas para este servicio
            active_stations = db.query(Station).filter(
                and_(
                    Station.ServiceTypeId == service_type_id,
                    Station.IsActive == True,
                    Station.Status == 'Available'
                )
            ).count()

            if active_stations == 0:
                active_stations = 1  # Mínimo 1 para evitar división por cero

            # Calcular tiempo estimado
            queue_length = max(0, position - 1)  # Tickets antes que este
            estimated_time = (queue_length * service_type.AverageTimeMinutes) // active_stations

            return max(1, estimated_time)  # Mínimo 1 minuto

        except Exception as e:
            logger.error(f"Error calculando tiempo estimado: {e}")
            return 10  # Fallback

    def get_by_ticket_number(self, db: Session, *, ticket_number: str, active_only: bool = True) -> Optional[Ticket]:
        """
        Busca un ticket por su número

        Args:
            db: Sesión de base de datos
            ticket_number: Número del ticket
            active_only: Si True, busca primero tickets en estado activo (Waiting/Called)

        Returns:
            Ticket: Ticket encontrado o None
        """
        try:
            query = db.query(Ticket).filter(
                Ticket.TicketNumber == ticket_number.upper().strip()
            )

            if active_only:
                # Primero buscar ticket en estado activo (Waiting o Called)
                active_ticket = query.filter(
                    Ticket.Status.in_(['Waiting', 'Called', 'InProgress'])
                ).order_by(Ticket.CreatedAt.desc()).first()

                if active_ticket:
                    return active_ticket

            # Si no hay activo o no se requiere, retornar el más reciente
            return query.order_by(Ticket.CreatedAt.desc()).first()
        except Exception as e:
            logger.error(f"Error buscando ticket por número {ticket_number}: {e}")
            return None

    def get_next_in_queue(
            self,
            db: Session,
            *,
            service_type_id: int,
            station_id: Optional[int] = None
    ) -> Optional[Ticket]:
        """
        Obtiene el próximo ticket en la cola para atender

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            station_id: ID de la estación (opcional)

        Returns:
            Ticket: Próximo ticket o None
        """
        try:
            query = db.query(Ticket).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.Status == 'Waiting'
                )
            )

            # Si se especifica estación, considerar solo tickets no asignados o de esa estación
            if station_id:
                query = query.filter(
                    or_(
                        Ticket.StationId.is_(None),
                        Ticket.StationId == station_id
                    )
                )

            # Ordenar por prioridad y posición
            return query.order_by(
                asc(Ticket.Position),
                asc(Ticket.CreatedAt )
            ).first()

        except Exception as e:
            logger.error(f"Error obteniendo próximo ticket: {e}")
            return None

    def get_queue_by_service(
            self,
            db: Session,
            *,
            service_type_id: int,
            limit: int = 50
    ) -> List[Ticket]:
        """
        Obtiene la cola de tickets para un servicio específico

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            limit: Límite de resultados

        Returns:
            List[Ticket]: Lista de tickets en cola
        """
        try:
            return db.query(Ticket).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.Status.in_(['Waiting', 'Called', 'InProgress'])
                )
            ).order_by(
                asc(Ticket.Position),
                asc(Ticket.CreatedAt )
            ).limit(limit).all()

        except Exception as e:
            logger.error(f"Error obteniendo cola de servicio {service_type_id}: {e}")
            return []

    def call_ticket(
            self,
            db: Session,
            *,
            ticket_id: str,
            station_id: int,
            user_id: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Llama un ticket para atención

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket
            station_id: ID de la estación que llama
            user_id: ID del usuario que hace la llamada

        Returns:
            Ticket: Ticket llamado o None
        """
        try:
            ticket = self.get(db, id=ticket_id)
            if not ticket:
                return None

            # Usar método del modelo SQLAlchemy
            if ticket.call_ticket(station_id):
                db.add(ticket)
                db.commit()
                db.refresh(ticket)

                logger.info(f"Ticket llamado: {ticket.TicketNumber} en estación {station_id}")

                # TODO: Agregar log de actividad cuando esté implementado
                # ActivityLog.log_action("ticket_called", user_id, ticket_id, station_id)

                return ticket

            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error llamando ticket {ticket_id}: {e}")
            return None

    def start_attention(
            self,
            db: Session,
            *,
            ticket_id: str,
            user_id: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Inicia la atención de un ticket

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket
            user_id: ID del usuario que inicia la atención

        Returns:
            Ticket: Ticket en atención o None
        """
        try:
            ticket = self.get(db, id=ticket_id)
            if not ticket:
                return None

            # Usar método del modelo SQLAlchemy
            if ticket.start_attention():
                db.add(ticket)
                db.commit()
                db.refresh(ticket)

                logger.info(f"Atención iniciada: {ticket.TicketNumber}")
                return ticket

            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error iniciando atención de ticket {ticket_id}: {e}")
            return None

    def complete_ticket(
            self,
            db: Session,
            *,
            ticket_id: str,
            notes: Optional[str] = None,
            user_id: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Completa la atención de un ticket

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket
            notes: Notas de finalización
            user_id: ID del usuario que completa

        Returns:
            Ticket: Ticket completado o None
        """
        try:
            ticket = self.get(db, id=ticket_id)
            if not ticket:
                return None

            # Usar método del modelo SQLAlchemy
            if ticket.complete_ticket(notes):
                db.add(ticket)
                db.commit()
                db.refresh(ticket)

                logger.info(f"Ticket completado: {ticket.TicketNumber}")
                return ticket

            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error completando ticket {ticket_id}: {e}")
            return None

    def cancel_ticket(
            self,
            db: Session,
            *,
            ticket_id: str,
            reason: str = "Cancelled",
            user_id: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Cancela un ticket

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket
            reason: Razón de cancelación
            user_id: ID del usuario que cancela

        Returns:
            Ticket: Ticket cancelado o None
        """
        try:
            ticket = self.get(db, id=ticket_id)
            if not ticket:
                return None

            # Usar método del modelo SQLAlchemy
            if ticket.cancel_ticket(reason):
                db.add(ticket)
                db.commit()
                db.refresh(ticket)

                logger.info(f"Ticket cancelado: {ticket.TicketNumber} - {reason}")
                return ticket

            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelando ticket {ticket_id}: {e}")
            return None

    def transfer_ticket(
            self,
            db: Session,
            ticket_id: str,
            new_station_id: int,
            reason: Optional[str] = None,  # AÑADIDO: parámetro reason
            user_id: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Transfiere un ticket a otra estación

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket
            new_station_id: ID de la nueva estación
            reason: Razón de la transferencia (opcional)
            user_id: ID del usuario que transfiere (opcional)

        Returns:
            Ticket: Ticket transferido o None
        """
        try:
            ticket = self.get(db, id=ticket_id)
            if not ticket:
                return None

            # Guardar la estación anterior para el registro
            old_station_id = ticket.StationId

            # Usar método del modelo SQLAlchemy
            if ticket.transfer_to_station(new_station_id):

                # Añadir la razón a las notas si se proporciona
                if reason:
                    transfer_note = f"Transferido desde estación {old_station_id} a {new_station_id}. Razón: {reason}"
                    if user_id:
                        transfer_note += f" (Por usuario: {user_id})"

                    if ticket.Notes:
                        ticket.Notes = f"{ticket.Notes} | {transfer_note}"
                    else:
                        ticket.Notes = transfer_note

                db.add(ticket)
                db.commit()
                db.refresh(ticket)

                logger.info(
                    f"Ticket transferido: {ticket.TicketNumber} de estación {old_station_id} a {new_station_id}")
                if reason:
                    logger.info(f"Razón de transferencia: {reason}")

                return ticket

            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error transfiriendo ticket {ticket_id}: {e}")
            return None


    def get_tickets_by_patient(
            self,
            db: Session,
            *,
            patient_id: str,
            limit: int = 20
    ) -> List[Ticket]:
        """
        Obtiene los tickets de un paciente específico

        Args:
            db: Sesión de base de datos
            patient_id: ID del paciente
            limit: Límite de resultados

        Returns:
            List[Ticket]: Lista de tickets del paciente
        """
        try:
            return db.query(Ticket).filter(
                Ticket.PatientId == patient_id
            ).order_by(
                desc(Ticket.CreatedAt )
            ).limit(limit).all()

        except Exception as e:
            logger.error(f"Error obteniendo tickets del paciente {patient_id}: {e}")
            return []

    def get_daily_tickets(
            self,
            db: Session,
            *,
            target_date: Optional[date] = None
    ) -> List[Ticket]:
        """
        Obtiene todos los tickets de un día específico

        Args:
            db: Sesión de base de datos
            target_date: Fecha objetivo (por defecto hoy)

        Returns:
            List[Ticket]: Lista de tickets del día
        """
        try:
            if target_date is None:
                target_date = date.today()

            return db.query(Ticket).filter(
                func.convert(literal_column('DATE'), Ticket.CreatedAt) == target_date
            ).order_by(Ticket.CreatedAt ).all()

        except Exception as e:
            logger.error(f"Error obteniendo tickets del día {target_date}: {e}")
            return []

    def get_active_tickets(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100,
            today_only: bool = True
    ) -> List[Ticket]:
        """
        Obtiene tickets activos (no completados ni cancelados)

        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar
            limit: Límite de registros a retornar
            today_only: Si True, solo retorna tickets del día actual (por defecto True)

        Returns:
            List[Ticket]: Lista de tickets activos
        """
        try:
            from datetime import datetime

            active_statuses = ['Waiting', 'Called', 'InProgress']

            query = db.query(Ticket).filter(
                Ticket.Status.in_(active_statuses)
            )

            # Filtrar por día actual si se especifica
            if today_only:
                today = date.today()
                start_of_day = datetime.combine(today, datetime.min.time())
                end_of_day = datetime.combine(today, datetime.max.time())
                query = query.filter(
                    Ticket.CreatedAt >= start_of_day,
                    Ticket.CreatedAt <= end_of_day
                )

            # Ordenar por prioridad y tiempo de creación
            query = query.join(ServiceType).order_by(
                ServiceType.Priority.asc(),
                Ticket.CreatedAt.asc()
            )

            # Aplicar paginación si se especifica
            if skip > 0:
                query = query.offset(skip)
            if limit > 0:
                query = query.limit(limit)

            tickets = query.all()

            logger.debug(f"Obtenidos {len(tickets)} tickets activos (today_only={today_only})")
            return tickets

        except Exception as e:
            logger.error(f"Error obteniendo tickets activos: {e}")
            return []

    def get_queue_statistics(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de la cola - SOLO DEL DÍA ACTUAL

        Returns:
            Dict con estadísticas completas del día
        """
        try:
            from app.models.service_type import ServiceType
            from app.models.station import Station
            from datetime import datetime, timedelta

            # Definir inicio y fin del día actual
            today = date.today()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())

            # Contar tickets por estado - SOLO DEL DÍA ACTUAL
            waiting_count = db.query(func.count(Ticket.Id)).filter(
                Ticket.Status == 'Waiting',
                Ticket.CreatedAt >= start_of_day,
                Ticket.CreatedAt <= end_of_day
            ).scalar() or 0

            called_count = db.query(func.count(Ticket.Id)).filter(
                Ticket.Status == 'Called',
                Ticket.CreatedAt >= start_of_day,
                Ticket.CreatedAt <= end_of_day
            ).scalar() or 0

            in_progress_count = db.query(func.count(Ticket.Id)).filter(
                Ticket.Status == 'InProgress',
                Ticket.CreatedAt >= start_of_day,
                Ticket.CreatedAt <= end_of_day
            ).scalar() or 0

            # Total de tickets del día
            total_today = db.query(func.count(Ticket.Id)).filter(
                Ticket.CreatedAt >= start_of_day,
                Ticket.CreatedAt <= end_of_day
            ).scalar() or 0

            completed_today = db.query(func.count(Ticket.Id)).filter(
                Ticket.Status == 'Completed',
                Ticket.CompletedAt >= start_of_day,
                Ticket.CompletedAt <= end_of_day
            ).scalar() or 0

            cancelled_today = db.query(func.count(Ticket.Id)).filter(
                Ticket.Status == 'Cancelled',
                Ticket.UpdatedAt >= start_of_day,
                Ticket.UpdatedAt <= end_of_day
            ).scalar() or 0

            no_show_today = db.query(func.count(Ticket.Id)).filter(
                Ticket.Status == 'NoShow',
                Ticket.UpdatedAt >= start_of_day,
                Ticket.UpdatedAt <= end_of_day
            ).scalar() or 0

            # Calcular tiempo promedio de espera - SOLO TICKETS CREADOS Y COMPLETADOS HOY
            avg_wait = db.query(func.avg(Ticket.ActualWaitTime)).filter(
                Ticket.Status == 'Completed',
                Ticket.CreatedAt >= start_of_day,
                Ticket.CreatedAt <= end_of_day,
                Ticket.CompletedAt >= start_of_day,
                Ticket.CompletedAt <= end_of_day,
                Ticket.ActualWaitTime.isnot(None)
            ).scalar()

            # Calcular tiempo promedio de servicio - SOLO TICKETS CREADOS Y COMPLETADOS HOY
            avg_service = db.query(func.avg(Ticket.ServiceTime)).filter(
                Ticket.Status == 'Completed',
                Ticket.CreatedAt >= start_of_day,
                Ticket.CreatedAt <= end_of_day,
                Ticket.CompletedAt >= start_of_day,
                Ticket.CompletedAt <= end_of_day,
                Ticket.ServiceTime.isnot(None)
            ).scalar()

            # Estadísticas por servicio - SOLO DEL DÍA ACTUAL
            service_stats = db.query(
                ServiceType.Id,
                ServiceType.Name,
                ServiceType.Code,
                ServiceType.Color,
                ServiceType.Priority,
                func.count(Ticket.Id).label('count')
            ).join(
                Ticket, Ticket.ServiceTypeId == ServiceType.Id
            ).filter(
                Ticket.Status == 'Waiting',
                Ticket.CreatedAt >= start_of_day,
                Ticket.CreatedAt <= end_of_day
            ).group_by(
                ServiceType.Id,
                ServiceType.Name,
                ServiceType.Code,
                ServiceType.Color,
                ServiceType.Priority
            ).all()

            # Crear diccionario de servicios y lista detallada
            by_service = {}
            services_breakdown = []

            for s in service_stats:
                by_service[s.Name] = s.count

                # Obtener estadísticas adicionales para cada servicio - SOLO HOY
                in_progress_service = db.query(func.count(Ticket.Id)).filter(
                    Ticket.ServiceTypeId == s.Id,
                    Ticket.Status.in_(['Called', 'InProgress']),
                    Ticket.CreatedAt >= start_of_day,
                    Ticket.CreatedAt <= end_of_day
                ).scalar() or 0

                # Calcular tiempo promedio para este servicio - SOLO HOY
                avg_service_wait = db.query(func.avg(Ticket.ActualWaitTime)).filter(
                    Ticket.ServiceTypeId == s.Id,
                    Ticket.Status == 'Completed',
                    Ticket.CreatedAt >= start_of_day,
                    Ticket.CreatedAt <= end_of_day,
                    Ticket.CompletedAt >= start_of_day,
                    Ticket.CompletedAt <= end_of_day,
                    Ticket.ActualWaitTime.isnot(None)
                ).scalar()

                service_detail = {
                    "service_id": s.Id,
                    "service_name": s.Name,
                    "service_code": s.Code,
                    "color": s.Color,
                    "priority": s.Priority,
                    "waiting_count": s.count,
                    "in_progress_count": in_progress_service,
                    "average_wait": round(avg_service_wait, 1) if avg_service_wait else 0
                }

                services_breakdown.append(service_detail)

            # Calcular estaciones activas
            active_stations = db.query(func.count(Station.Id)).filter(
                Station.Status.in_(['Available', 'Busy']),
                Station.IsActive == True
            ).scalar() or 0

            # Crear diccionario de respuesta completo
            stats = {
                # Fecha de referencia
                "stats_date": today.isoformat(),

                # Contadores de estado (solo hoy)
                "waiting_tickets": waiting_count,
                "called_tickets": called_count,
                "in_progress_tickets": in_progress_count,

                # Estadísticas del día
                "total_tickets_today": total_today,
                "completed_today": completed_today,
                "cancelled_today": cancelled_today,
                "no_show_today": no_show_today,

                # Tiempos promedio (solo hoy)
                "average_wait_time": round(avg_wait, 1) if avg_wait else 0.0,
                "average_service_time": round(avg_service, 1) if avg_service else 0.0,

                # Por servicio
                "by_service": by_service,
                "services_breakdown": services_breakdown,

                # Estaciones
                "active_stations": active_stations
            }

            logger.debug(f"Estadísticas del día {today}: waiting={waiting_count}, total={total_today}")

            return stats

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de cola: {e}")
            # Retornar estructura vacía pero completa
            return {
                "stats_date": date.today().isoformat(),
                "waiting_tickets": 0,
                "called_tickets": 0,
                "in_progress_tickets": 0,
                "total_tickets_today": 0,
                "completed_today": 0,
                "cancelled_today": 0,
                "no_show_today": 0,
                "average_wait_time": 0.0,
                "average_service_time": 0.0,
                "by_service": {},
                "services_breakdown": [],
                "active_stations": 0
            }

    def get_ticket_position(self, db: Session, *, ticket_id: str) -> Dict[str, Any]:
        """
        Obtiene información detallada de la posición de un ticket en la cola

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket

        Returns:
            Dict con información de posición
        """
        try:
            ticket = self.get(db, id=ticket_id)
            if not ticket:
                return {
                    "position": 0,
                    "estimated_wait": 0,
                    "ahead_count": 0,
                    "service_name": "Desconocido"
                }

            # Contar tickets adelante
            ahead_count = db.query(Ticket).filter(
                and_(
                    Ticket.ServiceTypeId == ticket.ServiceTypeId,
                    Ticket.Status.in_(['Waiting', 'Called']),
                    Ticket.Position < ticket.Position
                )
            ).count()

            # Obtener nombre del servicio
            service_name = ticket.service_name or "Servicio"

            return {
                "position": ticket.Position,
                "estimated_wait": ticket.EstimatedWaitTime or 0,
                "ahead_count": ahead_count,
                "service_name": service_name
            }

        except Exception as e:
            logger.error(f"Error obteniendo posición del ticket {ticket_id}: {e}")
            return {
                "position": 0,
                "estimated_wait": 0,
                "ahead_count": 0,
                "service_name": "Error"
            }


    def search_tickets(
            self,
            db: Session,
            *,
            patient_document: Optional[str] = None,
            patient_name: Optional[str] = None,
            ticket_number: Optional[str] = None,
            service_type_id: Optional[int] = None,
            station_id: Optional[int] = None,
            status: Optional[str] = None,
            date_from: Optional[datetime] = None,
            date_to: Optional[datetime] = None,
            limit: int = 50
    ) -> List[Ticket]:
        """
        Búsqueda avanzada de tickets con múltiples filtros

        Args:
            db: Sesión de base de datos
            patient_document: Filtro por documento de paciente
            patient_name: Filtro por nombre de paciente
            ticket_number: Filtro por número de ticket
            service_type_id: Filtro por tipo de servicio
            station_id: Filtro por estación
            status: Filtro por estado
            date_from: Fecha desde
            date_to: Fecha hasta
            limit: Límite de resultados

        Returns:
            List[Ticket]: Lista de tickets que coinciden
        """
        try:
            query = db.query(Ticket).join(Patient, Ticket.PatientId == Patient.Id)

            # Aplicar filtros dinámicamente
            if patient_document:
                query = query.filter(Patient.DocumentNumber.like(f"%{patient_document}%"))

            if patient_name:
                query = query.filter(Patient.FullName.like(f"%{patient_name}%"))

            if ticket_number:
                query = query.filter(Ticket.TicketNumber.like(f"%{ticket_number}%"))

            if service_type_id:
                query = query.filter(Ticket.ServiceTypeId == service_type_id)

            if station_id:
                query = query.filter(Ticket.StationId == station_id)

            if status:
                query = query.filter(Ticket.Status == status)

            if date_from:
                query = query.filter(Ticket.CreatedAt  >= date_from)

            if date_to:
                query = query.filter(Ticket.CreatedAt  <= date_to)

            return query.order_by(desc(Ticket.CreatedAt )).limit(limit).all()

        except Exception as e:
            logger.error(f"Error en búsqueda avanzada de tickets: {e}")
            return []

    def reset_daily_positions(self, db: Session) -> int:
        """
        Reinicia las posiciones de los tickets para un nuevo día

        Args:
            db: Sesión de base de datos

        Returns:
            int: Número de tickets actualizados
        """
        try:
            # Obtener tickets activos ordenados por servicio y creación
            active_tickets = db.query(Ticket).filter(
                Ticket.Status.in_(['Waiting', 'Called'])
            ).order_by(Ticket.ServiceTypeId, Ticket.CreatedAt ).all()

            # Reagrupar por servicio y reasignar posiciones
            current_service = None
            position = 0
            updated_count = 0

            for ticket in active_tickets:
                if ticket.ServiceTypeId != current_service:
                    current_service = ticket.ServiceTypeId
                    position = 1
                else:
                    position += 1

                if ticket.Position != position:
                    ticket.Position = position
                    updated_count += 1

            if updated_count > 0:
                db.commit()
                logger.info(f"Posiciones actualizadas para {updated_count} tickets")

            return updated_count

        except Exception as e:
            db.rollback()
            logger.error(f"Error reiniciando posiciones diarias: {e}")
            return 0

    def get_services_with_queues(self, db: Session) -> List[ServiceType]:
        """
        Obtiene todos los tipos de servicio que tienen tickets en cola

        Returns:
            List[ServiceType]: Lista de tipos de servicio con tickets activos
        """
        try:
            from app.models.service_type import ServiceType

            # Obtener servicios que tienen tickets en espera
            services = db.query(ServiceType).join(
                Ticket, Ticket.ServiceTypeId == ServiceType.Id
            ).filter(
                Ticket.Status.in_(['Waiting', 'Called', 'InProgress']),
                ServiceType.IsActive == True
            ).distinct().all()

            return services

        except Exception as e:
            logger.error(f"Error obteniendo servicios con colas: {e}")
            return []

    def get_queue_stats_by_service(self, db: Session, service_type_id: int) -> Dict[str, Any]:
        """
        Obtiene estadísticas de cola para un tipo de servicio específico

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio

        Returns:
            Dict con estadísticas del servicio
        """
        try:
            stats = {
                "waiting": db.query(func.count(Ticket.Id)).filter(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.Status == 'Waiting'
                ).scalar() or 0,

                "in_progress": db.query(func.count(Ticket.Id)).filter(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.Status.in_(['Called', 'InProgress'])
                ).scalar() or 0,

                "completed_today": db.query(func.count(Ticket.Id)).filter(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.Status == 'Completed',
                    func.convert(literal_column('DATE'), Ticket.CompletedAt)== date.today()
                ).scalar() or 0,

                "average_wait": db.query(func.avg(Ticket.ActualWaitTime)).filter(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.Status == 'Completed',
                    func.convert(literal_column('DATE'), Ticket.CompletedAt) == date.today(),
                    Ticket.ActualWaitTime.isnot(None)
                ).scalar() or 0
            }

            # Redondear el tiempo promedio
            stats["average_wait"] = round(stats["average_wait"], 1) if stats["average_wait"] else 0

            return stats

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del servicio {service_type_id}: {e}")
            return {"waiting": 0, "in_progress": 0, "completed_today": 0, "average_wait": 0}


    def update_ticket_status(
            self,
            db: Session,
            *,
            ticket_id: str,
            new_status: str,
            station_id: Optional[int] = None,
            notes: Optional[str] = None
    ) -> Optional[Ticket]:
        """
        Actualiza el estado de un ticket y registra los timestamps correspondientes

        Args:
            db: Sesión de base de datos
            ticket_id: ID del ticket a actualizar
            new_status: Nuevo estado del ticket ('Waiting', 'Called', 'InProgress', 'Completed', 'Cancelled', 'NoShow')
            station_id: ID de la estación (opcional, para cuando se llama)
            notes: Notas adicionales (opcional)

        Returns:
            Ticket: Ticket actualizado o None si no se encuentra
        """
        try:
            # Obtener el ticket
            ticket = db.query(Ticket).filter(Ticket.Id == ticket_id).first()

            if not ticket:
                logger.warning(f"Ticket no encontrado: {ticket_id}")
                return None

            # Validar estados válidos
            valid_statuses = ['Waiting', 'Called', 'InProgress', 'Completed', 'Cancelled', 'NoShow']
            if new_status not in valid_statuses:
                logger.error(f"Estado inválido: {new_status}")
                raise ValueError(f"Estado inválido: {new_status}. Debe ser uno de: {', '.join(valid_statuses)}")

            # Guardar estado anterior para log
            old_status = ticket.Status

            # Actualizar estado
            ticket.Status = new_status

            # Actualizar timestamps según el nuevo estado
            current_time = datetime.utcnow()

            if new_status == 'Called':
                ticket.CalledAt = current_time
                if station_id:
                    ticket.StationId = station_id

            elif new_status == 'InProgress':
                ticket.AttendedAt = current_time
                # Si no fue llamado antes, registrar también CalledAt
                if not ticket.CalledAt:
                    ticket.CalledAt = current_time
                if station_id:
                    ticket.StationId = station_id

            elif new_status == 'Completed':
                ticket.CompletedAt = current_time
                # Si no fue atendido antes, registrar también AttendedAt
                if not ticket.AttendedAt:
                    ticket.AttendedAt = current_time
                # Calcular tiempo real de espera si no está calculado
                if ticket.AttendedAt and not ticket.ActualWaitTime:
                    wait_time = (ticket.AttendedAt - ticket.CreatedAt).total_seconds() / 60
                    ticket.ActualWaitTime = int(wait_time)

            elif new_status == 'Cancelled' or new_status == 'NoShow':
                ticket.CompletedAt = current_time  # Marcar como completado también

            # Agregar notas si se proporcionaron
            if notes:
                existing_notes = ticket.Notes or ""
                separator = " | " if existing_notes else ""
                ticket.Notes = f"{existing_notes}{separator}{notes}"

            # Actualizar timestamp de modificación
            ticket.UpdatedAt = current_time

            # Guardar cambios
            db.commit()
            db.refresh(ticket)

            logger.info(f"Ticket {ticket.TicketNumber} actualizado: {old_status} -> {new_status}")

            return ticket

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error actualizando estado del ticket {ticket_id}: {e}")
            db.rollback()
            return None

    def get_next_ticket_number(
            self,
            db: Session,
            *,
            service_type_id: int,
            prefix: Optional[str] = None,
            date_for_number: Optional[date] = None
    ) -> str:
        """
        Genera el siguiente número de ticket para un servicio específico

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            prefix: Prefijo opcional para el número (si no se proporciona, usa el del servicio)
            date_for_number: Fecha para generar el número (por defecto hoy)

        Returns:
            str: Número de ticket generado (ej: "A001", "LAB-002")
        """
        try:
            # Usar fecha actual si no se proporciona
            if date_for_number is None:
                date_for_number = date.today()

            # Obtener el tipo de servicio para el prefijo si no se proporciona
            if not prefix:
                service_type = service_type_crud.get(db, service_type_id)
                if service_type and service_type.Code:
                    prefix = service_type.Code
                else:
                    # Prefijo por defecto basado en el ID del servicio
                    prefix = f"S{service_type_id}"

            # Buscar el último ticket del día para este servicio
            start_of_day = datetime.combine(date_for_number, datetime.min.time())
            end_of_day = datetime.combine(date_for_number, datetime.max.time())

            last_ticket = db.query(Ticket).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.CreatedAt >= start_of_day,
                    Ticket.CreatedAt <= end_of_day,
                    Ticket.TicketNumber.like(f"{prefix}%")
                )
            ).order_by(Ticket.TicketNumber.desc()).first()

            # Determinar el siguiente número
            if last_ticket:
                # Extraer el número del último ticket
                last_number_str = last_ticket.TicketNumber.replace(prefix, "")
                try:
                    # Intentar convertir a número
                    last_number = int(last_number_str.lstrip("-"))
                    next_number = last_number + 1
                except ValueError:
                    # Si no se puede convertir, empezar desde 1
                    next_number = 1
            else:
                # Primer ticket del día
                next_number = 1

            # Formatear el número con ceros a la izquierda (3 dígitos)
            ticket_number = f"{prefix}{next_number:03d}"

            logger.info(f"Generado número de ticket: {ticket_number} para servicio {service_type_id}")
            return ticket_number

        except Exception as e:
            logger.error(f"Error generando número de ticket: {e}")
            # Generar un número de respaldo único basado en timestamp
            timestamp = datetime.now().strftime("%H%M%S")
            fallback_number = f"{prefix or 'TKT'}{timestamp}"
            logger.warning(f"Usando número de respaldo: {fallback_number}")
            return fallback_number

    def reset_daily_counters(
            self,
            db: Session,
            *,
            target_date: Optional[date] = None
    ) -> bool:
        """
        Resetea los contadores diarios (útil para mantenimiento)

        Args:
            db: Sesión de base de datos
            target_date: Fecha para resetear (por defecto hoy)

        Returns:
            bool: True si se reseteó correctamente
        """
        try:
            if target_date is None:
                target_date = date.today()

            # Este método es más para logging/auditoría
            # Los números se resetean automáticamente cada día
            logger.info(f"Contadores reseteados para fecha {target_date}")
            return True

        except Exception as e:
            logger.error(f"Error reseteando contadores: {e}")
            return False

    def get_ticket_count_by_prefix(
            self,
            db: Session,
            *,
            prefix: str,
            target_date: Optional[date] = None
    ) -> int:
        """
        Obtiene la cantidad de tickets generados con un prefijo específico

        Args:
            db: Sesión de base de datos
            prefix: Prefijo a buscar
            target_date: Fecha para contar (por defecto hoy)

        Returns:
            int: Cantidad de tickets con ese prefijo
        """
        try:
            if target_date is None:
                target_date = date.today()

            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())

            count = db.query(Ticket).filter(
                and_(
                    Ticket.CreatedAt >= start_of_day,
                    Ticket.CreatedAt <= end_of_day,
                    Ticket.TicketNumber.like(f"{prefix}%")
                )
            ).count()

            return count

        except Exception as e:
            logger.error(f"Error contando tickets por prefijo: {e}")
            return 0

    def generate_ticket_number_with_format(
            self,
            db: Session,
            *,
            service_type_id: int,
            format_type: str = "standard"
    ) -> str:
        """
        Genera números de ticket con diferentes formatos

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            format_type: Tipo de formato ("standard", "daily", "full", "compact")

        Returns:
            str: Número de ticket formateado
        """
        try:
            # Obtener el servicio
            service_type = service_type_crud.get(db, service_type_id)
            prefix = service_type.Code if service_type else f"S{service_type_id}"

            # Obtener siguiente número base
            base_number = self.get_next_ticket_number(
                db,
                service_type_id=service_type_id,
                prefix=prefix
            )

            # Aplicar formato según el tipo
            if format_type == "daily":
                # Formato: PREFIX-YYYYMMDD-NNN
                today = date.today()
                return f"{prefix}-{today.strftime('%Y%m%d')}-{base_number[-3:]}"

            elif format_type == "full":
                # Formato: LAB-2024-MM-DD-NNN
                today = date.today()
                return f"LAB-{today.year}-{today.month:02d}-{today.day:02d}-{base_number[-3:]}"

            elif format_type == "compact":
                # Formato: XNNN (una letra + números)
                first_letter = prefix[0] if prefix else "T"
                return f"{first_letter}{base_number[-3:]}"

            else:
                # Formato estándar
                return base_number

        except Exception as e:
            logger.error(f"Error generando número con formato {format_type}: {e}")
            # Retornar número estándar como fallback
            return self.get_next_ticket_number(db, service_type_id=service_type_id)


    def close_daily_tickets(
            self,
            db: Session,
            *,
            target_date: Optional[date] = None,
            reason: str = "Cierre automático de jornada"
    ) -> Dict[str, Any]:
        """
        Cierra todos los tickets pendientes de un día específico.
        Los tickets en Waiting, Called o InProgress se marcan como NoShow.

        Args:
            db: Sesión de base de datos
            target_date: Fecha a cerrar (por defecto: ayer)
            reason: Razón del cierre

        Returns:
            Dict con resumen del cierre:
            - closed_count: Cantidad de tickets cerrados
            - by_status: Desglose por estado anterior
            - target_date: Fecha procesada
        """
        try:
            from datetime import datetime, timedelta

            # Por defecto cerrar tickets de ayer (no del día actual)
            if target_date is None:
                target_date = date.today() - timedelta(days=1)

            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())

            # Buscar tickets activos de esa fecha
            pending_tickets = db.query(Ticket).filter(
                Ticket.Status.in_(['Waiting', 'Called', 'InProgress']),
                Ticket.CreatedAt >= start_of_day,
                Ticket.CreatedAt <= end_of_day
            ).all()

            # Contadores por estado
            by_status = {
                'Waiting': 0,
                'Called': 0,
                'InProgress': 0
            }

            closed_count = 0
            current_time = datetime.now()

            for ticket in pending_tickets:
                old_status = ticket.Status
                by_status[old_status] = by_status.get(old_status, 0) + 1

                # Marcar como NoShow
                ticket.Status = 'NoShow'
                ticket.CompletedAt = current_time
                ticket.UpdatedAt = current_time

                # Agregar nota de cierre
                close_note = f"[{current_time.strftime('%Y-%m-%d %H:%M')}] {reason} (Estado anterior: {old_status})"
                if ticket.Notes:
                    ticket.Notes = f"{ticket.Notes} | {close_note}"
                else:
                    ticket.Notes = close_note

                closed_count += 1

            if closed_count > 0:
                db.commit()
                logger.info(f"Cierre diario: {closed_count} tickets cerrados para fecha {target_date}")
            else:
                logger.info(f"Cierre diario: No hay tickets pendientes para fecha {target_date}")

            return {
                "success": True,
                "closed_count": closed_count,
                "by_status": by_status,
                "target_date": target_date.isoformat(),
                "reason": reason
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error en cierre diario de tickets: {e}")
            return {
                "success": False,
                "closed_count": 0,
                "by_status": {},
                "target_date": target_date.isoformat() if target_date else None,
                "error": str(e)
            }


    def get_expired_tickets(
            self,
            db: Session,
            *,
            before_date: Optional[date] = None
    ) -> List[Ticket]:
        """
        Obtiene tickets activos que ya expiraron (de días anteriores).
        Útil para identificar tickets que necesitan cierre.

        Args:
            db: Sesión de base de datos
            before_date: Obtener tickets creados antes de esta fecha (por defecto: hoy)

        Returns:
            List[Ticket]: Lista de tickets expirados
        """
        try:
            from datetime import datetime

            if before_date is None:
                before_date = date.today()

            # Inicio del día de referencia (todo lo anterior está expirado)
            cutoff_datetime = datetime.combine(before_date, datetime.min.time())

            expired_tickets = db.query(Ticket).filter(
                Ticket.Status.in_(['Waiting', 'Called', 'InProgress']),
                Ticket.CreatedAt < cutoff_datetime
            ).order_by(
                Ticket.CreatedAt.asc()
            ).all()

            logger.debug(f"Encontrados {len(expired_tickets)} tickets expirados (antes de {before_date})")
            return expired_tickets

        except Exception as e:
            logger.error(f"Error obteniendo tickets expirados: {e}")
            return []

    def close_all_expired_tickets(
            self,
            db: Session,
            *,
            before_date: Optional[date] = None,
            reason: str = "Cierre automático - ticket expirado"
    ) -> Dict[str, Any]:
        """
        Cierra TODOS los tickets activos de días anteriores a la fecha especificada.
        A diferencia de close_daily_tickets que cierra UN día específico,
        este método cierra TODO lo anterior a la fecha dada.

        Args:
            db: Sesión de base de datos
            before_date: Cerrar tickets creados antes de esta fecha (por defecto: hoy)
            reason: Razón del cierre

        Returns:
            Dict con resumen del cierre:
            - closed_count: Cantidad de tickets cerrados
            - by_status: Desglose por estado anterior
            - by_date: Desglose por fecha de creación
            - before_date: Fecha de corte usada
        """
        try:
            if before_date is None:
                before_date = date.today()

            # Inicio del día de referencia (todo lo anterior está expirado)
            cutoff_datetime = datetime.combine(before_date, datetime.min.time())

            # Buscar TODOS los tickets activos anteriores a la fecha de corte
            expired_tickets = db.query(Ticket).filter(
                Ticket.Status.in_(['Waiting', 'Called', 'InProgress']),
                Ticket.CreatedAt < cutoff_datetime
            ).all()

            # Contadores por estado
            by_status = {
                'Waiting': 0,
                'Called': 0,
                'InProgress': 0
            }

            # Contadores por fecha
            by_date = {}

            closed_count = 0
            current_time = datetime.now()

            for ticket in expired_tickets:
                old_status = ticket.Status
                by_status[old_status] = by_status.get(old_status, 0) + 1

                # Contar por fecha de creación
                ticket_date = ticket.CreatedAt.date().isoformat()
                by_date[ticket_date] = by_date.get(ticket_date, 0) + 1

                # Marcar como NoShow
                ticket.Status = 'NoShow'
                ticket.CompletedAt = current_time
                ticket.UpdatedAt = current_time

                # Agregar nota de cierre
                close_note = f"[{current_time.strftime('%Y-%m-%d %H:%M')}] {reason} (Estado anterior: {old_status})"
                if ticket.Notes:
                    ticket.Notes = f"{ticket.Notes} | {close_note}"
                else:
                    ticket.Notes = close_note

                closed_count += 1

            if closed_count > 0:
                db.commit()
                logger.info(f"Cierre masivo: {closed_count} tickets expirados cerrados (antes de {before_date})")
            else:
                logger.info(f"Cierre masivo: No hay tickets expirados antes de {before_date}")

            return {
                "success": True,
                "closed_count": closed_count,
                "by_status": by_status,
                "by_date": by_date,
                "before_date": before_date.isoformat(),
                "reason": reason
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error en cierre masivo de tickets expirados: {e}")
            return {
                "success": False,
                "closed_count": 0,
                "by_status": {},
                "by_date": {},
                "before_date": before_date.isoformat() if before_date else None,
                "error": str(e)
            }


# ========================================
# INSTANCIA GLOBAL
# ========================================

ticket_crud = CRUDTicket(Ticket)