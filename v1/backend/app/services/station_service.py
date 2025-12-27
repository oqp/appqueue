"""
Servicio de lógica de negocio para gestión de estaciones/ventanillas
Compatible con toda la estructura existente del proyecto
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, time, date
import logging
import asyncio
from enum import Enum
import json

from app.crud.station import station_crud
from app.crud.ticket import ticket_crud
from app.crud.user import user_crud
from app.crud.service_type import service_type_crud
from app.models.station import Station
from app.models.ticket import Ticket
from app.models.user import User
from app.models.service_type import ServiceType
from app.schemas.station import (
    StationCreate, StationUpdate, StationStats, StationDashboard,
    StationStatus, CallNextPatientResponse, TransferPatientsRequest,
    StationPerformanceReport
)
from app.schemas.ticket import TicketResponse
from app.core.redis import cache_manager
from app.services.notification_service import notification_service
from app.websocket.connection_manager import websocket_manager

# ========================================
# CONFIGURACIÓN
# ========================================

logger = logging.getLogger(__name__)


class LoadBalanceStrategy(str, Enum):
    """Estrategias para balanceo de carga"""
    ROUND_ROBIN = "round_robin"
    LEAST_QUEUE = "least_queue"
    LEAST_WAIT_TIME = "least_wait_time"
    SERVICE_BASED = "service_based"
    MIXED = "mixed"


# ========================================
# CLASE PRINCIPAL DEL SERVICIO
# ========================================

class StationService:
    """
    Servicio principal para gestión de estaciones
    Maneja lógica de negocio compleja, balanceo de carga y optimización
    """

    def __init__(self):
        """Inicializa el servicio de estaciones"""
        self.load_balance_strategy = LoadBalanceStrategy.MIXED
        self.max_queue_threshold = 15  # Umbral máximo de cola
        self.auto_rebalance_enabled = True
        self.notification_enabled = True

    # ========================================
    # MÉTODOS DE CREACIÓN Y CONFIGURACIÓN
    # ========================================

    async def create_station_with_setup(
            self,
            db: Session,
            station_data: StationCreate,
            auto_assign_services: bool = True
    ) -> Station:
        """
        Crea una nueva estación con configuración automática

        Args:
            db: Sesión de base de datos
            station_data: Datos de la estación
            auto_assign_services: Asignar servicios automáticamente

        Returns:
            Station: Estación creada y configurada
        """
        try:
            logger.info(f"Creando estación con configuración: {station_data.Name}")

            # Crear estación usando CRUD
            station = station_crud.create_with_validation(db, obj_in=station_data)

            # Configuración automática de servicios si no se especificaron
            if auto_assign_services and not station_data.ServiceTypeIds:
                await self._auto_assign_services(db, station)

            # Configurar horarios por defecto si no se especificaron
            if not station_data.WorkingHours:
                await self._setup_default_working_hours(db, station)

            # Notificar creación via WebSocket
            if websocket_manager:
                await websocket_manager.broadcast_station_update({
                    "action": "station_created",
                    "station": station.to_dict()
                })

            logger.info(f"Estación creada exitosamente: {station.Name} ({station.Code})")
            return station

        except Exception as e:
            logger.error(f"Error creando estación con configuración: {e}")
            raise

    async def assign_user_with_validation(
            self,
            db: Session,
            station_id: int,
            user_id: str,
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None,
            validate_workload: bool = True
    ) -> Tuple[bool, str, Optional[Station]]:
        """
        Asigna usuario a estación con validaciones avanzadas

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            user_id: ID del usuario
            start_time: Hora de inicio
            end_time: Hora de fin
            validate_workload: Validar carga de trabajo

        Returns:
            Tuple[bool, str, Station]: (éxito, mensaje, estación)
        """
        try:
            # Validar que la estación existe y está disponible
            station = station_crud.get(db, id=station_id)
            if not station:
                return False, "Estación no encontrada", None

            if station.Status in ["maintenance", "offline"]:
                return False, f"Estación en estado {station.Status}", None

            # Validar usuario
            user = user_crud.get(db, id=user_id)
            if not user or not user.IsActive:
                return False, "Usuario no válido o inactivo", None

            # Verificar permisos del usuario
            if not self._user_can_attend_station(user, station):
                return False, "Usuario no tiene permisos para atender esta estación", None

            # Validar carga de trabajo si está habilitado
            if validate_workload:
                current_workload = self._get_user_workload(db, user_id)
                if current_workload >= 2:  # Máximo 2 estaciones por usuario
                    return False, "Usuario ya está asignado al máximo de estaciones", None

            # Asignar usuario
            station = station_crud.assign_user(
                db,
                station_id=station_id,
                user_id=user_id,
                start_time=start_time,
                end_time=end_time
            )

            if station:
                # Notificar via WebSocket
                if websocket_manager:
                    await websocket_manager.broadcast_station_update({
                        "action": "user_assigned",
                        "station_id": station_id,
                        "user_id": user_id
                    })

                return True, f"Usuario asignado correctamente a {station.Name}", station

            return False, "Error asignando usuario", None

        except Exception as e:
            logger.error(f"Error asignando usuario a estación: {e}")
            return False, f"Error interno: {str(e)}", None

    # ========================================
    # MÉTODOS DE GESTIÓN DE COLA
    # ========================================

    async def call_next_patient_intelligent(
            self,
            db: Session,
            station_id: int,
            service_type_id: Optional[int] = None,
            priority_boost: bool = False
    ) -> CallNextPatientResponse:
        """
        Llama al siguiente paciente usando algoritmo inteligente

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            service_type_id: ID del tipo de servicio específico
            priority_boost: Dar prioridad a casos urgentes

        Returns:
            CallNextPatientResponse con el resultado
        """
        try:
            station = station_crud.get(db, id=station_id)
            if not station:
                return CallNextPatientResponse(
                    Success=False,
                    Message="Estación no encontrada",
                    QueueLength=0
                )

            # Verificar si la estación puede aceptar más pacientes
            if not station.can_accept_more_patients():
                return CallNextPatientResponse(
                    Success=False,
                    Message="Estación al máximo de capacidad",
                    QueueLength=self._get_queue_length(db, station_id)
                )

            # Seleccionar siguiente ticket con algoritmo inteligente
            next_ticket = await self._select_next_ticket_intelligent(
                db,
                station_id,
                service_type_id,
                priority_boost
            )

            if next_ticket:
                # Llamar al paciente
                called_ticket = station_crud.call_next_patient(
                    db,
                    station_id=station_id,
                    service_type_id=service_type_id,
                    priority=5 if priority_boost else None
                )

                if called_ticket:
                    # Notificar al paciente
                    if self.notification_enabled and notification_service:
                        await notification_service.notify_patient_called(
                            called_ticket,
                            station
                        )

                    # Notificar via WebSocket
                    if websocket_manager:
                        await websocket_manager.broadcast_ticket_called({
                            "ticket_id": str(called_ticket.Id),
                            "ticket_number": called_ticket.TicketNumber,
                            "station_id": station_id,
                            "station_name": station.Name
                        })

                    # Verificar si se necesita rebalanceo automático
                    if self.auto_rebalance_enabled:
                        asyncio.create_task(self._check_auto_rebalance(db, station_id))

                    return CallNextPatientResponse(
                        Success=True,
                        Message=f"Paciente {called_ticket.TicketNumber} llamado correctamente",
                        TicketCalled={
                            "Id": str(called_ticket.Id),
                            "TicketNumber": called_ticket.TicketNumber,
                            "PatientName": called_ticket.patient.FullName if called_ticket.patient else "N/A",
                            "ServiceType": called_ticket.service_type.Name if called_ticket.service_type else "N/A"
                        },
                        QueueLength=self._get_queue_length(db, station_id)
                    )

            return CallNextPatientResponse(
                Success=False,
                Message="No hay pacientes en espera",
                QueueLength=0
            )

        except Exception as e:
            logger.error(f"Error llamando siguiente paciente: {e}")
            return CallNextPatientResponse(
                Success=False,
                Message=f"Error interno: {str(e)}",
                QueueLength=0
            )

    async def transfer_patients_between_stations(
            self,
            db: Session,
            transfer_request: TransferPatientsRequest
    ) -> Dict[str, Any]:
        """
        Transfiere pacientes entre estaciones

        Args:
            db: Sesión de base de datos
            transfer_request: Datos de la transferencia

        Returns:
            Resultado de la transferencia
        """
        try:
            from_station = station_crud.get(db, id=transfer_request.FromStationId)
            to_station = station_crud.get(db, id=transfer_request.ToStationId)

            if not from_station or not to_station:
                return {
                    "success": False,
                    "message": "Estación origen o destino no encontrada"
                }

            # Obtener tickets a transferir
            tickets_to_transfer = db.query(Ticket).filter(
                Ticket.StationId == transfer_request.FromStationId,
                Ticket.Status == 'waiting'
            ).limit(transfer_request.PatientCount or 5).all()

            transferred_count = 0
            for ticket in tickets_to_transfer:
                ticket.StationId = transfer_request.ToStationId

                # Notificar al paciente
                if self.notification_enabled and notification_service:
                    await notification_service.notify_transfer(
                        ticket,
                        from_station,
                        to_station
                    )

                transferred_count += 1

            db.commit()

            # Notificar via WebSocket
            if websocket_manager:
                await websocket_manager.broadcast_queue_update({
                    "action": "patients_transferred",
                    "from_station": from_station.Name,
                    "to_station": to_station.Name,
                    "count": transferred_count
                })

            logger.info(f"Transferidos {transferred_count} pacientes de {from_station.Name} a {to_station.Name}")

            return {
                "success": True,
                "message": f"Transferidos {transferred_count} pacientes exitosamente",
                "transferred_count": transferred_count,
                "from_station": from_station.Name,
                "to_station": to_station.Name
            }

        except Exception as e:
            logger.error(f"Error transfiriendo pacientes: {e}")
            return {
                "success": False,
                "message": f"Error interno: {str(e)}"
            }

    # ========================================
    # MÉTODOS DE BALANCEO DE CARGA
    # ========================================

    async def balance_load_across_stations(
            self,
            db: Session,
            strategy: LoadBalanceStrategy = LoadBalanceStrategy.MIXED
    ) -> Dict[str, Any]:
        """
        Balancea la carga entre todas las estaciones activas

        Args:
            db: Sesión de base de datos
            strategy: Estrategia de balanceo

        Returns:
            Dict: Resultado del balanceo con estadísticas
        """
        try:
            logger.info(f"Iniciando balanceo de carga con estrategia: {strategy}")

            # Obtener estaciones activas
            active_stations = station_crud.get_stations_with_stats(db, include_inactive=False)
            active_stations = [s for s in active_stations if s['Status'] == 'active']

            if len(active_stations) < 2:
                return {
                    "success": False,
                    "message": "Se necesitan al menos 2 estaciones activas para balancear",
                    "transfers": []
                }

            # Analizar carga actual
            station_loads = []
            for station in active_stations:
                queue_length = station.get('waiting', 0)
                current_patients = station.get('in_progress', 0)
                load_score = self._calculate_load_score(
                    station,
                    queue_length,
                    current_patients
                )

                station_loads.append({
                    'station': station,
                    'queue_length': queue_length,
                    'current_patients': current_patients,
                    'load_score': load_score
                })

            # Ejecutar estrategia de balanceo
            transfers = await self._execute_load_balance_strategy(
                db,
                station_loads,
                strategy
            )

            # Aplicar transferencias
            total_transferred = 0
            for transfer in transfers:
                result = await self.transfer_patients_between_stations(
                    db,
                    TransferPatientsRequest(
                        FromStationId=transfer['from_id'],
                        ToStationId=transfer['to_id'],
                        PatientCount=transfer['count'],
                        Reason="Balanceo automático de carga"
                    )
                )
                if result['success']:
                    total_transferred += result['transferred_count']

            logger.info(f"Balanceo completado: {total_transferred} pacientes transferidos")

            return {
                "success": True,
                "strategy": strategy,
                "stations_analyzed": len(active_stations),
                "transfers_executed": len(transfers),
                "total_patients_transferred": total_transferred,
                "new_distribution": self._get_current_distribution(db, active_stations)
            }

        except Exception as e:
            logger.error(f"Error balanceando carga: {e}")
            return {
                "success": False,
                "message": f"Error interno: {str(e)}",
                "transfers": []
            }

    # ========================================
    # MÉTODOS DE OPTIMIZACIÓN
    # ========================================

    async def optimize_station_configuration(
            self,
            db: Session,
            station_id: int,
            analysis_days: int = 7
    ) -> Dict[str, Any]:
        """
        Optimiza la configuración de una estación basado en datos históricos

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            analysis_days: Días de datos a analizar

        Returns:
            Recomendaciones de optimización
        """
        try:
            station = station_crud.get(db, id=station_id)
            if not station:
                return {"success": False, "message": "Estación no encontrada"}

            # Analizar datos históricos
            end_date = date.today()
            start_date = end_date - timedelta(days=analysis_days)

            performance_report = station_crud.get_performance_report(
                db,
                station_id,
                start_date,
                end_date
            )

            # Generar recomendaciones de optimización
            optimizations = {
                "capacity": self._analyze_capacity_optimization(performance_report, station),
                "service_time": self._analyze_service_time_optimization(performance_report, station),
                "working_hours": self._analyze_working_hours_optimization(performance_report, station),
                "service_types": self._analyze_service_types_optimization(performance_report, station)
            }

            # Calcular impacto potencial
            potential_improvements = self._calculate_potential_improvements(optimizations)

            logger.info(f"Optimización generada para estación {station.Name}")

            return {
                "success": True,
                "station_id": station_id,
                "station_name": station.Name,
                "analysis_period": f"{analysis_days} días",
                "current_performance": performance_report.get('summary', {}),
                "optimizations": optimizations,
                "potential_improvements": potential_improvements,
                "implementation_priority": self._prioritize_optimizations(optimizations)
            }

        except Exception as e:
            logger.error(f"Error optimizando configuración de estación: {e}")
            return {"success": False, "message": f"Error interno: {str(e)}"}

    async def generate_performance_report(
            self,
            db: Session,
            station_id: int,
            period: str = "day"
    ) -> StationPerformanceReport:
        """
        Genera reporte de rendimiento de estación

        Args:
            db: Sesión de base de datos
            station_id: ID de la estación
            period: Período del reporte (day/week/month)

        Returns:
            StationPerformanceReport
        """
        try:
            # Determinar rango de fechas
            end_date = date.today()
            if period == "day":
                start_date = end_date
            elif period == "week":
                start_date = end_date - timedelta(days=7)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date

            # Obtener reporte del CRUD
            report_data = station_crud.get_performance_report(
                db,
                station_id,
                start_date,
                end_date
            )

            # Calcular métricas de rendimiento
            efficiency = report_data.get('summary', {}).get('average_efficiency', 0)

            # Calcular satisfacción estimada (basada en tiempo de espera)
            avg_wait = report_data.get('summary', {}).get('average_wait_time', 0)
            patient_satisfaction = max(0, 100 - (avg_wait * 2))  # Reducir 2% por cada minuto de espera

            # Calcular calidad de servicio
            service_quality = (efficiency * 0.6 + patient_satisfaction * 0.4)

            # Generar recomendaciones
            recommendations = report_data.get('recommendations', [])
            issues = []

            if efficiency < 70:
                issues.append("Eficiencia por debajo del objetivo")
            if avg_wait > 20:
                issues.append("Tiempo de espera elevado")
            if patient_satisfaction < 80:
                issues.append("Satisfacción del paciente mejorable")

            return StationPerformanceReport(
                StationId=station_id,
                ReportDate=datetime.now(),
                Period=period,
                Efficiency=efficiency,
                PatientSatisfaction=patient_satisfaction,
                ServiceQuality=service_quality,
                Recommendations=recommendations,
                IssuesFound=issues
            )

        except Exception as e:
            logger.error(f"Error generando reporte de rendimiento: {e}")
            raise

    # ========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ========================================

    async def _auto_assign_services(self, db: Session, station: Station) -> None:
        """Asigna servicios automáticamente basado en especialización"""
        try:
            service_mappings = {
                "general": ["Análisis", "Consultas"],
                "laboratory": ["Análisis", "Entrega de Muestras"],
                "results": ["Entrega de Resultados"],
                "samples": ["Entrega de Muestras"],
                "consultations": ["Consultas"],
                "priority": ["Servicios de Prioridad"]
            }

            service_names = service_mappings.get(station.Specialization, ["Análisis"])

            for service_name in service_names:
                service_type = db.query(ServiceType).filter(
                    ServiceType.Name == service_name
                ).first()

                if service_type and not station.ServiceTypeId:
                    station.ServiceTypeId = service_type.Id
                    break

            db.commit()

        except Exception as e:
            logger.error(f"Error asignando servicios automáticamente: {e}")

    async def _setup_default_working_hours(self, db: Session, station: Station) -> None:
        """Configura horarios de trabajo por defecto"""
        try:
            default_hours = {
                "monday": {"start": "08:00", "end": "17:00"},
                "tuesday": {"start": "08:00", "end": "17:00"},
                "wednesday": {"start": "08:00", "end": "17:00"},
                "thursday": {"start": "08:00", "end": "17:00"},
                "friday": {"start": "08:00", "end": "17:00"},
                "saturday": {"start": "08:00", "end": "13:00"},
                "sunday": None
            }

            station.WorkingHours = default_hours
            db.commit()

        except Exception as e:
            logger.error(f"Error configurando horarios por defecto: {e}")

    def _user_can_attend_station(self, user: User, station: Station) -> bool:
        """Verifica si un usuario puede atender una estación"""
        # Verificar rol del usuario
        if not user.Role:
            return False

        allowed_roles = ['Técnico', 'Enfermero', 'Doctor', 'Supervisor', 'Admin']
        return user.Role.Name in allowed_roles

    def _get_user_workload(self, db: Session, user_id: str) -> int:
        """Obtiene la carga de trabajo actual de un usuario"""
        try:
            # Como un usuario solo puede estar en una estación a la vez,
            # verificamos si ya tiene una estación asignada
            user = db.query(User).filter(User.Id == user_id).first()
            return 1 if user and user.StationId else 0
        except Exception:
            return 0

    async def _select_next_ticket_intelligent(
            self,
            db: Session,
            station_id: int,
            service_type_id: Optional[int],
            priority_boost: bool
    ) -> Optional[Ticket]:
        """Selecciona el próximo ticket usando algoritmo inteligente"""
        try:
            # Por ahora usar el método básico del CRUD
            # En el futuro se puede implementar ML aquí
            return station_crud.call_next_patient(
                db,
                station_id=station_id,
                service_type_id=service_type_id,
                priority=5 if priority_boost else None
            )

        except Exception as e:
            logger.error(f"Error seleccionando próximo ticket: {e}")
            return None

    def _get_queue_length(self, db: Session, station_id: int) -> int:
        """Obtiene la longitud actual de la cola"""
        try:
            return db.query(Ticket).filter(
                Ticket.StationId == station_id,
                Ticket.Status == 'waiting'
            ).count()
        except Exception:
            return 0

    def _calculate_load_score(
            self,
            station: Dict[str, Any],
            queue_length: int,
            current_patients: int
    ) -> float:
        """Calcula score de carga para una estación"""
        try:
            max_concurrent = station.get('MaxConcurrentPatients', 1)
            capacity_usage = current_patients / max_concurrent
            queue_factor = queue_length / 10.0  # Normalizar cola

            return (capacity_usage * 0.6) + (queue_factor * 0.4)

        except Exception:
            return 0.0

    async def _execute_load_balance_strategy(
            self,
            db: Session,
            station_loads: List[Dict],
            strategy: LoadBalanceStrategy
    ) -> List[Dict]:
        """Ejecuta la estrategia de balanceo seleccionada"""
        try:
            transfers = []

            if strategy == LoadBalanceStrategy.LEAST_QUEUE:
                transfers = await self._balance_by_least_queue(db, station_loads)
            elif strategy == LoadBalanceStrategy.LEAST_WAIT_TIME:
                transfers = await self._balance_by_wait_time(db, station_loads)
            elif strategy == LoadBalanceStrategy.SERVICE_BASED:
                transfers = await self._balance_by_service(db, station_loads)
            elif strategy == LoadBalanceStrategy.ROUND_ROBIN:
                transfers = await self._balance_round_robin(db, station_loads)
            else:  # MIXED
                transfers = await self._balance_mixed(db, station_loads)

            return transfers

        except Exception as e:
            logger.error(f"Error ejecutando estrategia de balanceo: {e}")
            return []

    async def _balance_by_least_queue(
            self,
            db: Session,
            station_loads: List[Dict]
    ) -> List[Dict]:
        """Balancea por menor cola"""
        transfers = []

        # Ordenar por carga
        sorted_stations = sorted(station_loads, key=lambda x: x['load_score'])

        if len(sorted_stations) >= 2:
            # Transferir del más cargado al menos cargado
            most_loaded = sorted_stations[-1]
            least_loaded = sorted_stations[0]

            if most_loaded['queue_length'] > self.max_queue_threshold:
                transfer_count = min(5, most_loaded['queue_length'] // 2)
                transfers.append({
                    'from_id': most_loaded['station']['Id'],
                    'to_id': least_loaded['station']['Id'],
                    'count': transfer_count
                })

        return transfers

    async def _balance_by_wait_time(
            self,
            db: Session,
            station_loads: List[Dict]
    ) -> List[Dict]:
        """Balancea por tiempo de espera"""
        # Similar a least_queue pero considerando tiempo promedio
        return await self._balance_by_least_queue(db, station_loads)

    async def _balance_by_service(
            self,
            db: Session,
            station_loads: List[Dict]
    ) -> List[Dict]:
        """Balancea por tipo de servicio"""
        transfers = []

        # Agrupar por tipo de servicio
        service_groups = {}
        for load in station_loads:
            service_id = load['station'].get('ServiceTypeId')
            if service_id not in service_groups:
                service_groups[service_id] = []
            service_groups[service_id].append(load)

        # Balancear dentro de cada grupo
        for service_id, group in service_groups.items():
            if len(group) >= 2:
                group_transfers = await self._balance_by_least_queue(db, group)
                transfers.extend(group_transfers)

        return transfers

    async def _balance_round_robin(
            self,
            db: Session,
            station_loads: List[Dict]
    ) -> List[Dict]:
        """Balancea en round robin"""
        transfers = []

        if len(station_loads) < 2:
            return transfers

        # Distribuir equitativamente
        total_queue = sum(s['queue_length'] for s in station_loads)
        target_per_station = total_queue // len(station_loads)

        for station in station_loads:
            diff = station['queue_length'] - target_per_station
            if diff > 2:  # Solo si la diferencia es significativa
                # Encontrar estación con menos cola
                target = min(station_loads, key=lambda x: x['queue_length'])
                if target['station']['Id'] != station['station']['Id']:
                    transfers.append({
                        'from_id': station['station']['Id'],
                        'to_id': target['station']['Id'],
                        'count': diff // 2
                    })

        return transfers

    async def _balance_mixed(
            self,
            db: Session,
            station_loads: List[Dict]
    ) -> List[Dict]:
        """Estrategia mixta de balanceo"""
        # Combinar diferentes estrategias
        transfers = []

        # Primero por servicio
        service_transfers = await self._balance_by_service(db, station_loads)
        transfers.extend(service_transfers)

        # Luego por cola si hay desbalance significativo
        queue_transfers = await self._balance_by_least_queue(db, station_loads)
        for qt in queue_transfers:
            # Evitar duplicados
            if not any(t['from_id'] == qt['from_id'] and t['to_id'] == qt['to_id'] for t in transfers):
                transfers.append(qt)

        return transfers

    async def _check_auto_rebalance(self, db: Session, station_id: int) -> None:
        """Verifica si se necesita rebalanceo automático"""
        try:
            queue_length = self._get_queue_length(db, station_id)

            if queue_length > self.max_queue_threshold:
                logger.info(f"Rebalanceo automático activado para estación {station_id}")
                await self.balance_load_across_stations(db, LoadBalanceStrategy.MIXED)

        except Exception as e:
            logger.error(f"Error en verificación de rebalanceo automático: {e}")

    def _get_current_distribution(
            self,
            db: Session,
            stations: List[Dict]
    ) -> Dict[str, Any]:
        """Obtiene la distribución actual de carga"""
        total_queue = sum(s.get('waiting', 0) for s in stations)
        total_in_progress = sum(s.get('in_progress', 0) for s in stations)

        distribution = {
            'total_waiting': total_queue,
            'total_in_progress': total_in_progress,
            'average_per_station': total_queue / len(stations) if stations else 0,
            'stations': []
        }

        for station in stations:
            distribution['stations'].append({
                'id': station['Id'],
                'name': station['Name'],
                'waiting': station.get('waiting', 0),
                'in_progress': station.get('in_progress', 0),
                'load_percentage': (station.get('waiting', 0) / total_queue * 100) if total_queue > 0 else 0
            })

        return distribution

    def _analyze_capacity_optimization(
            self,
            report: Dict[str, Any],
            station: Station
    ) -> Dict[str, Any]:
        """Analiza optimizaciones de capacidad"""
        avg_efficiency = report.get('summary', {}).get('average_efficiency', 0)

        recommendations = []
        if avg_efficiency > 90:
            recommendations.append("Considerar aumentar MaxConcurrentPatients")
        elif avg_efficiency < 50:
            recommendations.append("Reducir MaxConcurrentPatients para mejorar calidad")

        return {
            'current_capacity': station.MaxConcurrentPatients,
            'recommended_capacity': self._calculate_optimal_capacity(report),
            'recommendations': recommendations
        }

    def _analyze_service_time_optimization(
            self,
            report: Dict[str, Any],
            station: Station
    ) -> Dict[str, Any]:
        """Analiza optimizaciones de tiempo de servicio"""
        actual_service_time = report.get('summary', {}).get('average_service_time', 15)
        configured_time = station.AverageServiceTimeMinutes

        recommendations = []
        if actual_service_time > configured_time * 1.2:
            recommendations.append("Revisar procesos o proporcionar capacitación adicional")
        elif actual_service_time < configured_time * 0.8:
            recommendations.append("Actualizar tiempo configurado para reflejar eficiencia actual")

        return {
            'configured_time': configured_time,
            'actual_average': actual_service_time,
            'variance': actual_service_time - configured_time,
            'recommendations': recommendations
        }

    def _analyze_working_hours_optimization(
            self,
            report: Dict[str, Any],
            station: Station
    ) -> Dict[str, Any]:
        """Analiza optimizaciones de horarios"""
        daily_metrics = report.get('daily_metrics', [])

        peak_hours = []
        low_hours = []

        # Análisis simplificado de patrones
        recommendations = []
        if daily_metrics:
            avg_morning = sum(m.get('tickets_completed', 0) for m in daily_metrics[:len(daily_metrics)//2])
            avg_afternoon = sum(m.get('tickets_completed', 0) for m in daily_metrics[len(daily_metrics)//2:])

            if avg_morning > avg_afternoon * 1.5:
                recommendations.append("Mayor demanda en horario matutino")
                peak_hours = ["08:00-12:00"]
            elif avg_afternoon > avg_morning * 1.5:
                recommendations.append("Mayor demanda en horario vespertino")
                peak_hours = ["14:00-17:00"]

        return {
            'current_hours': station.WorkingHours,
            'peak_hours': peak_hours,
            'low_demand_hours': low_hours,
            'recommendations': recommendations
        }

    def _analyze_service_types_optimization(
            self,
            report: Dict[str, Any],
            station: Station
    ) -> Dict[str, Any]:
        """Analiza optimizaciones de tipos de servicio"""
        recommendations = []

        if station.Specialization == "general":
            recommendations.append("Considerar especialización para mejorar eficiencia")

        return {
            'current_specialization': station.Specialization,
            'service_types_handled': 1,  # Simplificado
            'recommendations': recommendations
        }

    def _calculate_optimal_capacity(self, report: Dict[str, Any]) -> int:
        """Calcula la capacidad óptima basada en métricas"""
        avg_tickets = report.get('summary', {}).get('average_tickets_per_day', 0)

        if avg_tickets > 50:
            return 3
        elif avg_tickets > 30:
            return 2
        else:
            return 1

    def _calculate_potential_improvements(
            self,
            optimizations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula mejoras potenciales"""
        improvements = {
            'efficiency_gain': 0,
            'wait_time_reduction': 0,
            'capacity_increase': 0
        }

        # Calcular mejoras estimadas
        if optimizations.get('capacity', {}).get('recommendations'):
            improvements['efficiency_gain'] += 10

        if optimizations.get('service_time', {}).get('recommendations'):
            improvements['wait_time_reduction'] += 15

        if optimizations.get('working_hours', {}).get('recommendations'):
            improvements['capacity_increase'] += 20

        return improvements

    def _prioritize_optimizations(
            self,
            optimizations: Dict[str, Any]
    ) -> List[str]:
        """Prioriza las optimizaciones por impacto"""
        priorities = []

        # Orden de prioridad
        if optimizations.get('service_time', {}).get('recommendations'):
            priorities.append("service_time")

        if optimizations.get('capacity', {}).get('recommendations'):
            priorities.append("capacity")

        if optimizations.get('working_hours', {}).get('recommendations'):
            priorities.append("working_hours")

        if optimizations.get('service_types', {}).get('recommendations'):
            priorities.append("service_types")

        return priorities


# ========================================
# INSTANCIA SINGLETON DEL SERVICIO
# ========================================

station_service = StationService()