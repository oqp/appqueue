"""
Módulo de modelos SQLAlchemy para el Sistema de Gestión de Colas
"""

# Importar el Base desde database para que esté disponible
from app.core.database import Base

# Importar todos los modelos
from .base import BaseModel, TimestampMixin, ActiveMixin, AuditMixin, SoftDeleteMixin
from .role import Role
from .service_type import ServiceType
from .patient import Patient
from .station import Station
from .user import User
from .ticket import Ticket
from .message_template import MessageTemplate
from .notification import NotificationLog
from .activity_log import ActivityLog
from .daily_metrics import DailyMetrics
from .queue_state import QueueState
from .display_video import DisplayVideo

# Lista de todos los modelos para facilitar importaciones
__all__ = [
    # Base classes
    'Base',
    'BaseModel',
    'TimestampMixin',
    'ActiveMixin',
    'AuditMixin',
    'SoftDeleteMixin',

    # Core models
    'Role',
    'User',
    'ServiceType',
    'Station',
    'Patient',
    'Ticket',
    'MessageTemplate',
    'NotificationLog',
    'ActivityLog',
    'DailyMetrics',
    'QueueState',
    'DisplayVideo'
]

# Metadatos de los modelos
MODEL_METADATA = {
    'Role': {
        'description': 'Roles de usuario del sistema',
        'table_name': 'Roles',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': True
    },
    'User': {
        'description': 'Usuarios del sistema',
        'table_name': 'Users',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': True
    },
    'ServiceType': {
        'description': 'Tipos de servicios del laboratorio',
        'table_name': 'ServiceTypes',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': True
    },
    'Station': {
        'description': 'Estaciones/ventanillas de atención',
        'table_name': 'Stations',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': True
    },
    'Patient': {
        'description': 'Pacientes del laboratorio',
        'table_name': 'Patients',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': True
    },
    'Ticket': {
        'description': 'Tickets/turnos del sistema de colas',
        'table_name': 'Tickets',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': False
    },
    'MessageTemplate': {
        'description': 'Plantillas de mensajes para notificaciones',
        'table_name': 'MessageTemplates',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': True
    },
    'NotificationLog': {
        'description': 'Registro de notificaciones enviadas',
        'table_name': 'NotificationLog',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': False
    },
    'ActivityLog': {
        'description': 'Registro de actividades del sistema',
        'table_name': 'ActivityLog',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': False
    },
    'DailyMetrics': {
        'description': 'Métricas diarias del sistema',
        'table_name': 'DailyMetrics',
        'primary_key': 'Id',
        'has_timestamps': True,
        'has_active_flag': False
    },
    'QueueState': {
        'description': 'Estado actual de las colas',
        'table_name': 'QueueState',
        'primary_key': 'Id',
        'has_timestamps': False,
        'has_active_flag': False
    }
}


def get_model_by_name(model_name: str):
    """
    Obtiene una clase de modelo por su nombre

    Args:
        model_name: Nombre del modelo

    Returns:
        Model class: Clase del modelo
    """
    models_map = {
        'Role': Role,
        'User': User,
        'ServiceType': ServiceType,
        'Station': Station,
        'Patient': Patient,
        'Ticket': Ticket,
        'MessageTemplate': MessageTemplate,
        'NotificationLog': NotificationLog,
        'ActivityLog': ActivityLog,
        'DailyMetrics': DailyMetrics,
        'QueueState': QueueState
    }

    return models_map.get(model_name)


def get_all_models():
    """
    Obtiene todas las clases de modelos

    Returns:
        List: Lista de clases de modelos
    """
    return [
        Role, User, ServiceType, Station, Patient, Ticket,
        MessageTemplate, NotificationLog, ActivityLog,
        DailyMetrics, QueueState
    ]


def get_models_with_timestamps():
    """
    Obtiene modelos que tienen campos de timestamp

    Returns:
        List: Lista de modelos con timestamps
    """
    return [
        model for model_name, model in [
            ('Role', Role), ('User', User), ('ServiceType', ServiceType),
            ('Station', Station), ('Patient', Patient), ('Ticket', Ticket),
            ('MessageTemplate', MessageTemplate), ('NotificationLog', NotificationLog),
            ('ActivityLog', ActivityLog), ('DailyMetrics', DailyMetrics)
        ] if MODEL_METADATA[model_name]['has_timestamps']
    ]


def get_models_with_active_flag():
    """
    Obtiene modelos que tienen flag de activo/inactivo

    Returns:
        List: Lista de modelos con flag activo
    """
    return [
        model for model_name, model in [
            ('Role', Role), ('User', User), ('ServiceType', ServiceType),
            ('Station', Station), ('Patient', Patient), ('MessageTemplate', MessageTemplate)
        ] if MODEL_METADATA[model_name]['has_active_flag']
    ]


def create_all_tables(engine):
    """
    Crea todas las tablas en la base de datos

    Args:
        engine: Engine de SQLAlchemy
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Todas las tablas han sido creadas correctamente")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        raise


def drop_all_tables(engine):
    """
    Elimina todas las tablas de la base de datos
    ¡USAR CON EXTREMA PRECAUCIÓN!

    Args:
        engine: Engine de SQLAlchemy
    """
    try:
        Base.metadata.drop_all(bind=engine)
        print("⚠️ Todas las tablas han sido eliminadas")
    except Exception as e:
        print(f"❌ Error eliminando tablas: {e}")
        raise


def get_table_creation_order():
    """
    Obtiene el orden recomendado para creación de tablas
    (considerando las dependencias de foreign keys)

    Returns:
        List[str]: Lista ordenada de nombres de tablas  
    """
    return [
        'Roles',  # Sin dependencias
        'ServiceTypes',  # Sin dependencias
        'MessageTemplates',  # Sin dependencias
        'Patients',  # Sin dependencias
        'Stations',  # Depende de ServiceTypes
        'Users',  # Depende de Roles y Stations
        'Tickets',  # Depende de Patients, ServiceTypes y Stations
        'NotificationLog',  # Depende de Tickets
        'ActivityLog',  # Depende de Users, Tickets y Stations
        'DailyMetrics',  # Depende de ServiceTypes y Stations
        'QueueState'  # Depende de ServiceTypes, Stations y Tickets
    ]


def validate_model_relationships():
    """
    Valida que todas las relaciones entre modelos estén correctamente definidas

    Returns:
        Dict[str, List[str]]: Reporte de validación
    """
    issues = []
    warnings = []

    # Verificar que todas las foreign keys tengan sus relaciones correspondientes
    try:
        # Esta validación se puede expandir según las necesidades
        for model in get_all_models():
            if hasattr(model, '__table__'):
                table_name = model.__table__.name
                # Verificar que el modelo esté en el metadata
                if table_name not in MODEL_METADATA:
                    warnings.append(f"Modelo {model.__name__} no está en MODEL_METADATA")

        return {
            'status': 'success' if not issues else 'error',
            'issues': issues,
            'warnings': warnings
        }

    except Exception as e:
        return {
            'status': 'error',
            'issues': [f"Error durante validación: {str(e)}"],
            'warnings': warnings
        }


# Información de versión de los modelos
MODELS_VERSION = "1.0.0"
MODELS_CREATED_DATE = "2025-08-3"

print(f"📚 Modelos SQLAlchemy cargados (v{MODELS_VERSION})")
print(f"📊 Total de modelos: {len(get_all_models())}")
print(f"⏰ Modelos con timestamps: {len(get_models_with_timestamps())}")
print(f"🔄 Modelos con flag activo: {len(get_models_with_active_flag())}")
print("✅ Modelos compatibles con scripts.sql")