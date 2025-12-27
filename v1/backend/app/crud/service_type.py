"""
Operaciones CRUD específicas para el modelo ServiceType
100% compatible con SQLAlchemy ServiceType model y schemas Pydantic
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, cast, Date
from datetime import datetime, timedelta
import logging

from app.crud.base import CRUDBase
from app.models.service_type import ServiceType
from app.schemas.service_type import ServiceTypeCreate, ServiceTypeUpdate

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)


# ========================================
# CLASE CRUD SERVICE TYPE
# ========================================

class CRUDServiceType(CRUDBase[ServiceType, ServiceTypeCreate, ServiceTypeUpdate]):
    """
    Operaciones CRUD específicas para tipos de servicios
    Hereda operaciones básicas de CRUDBase y agrega funcionalidades específicas
    """

    def get_by_code(self, db: Session, *, code: str) -> Optional[ServiceType]:
        """
        Busca un tipo de servicio por su código único

        Args:
            db: Sesión de base de datos
            code: Código único del servicio (ej: LAB, RES, MUE)

        Returns:
            ServiceType: Tipo de servicio encontrado o None
        """
        try:
            # Normalizar código (igual que en modelo SQLAlchemy)
            normalized_code = code.upper().strip()

            return db.query(ServiceType).filter(
                and_(
                    ServiceType.Code == normalized_code,
                    ServiceType.IsActive == True
                )
            ).first()

        except Exception as e:
            logger.error(f"Error buscando tipo de servicio por código {code}: {e}")
            return None

    def get_by_priority(
            self,
            db: Session,
            *,
            priority: int,
            limit: int = 50
    ) -> List[ServiceType]:
        """
        Obtiene tipos de servicios por nivel de prioridad

        Args:
            db: Sesión de base de datos
            priority: Nivel de prioridad (1-5)
            limit: Límite de resultados

        Returns:
            List[ServiceType]: Lista de servicios con esa prioridad
        """
        try:
            if priority < 1 or priority > 5:
                logger.warning(f"Prioridad inválida: {priority}")
                return []

            return db.query(ServiceType).filter(
                and_(
                    ServiceType.Priority == priority,
                    ServiceType.IsActive == True
                )
            ).order_by(ServiceType.Name).limit(limit).all()

        except Exception as e:
            logger.error(f"Error obteniendo servicios por prioridad {priority}: {e}")
            return []

    def get_high_priority_services(self, db: Session) -> List[ServiceType]:
        """
        Obtiene servicios de alta prioridad (1 y 2)

        Args:
            db: Sesión de base de datos

        Returns:
            List[ServiceType]: Servicios de alta prioridad
        """
        try:
            return db.query(ServiceType).filter(
                and_(
                    ServiceType.Priority.in_([1, 2]),
                    ServiceType.IsActive == True
                )
            ).order_by(ServiceType.Priority, ServiceType.Name).all()

        except Exception as e:
            logger.error(f"Error obteniendo servicios de alta prioridad: {e}")
            return []

    def search_services(
            self,
            db: Session,
            *,
            query: str,
            limit: int = 20
    ) -> List[ServiceType]:
        """
        Búsqueda general de servicios por nombre o código

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda (nombre o código)
            limit: Límite de resultados

        Returns:
            List[ServiceType]: Lista de servicios encontrados
        """
        try:
            search_term = f"%{query.strip()}%"

            return db.query(ServiceType).filter(
                and_(
                    ServiceType.IsActive == True,
                    or_(
                        ServiceType.Name.like(search_term),
                        ServiceType.Code.like(search_term),
                        ServiceType.Description.like(search_term)
                    )
                )
            ).order_by(ServiceType.Priority, ServiceType.Name).limit(limit).all()

        except Exception as e:
            logger.error(f"Error en búsqueda de servicios '{query}': {e}")
            return []

    def get_services_with_stats(
            self,
            db: Session,
            *,
            include_inactive: bool = False
    ) -> List[ServiceType]:
        """
        Obtiene servicios con estadísticas de colas y estaciones

        Args:
            db: Sesión de base de datos
            include_inactive: Si incluir servicios inactivos

        Returns:
            List[ServiceType]: Servicios con estadísticas cargadas
        """
        try:
            query = db.query(ServiceType)

            if not include_inactive:
                query = query.filter(ServiceType.IsActive == True)

            services = query.order_by(ServiceType.Priority, ServiceType.Name).all()

            # Las estadísticas se cargan automáticamente a través de las propiedades
            # del modelo SQLAlchemy como station_count, active_station_count, etc.

            return services

        except Exception as e:
            logger.error(f"Error obteniendo servicios con estadísticas: {e}")
            return []

    def get_services_by_average_time(
            self,
            db: Session,
            *,
            min_minutes: Optional[int] = None,
            max_minutes: Optional[int] = None,
            limit: int = 50
    ) -> List[ServiceType]:
        """
        Obtiene servicios por rango de tiempo promedio de atención

        Args:
            db: Sesión de base de datos
            min_minutes: Tiempo mínimo en minutos
            max_minutes: Tiempo máximo en minutos
            limit: Límite de resultados

        Returns:
            List[ServiceType]: Servicios en el rango de tiempo
        """
        try:
            query = db.query(ServiceType).filter(ServiceType.IsActive == True)

            if min_minutes is not None:
                query = query.filter(ServiceType.AverageTimeMinutes >= min_minutes)

            if max_minutes is not None:
                query = query.filter(ServiceType.AverageTimeMinutes <= max_minutes)

            return query.order_by(ServiceType.AverageTimeMinutes).limit(limit).all()

        except Exception as e:
            logger.error(f"Error obteniendo servicios por tiempo promedio: {e}")
            return []

    def validate_unique_code(self, db: Session, *, code: str, exclude_id: Optional[int] = None) -> bool:
        """
        Valida que un código sea único

        Args:
            db: Sesión de base de datos
            code: Código a validar
            exclude_id: ID a excluir de la validación (para updates)

        Returns:
            bool: True si el código es único
        """
        try:
            normalized_code = code.upper().strip()
            query = db.query(ServiceType).filter(ServiceType.Code == normalized_code)

            if exclude_id:
                query = query.filter(ServiceType.Id != exclude_id)

            existing = query.first()
            return existing is None

        except Exception as e:
            logger.error(f"Error validando código único {code}: {e}")
            return False

    def validate_unique_ticket_prefix(
            self,
            db: Session,
            *,
            prefix: str,
            exclude_id: Optional[int] = None
    ) -> bool:
        """
        Valida que un prefijo de ticket sea único

        Args:
            db: Sesión de base de datos
            prefix: Prefijo a validar
            exclude_id: ID a excluir de la validación

        Returns:
            bool: True si el prefijo es único
        """
        try:
            normalized_prefix = prefix.upper().strip()
            query = db.query(ServiceType).filter(ServiceType.TicketPrefix == normalized_prefix)

            if exclude_id:
                query = query.filter(ServiceType.Id != exclude_id)

            existing = query.first()
            return existing is None

        except Exception as e:
            logger.error(f"Error validando prefijo único {prefix}: {e}")
            return False

    def create_with_validation(self, db: Session, *, obj_in: ServiceTypeCreate) -> ServiceType:
        """
        Crea un tipo de servicio con validaciones adicionales

        Args:
            db: Sesión de base de datos
            obj_in: Datos del servicio a crear

        Returns:
            ServiceType: Servicio creado

        Raises:
            ValueError: Si las validaciones fallan
        """
        try:
            # Validar código único
            if not self.validate_unique_code(db, code=obj_in.Code):
                raise ValueError(f"El código {obj_in.Code} ya está en uso")

            # Validar prefijo único
            if not self.validate_unique_ticket_prefix(db, prefix=obj_in.TicketPrefix):
                raise ValueError(f"El prefijo {obj_in.TicketPrefix} ya está en uso")

            # Crear usando el método base
            service_type = self.create(db, obj_in=obj_in)

            logger.info(f"Tipo de servicio creado: {service_type.Name} ({service_type.Code})")
            return service_type

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creando tipo de servicio: {e}")
            raise

    def update_with_validation(
            self,
            db: Session,
            *,
            db_obj: ServiceType,
            obj_in: ServiceTypeUpdate
    ) -> ServiceType:
        """
        Actualiza un tipo de servicio con validaciones

        Args:
            db: Sesión de base de datos
            db_obj: Objeto existente
            obj_in: Datos de actualización

        Returns:
            ServiceType: Servicio actualizado

        Raises:
            ValueError: Si las validaciones fallan
        """
        try:
            # Validar código único si se está cambiando
            if obj_in.Code and obj_in.Code != db_obj.Code:
                if not self.validate_unique_code(db, code=obj_in.Code, exclude_id=db_obj.Id):
                    raise ValueError(f"El código {obj_in.Code} ya está en uso")

            # Validar prefijo único si se está cambiando
            if obj_in.TicketPrefix and obj_in.TicketPrefix != db_obj.TicketPrefix:
                if not self.validate_unique_ticket_prefix(
                    db, prefix=obj_in.TicketPrefix, exclude_id=db_obj.Id
                ):
                    raise ValueError(f"El prefijo {obj_in.TicketPrefix} ya está en uso")

            # Actualizar usando el método base
            service_type = self.update(db, db_obj=db_obj, obj_in=obj_in)

            logger.info(f"Tipo de servicio actualizado: {service_type.Name} ({service_type.Code})")
            return service_type

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error actualizando tipo de servicio: {e}")
            raise

    def get_dashboard_stats(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene estadísticas para el dashboard administrativo

        Args:
            db: Sesión de base de datos

        Returns:
            Dict[str, Any]: Estadísticas de tipos de servicios
        """
        try:
            # Servicios totales
            total_services = self.get_count(db, active_only=True)

            # Servicios por prioridad
            priority_stats = {}
            for priority in range(1, 6):
                count = db.query(ServiceType).filter(
                    and_(
                        ServiceType.Priority == priority,
                        ServiceType.IsActive == True
                    )
                ).count()
                priority_stats[f"priority_{priority}"] = count

            # Tiempo promedio general
            avg_time_query = db.query(
                func.avg(ServiceType.AverageTimeMinutes).label('avg_time')
            ).filter(ServiceType.IsActive == True).scalar()

            avg_time = float(avg_time_query) if avg_time_query else 0.0

            # Servicios con más estaciones
            services_with_stations = db.query(ServiceType).filter(
                ServiceType.IsActive == True
            ).all()

            # Calcular estadísticas de estaciones (usando propiedades del modelo)
            total_stations = sum(s.station_count for s in services_with_stations)
            active_stations = sum(s.active_station_count for s in services_with_stations)

            return {
                "total_services": total_services,
                "priority_distribution": priority_stats,
                "average_service_time": round(avg_time, 2),
                "total_stations": total_stations,
                "active_stations": active_stations,
                "services_with_high_priority": priority_stats.get("priority_1", 0) + priority_stats.get("priority_2", 0),
                "utilization_rate": round((active_stations / total_stations * 100), 2) if total_stations > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del dashboard: {e}")
            return {
                "total_services": 0,
                "priority_distribution": {},
                "average_service_time": 0.0,
                "total_stations": 0,
                "active_stations": 0,
                "services_with_high_priority": 0,
                "utilization_rate": 0.0
            }

    def initialize_default_services(self, db: Session) -> List[ServiceType]:
        """
        Inicializa los tipos de servicios por defecto si no existen

        Args:
            db: Sesión de base de datos

        Returns:
            List[ServiceType]: Servicios creados o existentes
        """
        try:
            # Verificar si ya existen servicios
            existing_count = self.get_count(db, active_only=False)
            if existing_count > 0:
                logger.info("Ya existen tipos de servicios configurados")
                return self.get_active(db)

            # Crear servicios por defecto usando el método del modelo
            default_services_data = ServiceType.get_default_service_types()
            created_services = []

            for service_data in default_services_data:
                try:
                    # Convertir a schema para validación
                    from app.schemas.service_type import ServiceTypeCreate
                    service_create = ServiceTypeCreate(**service_data)

                    # Crear servicio
                    service = self.create_with_validation(db, obj_in=service_create)
                    created_services.append(service)

                except Exception as e:
                    logger.error(f"Error creando servicio por defecto {service_data.get('Name')}: {e}")

            logger.info(f"{len(created_services)} tipos de servicios por defecto creados")
            return created_services

        except Exception as e:
            logger.error(f"Error inicializando servicios por defecto: {e}")
            return []

    def get_service_performance(
            self,
            db: Session,
            *,
            service_type_id: int,
            days: int = 30
    ) -> Dict[str, Any]:
        """
        Obtiene métricas de rendimiento de un servicio específico

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            days: Días hacia atrás para el análisis

        Returns:
            Dict[str, Any]: Métricas de rendimiento
        """
        try:
            from app.models.daily_metrics import DailyMetrics
            from app.models.ticket import Ticket
            from datetime import date

            service = self.get(db, id=service_type_id)
            if not service:
                return {"error": "Servicio no encontrado"}

            # Obtener métricas de los últimos días
            start_date = date.today() - timedelta(days=days)

            # Tickets totales del período
            total_tickets = db.query(Ticket).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.CreatedAt >= start_date
                )
            ).count()

            # Tickets completados
            completed_tickets = db.query(Ticket).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.Status == 'Completed',
                    Ticket.CreatedAt >= start_date
                )
            ).count()

            # Tiempo promedio de espera
            avg_wait_query = db.query(
                func.avg(Ticket.ActualWaitTime).label('avg_wait')
            ).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.ActualWaitTime.isnot(None),
                    Ticket.CreatedAt >= start_date
                )
            ).scalar()

            avg_wait_time = float(avg_wait_query) if avg_wait_query else 0.0

            # Calcular tasa de completación
            completion_rate = (completed_tickets / total_tickets * 100) if total_tickets > 0 else 0

            return {
                "service_id": service_type_id,
                "service_name": service.Name,
                "service_code": service.Code,
                "period_days": days,
                "total_tickets": total_tickets,
                "completed_tickets": completed_tickets,
                "completion_rate": round(completion_rate, 2),
                "average_wait_time": round(avg_wait_time, 2),
                "daily_average": round(total_tickets / days, 2) if days > 0 else 0,
                "current_queue_length": service.get_current_queue_length(),
                "estimated_wait_time": service.get_estimated_wait_time()
            }

        except Exception as e:
            logger.error(f"Error obteniendo rendimiento del servicio {service_type_id}: {e}")
            return {"error": str(e)}

    # Agregar estos métodos a la clase CRUDServiceType en app/crud/service_type.py

    def remove(self, db: Session, *, id: int, hard_delete: bool = False) -> Optional[ServiceType]:
        """
        Elimina o desactiva un tipo de servicio

        Args:
            db: Sesión de base de datos
            id: ID del servicio a eliminar
            hard_delete: Si True hace eliminación física, si False hace soft delete

        Returns:
            ServiceType: Servicio eliminado/desactivado o None
        """
        try:
            service = self.get(db, id=id)
            if not service:
                return None

            if hard_delete:
                # Verificar si hay referencias antes de eliminar
                from app.models.station import Station
                from app.models.ticket import Ticket

                # Verificar estaciones asociadas
                stations = db.query(Station).filter(Station.ServiceTypeId == id).first()
                if stations:
                    logger.warning(f"No se puede eliminar servicio {id}, tiene estaciones asociadas")
                    raise ValueError("No se puede eliminar el servicio, tiene estaciones asociadas")

                # Verificar tickets asociados
                tickets = db.query(Ticket).filter(Ticket.ServiceTypeId == id).first()
                if tickets:
                    logger.warning(f"No se puede eliminar servicio {id}, tiene tickets asociados")
                    raise ValueError("No se puede eliminar el servicio, tiene tickets asociados")

                # Eliminación física
                db.delete(service)
                db.commit()
                logger.warning(f"ServiceType {id} eliminado físicamente")
            else:
                # Soft delete (desactivar)
                service.IsActive = False
                if hasattr(service, 'UpdatedAt'):
                    service.UpdatedAt = datetime.now()
                db.add(service)
                db.commit()
                db.refresh(service)
                logger.info(f"ServiceType {id} desactivado (soft delete)")

            return service

        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error eliminando ServiceType {id}: {e}")
            raise

    def search(
            self,
            db: Session,
            *,
            search_term: str,
            filters: Optional[Dict[str, Any]] = None,
            limit: int = 50
    ) -> List[ServiceType]:
        """
        Busca tipos de servicios por término y filtros opcionales

        Args:
            db: Sesión de base de datos
            search_term: Término de búsqueda
            filters: Filtros adicionales (priority, is_active, etc.)
            limit: Límite de resultados

        Returns:
            List[ServiceType]: Lista de servicios que coinciden
        """
        try:
            query = db.query(ServiceType)

            # Aplicar búsqueda por texto si hay término
            if search_term:
                search_pattern = f"%{search_term}%"
                query = query.filter(
                    or_(
                        ServiceType.Name.ilike(search_pattern),
                        ServiceType.Code.ilike(search_pattern),
                        ServiceType.Description.ilike(search_pattern)
                    )
                )

            # Aplicar filtros adicionales
            if filters:
                if "priority" in filters and filters["priority"] is not None:
                    query = query.filter(ServiceType.Priority == filters["priority"])

                if "is_active" in filters and filters["is_active"] is not None:
                    query = query.filter(ServiceType.IsActive == filters["is_active"])

                if "min_time" in filters and filters["min_time"] is not None:
                    query = query.filter(ServiceType.AverageTimeMinutes >= filters["min_time"])

                if "max_time" in filters and filters["max_time"] is not None:
                    query = query.filter(ServiceType.AverageTimeMinutes <= filters["max_time"])

            # Ordenar por relevancia (prioridad y nombre)
            query = query.order_by(ServiceType.Priority, ServiceType.Name)

            return query.limit(limit).all()

        except Exception as e:
            logger.error(f"Error buscando servicios con término '{search_term}': {e}")
            return []

    def get_by_prefix(self, db: Session, *, prefix: str) -> Optional[ServiceType]:
        """
        Busca un tipo de servicio por su prefijo de ticket

        Args:
            db: Sesión de base de datos
            prefix: Prefijo del ticket

        Returns:
            ServiceType: Tipo de servicio encontrado o None
        """
        try:
            normalized_prefix = prefix.upper().strip()

            return db.query(ServiceType).filter(
                and_(
                    ServiceType.TicketPrefix == normalized_prefix,
                    ServiceType.IsActive == True
                )
            ).first()

        except Exception as e:
            logger.error(f"Error buscando servicio por prefijo {prefix}: {e}")
            return None

    def count_by_priority(self, db: Session, *, priority: int) -> int:
        """
        Cuenta servicios por nivel de prioridad

        Args:
            db: Sesión de base de datos
            priority: Nivel de prioridad (1-5)

        Returns:
            int: Cantidad de servicios con esa prioridad
        """
        try:
            return db.query(ServiceType).filter(
                and_(
                    ServiceType.Priority == priority,
                    ServiceType.IsActive == True
                )
            ).count()

        except Exception as e:
            logger.error(f"Error contando servicios con prioridad {priority}: {e}")
            return 0

    def get_services_with_stats(
            self,
            db: Session,
            *,
            include_inactive: bool = False
    ) -> List[ServiceType]:
        """
        Obtiene servicios con estadísticas adicionales

        Args:
            db: Sesión de base de datos
            include_inactive: Incluir servicios inactivos

        Returns:
            List[ServiceType]: Servicios con estadísticas
        """
        try:
            from app.models.ticket import Ticket
            from app.models.station import Station
            from sqlalchemy import case, literal_column

            query = db.query(
                ServiceType,
                func.count(Ticket.Id).label('ticket_count'),
                func.count(Station.Id).label('station_count')
            ).outerjoin(
                Ticket, Ticket.ServiceTypeId == ServiceType.Id
            ).outerjoin(
                Station, Station.ServiceTypeId == ServiceType.Id
            ).group_by(ServiceType.Id)

            if not include_inactive:
                query = query.filter(ServiceType.IsActive == True)

            results = query.all()

            # Agregar estadísticas como atributos dinámicos
            services = []
            for service, ticket_count, station_count in results:
                service.ticket_count = ticket_count
                service.station_count = station_count
                services.append(service)

            return services

        except Exception as e:
            logger.error(f"Error obteniendo servicios con estadísticas: {e}")
            return []

    def get_dashboard_stats(self, db: Session) -> Dict[str, Any]:
        """
        Obtiene estadísticas mejoradas para el dashboard administrativo

        Args:
            db: Sesión de base de datos

        Returns:
            Dict[str, Any]: Estadísticas de tipos de servicios
        """
        try:
            # Servicios totales
            total_services = self.get_count(db, active_only=True)

            # Servicios por prioridad - CORREGIDO
            priority_distribution = {}
            for priority in range(1, 6):
                count = db.query(ServiceType).filter(
                    and_(
                        ServiceType.Priority == priority,
                        ServiceType.IsActive == True
                    )
                ).count()
                priority_distribution[priority] = count

            # Estadísticas de tiempo promedio
            time_stats = db.query(
                func.min(ServiceType.AverageTimeMinutes).label('min'),
                func.max(ServiceType.AverageTimeMinutes).label('max'),
                func.avg(ServiceType.AverageTimeMinutes).label('avg')
            ).filter(ServiceType.IsActive == True).first()

            average_time_stats = {
                'min': time_stats.min if time_stats else 0,
                'max': time_stats.max if time_stats else 0,
                'avg': float(time_stats.avg) if time_stats and time_stats.avg else 0
            }

            # Servicios más utilizados (por tickets)
            from app.models.ticket import Ticket

            most_used = db.query(
                ServiceType.Name,
                ServiceType.Code,
                func.count(Ticket.Id).label('usage_count')
            ).join(
                Ticket, Ticket.ServiceTypeId == ServiceType.Id
            ).filter(
                ServiceType.IsActive == True
            ).group_by(
                ServiceType.Id, ServiceType.Name, ServiceType.Code
            ).order_by(
                desc('usage_count')
            ).limit(5).all()

            most_used_services = [
                {
                    'name': name,
                    'code': code,
                    'usage_count': count
                }
                for name, code, count in most_used
            ]

            return {
                'total_services': total_services,
                'priority_distribution': priority_distribution,
                'average_time_stats': average_time_stats,
                'most_used_services': most_used_services,
                'services_by_status': {
                    'active': total_services,
                    'inactive': self.get_count(db, active_only=False) - total_services
                }
            }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del dashboard: {e}")
            return {
                'total_services': 0,
                'priority_distribution': {},
                'average_time_stats': {'min': 0, 'max': 0, 'avg': 0},
                'most_used_services': [],
                'services_by_status': {'active': 0, 'inactive': 0}
            }

    def get_service_performance(
            self,
            db: Session,
            *,
            service_type_id: int,
            days: int = 30
    ) -> Dict[str, Any]:
        """
        Obtiene métricas de rendimiento mejoradas de un servicio específico

        Args:
            db: Sesión de base de datos
            service_type_id: ID del tipo de servicio
            days: Días hacia atrás para el análisis

        Returns:
            Dict[str, Any]: Métricas de rendimiento
        """
        try:
            from app.models.ticket import Ticket
            from app.models.station import Station
            from datetime import date

            service = self.get(db, id=service_type_id)
            if not service:
                return {"error": "Servicio no encontrado"}

            # Fecha de inicio para el análisis
            start_date = datetime.now() - timedelta(days=days)

            # Total de tickets en el período
            total_tickets = db.query(func.count(Ticket.Id)).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.CreatedAt >= start_date
                )
            ).scalar() or 0

            # Tickets por estado
            tickets_by_status = db.query(
                Ticket.Status,
                func.count(Ticket.Id).label('count')
            ).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.CreatedAt >= start_date
                )
            ).group_by(Ticket.Status).all()

            status_distribution = {
                status: count for status, count in tickets_by_status
            }

            # Tiempo promedio de espera real
            avg_wait_time = db.query(
                func.avg(Ticket.EstimatedWaitTime)
            ).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.CreatedAt >= start_date,
                    Ticket.Status == 'Completed'
                )
            ).scalar()

            # Tickets por día
            daily_tickets = db.query(
                #func.date(Ticket.CreatedAt).label('date'),
                cast(Ticket.CreatedAt, Date).label('date'),
                func.count(Ticket.Id).label('count')
            ).filter(
                and_(
                    Ticket.ServiceTypeId == service_type_id,
                    Ticket.CreatedAt >= start_date
                )
            ).group_by(
                func.date(Ticket.CreatedAt)
            ).order_by('date').all()

            # Estaciones asignadas
            stations_count = db.query(Station).filter(
                Station.ServiceTypeId == service_type_id
            ).count()

            # Calcular métricas adicionales
            avg_tickets_per_day = total_tickets / days if days > 0 else 0

            return {
                'service': {
                    'id': service.Id,
                    'name': service.Name,
                    'code': service.Code
                },
                'period_days': days,
                'total_tickets': total_tickets,
                'status_distribution': status_distribution,
                'average_wait_time': float(avg_wait_time) if avg_wait_time else 0,
                'average_service_time': service.AverageTimeMinutes,
                'daily_distribution': [
                    {'date': str(date), 'count': count}
                    for date, count in daily_tickets
                ],
                'avg_tickets_per_day': round(avg_tickets_per_day, 2),
                'stations_assigned': stations_count,
                'performance_rating': self._calculate_performance_rating(
                    avg_wait_time, service.AverageTimeMinutes
                )
            }

        except Exception as e:
            logger.error(f"Error obteniendo rendimiento del servicio {service_type_id}: {e}")
            return {"error": f"Error al obtener métricas: {str(e)}"}

    def _calculate_performance_rating(
            self,
            actual_wait_time: Optional[float],
            expected_time: int
    ) -> str:
        """
        Calcula la calificación de rendimiento

        Args:
            actual_wait_time: Tiempo de espera real promedio
            expected_time: Tiempo esperado configurado

        Returns:
            str: Calificación (Excelente, Bueno, Regular, Necesita mejora)
        """
        if not actual_wait_time:
            return "Sin datos"

        ratio = actual_wait_time / expected_time if expected_time > 0 else 1

        if ratio <= 0.8:
            return "Excelente"
        elif ratio <= 1.0:
            return "Bueno"
        elif ratio <= 1.5:
            return "Regular"
        else:
            return "Necesita mejora"

    def bulk_update_priority(
            self,
            db: Session,
            *,
            service_ids: List[int],
            new_priority: int
    ) -> int:
        """
        Actualiza la prioridad de múltiples servicios

        Args:
            db: Sesión de base de datos
            service_ids: Lista de IDs de servicios
            new_priority: Nueva prioridad (1-5)

        Returns:
            int: Cantidad de servicios actualizados
        """
        try:
            if new_priority < 1 or new_priority > 5:
                raise ValueError("La prioridad debe estar entre 1 y 5")

            updated = db.query(ServiceType).filter(
                ServiceType.Id.in_(service_ids)
            ).update(
                {
                    ServiceType.Priority: new_priority,
                    ServiceType.UpdatedAt: datetime.now()
                },
                synchronize_session=False
            )

            db.commit()
            logger.info(f"Actualizada prioridad de {updated} servicios a {new_priority}")
            return updated

        except Exception as e:
            db.rollback()
            logger.error(f"Error actualizando prioridad masiva: {e}")
            raise

    def get_available_prefixes(self, db: Session) -> List[str]:
        """
        Obtiene lista de prefijos disponibles (no usados)

        Args:
            db: Sesión de base de datos

        Returns:
            List[str]: Lista de prefijos disponibles
        """
        try:
            # Todos los prefijos posibles (letras A-Z y combinaciones comunes)
            all_prefixes = [chr(i) for i in range(65, 91)]  # A-Z

            # Prefijos ya usados
            used_prefixes = db.query(ServiceType.TicketPrefix).filter(
                ServiceType.IsActive == True
            ).all()

            used_set = {prefix[0] for prefix in used_prefixes if prefix[0]}

            # Retornar los disponibles
            available = [p for p in all_prefixes if p not in used_set]

            return available[:10]  # Retornar máximo 10 sugerencias

        except Exception as e:
            logger.error(f"Error obteniendo prefijos disponibles: {e}")
            return []


# ========================================
# INSTANCIA GLOBAL
# ========================================

service_type_crud = CRUDServiceType(ServiceType)