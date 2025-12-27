"""
WebSocket Connection Manager para el sistema de gestión de colas
Ubicado en la estructura correcta: app/websocket/connection_manager.py
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Optional, Any
import json
import asyncio
import logging
from datetime import datetime
from enum import Enum
import uuid

from app.core.redis import cache_manager

# ========================================
# CONFIGURACIÓN Y ENUMS
# ========================================

logger = logging.getLogger(__name__)


class ConnectionType(str, Enum):
    """Tipos de conexiones WebSocket"""
    DISPLAY = "display"  # Pantallas de información
    STATION = "station"  # Estaciones de trabajo
    ADMIN = "admin"  # Panel administrativo
    MOBILE = "mobile"  # Aplicaciones móviles
    PUBLIC = "public"  # Acceso público


class MessageType(str, Enum):
    """Tipos de mensajes WebSocket"""
    QUEUE_UPDATE = "queue_update"
    STATION_UPDATE = "station_update"
    TICKET_CALLED = "ticket_called"
    PATIENT_UPDATE = "patient_update"
    SYSTEM_ALERT = "system_alert"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


# ========================================
# CLASE DE CONEXIÓN WEBSOCKET
# ========================================

class WebSocketConnection:
    """Representa una conexión WebSocket individual"""

    def __init__(
            self,
            websocket: WebSocket,
            connection_id: str,
            connection_type: ConnectionType,
            user_id: Optional[str] = None,
            station_id: Optional[int] = None,
            metadata: Optional[Dict[str, Any]] = None
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.connection_type = connection_type
        self.user_id = user_id
        self.station_id = station_id
        self.metadata = metadata or {}
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.is_active = True

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Envía mensaje a través de WebSocket"""
        try:
            message_with_meta = {
                **message,
                "timestamp": datetime.now().isoformat(),
                "connection_id": self.connection_id
            }

            await self.websocket.send_text(json.dumps(message_with_meta))
            return True

        except Exception as e:
            logger.error(f"Error enviando mensaje WebSocket: {e}")
            self.is_active = False
            return False

    def update_heartbeat(self) -> None:
        """Actualiza timestamp del último heartbeat"""
        self.last_heartbeat = datetime.now()


# ========================================
# CLASE PRINCIPAL DEL WEBSOCKET MANAGER
# ========================================

