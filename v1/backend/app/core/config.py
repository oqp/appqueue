from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os


class Settings(BaseSettings):
    """
    Configuración general del sistema de gestión de colas
    """

    # ========================================
    # CONFIGURACIÓN DE LA APLICACIÓN
    # ========================================
    APP_NAME: str = Field(default="QXpert", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")

    # ========================================
    # CONFIGURACIÓN DE BASE DE DATOS
    # ========================================
    DATABASE_URL: str = Field(
        default="mssql+pyodbc://username:password@server/AppQueueMunoz?driver=ODBC+Driver+17+for+SQL+Server",
        env="DATABASE_URL"
    )

    # Configuración específica de SQL Server
    DB_SERVER: str = Field(default="localhost", env="DB_SERVER")
    DB_HOST: str = Field(default="localhost", env="DB_SERVER")
    DB_NAME: str = Field(default="AppQueueMunoz", env="DB_NAME")
    DB_USERNAME: str = Field(default="sa", env="DB_USERNAME")
    DB_USER: str = Field(default="sa", env="DB_USERNAME")
    DB_PORT: str = Field(default="1433", env="DB_PORT")
    DB_PASSWORD: str = Field(default="", env="DB_PASSWORD")
    DB_DRIVER: str = Field(default="ODBC Driver 17 for SQL Server", env="DB_DRIVER")

    # Pool de conexiones
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=30, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=3600, env="DB_POOL_RECYCLE")

    # ========================================
    # CONFIGURACIÓN DE REDIS
    # ========================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    # Configuración de cache
    REDIS_EXPIRE_SECONDS: int = Field(default=3600, env="REDIS_EXPIRE_SECONDS")  # 1 hora
    REDIS_QUEUE_EXPIRE: int = Field(default=86400, env="REDIS_QUEUE_EXPIRE")  # 24 horas

    # ========================================
    # CONFIGURACIÓN DE SEGURIDAD
    # ========================================
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # ========================================
    # CONFIGURACIÓN DE CORS
    # ========================================
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:4200,http://localhost:3000,http://localhost:8080",
        env="ALLOWED_ORIGINS"
    )
    ALLOWED_METHODS: str = Field(
        default="GET,POST,PUT,DELETE,PATCH,OPTIONS",
        env="ALLOWED_METHODS"
    )
    ALLOWED_HEADERS: str = Field(
        default="*",
        env="ALLOWED_HEADERS"
    )

    # ========================================
    # APIS EXTERNAS
    # ========================================
    # API externa para datos de pacientes
    EXTERNAL_PATIENT_API_URL: str = Field(
        default="https://api.patient-system.com/patient",
        env="EXTERNAL_PATIENT_API_URL"
    )
    EXTERNAL_PATIENT_API_KEY: Optional[str] = Field(
        default=None,
        env="EXTERNAL_PATIENT_API_KEY"
    )
    EXTERNAL_PATIENT_API_TIMEOUT: int = Field(default=10, env="EXTERNAL_PATIENT_API_TIMEOUT")

    # API para SMS
    SMS_API_URL: str = Field(
        default="https://api.sms-provider.com/send",
        env="SMS_API_URL"
    )
    SMS_API_KEY: Optional[str] = Field(default=None, env="SMS_API_KEY")
    SMS_API_TIMEOUT: int = Field(default=5, env="SMS_API_TIMEOUT")
    SMS_ENABLED: bool = Field(default=True, env="SMS_ENABLED")

    # ========================================
    # CONFIGURACIÓN DE COLAS
    # ========================================
    # Configuración del sistema de colas
    MAX_TICKETS_PER_DAY: int = Field(default=500, env="MAX_TICKETS_PER_DAY")
    TICKET_RESET_HOUR: int = Field(default=0, env="TICKET_RESET_HOUR")  # Hora de reset (0-23)
    DEFAULT_WAIT_TIME_MINUTES: int = Field(default=10, env="DEFAULT_WAIT_TIME_MINUTES")

    # Horarios de operación
    WORKING_HOURS_START: str = Field(default="07:00", env="WORKING_HOURS_START")
    WORKING_HOURS_END: str = Field(default="18:00", env="WORKING_HOURS_END")

    # ========================================
    # CONFIGURACIÓN DE NOTIFICACIONES
    # ========================================
    # Notificaciones en tiempo real
    WEBSOCKET_HEARTBEAT_INTERVAL: int = Field(default=30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    NOTIFICATION_BATCH_SIZE: int = Field(default=100, env="NOTIFICATION_BATCH_SIZE")

    # Audio/TTS
    ANNOUNCEMENT_LANGUAGE: str = Field(default="es", env="ANNOUNCEMENT_LANGUAGE")
    AUDIO_ENABLED: bool = Field(default=True, env="AUDIO_ENABLED")

    # ========================================
    # CONFIGURACIÓN DE PANTALLAS
    # ========================================
    DISPLAY_REFRESH_INTERVAL: int = Field(default=5, env="DISPLAY_REFRESH_INTERVAL")  # segundos
    DISPLAY_MAX_TICKETS_SHOWN: int = Field(default=10, env="DISPLAY_MAX_TICKETS_SHOWN")

    # ========================================
    # CONFIGURACIÓN DE REPORTES
    # ========================================
    REPORTS_EXPORT_PATH: str = Field(default="./static/reports/", env="REPORTS_EXPORT_PATH")
    REPORTS_RETENTION_DAYS: int = Field(default=90, env="REPORTS_RETENTION_DAYS")

    # ========================================
    # CONFIGURACIÓN DE ARCHIVOS
    # ========================================
    UPLOAD_PATH: str = Field(default="./static/uploads/", env="UPLOAD_PATH")
    MAX_FILE_SIZE_MB: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    ALLOWED_FILE_EXTENSIONS: str = Field(
        default=".jpg,.jpeg,.png,.pdf,.doc,.docx",
        env="ALLOWED_FILE_EXTENSIONS"
    )

    # ========================================
    # CONFIGURACIÓN DE LOGS
    # ========================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE_PATH: str = Field(default="./logs/app.log", env="LOG_FILE_PATH")
    LOG_MAX_SIZE_MB: int = Field(default=10, env="LOG_MAX_SIZE_MB")
    LOG_BACKUP_COUNT: int = Field(default=5, env="LOG_BACKUP_COUNT")

    # ========================================
    # MÉTODOS CALCULADOS
    # ========================================

    @property
    def database_url_sync(self) -> str:
        """URL de base de datos síncrona"""
        if self.DATABASE_URL != "mssql+pyodbc://username:password@server/AppQueueMunoz?driver=ODBC+Driver+17+for+SQL+Server":
            return self.DATABASE_URL

        # Construir URL desde componentes individuales con encoding de caracteres especiales
        import urllib.parse

        username_encoded = urllib.parse.quote_plus(self.DB_USERNAME)
        password_encoded = urllib.parse.quote_plus(self.DB_PASSWORD)
        server_encoded = urllib.parse.quote_plus(self.DB_SERVER)
        database_encoded = urllib.parse.quote_plus(self.DB_NAME)
        driver_encoded = urllib.parse.quote_plus(self.DB_DRIVER)

        return f"mssql+pyodbc://{username_encoded}:{password_encoded}@{server_encoded}/{database_encoded}?driver={driver_encoded}"

    @property
    def redis_url_complete(self) -> str:
        """URL completa de Redis"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def is_development(self) -> bool:
        """Verifica si estamos en modo desarrollo"""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]

    @property
    def is_production(self) -> bool:
        """Verifica si estamos en modo producción"""
        return self.ENVIRONMENT.lower() in ["production", "prod"]

    def get_cors_origins(self) -> List[str]:
        """Obtiene los orígenes permitidos para CORS"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return [self.ALLOWED_ORIGINS] if isinstance(self.ALLOWED_ORIGINS, str) else self.ALLOWED_ORIGINS

    def get_cors_methods(self) -> List[str]:
        """Obtiene los métodos permitidos para CORS"""
        if isinstance(self.ALLOWED_METHODS, str):
            return [method.strip() for method in self.ALLOWED_METHODS.split(",")]
        return [self.ALLOWED_METHODS] if isinstance(self.ALLOWED_METHODS, str) else self.ALLOWED_METHODS

    def get_cors_headers(self) -> List[str]:
        """Obtiene los headers permitidos para CORS"""
        if isinstance(self.ALLOWED_HEADERS, str):
            if self.ALLOWED_HEADERS == "*":
                return ["*"]
            return [header.strip() for header in self.ALLOWED_HEADERS.split(",")]
        return [self.ALLOWED_HEADERS] if isinstance(self.ALLOWED_HEADERS, str) else self.ALLOWED_HEADERS

    def get_allowed_extensions(self) -> List[str]:
        """Obtiene las extensiones de archivo permitidas"""
        if isinstance(self.ALLOWED_FILE_EXTENSIONS, str):
            return [ext.strip() for ext in self.ALLOWED_FILE_EXTENSIONS.split(",")]
        return [self.ALLOWED_FILE_EXTENSIONS] if isinstance(self.ALLOWED_FILE_EXTENSIONS,
                                                            str) else self.ALLOWED_FILE_EXTENSIONS

    def ensure_directories(self):
        """Crea los directorios necesarios si no existen"""
        directories = [
            self.UPLOAD_PATH,
            self.REPORTS_EXPORT_PATH,
            os.path.dirname(self.LOG_FILE_PATH),
            "./static/images/",
            "./static/audio/",
            "./static/qr_codes/"
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# ========================================
# INSTANCIA GLOBAL DE CONFIGURACIÓN
# ========================================
settings = Settings()

# Crear directorios necesarios al importar
settings.ensure_directories()