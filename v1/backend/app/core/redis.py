import redis
from redis.asyncio import Redis as AsyncRedis
import json
import pickle
from typing import Any, Optional, Union, Dict, List
import logging
from datetime import datetime, timedelta
from .config import settings

# ========================================
# CONFIGURACIÓN DE LOGGING
# ========================================
logger = logging.getLogger(__name__)

# ========================================
# CONFIGURACIÓN DE REDIS
# ========================================

# Cliente Redis síncrono
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )

    # Verificar conexión
    redis_client.ping()
    logger.info("✅ Cliente Redis síncrono conectado correctamente")

except Exception as e:
    logger.error(f"❌ Error conectando a Redis síncrono: {e}")
    redis_client = None

# Cliente Redis asíncrono (para FastAPI)
async_redis_client = None


async def init_async_redis():
    """
    Inicializa el cliente Redis asíncrono
    """
    global async_redis_client
    try:
        async_redis_client = AsyncRedis.from_url(
            settings.redis_url_complete,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )

        # Verificar conexión
        await async_redis_client.ping()
        logger.info("Cliente Redis asíncrono conectado correctamente")

    except Exception as e:
        logger.error(f"Error conectando a Redis asíncrono: {e}")
        async_redis_client = None


async def close_async_redis():
    """
    Cierra la conexión Redis asíncrona
    """
    global async_redis_client
    if async_redis_client:
        await async_redis_client.close()
        logger.info("Cliente Redis asíncrono cerrado")


# ========================================
# CLASES DE GESTIÓN DE CACHE
# ========================================

