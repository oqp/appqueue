"""
CRUD operations para gestión de estados de cola (QueueState)
Compatible con SQL Server y Pydantic v2
VERSIÓN CORREGIDA CON PASCALCASE - Coincide con BD, modelos y schemas
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError
import logging
import uuid

from app.models.queue_state import QueueState
from app.models.service_type import ServiceType
from app.models.station import Station
from app.models.ticket import Ticket
from app.crud.base import CRUDBase
from app.schemas.queue import QueueStateCreate, QueueStateUpdate

logger = logging.getLogger(__name__)


class CRUDQueue(CRUDBase[QueueState, QueueStateCreate, QueueStateUpdate]):
    """
    CRUD operations para QueueState
    Incluye operaciones especializadas para gestión de colas
    Usa PascalCase para coincidir con BD y modelos
    """

    def get_by_service_and_station(
        self,
        db: Session,
        *,
        service_type_id: int,
        station_id: Optional[int] = None
    ) -> Optional[QueueState]:
        """
        Obtiene el estado de cola para un servicio y estación específicos

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            station_id: ID de la estación (opcional)

        Returns:
            QueueState: Estado de la cola o None
        """
        try:
            query = db.query(QueueState).filter(
                QueueState.ServiceTypeId == service_type_id
            )

            if station_id:
                query = query.filter(QueueState.StationId == station_id)
            else:
                query = query.filter(QueueState.StationId == None)

            return query.first()

        except Exception as e:
            logger.error(f"Error obteniendo estado de cola: {e}")
            return None

    def get_or_create(
        self,
        db: Session,
        *,
        service_type_id: int,
        station_id: Optional[int] = None
    ) -> QueueState:
        """
        Obtiene o crea un estado de cola

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            station_id: ID de la estación (opcional)

        Returns:
            QueueState: Estado de la cola (existente o nuevo)
        """
        try:
            # Intentar obtener existente
            queue_state = self.get_by_service_and_station(
                db,
                service_type_id=service_type_id,
                station_id=station_id
            )

            if queue_state:
                return queue_state

            # Crear nuevo si no existe
            queue_state = QueueState(
                ServiceTypeId=service_type_id,
                StationId=station_id,
                QueueLength=0,
                AverageWaitTime=0,
                LastUpdateAt=datetime.now()
            )

            db.add(queue_state)
            db.commit()
            db.refresh(queue_state)

            logger.info(f"Nuevo estado de cola creado para servicio {service_type_id}")
            return queue_state

        except Exception as e:
            logger.error(f"Error en get_or_create: {e}")
            db.rollback()
            # Retornar un objeto nuevo sin guardar
            return QueueState(
                ServiceTypeId=service_type_id,
                StationId=station_id,
                QueueLength=0,
                AverageWaitTime=0
            )

    def create(
        self,
        db: Session,
        *,
        obj_in: QueueStateCreate
    ) -> QueueState:
        """
        Crea un nuevo estado de cola usando el schema QueueStateCreate

        Args:
            db: Sesión de base de datos
            obj_in: Schema con datos de creación

        Returns:
            QueueState: Estado creado
        """
        try:
            # Convertir schema a dict excluyendo valores no establecidos
            obj_in_data = obj_in.model_dump(exclude_unset=True)

            # Asegurar que LastUpdateAt esté presente
            if 'LastUpdateAt' not in obj_in_data:
                obj_in_data['LastUpdateAt'] = datetime.now()

            # Crear objeto del modelo
            db_obj = QueueState(**obj_in_data)

            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            logger.info(f"QueueState creado: ID={db_obj.Id}")
            return db_obj

        except Exception as e:
            logger.error(f"Error creando QueueState: {e}")
            db.rollback()
            raise

    def update(
        self,
        db: Session,
        *,
        db_obj: QueueState,
        obj_in: QueueStateUpdate
    ) -> QueueState:
        """
        Actualiza un estado de cola existente

        Args:
            db: Sesión de base de datos
            db_obj: Objeto QueueState existente
            obj_in: Schema con datos de actualización

        Returns:
            QueueState: Estado actualizado
        """
        try:
            # Convertir schema a dict
            update_data = obj_in.model_dump(exclude_unset=True)

            # Actualizar campos
            for field, value in update_data.items():
                setattr(db_obj, field, value)

            # Actualizar timestamp
            db_obj.LastUpdateAt = datetime.now()

            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            logger.debug(f"QueueState {db_obj.Id} actualizado")
            return db_obj

        except Exception as e:
            logger.error(f"Error actualizando QueueState: {e}")
            db.rollback()
            raise

    def update_queue_state(
        self,
        db: Session,
        *,
        queue_id: int,
        queue_length: Optional[int] = None,
        current_ticket_id: Optional[str] = None,
        next_ticket_id: Optional[str] = None,
        average_wait_time: Optional[int] = None
    ) -> Optional[QueueState]:
        """
        Actualiza el estado de una cola por ID

        Args:
            db: Sesión de base de datos
            queue_id: ID del estado de cola
            queue_length: Nueva longitud de la cola
            current_ticket_id: ID del ticket actual
            next_ticket_id: ID del próximo ticket
            average_wait_time: Tiempo promedio de espera en minutos

        Returns:
            QueueState: Estado actualizado o None
        """
        try:
            queue_state = db.query(QueueState).filter(
                QueueState.Id == queue_id
            ).first()

            if not queue_state:
                logger.error(f"Estado de cola {queue_id} no encontrado")
                return None

            # Actualizar campos si se proporcionan
            if queue_length is not None:
                queue_state.QueueLength = queue_length

            if current_ticket_id is not None:
                queue_state.CurrentTicketId = current_ticket_id

            if next_ticket_id is not None:
                queue_state.NextTicketId = next_ticket_id

            if average_wait_time is not None:
                queue_state.AverageWaitTime = average_wait_time

            queue_state.LastUpdateAt = datetime.now()

            db.add(queue_state)
            db.commit()
            db.refresh(queue_state)

            logger.debug(f"Estado de cola {queue_id} actualizado")
            return queue_state

        except Exception as e:
            logger.error(f"Error actualizando estado de cola: {e}")
            db.rollback()
            return None

    def advance_queue(
        self,
        db: Session,
        *,
        service_type_id: int,
        station_id: Optional[int] = None
    ) -> Optional[QueueState]:
        """
        Avanza la cola al siguiente ticket

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            station_id: ID de la estación

        Returns:
            QueueState: Estado actualizado o None
        """
        try:
            # Obtener estado actual
            queue_state = self.get_by_service_and_station(
                db,
                service_type_id=service_type_id,
                station_id=station_id
            )

            if not queue_state:
                logger.warning(f"No se encontró estado de cola para servicio {service_type_id}")
                return None

            # Si la cola está vacía y no hay tickets, no hay nada que avanzar
            if queue_state.QueueLength == 0 and queue_state.NextTicketId is None:
                logger.info(f"Cola vacía para servicio {service_type_id}, nada que avanzar")
                return queue_state  # Retornar el estado sin cambios

            # El próximo ticket se convierte en el actual
            queue_state.CurrentTicketId = queue_state.NextTicketId

            # Buscar el siguiente ticket en espera
            next_waiting = db.query(Ticket).filter(
                Ticket.ServiceTypeId == service_type_id,
                Ticket.Status == 'Waiting'
            ).order_by(
                Ticket.Position.asc()  # Ordenar por posición
            ).first()

            queue_state.NextTicketId = str(next_waiting.Id) if next_waiting else None

            # Actualizar longitud de la cola
            if queue_state.QueueLength > 0:
                queue_state.QueueLength -= 1

            queue_state.LastUpdateAt = datetime.now()

            db.add(queue_state)
            db.commit()
            db.refresh(queue_state)

            logger.info(f"Cola avanzada para servicio {service_type_id}")
            return queue_state

        except Exception as e:
            logger.error(f"Error avanzando cola: {e}")
            db.rollback()
            return None

    def reset_queue(
        self,
        db: Session,
        *,
        service_type_id: int,
        station_id: Optional[int] = None
    ) -> Optional[QueueState]:
        """
        Reinicia el estado de una cola

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            station_id: ID de la estación

        Returns:
            QueueState: Estado reiniciado o None
        """
        try:
            queue_state = self.get_by_service_and_station(
                db,
                service_type_id=service_type_id,
                station_id=station_id
            )

            if not queue_state:
                # Crear nuevo estado si no existe
                queue_state = self.get_or_create(
                    db,
                    service_type_id=service_type_id,
                    station_id=station_id
                )

            # Reiniciar todos los campos
            queue_state.CurrentTicketId = None
            queue_state.NextTicketId = None
            queue_state.QueueLength = 0
            queue_state.AverageWaitTime = 0
            queue_state.LastUpdateAt = datetime.now()

            db.add(queue_state)
            db.commit()
            db.refresh(queue_state)

            logger.info(f"Cola reiniciada para servicio {service_type_id}")
            return queue_state

        except Exception as e:
            logger.error(f"Error reiniciando cola: {e}")
            db.rollback()
            return None

    def calculate_and_update_wait_time(
        self,
        db: Session,
        *,
        queue_state_id: int
    ) -> Optional[int]:
        """
        Calcula y actualiza el tiempo promedio de espera

        Args:
            db: Sesión de base de datos
            queue_state_id: ID del estado de cola

        Returns:
            int: Tiempo promedio en minutos o None
        """
        try:
            queue_state = db.query(QueueState).filter(
                QueueState.Id == queue_state_id
            ).first()

            if not queue_state:
                logger.error(f"Estado de cola {queue_state_id} no encontrado")
                return None

            # Obtener tickets completados recientemente (últimas 2 horas)
            cutoff_time = datetime.now() - timedelta(hours=2)

            completed_tickets = db.query(Ticket).filter(
                Ticket.ServiceTypeId == queue_state.ServiceTypeId,
                Ticket.Status == 'Completed',
                Ticket.CompletedAt != None,
                Ticket.CompletedAt > cutoff_time
            ).all()

            if completed_tickets:
                # Calcular tiempo promedio de espera real
                total_wait_time = 0
                valid_tickets = 0

                for ticket in completed_tickets:
                    if ticket.CreatedAt and ticket.CalledAt:
                        wait_time = (ticket.CalledAt - ticket.CreatedAt).total_seconds() / 60
                        if wait_time > 0:  # Solo tiempos válidos
                            total_wait_time += wait_time
                            valid_tickets += 1

                if valid_tickets > 0:
                    avg_time = int(total_wait_time / valid_tickets)
                else:
                    # Usar tiempo promedio del servicio como fallback
                    service = db.query(ServiceType).filter(
                        ServiceType.Id == queue_state.ServiceTypeId
                    ).first()
                    avg_time = service.AverageTimeMinutes if service else 10
            else:
                # No hay tickets completados, usar tiempo del servicio
                service = db.query(ServiceType).filter(
                    ServiceType.Id == queue_state.ServiceTypeId
                ).first()
                avg_time = service.AverageTimeMinutes if service else 10

            # Actualizar el tiempo promedio
            queue_state.AverageWaitTime = avg_time
            queue_state.LastUpdateAt = datetime.now()

            db.add(queue_state)
            db.commit()

            logger.debug(f"Tiempo promedio actualizado para cola {queue_state_id}: {avg_time} min")
            return avg_time

        except Exception as e:
            logger.error(f"Error calculando tiempo de espera: {e}")
            db.rollback()
            return None

    def get_all_active(
        self,
        db: Session
    ) -> List[QueueState]:
        """
        Obtiene todos los estados de cola activos

        Returns:
            List[QueueState]: Lista de estados activos
        """
        try:
            return db.query(QueueState).filter(
                or_(
                    QueueState.QueueLength > 0,
                    QueueState.CurrentTicketId != None
                )
            ).all()

        except Exception as e:
            logger.error(f"Error obteniendo colas activas: {e}")
            return []

    def get_queue_summary(
        self,
        db: Session
    ) -> Dict[str, Any]:
        """
        Obtiene un resumen del estado global de las colas
        CORREGIDO: Cuenta tickets reales, no solo QueueState.QueueLength

        Returns:
            Dict: Resumen con estadísticas
        """
        try:
            # Total de colas (tipos de servicio con QueueState)
            total_queues = db.query(QueueState).count()

            # Total de personas esperando - CONTAR TICKETS REALES
            total_waiting = db.query(func.count(Ticket.Id)).filter(
                Ticket.Status == 'Waiting'
            ).scalar() or 0

            # Colas activas - servicios que tienen tickets esperando
            active_queues = db.query(func.count(func.distinct(Ticket.ServiceTypeId))).filter(
                Ticket.Status == 'Waiting'
            ).scalar() or 0

            # Tickets siendo atendidos (Called o InProgress)
            in_attention = db.query(func.count(Ticket.Id)).filter(
                Ticket.Status.in_(['Called', 'InProgress'])
            ).scalar() or 0

            # Estaciones ocupadas - estaciones con ticket actual
            stations_busy = db.query(func.count(func.distinct(Ticket.StationId))).filter(
                Ticket.Status.in_(['Called', 'InProgress']),
                Ticket.StationId != None
            ).scalar() or 0

            # Tiempo promedio global de espera
            avg_wait = db.query(func.avg(QueueState.AverageWaitTime)).filter(
                QueueState.AverageWaitTime > 0
            ).scalar() or 0

            # Tickets completados hoy
            from datetime import date
            today = date.today()
            try:
                completed_today = db.query(func.count(Ticket.Id)).filter(
                    Ticket.Status == 'Completed',
                    Ticket.CompletedAt >= datetime.combine(today, datetime.min.time())
                ).scalar() or 0
            except:
                completed_today = 0

            return {
                'total_queues': total_queues,
                'active_queues': active_queues,
                'total_waiting': int(total_waiting),
                'in_attention': int(in_attention),
                'stations_busy': stations_busy,
                'average_wait_time': round(avg_wait, 1),
                'completed_today': completed_today
            }

        except Exception as e:
            logger.error(f"Error obteniendo resumen de colas: {e}")
            return {
                'total_queues': 0,
                'active_queues': 0,
                'total_waiting': 0,
                'in_attention': 0,
                'stations_busy': 0,
                'average_wait_time': 0,
                'completed_today': 0
            }


    def refresh_all_states(
        self,
        db: Session
    ) -> int:
        """
        Refresca todos los estados de cola desde los datos actuales

        Returns:
            int: Número de estados actualizados
        """
        try:
            updated_count = 0

            # Obtener todos los servicios activos
            services = db.query(ServiceType).filter(
                ServiceType.IsActive == True
            ).all()

            for service in services:
                # Contar tickets en espera
                waiting_count = db.query(Ticket).filter(
                    Ticket.ServiceTypeId == service.Id,
                    Ticket.Status == 'Waiting'
                ).count()

                # Obtener o crear estado de cola
                queue_state = self.get_or_create(
                    db,
                    service_type_id=service.Id
                )

                # Actualizar longitud
                queue_state.QueueLength = waiting_count

                # Buscar ticket actual si hay alguno siendo atendido
                current_ticket = db.query(Ticket).filter(
                    Ticket.ServiceTypeId == service.Id,
                    Ticket.Status.in_(['Called', 'InProgress'])
                ).first()

                if current_ticket:
                    queue_state.CurrentTicketId = str(current_ticket.Id)

                # Buscar próximo ticket
                next_ticket = db.query(Ticket).filter(
                    Ticket.ServiceTypeId == service.Id,
                    Ticket.Status == 'Waiting'
                ).order_by(
                    Ticket.Position.asc()  # Ordenar por posición
                ).first()

                if next_ticket:
                    queue_state.NextTicketId = str(next_ticket.Id)

                queue_state.LastUpdateAt = datetime.now()

                db.add(queue_state)
                updated_count += 1

            db.commit()

            logger.info(f"Refrescados {updated_count} estados de cola")
            return updated_count

        except Exception as e:
            logger.error(f"Error refrescando estados: {e}")
            db.rollback()
            return 0

    def get_by_station(
        self,
        db: Session,
        *,
        station_id: int
    ) -> List[QueueState]:
        """
        Obtiene todos los estados de cola de una estación

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación

        Returns:
            List[QueueState]: Lista de estados
        """
        try:
            return db.query(QueueState).filter(
                QueueState.StationId == station_id
            ).all()

        except Exception as e:
            logger.error(f"Error obteniendo colas de estación {station_id}: {e}")
            return []

    def cleanup_stale_states(
        self,
        db: Session,
        *,
        minutes: int = 30
    ) -> int:
        """
        Limpia estados de cola obsoletos (sin actualización reciente)

        Args:
            db: Sesión de base de datos
            minutes: Minutos de antigüedad para considerar obsoleto

        Returns:
            int: Número de estados limpiados
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)

            # Buscar estados obsoletos
            stale_states = db.query(QueueState).filter(
                QueueState.LastUpdateAt < cutoff_time,
                QueueState.QueueLength == 0,
                QueueState.CurrentTicketId == None
            ).all()

            count = len(stale_states)

            for state in stale_states:
                db.delete(state)

            db.commit()

            if count > 0:
                logger.info(f"Limpiados {count} estados de cola obsoletos")

            return count

        except Exception as e:
            logger.error(f"Error limpiando estados obsoletos: {e}")
            db.rollback()
            return 0


# Instancia singleton del CRUD
queue_crud = CRUDQueue(QueueState)