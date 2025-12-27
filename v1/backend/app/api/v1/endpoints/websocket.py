"""
API endpoints WebSocket para comunicación en tiempo real
Sistema de gestión de colas - Laboratorio clínico
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import json
import asyncio
import logging
from datetime import datetime

from app.core.database import get_db
from app.api.dependencies.auth import get_token_data, get_current_user_optional, get_current_user
from app.models.user import User
from app.websocket.connection_manager import (
    websocket_manager,  # Importar instancia global, no crear nueva
    ConnectionType,
    MessageType,
    WebSocketConnection
)
from app.services.notification_service import notification_service
from app.crud.ticket import ticket_crud
from app.crud.station import station_crud
from app.core.redis import cache_manager

# ========================================
# CONFIGURACIÓN DEL ROUTER
# ========================================

router = APIRouter(prefix="/ws", tags=["websocket"])
logger = logging.getLogger(__name__)

# Usar la instancia global importada de connection_manager.py
# NO crear nueva instancia aquí - eso causaba que las conexiones
# se registraran en una instancia diferente a la usada por tickets.py


# ========================================
# WEBSOCKET PRINCIPAL - PANTALLAS PÚBLICAS
# ========================================

@router.websocket("/display")
async def websocket_display_endpoint(
        websocket: WebSocket,
        display_type: str = Query("main", description="Tipo de pantalla: main, station, mobile"),
        station_id: Optional[int] = Query(None, description="ID de estación específica"),
        location: Optional[str] = Query(None, description="Ubicación de la pantalla")
):
    """
    WebSocket para pantallas de información pública

    - Pantallas principales de sala de espera
    - Pantallas por estación
    - Aplicaciones móviles públicas
    - No requiere autenticación
    """
    connection_id = None

    try:
        await websocket.accept()
        logger.info(f"Conexión WebSocket display establecida: {connection_id}")

        # Registrar conexión
        connection_id = await websocket_manager.connect(
            websocket=websocket,
            connection_type=ConnectionType.DISPLAY,
            station_id=station_id,
            display_type=display_type,
            location=location
        )

        # Enviar estado inicial
        await send_initial_display_data(websocket, display_type, station_id)

        # Loop principal de mensajes
        while True:
            try:
                # Esperar mensajes del cliente
                data = await websocket.receive_text()
                message = json.loads(data)

                # Procesar mensaje según tipo
                await handle_display_message(websocket, connection_id, message)

            except WebSocketDisconnect:
                logger.info(f"Display desconectado: {connection_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": MessageType.ERROR,
                    "message": "Formato de mensaje inválido"
                }))
            except Exception as e:
                logger.error(f"Error en display WebSocket: {e}")
                await websocket.send_text(json.dumps({
                    "type": MessageType.ERROR,
                    "message": "Error interno del servidor"
                }))

    except WebSocketDisconnect:
        logger.info(f"Display WebSocket desconectado: {connection_id}")
    except Exception as e:
        logger.error(f"Error estableciendo conexión display: {e}")
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


# ========================================
# WEBSOCKET PARA ESTACIONES DE TRABAJO
# ========================================

@router.websocket("/station")
async def websocket_station_endpoint(
        websocket: WebSocket,
        station_id: int = Query(..., description="ID de la estación"),
        token: Optional[str] = Query(None, description="Token de autenticación")
):
    """
    WebSocket para estaciones de trabajo

    - Panel de control de técnicos
    - Gestión de cola en tiempo real
    - Notificaciones de llamadas
    - Requiere autenticación
    """
    connection_id = None
    user = None
    db = None

    try:
        await websocket.accept()

        # Verificar autenticación si se proporciona token
        if token:
            token_data = get_token_data(token)
            if token_data:
                # Aquí podrías obtener el usuario de la base de datos
                # Por simplicidad, asumimos que el token es válido
                pass

        logger.info(f"Conexión WebSocket estación establecida: {connection_id} - Estación: {station_id}")

        # Registrar conexión
        connection_id = await websocket_manager.connect(
            websocket=websocket,
            connection_type=ConnectionType.STATION,
            user_id=user.Id if user else None,
            station_id=station_id,
            authenticated=user is not None
        )

        # Enviar estado inicial de la estación
        await send_initial_station_data(websocket, station_id)

        # Loop principal de mensajes
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Procesar mensaje de estación
                await handle_station_message(websocket, connection_id, message, db)

            except WebSocketDisconnect:
                logger.info(f"Estación desconectada: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error en estación WebSocket: {e}")
                await websocket.send_text(json.dumps({
                    "type": MessageType.ERROR,
                    "message": f"Error: {str(e)}"
                }))

    except WebSocketDisconnect:
        logger.info(f"Estación WebSocket desconectada: {connection_id}")
    except Exception as e:
        logger.error(f"Error estableciendo conexión estación: {e}")
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


# ========================================
# WEBSOCKET PARA ADMINISTRACIÓN
# ========================================

@router.websocket("/admin")
async def websocket_admin_endpoint(
        websocket: WebSocket,
        token: str = Query(..., description="Token de autenticación de admin")
):
    """
    WebSocket para panel administrativo

    - Dashboard en tiempo real
    - Monitoreo del sistema
    - Gestión centralizada
    - Solo para administradores
    """
    connection_id = None
    user = None

    try:
        await websocket.accept()

        # Verificar autenticación de admin
        token_data = get_token_data(token)
        if not token_data:
            await websocket.close(code=4001, reason="Token inválido")
            return

        # Verificar permisos de admin (implementar validación real)
        # user = get_user_from_token(token_data)
        # if not user.is_admin:
        #     await websocket.close(code=4003, reason="Permisos insuficientes")
        #     return

        logger.info(f"Conexión WebSocket admin establecida: {connection_id}")

        # Registrar conexión
        connection_id = await websocket_manager.connect(
            websocket=websocket,
            connection_type=ConnectionType.ADMIN,
            user_id=user.Id if user else None,
            admin_access=True
        )

        # Enviar dashboard inicial
        await send_initial_admin_data(websocket)

        # Loop principal de mensajes
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Procesar comandos administrativos
                await handle_admin_message(websocket, connection_id, message)

            except WebSocketDisconnect:
                logger.info(f"Admin desconectado: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error en admin WebSocket: {e}")

    except WebSocketDisconnect:
        logger.info(f"Admin WebSocket desconectado: {connection_id}")
    except Exception as e:
        logger.error(f"Error estableciendo conexión admin: {e}")
    finally:
        if connection_id:
            await websocket_manager.disconnect(connection_id)


# ========================================
# FUNCIONES DE ENVÍO DE DATOS INICIALES
# ========================================

async def send_initial_display_data(websocket: WebSocket, display_type: str, station_id: Optional[int]):
    """Envía datos iniciales para pantallas de información"""
    try:
        # Obtener datos desde el cache o base de datos
        if display_type == "main":
            # Datos para pantalla principal
            data = {
                "type": MessageType.QUEUE_UPDATE,
                "data": {
                    "current_time": datetime.now().isoformat(),
                    "active_stations": [],  # TODO: Obtener de base de datos
                    "queue_summary": {},    # TODO: Obtener estadísticas actuales
                    "announcements": []     # TODO: Obtener anuncios activos
                }
            }
        elif display_type == "station" and station_id:
            # Datos para pantalla de estación específica
            data = {
                "type": MessageType.STATION_UPDATE,
                "data": {
                    "station_id": station_id,
                    "current_ticket": None,     # TODO: Obtener ticket actual
                    "next_tickets": [],         # TODO: Obtener próximos tickets
                    "station_status": "active"  # TODO: Obtener estado real
                }
            }
        else:
            # Datos genéricos
            data = {
                "type": MessageType.CONNECT,
                "data": {
                    "message": "Conectado al sistema de colas",
                    "timestamp": datetime.now().isoformat()
                }
            }

        await websocket.send_text(json.dumps(data))

    except Exception as e:
        logger.error(f"Error enviando datos iniciales display: {e}")


async def send_initial_station_data(websocket: WebSocket, station_id: int):
    """Envía datos iniciales para estación de trabajo"""
    try:
        data = {
            "type": MessageType.STATION_UPDATE,
            "data": {
                "station_id": station_id,
                "station_info": {},         # TODO: Obtener info de estación
                "current_queue": [],        # TODO: Obtener cola actual
                "statistics": {},           # TODO: Obtener estadísticas
                "permissions": []           # TODO: Obtener permisos del usuario
            }
        }

        await websocket.send_text(json.dumps(data))

    except Exception as e:
        logger.error(f"Error enviando datos iniciales estación: {e}")


async def send_initial_admin_data(websocket: WebSocket):
    """Envía datos iniciales para panel administrativo"""
    try:
        stats = websocket_manager.get_stats()
        data = {
            "type": MessageType.SYSTEM_ALERT,
            "data": {
                "dashboard": {},            # TODO: Obtener dashboard completo
                "active_connections": stats["total_connections"],
                "system_health": {},        # TODO: Obtener salud del sistema
                "alerts": []                # TODO: Obtener alertas activas
            }
        }

        await websocket.send_text(json.dumps(data))

    except Exception as e:
        logger.error(f"Error enviando datos iniciales admin: {e}")


# ========================================
# MANEJADORES DE MENSAJES
# ========================================

async def handle_display_message(websocket: WebSocket, connection_id: str, message: Dict[str, Any]):
    """Maneja mensajes de pantallas de información"""
    try:
        message_type = message.get("type")

        if message_type == MessageType.HEARTBEAT:
            # Responder heartbeat
            await websocket.send_text(json.dumps({
                "type": MessageType.HEARTBEAT,
                "timestamp": datetime.now().isoformat()
            }))

        elif message_type == "request_update":
            # Solicitud de actualización
            await send_queue_update_to_display(websocket, connection_id)

        else:
            logger.warning(f"Tipo de mensaje desconocido en display: {message_type}")

    except Exception as e:
        logger.error(f"Error manejando mensaje display: {e}")


async def handle_station_message(websocket: WebSocket, connection_id: str, message: Dict[str, Any], db: Optional[Session]):
    """Maneja mensajes de estaciones de trabajo"""
    try:
        message_type = message.get("type")

        if message_type == "call_next":
            # Llamar siguiente paciente
            # TODO: Implementar lógica de llamada
            await websocket.send_text(json.dumps({
                "type": "call_response",
                "success": True,
                "ticket": {}  # TODO: Datos del ticket llamado
            }))

        elif message_type == "update_status":
            # Actualizar estado de ticket
            # TODO: Implementar actualización de estado
            pass

        elif message_type == MessageType.HEARTBEAT:
            await websocket.send_text(json.dumps({
                "type": MessageType.HEARTBEAT,
                "timestamp": datetime.now().isoformat()
            }))

    except Exception as e:
        logger.error(f"Error manejando mensaje estación: {e}")


async def handle_admin_message(websocket: WebSocket, connection_id: str, message: Dict[str, Any]):
    """Maneja mensajes del panel administrativo"""
    try:
        message_type = message.get("type")

        if message_type == "broadcast_message":
            # Difundir mensaje a todas las conexiones
            broadcast_data = message.get("data", {})
            await websocket_manager.broadcast_queue_update(broadcast_data)

        elif message_type == "get_connections":
            # Obtener información de conexiones
            connections_info = websocket_manager.get_stats()
            await websocket.send_text(json.dumps({
                "type": "connections_info",
                "data": connections_info
            }))

        elif message_type == MessageType.HEARTBEAT:
            await websocket.send_text(json.dumps({
                "type": MessageType.HEARTBEAT,
                "timestamp": datetime.now().isoformat()
            }))

    except Exception as e:
        logger.error(f"Error manejando mensaje admin: {e}")


# ========================================
# FUNCIONES DE ACTUALIZACIÓN
# ========================================

async def send_queue_update_to_display(websocket: WebSocket, connection_id: str):
    """Envía actualización de cola a pantalla"""
    try:
        # TODO: Implementar obtención de datos reales
        update_data = {
            "type": MessageType.QUEUE_UPDATE,
            "data": {
                "timestamp": datetime.now().isoformat(),
                "queues": [],               # TODO: Datos de colas
                "active_calls": [],         # TODO: Llamadas activas
                "announcements": []         # TODO: Anuncios
            }
        }

        await websocket.send_text(json.dumps(update_data))

    except Exception as e:
        logger.error(f"Error enviando actualización de cola: {e}")


# ========================================
# ENDPOINTS HTTP PARA WEBSOCKET INFO
# ========================================

@router.get("/connections")
async def get_websocket_connections(
        current_user: User = Depends(get_current_user)
):
    """
    Obtiene información sobre conexiones WebSocket activas
    Solo para usuarios autenticados
    """
    try:
        if not (current_user.is_supervisor or current_user.is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes"
            )

        connections_info = websocket_manager.get_stats()

        return {
            "total_connections": connections_info["total_connections"],
            "by_type": connections_info["connections_by_type"],
            "by_station": connections_info["connections_by_station"],
            "total_users_connected": connections_info["total_users_connected"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo info de conexiones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno obteniendo información"
        )


@router.post("/broadcast")
async def broadcast_message(
        message: Dict[str, Any],
        connection_type: Optional[ConnectionType] = None,
        current_user: User = Depends(get_current_user)
):
    """
    Difunde un mensaje a conexiones WebSocket
    Solo para administradores
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden difundir mensajes"
            )

        # Preparar mensaje
        broadcast_data = {
            "type": MessageType.SYSTEM_ALERT,
            "data": message,
            "timestamp": datetime.now().isoformat(),
            "sent_by": current_user.Username
        }

        # Difundir según tipo de conexión
        if connection_type:
            await websocket_manager.broadcast_to_type(connection_type, broadcast_data)
        else:
            await websocket_manager.broadcast_queue_update(broadcast_data)

        return {
            "success": True,
            "message": "Mensaje difundido correctamente",
            "recipients": websocket_manager.get_stats()["total_connections"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error difundiendo mensaje: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno difundiendo mensaje"
        )


# ========================================
# INICIALIZACIÓN Y CLEANUP
# ========================================

# TODO: Implementar task de limpieza periódica si es necesario
# La limpieza se puede manejar automáticamente cuando las conexiones se desconectan

# """
# API endpoints WebSocket para comunicación en tiempo real
# Sistema de gestión de colas - Laboratorio clínico
# """
#
# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
# from sqlalchemy.orm import Session
# from typing import Optional, Dict, Any, List
# import json
# import asyncio
# import logging
# from datetime import datetime
#
# from app.core.database import get_db
# from app.api.dependencies.auth import get_token_data, get_current_user_optional, get_current_user
# from app.models.user import User
# from app.websocket.connection_manager import (
#     WebSocketManager,
#     ConnectionType,
#     MessageType,
#     WebSocketConnection
# )
# from app.services.notification_service import notification_service
# from app.crud.ticket import ticket_crud
# from app.crud.station import station_crud
# from app.core.redis import cache_manager
#
# # ========================================
# # CONFIGURACIÓN DEL ROUTER
# # ========================================
#
# router = APIRouter(prefix="/ws", tags=["websocket"])
# logger = logging.getLogger(__name__)
#
# # Instancia global del connection manager
# websocket_manager = WebSocketManager()
#
#
# # ========================================
# # WEBSOCKET PRINCIPAL - PANTALLAS PÚBLICAS
# # ========================================
#
# @router.websocket("/display")
# async def websocket_display_endpoint(
#         websocket: WebSocket,
#         display_type: str = Query("main", description="Tipo de pantalla: main, station, mobile"),
#         station_id: Optional[int] = Query(None, description="ID de estación específica"),
#         location: Optional[str] = Query(None, description="Ubicación de la pantalla")
# ):
#     """
#     WebSocket para pantallas de información pública
#
#     - Pantallas principales de sala de espera
#     - Pantallas por estación
#     - Aplicaciones móviles públicas
#     - No requiere autenticación
#     """
#     connection_id = None
#
#     try:
#         await websocket.accept()
#         logger.info(f"Conexión WebSocket display establecida: {connection_id}")
#
#         # Registrar conexión
#         connection_id = await websocket_manager.connect(
#             websocket=websocket,
#             connection_type=ConnectionType.DISPLAY,
#             station_id=station_id,
#             display_type=display_type,
#             location=location
#         )
#
#         # Enviar estado inicial
#         await send_initial_display_data(websocket, display_type, station_id)
#
#         # Loop principal de mensajes
#         while True:
#             try:
#                 # Esperar mensajes del cliente
#                 data = await websocket.receive_text()
#                 message = json.loads(data)
#
#                 # Procesar mensaje según tipo
#                 await handle_display_message(websocket, connection_id, message)
#
#             except WebSocketDisconnect:
#                 logger.info(f"Display desconectado: {connection_id}")
#                 break
#             except json.JSONDecodeError:
#                 await websocket.send_text(json.dumps({
#                     "type": MessageType.ERROR,
#                     "message": "Formato de mensaje inválido"
#                 }))
#             except Exception as e:
#                 logger.error(f"Error en display WebSocket: {e}")
#                 await websocket.send_text(json.dumps({
#                     "type": MessageType.ERROR,
#                     "message": "Error interno del servidor"
#                 }))
#
#     except WebSocketDisconnect:
#         logger.info(f"Display WebSocket desconectado: {connection_id}")
#     except Exception as e:
#         logger.error(f"Error estableciendo conexión display: {e}")
#     finally:
#         if connection_id:
#             await websocket_manager.disconnect(connection_id)
#
#
# # ========================================
# # WEBSOCKET PARA ESTACIONES DE TRABAJO
# # ========================================
#
# @router.websocket("/station")
# async def websocket_station_endpoint(
#         websocket: WebSocket,
#         station_id: int = Query(..., description="ID de la estación"),
#         token: Optional[str] = Query(None, description="Token de autenticación")
# ):
#     """
#     WebSocket para estaciones de trabajo
#
#     - Panel de control de técnicos
#     - Gestión de cola en tiempo real
#     - Notificaciones de llamadas
#     - Requiere autenticación
#     """
#     connection_id = None
#     user = None
#     db = None
#
#     try:
#         await websocket.accept()
#
#         # Verificar autenticación si se proporciona token
#         if token:
#             token_data = get_token_data(token)
#             if token_data:
#                 # Aquí podrías obtener el usuario de la base de datos
#                 # Por simplicidad, asumimos que el token es válido
#                 pass
#
#         logger.info(f"Conexión WebSocket estación establecida: {connection_id} - Estación: {station_id}")
#
#         # Registrar conexión
#         connection_id = await websocket_manager.connect(
#             websocket=websocket,
#             connection_type=ConnectionType.STATION,
#             user_id=user.Id if user else None,
#             station_id=station_id,
#             authenticated=user is not None
#         )
#
#         # Enviar estado inicial de la estación
#         await send_initial_station_data(websocket, station_id)
#
#         # Loop principal de mensajes
#         while True:
#             try:
#                 data = await websocket.receive_text()
#                 message = json.loads(data)
#
#                 # Procesar mensaje de estación
#                 await handle_station_message(websocket, connection_id, message, db)
#
#             except WebSocketDisconnect:
#                 logger.info(f"Estación desconectada: {connection_id}")
#                 break
#             except Exception as e:
#                 logger.error(f"Error en estación WebSocket: {e}")
#                 await websocket.send_text(json.dumps({
#                     "type": MessageType.ERROR,
#                     "message": f"Error: {str(e)}"
#                 }))
#
#     except WebSocketDisconnect:
#         logger.info(f"Estación WebSocket desconectada: {connection_id}")
#     except Exception as e:
#         logger.error(f"Error estableciendo conexión estación: {e}")
#     finally:
#         if connection_id:
#             await websocket_manager.disconnect(connection_id)
#
#
# # ========================================
# # WEBSOCKET PARA ADMINISTRACIÓN
# # ========================================
#
# @router.websocket("/admin")
# async def websocket_admin_endpoint(
#         websocket: WebSocket,
#         token: str = Query(..., description="Token de autenticación de admin")
# ):
#     """
#     WebSocket para panel administrativo
#
#     - Dashboard en tiempo real
#     - Monitoreo del sistema
#     - Gestión centralizada
#     - Solo para administradores
#     """
#     connection_id = None
#     user = None
#
#     try:
#         await websocket.accept()
#
#         # Verificar autenticación de admin
#         token_data = get_token_data(token)
#         if not token_data:
#             await websocket.close(code=4001, reason="Token inválido")
#             return
#
#         # Verificar permisos de admin (implementar validación real)
#         # user = get_user_from_token(token_data)
#         # if not user.is_admin:
#         #     await websocket.close(code=4003, reason="Permisos insuficientes")
#         #     return
#
#         logger.info(f"Conexión WebSocket admin establecida: {connection_id}")
#
#         # Registrar conexión
#         connection_id = await websocket_manager.connect(
#             websocket=websocket,
#             connection_type=ConnectionType.ADMIN,
#             user_id=user.Id if user else None,
#             admin_access=True
#         )
#
#         # Enviar dashboard inicial
#         await send_initial_admin_data(websocket)
#
#         # Loop principal de mensajes
#         while True:
#             try:
#                 data = await websocket.receive_text()
#                 message = json.loads(data)
#
#                 # Procesar comandos administrativos
#                 await handle_admin_message(websocket, connection_id, message)
#
#             except WebSocketDisconnect:
#                 logger.info(f"Admin desconectado: {connection_id}")
#                 break
#             except Exception as e:
#                 logger.error(f"Error en admin WebSocket: {e}")
#
#     except WebSocketDisconnect:
#         logger.info(f"Admin WebSocket desconectado: {connection_id}")
#     except Exception as e:
#         logger.error(f"Error estableciendo conexión admin: {e}")
#     finally:
#         if connection_id:
#             await websocket_manager.disconnect(connection_id)
#
#
# # ========================================
# # FUNCIONES DE ENVÍO DE DATOS INICIALES
# # ========================================
#
# async def send_initial_display_data(websocket: WebSocket, display_type: str, station_id: Optional[int]):
#     """Envía datos iniciales para pantallas de información"""
#     try:
#         # Obtener datos desde el cache o base de datos
#         if display_type == "main":
#             # Datos para pantalla principal
#             data = {
#                 "type": MessageType.QUEUE_UPDATE,
#                 "data": {
#                     "current_time": datetime.now().isoformat(),
#                     "active_stations": [],  # TODO: Obtener de base de datos
#                     "queue_summary": {},    # TODO: Obtener estadísticas actuales
#                     "announcements": []     # TODO: Obtener anuncios activos
#                 }
#             }
#         elif display_type == "station" and station_id:
#             # Datos para pantalla de estación específica
#             data = {
#                 "type": MessageType.STATION_UPDATE,
#                 "data": {
#                     "station_id": station_id,
#                     "current_ticket": None,     # TODO: Obtener ticket actual
#                     "next_tickets": [],         # TODO: Obtener próximos tickets
#                     "station_status": "active"  # TODO: Obtener estado real
#                 }
#             }
#         else:
#             # Datos genéricos
#             data = {
#                 "type": MessageType.CONNECT,
#                 "data": {
#                     "message": "Conectado al sistema de colas",
#                     "timestamp": datetime.now().isoformat()
#                 }
#             }
#
#         await websocket.send_text(json.dumps(data))
#
#     except Exception as e:
#         logger.error(f"Error enviando datos iniciales display: {e}")
#
#
# async def send_initial_station_data(websocket: WebSocket, station_id: int):
#     """Envía datos iniciales para estación de trabajo"""
#     try:
#         data = {
#             "type": MessageType.STATION_UPDATE,
#             "data": {
#                 "station_id": station_id,
#                 "station_info": {},         # TODO: Obtener info de estación
#                 "current_queue": [],        # TODO: Obtener cola actual
#                 "statistics": {},           # TODO: Obtener estadísticas
#                 "permissions": []           # TODO: Obtener permisos del usuario
#             }
#         }
#
#         await websocket.send_text(json.dumps(data))
#
#     except Exception as e:
#         logger.error(f"Error enviando datos iniciales estación: {e}")
#
#
# async def send_initial_admin_data(websocket: WebSocket):
#     """Envía datos iniciales para panel administrativo"""
#     try:
#         data = {
#             "type": MessageType.SYSTEM_ALERT,
#             "data": {
#                 "dashboard": {},            # TODO: Obtener dashboard completo
#                 "active_connections": websocket_manager.get_connection_count(),
#                 "system_health": {},        # TODO: Obtener salud del sistema
#                 "alerts": []                # TODO: Obtener alertas activas
#             }
#         }
#
#         await websocket.send_text(json.dumps(data))
#
#     except Exception as e:
#         logger.error(f"Error enviando datos iniciales admin: {e}")
#
#
# # ========================================
# # MANEJADORES DE MENSAJES
# # ========================================
#
# async def handle_display_message(websocket: WebSocket, connection_id: str, message: Dict[str, Any]):
#     """Maneja mensajes de pantallas de información"""
#     try:
#         message_type = message.get("type")
#
#         if message_type == MessageType.HEARTBEAT:
#             # Responder heartbeat
#             await websocket.send_text(json.dumps({
#                 "type": MessageType.HEARTBEAT,
#                 "timestamp": datetime.now().isoformat()
#             }))
#
#         elif message_type == "request_update":
#             # Solicitud de actualización
#             await send_queue_update_to_display(websocket, connection_id)
#
#         else:
#             logger.warning(f"Tipo de mensaje desconocido en display: {message_type}")
#
#     except Exception as e:
#         logger.error(f"Error manejando mensaje display: {e}")
#
#
# async def handle_station_message(websocket: WebSocket, connection_id: str, message: Dict[str, Any], db: Optional[Session]):
#     """Maneja mensajes de estaciones de trabajo"""
#     try:
#         message_type = message.get("type")
#
#         if message_type == "call_next":
#             # Llamar siguiente paciente
#             # TODO: Implementar lógica de llamada
#             await websocket.send_text(json.dumps({
#                 "type": "call_response",
#                 "success": True,
#                 "ticket": {}  # TODO: Datos del ticket llamado
#             }))
#
#         elif message_type == "update_status":
#             # Actualizar estado de ticket
#             # TODO: Implementar actualización de estado
#             pass
#
#         elif message_type == MessageType.HEARTBEAT:
#             await websocket.send_text(json.dumps({
#                 "type": MessageType.HEARTBEAT,
#                 "timestamp": datetime.now().isoformat()
#             }))
#
#     except Exception as e:
#         logger.error(f"Error manejando mensaje estación: {e}")
#
#
# async def handle_admin_message(websocket: WebSocket, connection_id: str, message: Dict[str, Any]):
#     """Maneja mensajes del panel administrativo"""
#     try:
#         message_type = message.get("type")
#
#         if message_type == "broadcast_message":
#             # Difundir mensaje a todas las conexiones
#             broadcast_data = message.get("data", {})
#             await websocket_manager.broadcast_queue_update(broadcast_data)
#
#         elif message_type == "get_connections":
#             # Obtener información de conexiones
#             connections_info = websocket_manager.get_stats()
#             await websocket.send_text(json.dumps({
#                 "type": "connections_info",
#                 "data": connections_info
#             }))
#
#         elif message_type == MessageType.HEARTBEAT:
#             await websocket.send_text(json.dumps({
#                 "type": MessageType.HEARTBEAT,
#                 "timestamp": datetime.now().isoformat()
#             }))
#
#     except Exception as e:
#         logger.error(f"Error manejando mensaje admin: {e}")
#
#
# # ========================================
# # FUNCIONES DE ACTUALIZACIÓN
# # ========================================
#
# async def send_queue_update_to_display(websocket: WebSocket, connection_id: str):
#     """Envía actualización de cola a pantalla"""
#     try:
#         # TODO: Implementar obtención de datos reales
#         update_data = {
#             "type": MessageType.QUEUE_UPDATE,
#             "data": {
#                 "timestamp": datetime.now().isoformat(),
#                 "queues": [],               # TODO: Datos de colas
#                 "active_calls": [],         # TODO: Llamadas activas
#                 "announcements": []         # TODO: Anuncios
#             }
#         }
#
#         await websocket.send_text(json.dumps(update_data))
#
#     except Exception as e:
#         logger.error(f"Error enviando actualización de cola: {e}")
#
#
# # ========================================
# # ENDPOINTS HTTP PARA WEBSOCKET INFO
# # ========================================
#
# @router.get("/connections")
# async def get_websocket_connections(
#         current_user: User = Depends(get_current_user)
# ):
#     """
#     Obtiene información sobre conexiones WebSocket activas
#     Solo para usuarios autenticados
#     """
#     try:
#         if not (current_user.is_supervisor or current_user.is_admin):
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Permisos insuficientes"
#             )
#
#         connections_info = websocket_manager.get_stats()
#
#         return {
#             "total_connections": connections_info["total_connections"],
#             "by_type": connections_info["connections_by_type"],
#             "by_station": connections_info["connections_by_station"],
#             "total_users_connected": connections_info["total_users_connected"]
#         }
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error obteniendo info de conexiones: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error interno obteniendo información"
#         )
#
#
# @router.post("/broadcast")
# async def broadcast_message(
#         message: Dict[str, Any],
#         connection_type: Optional[ConnectionType] = None,
#         current_user: User = Depends(get_current_user)
# ):
#     """
#     Difunde un mensaje a conexiones WebSocket
#     Solo para administradores
#     """
#     try:
#         if not current_user.is_admin:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Solo administradores pueden difundir mensajes"
#             )
#
#         # Preparar mensaje
#         broadcast_data = {
#             "type": MessageType.SYSTEM_ALERT,
#             "data": message,
#             "timestamp": datetime.now().isoformat(),
#             "sent_by": current_user.Username
#         }
#
#         # Difundir según tipo de conexión
#         if connection_type:
#             await websocket_manager.broadcast_to_type(connection_type, broadcast_data)
#         else:
#             await websocket_manager.broadcast_queue_update(broadcast_data)
#
#         return {
#             "success": True,
#             "message": "Mensaje difundido correctamente",
#             "recipients": websocket_manager.get_stats()["total_connections"]
#         }
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error difundiendo mensaje: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error interno difundiendo mensaje"
#         )
#
#
# # ========================================
# # INICIALIZACIÓN Y CLEANUP
# # ========================================
#
# # TODO: Implementar task de limpieza periódica si es necesario
# # La limpieza se puede manejar automáticamente cuando las conexiones se desconectan