from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging
from .config import settings

# ========================================
# CONFIGURACIÓN DE LOGGING
# ========================================
logger = logging.getLogger(__name__)

# ========================================
# CONFIGURACIÓN DEL ENGINE
# ========================================

# Configuración simplificada y robusta para SQL Server
engine_config = {
    "echo": settings.DEBUG,  # Log de queries SQL en debug
    "pool_pre_ping": True,  # Verifica conexiones antes de usarlas
    "pool_recycle": 3600,  # Reciclar conexiones cada hora
}

# Para SQL Server, agregar configuración de pool solo si es necesario
database_url = settings.database_url_sync
if "mssql" in database_url.lower():
    engine_config.update({
        "pool_size": 10,  # Tamaño conservador del pool
        "max_overflow": 20,  # Overflow conservador
        "pool_timeout": 30,  # Timeout razonable
    })

# Crear engine de SQLAlchemy
try:
    engine = create_engine(database_url, **engine_config)
    logger.info("Engine de base de datos creado correctamente")
    logger.info(f"URL: {database_url.split('@')[0]}@***")  # Log sin credenciales
except Exception as e:
    logger.error(f" Error creando engine de base de datos: {e}")
    raise

# ========================================
# CONFIGURACIÓN DE SESIONES
# ========================================

# Configurar SessionLocal
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos SQLAlchemy
Base = declarative_base()


# ========================================
# EVENTOS DE CONEXIÓN (CORREGIDOS)
# ========================================

@event.listens_for(engine, "connect")
def set_sql_server_options(dbapi_connection, connection_record):
    """
    Configuraciones específicas para SQL Server al conectar
    CORREGIDO: Usar cursor directo sin SQLAlchemy text()
    """
    try:
        with dbapi_connection.cursor() as cursor:
            # Configuraciones de SQL Server para mejor rendimiento
            cursor.execute("SET ANSI_NULLS ON")
            cursor.execute("SET ANSI_PADDING ON")
            cursor.execute("SET ANSI_WARNINGS ON")
            cursor.execute("SET CONCAT_NULL_YIELDS_NULL ON")
            cursor.execute("SET QUOTED_IDENTIFIER ON")

            # Configuración de timeout
            cursor.execute("SET LOCK_TIMEOUT 30000")  # 30 segundos

            # Configuración de fecha
            cursor.execute("SET DATEFORMAT dmy")

            logger.debug("Configuraciones SQL Server aplicadas")
    except Exception as e:
        logger.warning(f"! Error configurando SQL Server: {e}")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """
    Evento cuando se toma una conexión del pool
    """
    logger.debug("Conexión tomada del pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """
    Evento cuando se devuelve una conexión al pool
    """
    logger.debug("Conexión devuelta al pool")


# ========================================
# DEPENDENCIAS DE SESIÓN
# ========================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependencia de FastAPI para obtener una sesión de base de datos.
    Se asegura de cerrar la sesión después de cada request.
    """
    db = SessionLocal()
    try:
        logger.debug("Nueva sesión de BD creada")
        yield db
        logger.debug("Sesión de BD completada exitosamente")
    except Exception as e:
        logger.error(f" Error en sesión de BD: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Sesión de BD cerrada")


# ========================================
# FUNCIONES UTILITARIAS
# ========================================

def create_all_tables():
    """
    Crea todas las tablas definidas en los modelos
    """
    try:
        logger.info("Creando tablas de base de datos...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas creadas correctamente")
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")
        raise


def drop_all_tables():
    """
    Elimina todas las tablas (¡USAR CON CUIDADO!)
    """
    if not settings.is_development:
        raise Exception("No se pueden eliminar tablas en producción")

    try:
        logger.warning("Eliminando todas las tablas...")
        Base.metadata.drop_all(bind=engine)
        logger.warning("Tablas eliminadas")
    except Exception as e:
        logger.error(f"Error eliminando tablas: {e}")
        raise


def check_database_connection() -> bool:
    """
    Verifica si la conexión a la base de datos está funcionando
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]

            if test_value == 1:
                logger.info("Conexión a base de datos verificada correctamente")
                return True
            else:
                logger.error("Test de conexión falló")
                return False

    except Exception as e:
        logger.error(f"Error verificando conexión a BD: {e}")
        return False


def get_database_info() -> dict:
    """
    Obtiene información sobre la base de datos
    """
    try:
        with engine.connect() as connection:
            # Información del servidor
            server_info = connection.execute(
                text("""
                SELECT 
                    @@SERVERNAME as server_name,
                    @@VERSION as version,
                    DB_NAME() as database_name,
                    SYSTEM_USER as user_name,
                    GETDATE() as [current_time]
                """)
            ).fetchone()

            # Información de la base de datos
            db_info = connection.execute(
                text("""
                SELECT 
                    name,
                    database_id,
                    create_date,
                    collation_name,
                    state_desc
                FROM sys.databases 
                WHERE name = DB_NAME()
                """)
            ).fetchone()

            return {
                "server_name": server_info[0],
                "version": server_info[1].split('\n')[0],  # Solo la primera línea
                "database_name": server_info[2],
                "user_name": server_info[3],
                "current_time": server_info[4],
                "database_id": db_info[1],
                "create_date": db_info[2],
                "collation": db_info[3],
                "state": db_info[4],
                "connection_pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW
            }

    except Exception as e:
        logger.error(f" Error obteniendo información de BD: {e}")
        return {"error": str(e)}


def execute_raw_sql(sql: str, params: dict = None) -> list:
    """
    Ejecuta SQL crudo
    """
    try:
        with engine.connect() as connection:
            stmt = text(sql)
            result = connection.execute(stmt, params or {})
            return result.fetchall()
    except Exception as e:
        logger.error(f" Error ejecutando SQL: {e}")
        raise


# ========================================
# CONTEXT MANAGERS
# ========================================

class DatabaseTransaction:
    """
    Context manager para transacciones de base de datos
    """

    def __init__(self):
        self.db = None

    def __enter__(self) -> Session:
        self.db = SessionLocal()
        logger.debug("Transacción iniciada")
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self.db.commit()
                logger.debug("Transacción confirmada")
            else:
                self.db.rollback()
                logger.error(f"Transacción revertida: {exc_val}")
        finally:
            self.db.close()
            logger.debug("Transacción finalizada")


# ========================================
# FUNCIÓN DE INICIALIZACIÓN
# ========================================

def init_database():
    """
    Inicializa la base de datos y verifica la conexión
    """
    logger.info("Inicializando conexión a base de datos...")

    # Verificar conexión
    if not check_database_connection():
        raise Exception("No se pudo conectar a la base de datos")

    # Obtener información de la BD
    db_info = get_database_info()
    if "error" not in db_info:
        logger.info(f"Conectado a: {db_info['database_name']} en {db_info['server_name']}")
        logger.info(f"Pool de conexiones: {db_info['connection_pool_size']} + {db_info['max_overflow']} overflow")

    logger.info("Base de datos inicializada correctamente")


# ========================================
# INICIALIZACIÓN AUTOMÁTICA
# ========================================

# Inicializar automáticamente al importar el módulo
try:
    init_database()
except Exception as e:
    logger.error(f"Error inicializando base de datos: {e}")
    # No hacer raise aquí para permitir que la app inicie y muestre el error