class CacheManager:
    """
    Gestor de cache para operaciones comunes
    """

    def __init__(self, client=None):
        self.client = client or redis_client
        self.default_expire = settings.REDIS_EXPIRE_SECONDS

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Establece un valor en cache
        """
        try:
            expire_time = expire or self.default_expire

            # Serializar valor según el tipo
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            elif isinstance(value, (datetime,)):
                serialized_value = value.isoformat()
            else:
                serialized_value = str(value)

            result = self.client.setex(key, expire_time, serialized_value)
            logger.debug(f"Cache SET: {key} (expire: {expire_time}s)")
            return result

        except Exception as e:
            logger.error(f"Error setting cache {key}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor del cache
        """
        try:
            value = self.client.get(key)

            if value is None:
                logger.debug(f"🔍 Cache MISS: {key}")
                return default

            # Intentar deserializar JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Si no es JSON, devolver como string
                logger.debug(f"Cache HIT: {key}")
                return value

        except Exception as e:
            logger.error(f"Error getting cache {key}: {e}")
            return default

    def delete(self, key: str) -> bool:
        """
        Elimina una clave del cache
        """
        try:
            result = self.client.delete(key)
            logger.debug(f"🗑️ Cache DELETE: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting cache {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Verifica si una clave existe en cache
        """
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Error checking cache {key}: {e}")
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """
        Establece tiempo de expiración para una clave
        """
        try:
            result = self.client.expire(key, seconds)
            logger.debug(f"Cache EXPIRE: {key} ({seconds}s)")
            return bool(result)
        except Exception as e:
            logger.error(f"Error setting expiration {key}: {e}")
            return False

    def get_ttl(self, key: str) -> int:
        """
        Obtiene el tiempo de vida restante de una clave
        """
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL {key}: {e}")
            return -1


# ========================================
# GESTOR DE COLAS
# ========================================

class QueueManager:
    """
    Gestor de colas en Redis para el sistema de turnos
    """

    def __init__(self, client=None):
        self.client = client or redis_client
        self.queue_prefix = "queue:"
        self.stats_prefix = "queue_stats:"

    def add_to_queue(self, service_type_id: int, ticket_data: dict) -> bool:
        """
        Agrega un ticket a la cola de un servicio
        """
        try:
            queue_key = f"{self.queue_prefix}{service_type_id}"
            ticket_json = json.dumps(ticket_data, default=str)

            # Agregar a la cola (lista)
            result = self.client.lpush(queue_key, ticket_json)

            # Actualizar estadísticas
            self._update_queue_stats(service_type_id)

            logger.debug(f"Ticket agregado a cola {service_type_id}: {ticket_data.get('ticket_number')}")
            return bool(result)

        except Exception as e:
            logger.error(f"Error agregando a cola {service_type_id}: {e}")
            return False

    def get_next_ticket(self, service_type_id: int) -> Optional[dict]:
        """
        Obtiene el siguiente ticket de la cola
        """
        try:
            queue_key = f"{self.queue_prefix}{service_type_id}"
            ticket_json = self.client.rpop(queue_key)

            if ticket_json:
                ticket_data = json.loads(ticket_json)
                self._update_queue_stats(service_type_id)
                logger.debug(f"📤 Ticket obtenido de cola {service_type_id}: {ticket_data.get('ticket_number')}")
                return ticket_data

            return None

        except Exception as e:
            logger.error(f"Error obteniendo de cola {service_type_id}: {e}")
            return None

    def get_queue_length(self, service_type_id: int) -> int:
        """
        Obtiene la longitud de una cola
        """
        try:
            queue_key = f"{self.queue_prefix}{service_type_id}"
            length = self.client.llen(queue_key)
            return length
        except Exception as e:
            logger.error(f"Error obteniendo longitud de cola {service_type_id}: {e}")
            return 0

    def get_queue_tickets(self, service_type_id: int, limit: int = 10) -> List[dict]:
        """
        Obtiene los tickets en cola sin removerlos
        """
        try:
            queue_key = f"{self.queue_prefix}{service_type_id}"
            tickets_json = self.client.lrange(queue_key, 0, limit - 1)

            tickets = []
            for ticket_json in tickets_json:
                try:
                    ticket_data = json.loads(ticket_json)
                    tickets.append(ticket_data)
                except json.JSONDecodeError:
                    continue

            return tickets

        except Exception as e:
            logger.error(f"Error obteniendo tickets de cola {service_type_id}: {e}")
            return []

    def clear_queue(self, service_type_id: int) -> bool:
        """
        Limpia una cola específica
        """
        try:
            queue_key = f"{self.queue_prefix}{service_type_id}"
            result = self.client.delete(queue_key)
            self._update_queue_stats(service_type_id)
            logger.warning(f"🗑️ Cola {service_type_id} limpiada")
            return bool(result)
        except Exception as e:
            logger.error(f"Error limpiando cola {service_type_id}: {e}")
            return False

    def _update_queue_stats(self, service_type_id: int):
        """
        Actualiza las estadísticas de una cola
        """
        try:
            stats_key = f"{self.stats_prefix}{service_type_id}"
            length = self.get_queue_length(service_type_id)

            stats = {
                "length": length,
                "last_updated": datetime.now().isoformat()
            }

            self.client.setex(stats_key, 3600, json.dumps(stats))  # 1 hora

        except Exception as e:
            logger.debug(f"Error actualizando stats de cola {service_type_id}: {e}")


# ========================================
# GESTOR DE SESIONES
# ========================================

class SessionManager:
    """
    Gestor de sesiones de usuario en Redis
    """

    def __init__(self, client=None):
        self.client = client or redis_client
        self.session_prefix = "session:"
        self.default_expire = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def create_session(self, user_id: str, session_data: dict, expire: Optional[int] = None) -> str:
        """
        Crea una nueva sesión
        """
        try:
            import uuid
            session_id = str(uuid.uuid4())
            session_key = f"{self.session_prefix}{session_id}"
            expire_time = expire or self.default_expire

            session_info = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(seconds=expire_time)).isoformat(),
                **session_data
            }

            self.client.setex(session_key, expire_time, json.dumps(session_info))
            logger.debug(f"Sesión creada: {session_id} para usuario {user_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error creando sesión: {e}")
            return None

    def get_session(self, session_id: str) -> Optional[dict]:
        """
        Obtiene datos de una sesión
        """
        try:
            session_key = f"{self.session_prefix}{session_id}"
            session_data = self.client.get(session_key)

            if session_data:
                return json.loads(session_data)
            return None

        except Exception as e:
            logger.error(f"Error obteniendo sesión {session_id}: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """
        Elimina una sesión
        """
        try:
            session_key = f"{self.session_prefix}{session_id}"
            result = self.client.delete(session_key)
            logger.debug(f"Sesión eliminada: {session_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error eliminando sesión {session_id}: {e}")
            return False


# ========================================
# INSTANCIAS GLOBALES
# ========================================

# Crear instancias de los gestores
cache_manager = CacheManager(redis_client) if redis_client else None
queue_manager = QueueManager(redis_client) if redis_client else None
session_manager = SessionManager(redis_client) if redis_client else None


# ========================================
# FUNCIONES UTILITARIAS
# ========================================

def check_redis_connection() -> bool:
    """
    Verifica si Redis está conectado
    """
    try:
        if redis_client:
            redis_client.ping()
            return True
        return False
    except Exception as e:
        logger.error(f"Error verificando conexión Redis: {e}")
        return False


def get_redis_info() -> dict:
    """
    Obtiene información sobre Redis
    """
    try:
        if not redis_client:
            return {"error": "Redis no disponible"}

        info = redis_client.info()
        return {
            "version": info.get("redis_version"),
            "uptime": info.get("uptime_in_seconds"),
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "total_connections_received": info.get("total_connections_received"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses")
        }
    except Exception as e:
        logger.error(f"Error obteniendo info de Redis: {e}")
        return {"error": str(e)}


def clear_all_cache(pattern: str = "*") -> int:
    """
    Limpia cache con patrón específico
    """
    try:
        if not redis_client:
            return 0

        keys = redis_client.keys(pattern)
        if keys:
            count = redis_client.delete(*keys)
            logger.warning(f"Cache limpiado: {count} claves eliminadas con patrón '{pattern}'")
            return count
        return 0
    except Exception as e:
        logger.error(f"Error limpiando cache: {e}")
        return 0


# ========================================
# FUNCIONES DE INICIALIZACIÓN
# ========================================

def init_redis():
    """
    Inicializa Redis y verifica la conexión
    """
    logger.info("Inicializando conexión a Redis...")

    if not check_redis_connection():
        logger.warning("Redis no está disponible - funcionando sin cache")
        return False

    # Obtener información de Redis
    redis_info = get_redis_info()
    if "error" not in redis_info:
        logger.info(f"Redis v{redis_info['version']} - Memoria: {redis_info['used_memory']}")
        logger.info(f"Clientes conectados: {redis_info['connected_clients']}")

    logger.info("Redis inicializado correctamente")
    return True


# ========================================
# INICIALIZACIÓN AUTOMÁTICA
# ========================================

# Inicializar automáticamente al importar el módulo
redis_available = init_redis()