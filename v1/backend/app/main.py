"""
Sistema de Gestión de Colas para Laboratorio Clínico
Aplicación principal FastAPI
Compatible 100% con toda la estructura existente
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import uvicorn
import os
from pathlib import Path

# Importaciones del proyecto
from app.core.config import settings
from app.core.database import init_database, check_database_connection
from app.core.redis import init_async_redis, close_async_redis, redis_available
from app.core.security import init_security

# ========================================
# IMPORTAR TODOS LOS ROUTERS DISPONIBLES
# ========================================

# Routers principales ya implementados
from app.api.v1.endpoints.tickets import router as tickets_router
from app.api.v1.endpoints.patients import router as patients_router

# Routers recién implementados - ACTIVADOS
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.stations import router as stations_router
from app.api.v1.endpoints.service_types import router as service_types_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.queue import router as queue_router
from app.api.v1.endpoints.websocket import router as websocket_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.display import router as display_router
# Routers pendientes por implementar - COMENTADOS
# from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.reports import router as reports_router

# ========================================
# CONFIGURACIÓN DE LOGGING
# ========================================

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE_PATH) if os.path.exists(
            os.path.dirname(settings.LOG_FILE_PATH)) else logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ========================================
# EVENTOS DE CICLO DE VIDA
# ========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación
    """
    # STARTUP
    logger.info("Iniciando Sistema de Gestión de Colas...")

    try:
        # Inicializar base de datos
        logger.info("Inicializando base de datos...")
        init_database()

        # Verificar conexión a base de datos
        if not check_database_connection():
            logger.error("No se pudo conectar a la base de datos")
            raise Exception("Error de conexión a base de datos")

        # Inicializar Redis asíncrono
        logger.info("Inicializando Redis...")
        await init_async_redis()

        # Inicializar sistema de seguridad
        logger.info("Inicializando sistema de seguridad...")
        init_security()

        # Crear directorios necesarios
        logger.info("Creando directorios necesarios...")
        settings.ensure_directories()

        logger.info("Aplicación iniciada correctamente")
        logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"Entorno: {settings.ENVIRONMENT}")
        logger.info(f"Debug: {settings.DEBUG}")

        yield

    except Exception as e:
        logger.error(f"Error durante la inicialización: {e}")
        raise

    # SHUTDOWN
    logger.info("Cerrando Sistema de Gestión de Colas...")

    # Cerrar conexiones Redis
    await close_async_redis()

    logger.info("Aplicación cerrada correctamente")


