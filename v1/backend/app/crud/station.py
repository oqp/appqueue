"""
Operaciones CRUD para el modelo Station
Compatible con SQL Server y toda la estructura existente del proyecto
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc, text, Date, literal_column
from datetime import datetime, date, timedelta
import logging
import uuid

from app.crud.base import CRUDBase
from app.models.station import Station
from app.models.ticket import Ticket
from app.models.service_type import ServiceType
from app.models.user import User
from app.schemas.station import StationCreate, StationUpdate

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)


# ========================================
# CLASE CRUD STATION
# ========================================

class CRUDStation(CRUDBase[Station, StationCreate, StationUpdate]):
    """
    Operaciones CRUD específicas para estaciones
    Hereda de CRUDBase y añade métodos específicos
    """

    # ========================================
    # MÉTODOS DE OBTENCIÓN BÁSICOS
    # ========================================

    def get_by_code(self, db: Session, code: str) -> Optional[Station]:
        """
        Obtiene una estación por su código único

        Args:
            db: Sesión de base de datos
            code: Código de la estación

        Returns:
            Station o None si no existe
        """
        try:
            return db.query(Station).filter(
                Station.Code == code.upper()
            ).first()
        except Exception as e:
            logger.error(f"Error obteniendo estación por código {code}: {e}")
            return None

    def get_active_stations(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Station]:
        """
        Obtiene todas las estaciones activas

        Args:
            db: Sesión de base de datos
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de estaciones activas
        """
        try:
            return db.query(Station).filter(
                Station.IsActive == True,
                Station.Status.in_(['active', 'break'])
            ).order_by(Station.Id).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error obteniendo estaciones activas: {e}")
            return []

    def get_by_specialization(
        self,
        db: Session,
        specialization: str,
        only_active: bool = True
    ) -> List[Station]:
        """
        Obtiene estaciones por especialización

        Args:
            db: Sesión de base de datos
            specialization: Tipo de especialización
            only_active: Solo estaciones activas

        Returns:
            Lista de estaciones con la especialización
        """
        try:
            query = db.query(Station).filter(
                Station.Specialization == specialization
            )

            if only_active:
                query = query.filter(
                    Station.IsActive == True,
                    Station.Status == 'active'
                )

            return query.all()
        except Exception as e:
            logger.error(f"Error obteniendo estaciones por especialización {specialization}: {e}")
            return []

    def get_by_service_type(
        self,
        db: Session,
        service_type_id: int,
        only_available: bool = False
    ) -> List[Station]:
        """
        Obtiene estaciones que atienden un tipo de servicio

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            only_available: Solo estaciones disponibles

        Returns:
            Lista de estaciones
        """
        try:
            query = db.query(Station).filter(
                Station.ServiceTypeId == service_type_id,
                Station.IsActive == True
            )

            if only_available:
                # Filtrar estaciones que tienen usuarios asignados
                query = query.filter(
                    Station.Status == 'active'
                ).join(User).filter(
                    User.StationId == Station.Id,
                    User.IsActive == True
                )

            return query.all()
        except Exception as e:
            logger.error(f"Error obteniendo estaciones por tipo de servicio {service_type_id}: {e}")
            return []

    # ========================================
    # MÉTODOS DE CREACIÓN Y ACTUALIZACIÓN
    # ========================================

    def create_with_validation(
        self,
        db: Session,
        *,
        obj_in: StationCreate
    ) -> Station:
        """
        Crea una nueva estación con validaciones

        Args:
            db: Sesión de base de datos
            obj_in: Datos de la estación a crear

        Returns:
            Station creada
        """
        try:
            # Verificar código único
            if self.get_by_code(db, obj_in.Code):
                raise ValueError(f"El código {obj_in.Code} ya existe")

            # Crear objeto Station
            db_obj = Station(
                Name=obj_in.Name,
                Code=obj_in.Code.upper(),
                Description=obj_in.Description,
                Location=obj_in.Location if hasattr(obj_in, 'Location') else None,
                Specialization=obj_in.Specialization,
                ServiceTypeId=obj_in.ServiceTypeIds[0] if obj_in.ServiceTypeIds else None,
                MaxConcurrentPatients=obj_in.MaxConcurrentPatients,
                AverageServiceTimeMinutes=obj_in.AverageServiceTimeMinutes,
                Status='active',
                IsActive=obj_in.IsActive,
                WorkingHours=obj_in.WorkingHours,
                ConfigData={
                    'created_date': datetime.now().isoformat(),
                    'service_type_ids': obj_in.ServiceTypeIds or []
                }
            )

            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            logger.info(f"Estación creada: {db_obj.Name} ({db_obj.Code})")
            return db_obj

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando estación: {e}")
            raise

    def update_with_validation(
        self,
        db: Session,
        *,
        db_obj: Station,
        obj_in: StationUpdate
    ) -> Station:
        """
        Actualiza una estación con validaciones

        Args:
            db: Sesión de base de datos
            db_obj: Estación existente
            obj_in: Datos de actualización

        Returns:
            Station actualizada
        """
        try:
            # Actualizar campos si están presentes
            update_data = obj_in.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Actualizar metadata
            if db_obj.ConfigData is None:
                db_obj.ConfigData = {}
            db_obj.ConfigData['last_updated'] = datetime.now().isoformat()

            # Si se actualizaron los ServiceTypeIds
            if 'ServiceTypeIds' in update_data and update_data['ServiceTypeIds']:
                db_obj.ServiceTypeId = update_data['ServiceTypeIds'][0]
                db_obj.ConfigData['service_type_ids'] = update_data['ServiceTypeIds']

            db.commit()
            db.refresh(db_obj)

            logger.info(f"Estación actualizada: {db_obj.Name} ({db_obj.Code})")
            return db_obj

        except Exception as e:
            db.rollback()
            logger.error(f"Error actualizando estación: {e}")
            raise

    # ========================================
    # MÉTODOS DE GESTIÓN DE ESTADO
    # ========================================

    def update_status(
            self,
            db: Session,
            station_id: int,
            new_status: str,
            reason: Optional[str] = None
    ) -> Optional[Station]:
        """
        Actualiza el estado de una estación
        """
        try:
            station = self.get(db, id=station_id)
            if not station:
                return None

            # Validar que el estado sea válido
            valid_statuses = ['Available', 'Busy', 'Break', 'Maintenance', 'Offline']
            if new_status not in valid_statuses:
                logger.warning(f"Estado inválido: {new_status}. Estados válidos: {valid_statuses}")
                return None

            # Usar el método correcto del modelo Station
            station.Status = new_status  # ✅ Opción 1: Asignación directa
            # O alternativamente:
            # station.set_status(new_status)  # ✅ Opción 2: Usar set_status() que SÍ existe

            # Si quieres guardar la razón del cambio (opcional)
            if reason:
                # Si tu modelo tiene ConfigData o algún campo para metadata
                if not hasattr(station, 'ConfigData') or station.ConfigData is None:
                    station.ConfigData = {}
                station.ConfigData['last_status_change'] = {
                    'status': new_status,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat()
                }

            db.commit()
            db.refresh(station)
            logger.info(f"Estado de estación {station.Code} actualizado a {new_status}")
            return station

        except Exception as e:
            db.rollback()
            logger.error(f"Error actualizando estado de estación {station_id}: {e}")
            return None

    def assign_user(
            self,
            db: Session,
            station_id: int,
            user_id: str,
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None
    ) -> Optional[Station]:
        """
        Asigna un usuario a una estación
        """
        try:
            station = self.get(db, id=station_id)
            user = db.query(User).filter(User.Id == user_id).first()

            if not station or not user:
                return None

            # Asignar estación al usuario
            user.StationId = station_id

            # Opcional: Actualizar el estado de la estación si está disponible
            if station.Status == 'Available':
                station.Status = 'Busy'

            # Opcional: Si quieres trackear la asignación, puedes usar campos existentes
            # Por ejemplo, podrías guardar el user_id en algún campo existente
            # o simplemente confiar en la relación User.StationId

            db.commit()
            db.refresh(station)
            db.refresh(user)

            logger.info(f"Usuario {user.Username} asignado a estación {station.Code}")
            return station

        except Exception as e:
            db.rollback()
            logger.error(f"Error asignando usuario a estación: {e}")
            return None





    def remove_user(
        self,
        db: Session,
        station_id: int
    ) -> Optional[Station]:
        """
        Remueve el usuario asignado de una estación

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación

        Returns:
            Station actualizada o None
        """
        try:
            station = self.get(db, id=station_id)
            if not station:
                return None

            # Buscar usuarios asignados a esta estación y desasignarlos
            users = db.query(User).filter(User.StationId == station_id).all()
            for user in users:
                user.StationId = None

            # Actualizar metadata
            if station.ConfigData and 'current_assignment' in station.ConfigData:
                station.ConfigData['last_assignment'] = station.ConfigData['current_assignment']
                station.ConfigData['last_assignment']['end_time'] = datetime.now().isoformat()
                del station.ConfigData['current_assignment']

            db.commit()
            db.refresh(station)

            logger.info(f"Usuarios removidos de estación {station.Code}")
            return station

        except Exception as e:
            db.rollback()
            logger.error(f"Error removiendo usuario de estación: {e}")
            return None

    # ========================================
    # MÉTODOS DE GESTIÓN DE COLA
    # ========================================

    def get_station_queue(
        self,
        db: Session,
        station_id: int,
        limit: int = 50
    ) -> List[Ticket]:
        """
        Obtiene la cola de tickets de una estación

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            limit: Límite de tickets

        Returns:
            Lista de tickets en cola
        """
        try:
            return db.query(Ticket).filter(
                Ticket.StationId == station_id,
                Ticket.Status.in_(['waiting', 'called'])
            ).order_by(
                Ticket.Priority.desc(),
                Ticket.CreatedAt.asc()
            ).limit(limit).all()

        except Exception as e:
            logger.error(f"Error obteniendo cola de estación {station_id}: {e}")
            return []

    def get_queue_stats(
            self,
            db: Session,
            station_id: int
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la cola de una estación

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación

        Returns:
            Diccionario con estadísticas
        """
        try:
            station = self.get(db, id=station_id)
            if not station:
                return {
                    'queue_length': 0,
                    'average_wait_time': 0,
                    'tickets_today': 0
                }

            # Contar tickets en espera
            waiting_count = db.query(func.count(Ticket.Id)).filter(
                Ticket.StationId == station_id,
                Ticket.Status == 'Waiting'
            ).scalar() or 0

            # Contar tickets en proceso
            in_progress_count = db.query(func.count(Ticket.Id)).filter(
                Ticket.StationId == station_id,
                Ticket.Status.in_(['Called', 'InProgress'])
            ).scalar() or 0

            # Tickets completados hoy
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = datetime.combine(date.today(), datetime.max.time())

            completed_today = db.query(func.count(Ticket.Id)).filter(
                Ticket.StationId == station_id,
                Ticket.Status == 'Completed',
                Ticket.CompletedAt >= today_start,
                Ticket.CompletedAt <= today_end
            ).scalar() or 0

            # Calcular tiempo promedio de espera (en minutos)
            # Para SQL Server, usar DATEDIFF directamente
            avg_wait_time_query = db.query(
                func.avg(
                    func.datediff(
                        literal_column("minute"),
                        Ticket.CreatedAt,
                        Ticket.CalledAt
                    )
                )
            ).filter(
                Ticket.StationId == station_id,
                Ticket.CalledAt.isnot(None),
                Ticket.CreatedAt >= today_start,
                Ticket.CreatedAt <= today_end
            ).scalar()

            avg_wait_time = float(avg_wait_time_query) if avg_wait_time_query else 0

            return {
                'queue_length': waiting_count,
                'average_wait_time': round(avg_wait_time, 2),
                'tickets_today': completed_today,
                'waiting': waiting_count,
                'in_progress': in_progress_count,
                'completed_today': completed_today
            }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de cola para estación {station_id}: {e}")
            return {
                'queue_length': 0,
                'average_wait_time': 0,
                'tickets_today': 0
            }




    def call_next_patient(
        self,
        db: Session,
        station_id: int,
        service_type_id: Optional[int] = None,
        priority: Optional[int] = None
    ) -> Optional[Ticket]:
        """
        Llama al siguiente paciente en la cola

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            service_type_id: ID del tipo de servicio (opcional)
            priority: Prioridad mínima (opcional)

        Returns:
            Ticket llamado o None
        """
        try:
            station = self.get(db, id=station_id)
            if not station or not station.can_accept_more_patients():
                return None

            # Construir query para siguiente ticket
            query = db.query(Ticket).filter(
                Ticket.Status == 'waiting'
            )

            # Filtrar por estación o tipo de servicio
            if service_type_id:
                query = query.filter(Ticket.ServiceTypeId == service_type_id)
            else:
                query = query.filter(
                    or_(
                        Ticket.StationId == station_id,
                        Ticket.StationId.is_(None)
                    )
                )

            # Filtrar por prioridad si se especifica
            if priority:
                query = query.filter(Ticket.Priority >= priority)

            # Ordenar por prioridad y tiempo de espera
            next_ticket = query.order_by(
                Ticket.Priority.desc(),
                Ticket.CreatedAt.asc()
            ).first()

            if next_ticket:
                # Actualizar ticket
                next_ticket.Status = 'called'
                next_ticket.StationId = station_id
                next_ticket.CalledAt = datetime.now()

                # Actualizar estación
                station.CurrentTicketId = next_ticket.Id
                station.LastCallTime = datetime.now()

                db.commit()
                db.refresh(next_ticket)

                logger.info(f"Ticket {next_ticket.TicketNumber} llamado en estación {station.Code}")
                return next_ticket

            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error llamando siguiente paciente en estación {station_id}: {e}")
            return None

    def complete_current_ticket(
        self,
        db: Session,
        station_id: int,
        notes: Optional[str] = None
    ) -> bool:
        """
        Completa el ticket actual de una estación

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            notes: Notas adicionales

        Returns:
            True si se completó correctamente
        """
        try:
            station = self.get(db, id=station_id)
            if not station or not station.CurrentTicketId:
                return False

            # Buscar ticket actual
            current_ticket = db.query(Ticket).filter(
                Ticket.Id == station.CurrentTicketId
            ).first()

            if current_ticket:
                # Completar ticket
                current_ticket.Status = 'completed'
                current_ticket.CompletedAt = datetime.now()
                if notes:
                    current_ticket.Notes = notes

                # Calcular tiempo de servicio
                service_time = (datetime.now() - current_ticket.CalledAt).total_seconds() / 60

                # Actualizar estación
                station.CurrentTicketId = None
                station.increment_patient_count()
                station.update_average_wait_time(int(service_time))

                db.commit()

                logger.info(f"Ticket {current_ticket.TicketNumber} completado en estación {station.Code}")
                return True

            return False

        except Exception as e:
            db.rollback()
            logger.error(f"Error completando ticket en estación {station_id}: {e}")
            return False

    # ========================================
    # MÉTODOS DE ESTADÍSTICAS Y REPORTES
    # ========================================

    def get_station_stats(
            self,
            db: Session,
            station_id: int,
            target_date: date = None  # Cambiado de 'date' a 'target_date'
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas de una estación para una fecha específica

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            target_date: Fecha objetivo (por defecto hoy)

        Returns:
            Diccionario con estadísticas detalladas
        """
        try:
            station = self.get(db, id=station_id)
            if not station:
                return {}

            # Usar la fecha proporcionada o la fecha actual
            date_filter = target_date or date.today()

            # Crear rango de fecha para consultas
            date_start = datetime.combine(date_filter, datetime.min.time())
            date_end = datetime.combine(date_filter, datetime.max.time())

            # Tickets completados
            tickets_completed = db.query(func.count(Ticket.Id)).filter(
                Ticket.StationId == station_id,
                Ticket.Status == 'Completed',
                Ticket.CompletedAt >= date_start,
                Ticket.CompletedAt <= date_end
            ).scalar() or 0

            # Tiempo promedio de servicio (en minutos)
            avg_service_time_query = db.query(
                func.avg(
                    func.datediff(
                        literal_column("minute"),
                        Ticket.CalledAt,
                        Ticket.CompletedAt
                    )
                )
            ).filter(
                Ticket.StationId == station_id,
                Ticket.Status == 'Completed',
                Ticket.CompletedAt >= date_start,
                Ticket.CompletedAt <= date_end,
                Ticket.CalledAt.isnot(None)
            ).scalar()

            avg_service_time = float(avg_service_time_query) if avg_service_time_query else 0

            # Tiempo promedio de espera (en minutos)
            avg_wait_time_query = db.query(
                func.avg(
                    func.datediff(
                        literal_column("minute"),
                        Ticket.CreatedAt,
                        Ticket.CalledAt
                    )
                )
            ).filter(
                Ticket.StationId == station_id,
                Ticket.CalledAt >= date_start,
                Ticket.CalledAt <= date_end,
                Ticket.CalledAt.isnot(None)
            ).scalar()

            avg_wait_time = float(avg_wait_time_query) if avg_wait_time_query else 0

            # Tickets cancelados
            tickets_cancelled = db.query(func.count(Ticket.Id)).filter(
                Ticket.StationId == station_id,
                Ticket.Status == 'Cancelled',
                Ticket.UpdatedAt >= date_start,
                Ticket.UpdatedAt <= date_end
            ).scalar() or 0

            # Calcular tasa de eficiencia
            total_tickets = tickets_completed + tickets_cancelled
            efficiency_rate = (tickets_completed / total_tickets * 100) if total_tickets > 0 else 0

            return {
                'station_id': station_id,
                'station_name': station.Name,
                'date': date_filter.isoformat(),
                'tickets_completed': tickets_completed,
                'tickets_cancelled': tickets_cancelled,
                'average_service_time': round(avg_service_time, 2),
                'average_wait_time': round(avg_wait_time, 2),
                'efficiency_rate': round(efficiency_rate, 2),
                'total_tickets': total_tickets
            }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de estación {station_id}: {e}")
            return {
                'station_id': station_id,
                'tickets_completed': 0,
                'average_service_time': 0,
                'average_wait_time': 0,
                'efficiency_rate': 0
            }

    def get_stations_with_stats(
            self,
            db: Session,
            include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obtiene todas las estaciones con sus estadísticas

        Args:
            db: Sesión de base de datos
            include_inactive: Incluir estaciones inactivas

        Returns:
            Lista de estaciones con estadísticas
        """
        try:
            query = db.query(Station)

            if not include_inactive:
                query = query.filter(Station.IsActive == True)

            stations = query.all()

            result = []
            for station in stations:
                # Obtener estadísticas básicas
                stats = self.get_queue_stats(db, station.Id)

                # Crear diccionario con datos de la estación
                station_dict = {
                    'Id': station.Id,
                    'Name': station.Name,
                    'Code': station.Code,
                    'Description': station.Description,
                    'ServiceTypeId': station.ServiceTypeId,
                    'Location': station.Location,
                    'Status': station.Status,
                    'CurrentTicketId': str(station.CurrentTicketId) if station.CurrentTicketId else None,
                    'IsActive': station.IsActive,
                    'CreatedAt': station.CreatedAt.isoformat() if station.CreatedAt else None,
                    'UpdatedAt': station.UpdatedAt.isoformat() if station.UpdatedAt else None,
                    # Agregar las estadísticas IMPORTANTES
                    'queue_length': stats.get('queue_length', 0),
                    'average_wait_time': stats.get('average_wait_time', 0),
                    'tickets_today': stats.get('tickets_today', 0),
                    'waiting': stats.get('waiting', 0),
                    'in_progress': stats.get('in_progress', 0),
                    'completed_today': stats.get('completed_today', 0)
                }
                result.append(station_dict)

            return result

        except Exception as e:
            logger.error(f"Error obteniendo estaciones con estadísticas: {e}")
            return []

    def get_performance_report(
            self,
            db: Session,
            station_id: int,
            start_date: date,
            end_date: date
    ) -> Dict[str, Any]:
        """
        Genera reporte de rendimiento de una estación

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Reporte de rendimiento
        """
        try:
            station = self.get(db, id=station_id)
            if not station:
                return {}

            # Recopilar métricas por día
            daily_metrics = []
            current_date = start_date

            while current_date <= end_date:
                # Usar target_date en lugar de date
                day_stats = self.get_station_stats(db, station_id, target_date=current_date)

                # Asegurar que tiene los campos necesarios
                if day_stats:
                    daily_metrics.append({
                        'date': current_date.isoformat(),
                        'tickets_completed': day_stats.get('tickets_completed', 0),
                        'average_service_time': day_stats.get('average_service_time', 0),
                        'average_wait_time': day_stats.get('average_wait_time', 0),
                        'efficiency_rate': day_stats.get('efficiency_rate', 0)
                    })

                current_date += timedelta(days=1)

            # Calcular promedios solo si hay métricas
            if daily_metrics:
                total_tickets = sum(m['tickets_completed'] for m in daily_metrics)
                avg_service_time = sum(m['average_service_time'] for m in daily_metrics) / len(daily_metrics)
                avg_wait_time = sum(m['average_wait_time'] for m in daily_metrics) / len(daily_metrics)
                avg_efficiency = sum(m['efficiency_rate'] for m in daily_metrics) / len(daily_metrics)
            else:
                total_tickets = 0
                avg_service_time = 0
                avg_wait_time = 0
                avg_efficiency = 0

            return {
                'station_id': station_id,
                'station_name': station.Name,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': len(daily_metrics)
                },
                'summary': {
                    'total_tickets_completed': total_tickets,
                    'average_tickets_per_day': round(total_tickets / len(daily_metrics), 2) if daily_metrics else 0,
                    'average_service_time': round(avg_service_time, 2),
                    'average_wait_time': round(avg_wait_time, 2),
                    'average_efficiency': round(avg_efficiency, 2)
                },
                'daily_metrics': daily_metrics,
                'recommendations': []  # Simplificado por ahora
            }

        except Exception as e:
            logger.error(f"Error generando reporte de rendimiento para estación {station_id}: {e}")
            return {
                'station_id': station_id,
                'station_name': '',
                'period': {},
                'summary': {},
                'daily_metrics': [],
                'recommendations': []
            }

    def soft_delete(self, db: Session, *, id: int) -> Optional[Station]:
        """
        Eliminación lógica de una estación (soft delete)

        Args:
            db: Sesión de base de datos
            id: ID de la estación

        Returns:
            Station desactivada o None si no existe
        """
        try:
            station = self.get(db, id=id)
            if not station:
                return None

            # Soft delete: solo marcar como inactiva
            station.IsActive = False
            station.Status = 'Offline'  # Opcional: cambiar estado también

            db.commit()
            db.refresh(station)

            logger.info(f"Estación {station.Code} desactivada (soft delete)")
            return station

        except Exception as e:
            db.rollback()
            logger.error(f"Error en soft delete de estación {id}: {e}")
            return None


    # ========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ========================================

    def _generate_recommendations(
        self,
        station: Station,
        metrics: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Genera recomendaciones basadas en métricas

        Args:
            station: Estación
            metrics: Lista de métricas diarias

        Returns:
            Lista de recomendaciones
        """
        recommendations = []

        if not metrics:
            return recommendations

        # Analizar eficiencia
        avg_efficiency = sum(m['efficiency_rate'] for m in metrics) / len(metrics)
        if avg_efficiency < 70:
            recommendations.append("Considerar optimización de procesos para mejorar eficiencia")
        elif avg_efficiency > 95:
            recommendations.append("Excelente eficiencia, considerar compartir mejores prácticas")

        # Analizar tiempo de espera
        avg_wait = sum(m['average_wait_time'] for m in metrics) / len(metrics)
        if avg_wait > 30:
            recommendations.append("Tiempo de espera elevado, considerar añadir más personal en horas pico")

        # Analizar tiempo de servicio
        avg_service = sum(m['average_service_time'] for m in metrics) / len(metrics)
        if avg_service > station.AverageServiceTimeMinutes * 1.5:
            recommendations.append("Tiempo de servicio excede lo esperado, revisar procesos o capacitación")

        return recommendations


# ========================================
# INSTANCIA SINGLETON DEL CRUD
# ========================================

station_crud = CRUDStation(Station)