class WebSocketManager:
    """Manager principal para conexiones WebSocket"""

    def __init__(self):
        """Inicializa el WebSocket Manager"""
        self.connections: Dict[str, WebSocketConnection] = {}
        self.connections_by_type: Dict[ConnectionType, Set[str]] = {
            connection_type: set() for connection_type in ConnectionType
        }
        self.connections_by_station: Dict[int, Set[str]] = {}
        self.connections_by_user: Dict[str, Set[str]] = {}

        # Configuración
        self.heartbeat_interval = 30  # segundos
        self.max_connections_per_user = 5

    async def connect(
            self,
            websocket: WebSocket,
            connection_type: ConnectionType,
            user_id: Optional[str] = None,
            station_id: Optional[int] = None,
            **metadata
    ) -> str:
        """Conecta un nuevo WebSocket"""
        try:
            # Intentar accept solo si no está ya aceptado
            if websocket.client_state.name == "CONNECTING":
                await websocket.accept()
            connection_id = str(uuid.uuid4())

            # Verificar límite de conexiones por usuario
            if user_id and self._count_user_connections(user_id) >= self.max_connections_per_user:
                await websocket.close(code=1008, reason="Máximo de conexiones excedido")
                raise Exception(f"Usuario {user_id} excedió límite de conexiones")

            # Crear conexión
            connection = WebSocketConnection(
                websocket=websocket,
                connection_id=connection_id,
                connection_type=connection_type,
                user_id=user_id,
                station_id=station_id,
                metadata=metadata
            )

            # Registrar conexión
            self.connections[connection_id] = connection
            self.connections_by_type[connection_type].add(connection_id)

            if station_id:
                if station_id not in self.connections_by_station:
                    self.connections_by_station[station_id] = set()
                self.connections_by_station[station_id].add(connection_id)

            if user_id:
                if user_id not in self.connections_by_user:
                    self.connections_by_user[user_id] = set()
                self.connections_by_user[user_id].add(connection_id)

            # Enviar mensaje de bienvenida
            await connection.send_message({
                "type": MessageType.CONNECT,
                "message": "Conexión establecida correctamente",
                "connection_id": connection_id,
                "connection_type": connection_type
            })

            logger.info(f"Nueva conexión WebSocket: {connection_id} ({connection_type})")
            return connection_id

        except Exception as e:
            logger.error(f"Error conectando WebSocket: {e}")
            raise

    async def disconnect(self, connection_id: str) -> None:
        """Desconecta un WebSocket"""
        try:
            connection = self.connections.get(connection_id)
            if not connection:
                return

            # Remover de índices
            self.connections_by_type[connection.connection_type].discard(connection_id)

            if connection.station_id:
                if connection.station_id in self.connections_by_station:
                    self.connections_by_station[connection.station_id].discard(connection_id)
                    if not self.connections_by_station[connection.station_id]:
                        del self.connections_by_station[connection.station_id]

            if connection.user_id:
                if connection.user_id in self.connections_by_user:
                    self.connections_by_user[connection.user_id].discard(connection_id)
                    if not self.connections_by_user[connection.user_id]:
                        del self.connections_by_user[connection.user_id]

            # Remover conexión principal
            del self.connections[connection_id]
            logger.info(f"Desconectado WebSocket: {connection_id}")

        except Exception as e:
            logger.error(f"Error desconectando WebSocket: {e}")

    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Envía mensaje a una conexión específica"""
        connection = self.connections.get(connection_id)
        if connection and connection.is_active:
            return await connection.send_message(message)
        return False

    async def broadcast_queue_update(self, data: Dict[str, Any]) -> int:
        """Broadcast de actualización de cola"""
        message = {
            "type": MessageType.QUEUE_UPDATE,
            "data": data
        }

        # Enviar a pantallas y estaciones
        sent_count = 0
        sent_count += await self.broadcast_to_type(ConnectionType.DISPLAY, message)
        sent_count += await self.broadcast_to_type(ConnectionType.STATION, message)
        sent_count += await self.broadcast_to_type(ConnectionType.ADMIN, message)

        return sent_count


    async def broadcast_station_update(self, data: Dict[str, Any]) -> int:
        """Broadcast de actualización de estación"""
        message = {
            "type": MessageType.STATION_UPDATE,
            "data": data
        }

        # Enviar a administradores
        sent_count = await self.broadcast_to_type(ConnectionType.ADMIN, message)

        # Si hay station_id específico, enviar también a esa estación
        if "station_id" in data:
            sent_count += await self.send_to_station(data["station_id"], message)

        return sent_count

    async def broadcast_to_type(
            self,
            connection_type: ConnectionType,
            message: Dict[str, Any],
            exclude_connections: Optional[Set[str]] = None
    ) -> int:
        """Envía mensaje a todas las conexiones de un tipo específico"""
        sent_count = 0
        exclude_connections = exclude_connections or set()
        connection_ids = self.connections_by_type[connection_type].copy()

        for connection_id in connection_ids:
            if connection_id not in exclude_connections:
                if await self.send_to_connection(connection_id, message):
                    sent_count += 1

        return sent_count

    async def send_to_station(self, station_id: int, message: Dict[str, Any]) -> int:
        """Envía mensaje a todas las conexiones de una estación"""
        sent_count = 0
        connection_ids = self.connections_by_station.get(station_id, set()).copy()

        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    def _count_user_connections(self, user_id: str) -> int:
        """Cuenta conexiones activas de un usuario"""
        return len(self.connections_by_user.get(user_id, set()))

    # ========================================
    # MÉTODOS PARA NOTIFICACIÓN DE TICKETS
    # ========================================

    async def broadcast_new_ticket(self, ticket_data: Dict[str, Any]) -> int:
        """
        Broadcast cuando se crea un nuevo ticket
        Notifica a displays, estaciones y admin

        Args:
            ticket_data: Datos del ticket creado
        """
        message = {
            "type": MessageType.QUEUE_UPDATE,
            "action": "new_ticket",
            "data": {
                "ticket_id": ticket_data.get("id"),
                "ticket_number": ticket_data.get("ticket_number"),
                "patient_name": ticket_data.get("patient_name"),
                "service_type_id": ticket_data.get("service_type_id"),
                "service_name": ticket_data.get("service_name"),
                "position": ticket_data.get("position"),
                "estimated_wait_time": ticket_data.get("estimated_wait_time"),
                "status": ticket_data.get("status", "Waiting"),
                "created_at": ticket_data.get("created_at", datetime.now().isoformat())
            }
        }

        sent_count = 0
        sent_count += await self.broadcast_to_type(ConnectionType.DISPLAY, message)
        sent_count += await self.broadcast_to_type(ConnectionType.STATION, message)
        sent_count += await self.broadcast_to_type(ConnectionType.ADMIN, message)

        logger.info(f"New ticket broadcast '{ticket_data.get('ticket_number')}' enviado a {sent_count} conexiones")
        return sent_count

    async def broadcast_ticket_called(self, ticket_data: Dict[str, Any],
                                      station_data: Optional[Dict[str, Any]] = None) -> int:
        """
        Broadcast cuando se llama un ticket - para pantallas de display

        Soporta dos formas de llamada:
        1. broadcast_ticket_called(ticket_data, station_data) - con dos argumentos
        2. broadcast_ticket_called(data) - con un solo diccionario que contiene todo

        Args:
            ticket_data: Datos del ticket (o todos los datos si station_data es None)
            station_data: Datos de la estación (opcional)
        """
        # Si station_data es None, ticket_data contiene todos los datos
        if station_data is None:
            # Formato de un solo argumento
            data = ticket_data
            message = {
                "type": MessageType.TICKET_CALLED,
                "data": {
                    "ticket_number": data.get("ticket_number"),
                    "station_id": data.get("station_id"),
                    "station_name": data.get("station_name"),
                    "station_code": data.get("station_code"),
                    "service_name": data.get("service_name"),
                    "patient_name": data.get("patient_name"),
                    "called_at": data.get("timestamp") or datetime.now().isoformat(),
                    "play_sound": True,
                    "announce": True
                }
            }
        else:
            # Formato de dos argumentos
            message = {
                "type": MessageType.TICKET_CALLED,
                "action": "call_ticket",
                "data": {
                    "ticket_id": ticket_data.get("id"),
                    "ticket_number": ticket_data.get("ticket_number"),
                    "patient_name": ticket_data.get("patient_name"),
                    "service_name": ticket_data.get("service_name"),
                    "station_id": station_data.get("id"),
                    "station_name": station_data.get("name"),
                    "station_code": station_data.get("code"),
                    "called_at": datetime.now().isoformat(),
                    "play_sound": True,
                    "announce": True
                }
            }

        # Enviar a pantallas, estaciones y admin
        sent_count = 0
        sent_count += await self.broadcast_to_type(ConnectionType.DISPLAY, message)
        sent_count += await self.broadcast_to_type(ConnectionType.STATION, message)
        sent_count += await self.broadcast_to_type(ConnectionType.ADMIN, message)

        logger.info(f"Ticket called broadcast enviado a {sent_count} conexiones")
        return sent_count

    async def broadcast_ticket_status_change(self, ticket_data: Dict[str, Any], old_status: str, new_status: str) -> int:
        """
        Broadcast cuando cambia el estado de un ticket

        Args:
            ticket_data: Datos del ticket
            old_status: Estado anterior
            new_status: Nuevo estado
        """
        message = {
            "type": MessageType.QUEUE_UPDATE,
            "action": "status_change",
            "data": {
                "ticket_id": ticket_data.get("id"),
                "ticket_number": ticket_data.get("ticket_number"),
                "old_status": old_status,
                "new_status": new_status,
                "service_type_id": ticket_data.get("service_type_id"),
                "timestamp": datetime.now().isoformat()
            }
        }

        sent_count = 0
        sent_count += await self.broadcast_to_type(ConnectionType.DISPLAY, message)
        sent_count += await self.broadcast_to_type(ConnectionType.STATION, message)
        sent_count += await self.broadcast_to_type(ConnectionType.ADMIN, message)

        logger.info(f"Status change broadcast: {ticket_data.get('ticket_number')} {old_status} -> {new_status}")
        return sent_count

    async def broadcast(self, message: str) -> int:
        """
        Broadcast de mensaje raw a todas las conexiones
        Compatibilidad con llamadas existentes

        Args:
            message: Mensaje JSON como string
        """
        try:
            parsed_message = json.loads(message) if isinstance(message, str) else message
        except json.JSONDecodeError:
            parsed_message = {"raw": message}

        sent_count = 0
        for connection_type in ConnectionType:
            sent_count += await self.broadcast_to_type(connection_type, parsed_message)

        return sent_count

    async def broadcast_json(self, data: Dict[str, Any]) -> int:
        """
        Broadcast de diccionario JSON a todas las conexiones
        Compatibilidad con llamadas existentes

        Args:
            data: Diccionario con datos a enviar
        """
        sent_count = 0
        for connection_type in ConnectionType:
            sent_count += await self.broadcast_to_type(connection_type, data)

        return sent_count



    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del WebSocket Manager"""
        return {
            "total_connections": len(self.connections),
            "connections_by_type": {
                connection_type.value: len(connection_ids)
                for connection_type, connection_ids in self.connections_by_type.items()
            },
            "connections_by_station": {
                station_id: len(connection_ids)
                for station_id, connection_ids in self.connections_by_station.items()
            },
            "total_users_connected": len(self.connections_by_user)
        }

    async def broadcast_system_alert(self, alert_type: str, data: Dict[str, Any]) -> int:
        """
        Broadcast de alerta del sistema a todas las conexiones

        Args:
            alert_type: Tipo de alerta (daily_cleanup, system_reset, maintenance, etc.)
            data: Datos adicionales de la alerta
        """
        message = {
            "type": MessageType.SYSTEM_ALERT,
            "alert_type": alert_type,
            "data": data
        }

        sent_count = 0
        # Enviar a TODAS las conexiones
        for connection_type in ConnectionType:
            sent_count += await self.broadcast_to_type(connection_type, message)

        logger.info(f"System alert '{alert_type}' enviado a {sent_count} conexiones")
        return sent_count

    async def broadcast_daily_reset(self, cleanup_data: Dict[str, Any]) -> int:
        """
        Broadcast específico para reset diario del sistema
        Notifica a todos los clientes que deben limpiar su estado local

        Args:
            cleanup_data: Resumen de la limpieza realizada
        """
        message = {
            "type": MessageType.SYSTEM_ALERT,
            "alert_type": "daily_reset",
            "action": "clear_all_data",
            "data": {
                "reason": "Inicio de nueva jornada",
                "tickets_cancelled": cleanup_data.get("tickets_cancelled", 0),
                "queues_reset": cleanup_data.get("queues_reset", 0),
                "stations_reset": cleanup_data.get("stations_reset", 0),
                "timestamp": datetime.now().isoformat(),
                "instructions": {
                    "clear_queue_display": True,
                    "clear_current_ticket": True,
                    "reset_station_status": True,
                    "reload_service_types": True
                }
            }
        }

        sent_count = 0
        # Enviar a TODAS las conexiones
        for connection_type in ConnectionType:
            sent_count += await self.broadcast_to_type(connection_type, message)

        logger.info(f"Daily reset broadcast enviado a {sent_count} conexiones")
        return sent_count


# ========================================
# INSTANCIA GLOBAL
# ========================================

websocket_manager = WebSocketManager()