# ========================================
# CREAR APLICACIÓN FASTAPI
# ========================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Sistema de Gestión de Colas para Laboratorio Clínico

    ## Características principales:

    * **Gestión de Pacientes** - Registro y búsqueda con API externa
    * **Sistema de Tickets** - Generación automática de turnos con QR
    * **Control de Colas** - Gestión inteligente en tiempo real
    * **Estaciones de Trabajo** - Multi-ventanilla con balanceo de carga
    * **Autenticación** - JWT con roles y permisos granulares
    * **Usuarios** - Gestión completa con perfiles y actividad
    * **WebSocket** - Comunicación en tiempo real para displays
    * **Notificaciones** - SMS, Email y tiempo real
    * **Reportes** - Analytics y métricas operacionales

    Compatible con SQL Server, Redis y APIs externas.
    """,
    contact={
        "name": "Sistema de Gestión de Colas",
        "email": "soporte@laboratorio.com",
    },
    license_info={
        "name": "Propietario",
    },
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# ========================================
# MIDDLEWARE DE SEGURIDAD
# ========================================

# CORS - Configurado desde settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=settings.get_cors_methods(),
    allow_headers=settings.get_cors_headers(),
)

# Trusted Host (solo en producción)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configurar hosts específicos en producción
    )


# ========================================
# MIDDLEWARE PERSONALIZADO
# ========================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log de requests HTTP para monitoreo
    """
    start_time = time.time()

    # Log request
    logger.debug(f"Request: {request.method} {request.url}")

    # Procesar request
    response = await call_next(request)

    # Calcular tiempo de procesamiento
    process_time = time.time() - start_time

    # Log response
    logger.debug(
        f"Response: {response.status_code} | "
        f"Time: {process_time:.4f}s | "
        f"Path: {request.url.path}"
    )

    # Agregar header con tiempo de procesamiento
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Manejador global de excepciones
    """
    logger.error(f"Error no controlado: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor",
            "message": "Ha ocurrido un error inesperado",
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )


# ========================================
# ENDPOINT DE SALUD DEL SISTEMA
# ========================================

@app.get("/health", tags=["sistema"])
async def health_check():
    """
    Endpoint de verificación de salud del sistema
    """
    try:
        # Verificar base de datos
        db_status = check_database_connection()

        # Verificar Redis (redis_available es un booleano, no una función)
        redis_status = redis_available

        # Estado general
        is_healthy = db_status and redis_status

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "version": settings.APP_VERSION,
            "services": {
                "database": {
                    "status": "ok" if db_status else "error",
                    "type": "SQL Server"
                },
                "cache": {
                    "status": "ok" if redis_status else "error",
                    "type": "Redis"
                }
            },
            "uptime": "Active",  # TODO: Calcular uptime real
            "environment": settings.ENVIRONMENT
        }
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


# ========================================
# INCLUIR ROUTERS DE API
# ========================================

# API v1 - Rutas principales
API_V1_PREFIX = "/api/v1"

# ✅ ROUTERS ACTIVOS - Ya implementados y funcionando
logger.info("Registrando routers principales...")

app.include_router(
    tickets_router,
    prefix=API_V1_PREFIX,
    tags=["tickets"]
)

app.include_router(
    patients_router,
    prefix=API_V1_PREFIX,
    tags=["patients"]
)

app.include_router(
    auth_router,
    prefix=API_V1_PREFIX,
    tags=["auth"]
)

app.include_router(
    stations_router,
    prefix=API_V1_PREFIX,
    tags=["stations"]
)

app.include_router(
    service_types_router,
    prefix=API_V1_PREFIX,
    tags=["service-types"]
)

app.include_router(
    users_router,
    prefix=API_V1_PREFIX,
    tags=["users"]
)

app.include_router(
    queue_router,
    prefix=API_V1_PREFIX,
    tags=["queue-states"]
)

# WebSocket para tiempo real
app.include_router(
    websocket_router,
    prefix=API_V1_PREFIX,
    tags=["websocket"]
)

# ❌ ROUTERS PENDIENTES - Comentados hasta implementar
# app.include_router(notifications_router, prefix=API_V1_PREFIX, tags=["notifications"])

app.include_router(
    reports_router,
    prefix=API_V1_PREFIX,
    tags=["reports"]
)

app.include_router(
    admin_router,
    prefix=API_V1_PREFIX,
    tags=["admin"]
)

app.include_router(
    display_router,
    prefix=API_V1_PREFIX,
    tags=["display"]
)

logger.info("Todos los routers registrados correctamente")

# ========================================
# ENDPOINT DE INFORMACIÓN DE API
# ========================================

@app.get("/api", tags=["sistema"])
async def api_info():
    """
    Información sobre la API disponible
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_version": "v1",
        "base_url": API_V1_PREFIX,
        "available_endpoints": {
            "patients": f"{API_V1_PREFIX}/patients",
            "tickets": f"{API_V1_PREFIX}/tickets",
            "auth": f"{API_V1_PREFIX}/auth",
            "stations": f"{API_V1_PREFIX}/stations",
            "service-types": f"{API_V1_PREFIX}/service-types",
            "users": f"{API_V1_PREFIX}/users",
            "queue": f"{API_V1_PREFIX}/queue",
            # Pendientes por implementar:
            # "notifications": f"{API_V1_PREFIX}/notifications",
            # "reports": f"{API_V1_PREFIX}/reports",
            # "admin": f"{API_V1_PREFIX}/admin"
        },
        "websocket": "/ws",
        "documentation": "/docs" if settings.DEBUG else "Not available in production",
        "health_check": "/health"
    }


# ========================================
# ARCHIVOS ESTÁTICOS (si se necesitan)
# ========================================

if os.path.exists("./static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Directorio estático montado en /static")


# ========================================
# FUNCIÓN PARA DESARROLLO
# ========================================

def start_dev_server():
    """
    Inicia el servidor de desarrollo
    Solo para uso local - NO usar en producción
    """
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        # reload=True,
        reload_dirs=["app"],
        log_level="debug" if settings.DEBUG else "info"
    )


# ========================================
# IMPORTS ADICIONALES NECESARIOS
# ========================================

import time
from datetime import datetime

# ========================================
# PUNTO DE ENTRADA
# ========================================

if __name__ == "__main__":
    # Solo para desarrollo local
    if settings.is_development:
        start_dev_server()
    else:
        logger.warning("Use un servidor WSGI como Uvicorn para producción")
        logger.info("Ejemplo: uvicorn app.main:app --host 0.0.0.0 --port 8000")