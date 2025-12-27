from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import validates
from sqlalchemy.sql import func
from typing import Optional, Dict, Any, List
import json
from .base import BaseModel, TimestampMixin, ActiveMixin


class SystemConfig(BaseModel, TimestampMixin, ActiveMixin):
    """
    Modelo para configuraciones del sistema
    Nota: Esta tabla no está en el SQL original, se creará via migración
    """
    __tablename__ = 'SystemConfig'

    # Campos principales
    Id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="ID único de la configuración"
    )

    Key = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Clave única de la configuración"
    )

    Value = Column(
        Text,
        nullable=True,
        comment="Valor de la configuración (JSON si es complejo)"
    )

    DataType = Column(
        String(20),
        nullable=False,
        default='string',
        comment="Tipo de dato (string, int, float, bool, json)"
    )

    Category = Column(
        String(50),
        nullable=False,
        default='general',
        comment="Categoría de la configuración"
    )

    Description = Column(
        Text,
        nullable=True,
        comment="Descripción de la configuración"
    )

    DefaultValue = Column(
        Text,
        nullable=True,
        comment="Valor por defecto"
    )

    IsReadOnly = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Indica si la configuración es de solo lectura"
    )

    RequiresRestart = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Indica si cambiar esta configuración requiere reinicio"
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo SystemConfig
        """
        super().__init__(**kwargs)

    @validates('Key')
    def validate_key(self, key, config_key):
        """
        Valida y normaliza la clave de configuración
        """
        if config_key:
            # Normalizar a snake_case
            import re
            normalized_key = re.sub(r'[^\w\.]', '_', config_key.strip().lower())
            normalized_key = re.sub(r'_+', '_', normalized_key)

            if len(normalized_key) < 3:
                raise ValueError("La clave debe tener al menos 3 caracteres")

            return normalized_key
        return config_key

    @validates('DataType')
    def validate_data_type(self, key, data_type):
        """
        Valida el tipo de dato
        """
        valid_types = ['string', 'int', 'float', 'bool', 'json', 'list']
        if data_type and data_type not in valid_types:
            raise ValueError(f"Tipo de dato inválido. Debe ser uno de: {', '.join(valid_types)}")
        return data_type

    @validates('Category')
    def validate_category(self, key, category):
        """
        Valida y normaliza la categoría
        """
        if category:
            return category.strip().lower()
        return category

    @property
    def typed_value(self) -> Any:
        """
        Obtiene el valor convertido al tipo apropiado

        Returns:
            Any: Valor con el tipo correcto
        """
        if not self.Value:
            return self.typed_default_value

        try:
            if self.DataType == 'int':
                return int(self.Value)
            elif self.DataType == 'float':
                return float(self.Value)
            elif self.DataType == 'bool':
                return self.Value.lower() in ('true', '1', 'yes', 'on')
            elif self.DataType == 'json':
                return json.loads(self.Value)
            elif self.DataType == 'list':
                if isinstance(self.Value, str):
                    return json.loads(self.Value)
                return self.Value
            else:  # string
                return self.Value
        except (ValueError, json.JSONDecodeError, TypeError):
            return self.typed_default_value

    @typed_value.setter
    def typed_value(self, value: Any):
        """
        Establece el valor con conversión automática

        Args:
            value: Valor a establecer
        """
        if value is None:
            self.Value = None
            return

        if self.DataType in ['json', 'list']:
            self.Value = json.dumps(value, default=str)
        else:
            self.Value = str(value)

    @property
    def typed_default_value(self) -> Any:
        """
        Obtiene el valor por defecto convertido al tipo apropiado

        Returns:
            Any: Valor por defecto con el tipo correcto
        """
        if not self.DefaultValue:
            return self._get_type_default()

        try:
            if self.DataType == 'int':
                return int(self.DefaultValue)
            elif self.DataType == 'float':
                return float(self.DefaultValue)
            elif self.DataType == 'bool':
                return self.DefaultValue.lower() in ('true', '1', 'yes', 'on')
            elif self.DataType == 'json':
                return json.loads(self.DefaultValue)
            elif self.DataType == 'list':
                return json.loads(self.DefaultValue)
            else:  # string
                return self.DefaultValue
        except (ValueError, json.JSONDecodeError, TypeError):
            return self._get_type_default()

    def _get_type_default(self) -> Any:
        """
        Obtiene el valor por defecto según el tipo

        Returns:
            Any: Valor por defecto del tipo
        """
        defaults = {
            'string': '',
            'int': 0,
            'float': 0.0,
            'bool': False,
            'json': {},
            'list': []
        }
        return defaults.get(self.DataType, '')

    @property
    def category_display(self) -> str:
        """
        Obtiene el nombre descriptivo de la categoría

        Returns:
            str: Categoría en formato legible
        """
        category_map = {
            'general': 'General',
            'queue': 'Gestión de Colas',
            'notifications': 'Notificaciones',
            'display': 'Pantallas',
            'audio': 'Audio/TTS',
            'security': 'Seguridad',
            'api': 'APIs Externas',
            'database': 'Base de Datos',
            'cache': 'Cache/Redis',
            'reports': 'Reportes',
            'backup': 'Respaldos',
            'maintenance': 'Mantenimiento'
        }
        return category_map.get(self.Category, self.Category.title())

    @property
    def is_default_value(self) -> bool:
        """
        Verifica si el valor actual es el valor por defecto

        Returns:
            bool: True si es el valor por defecto
        """
        return self.typed_value == self.typed_default_value

    @property
    def can_edit(self) -> bool:
        """
        Verifica si la configuración se puede editar

        Returns:
            bool: True si se puede editar
        """
        return not self.IsReadOnly and self.IsActive

    def set_value(self, value: Any, validate: bool = True) -> bool:
        """
        Establece un nuevo valor para la configuración

        Args:
            value: Nuevo valor
            validate: Si validar el valor

        Returns:
            bool: True si se estableció correctamente
        """
        if not self.can_edit:
            return False

        if validate and not self.validate_value(value):
            return False

        self.typed_value = value
        return True

    def validate_value(self, value: Any) -> bool:
        """
        Valida un valor para esta configuración

        Args:
            value: Valor a validar

        Returns:
            bool: True si es válido
        """
        try:
            # Validaciones específicas por clave
            if self.Key == 'max_tickets_per_day' and isinstance(value, (int, str)):
                return int(value) > 0
            elif self.Key == 'working_hours_start' and isinstance(value, str):
                import re
                return bool(re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', value))
            elif self.Key == 'working_hours_end' and isinstance(value, str):
                import re
                return bool(re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', value))
            elif self.DataType == 'int':
                int(value)
                return True
            elif self.DataType == 'float':
                float(value)
                return True
            elif self.DataType == 'bool':
                return isinstance(value, (bool, str, int))
            elif self.DataType in ['json', 'list']:
                if isinstance(value, str):
                    json.loads(value)
                return True
            else:
                return True
        except (ValueError, json.JSONDecodeError, TypeError):
            return False

    def reset_to_default(self) -> bool:
        """
        Restablece la configuración a su valor por defecto

        Returns:
            bool: True si se restableció correctamente
        """
        if not self.can_edit:
            return False

        self.Value = self.DefaultValue
        return True

    @classmethod
    def get_default_configs(cls) -> List[Dict]:
        """
        Obtiene las configuraciones por defecto del sistema

        Returns:
            List[Dict]: Lista de configuraciones predeterminadas
        """
        return [
            # Configuraciones generales
            {
                'Key': 'app_name',
                'Value': 'Sistema de Gestión de Colas',
                'DataType': 'string',
                'Category': 'general',
                'Description': 'Nombre de la aplicación',
                'DefaultValue': 'Sistema de Gestión de Colas'
            },
            {
                'Key': 'lab_name',
                'Value': 'Laboratorio Clínico',
                'DataType': 'string',
                'Category': 'general',
                'Description': 'Nombre del laboratorio',
                'DefaultValue': 'Laboratorio Clínico'
            },

            # Configuraciones de colas
            {
                'Key': 'max_tickets_per_day',
                'Value': '500',
                'DataType': 'int',
                'Category': 'queue',
                'Description': 'Máximo número de tickets por día',
                'DefaultValue': '500'
            },
            {
                'Key': 'ticket_reset_hour',
                'Value': '0',
                'DataType': 'int',
                'Category': 'queue',
                'Description': 'Hora de reinicio de numeración (0-23)',
                'DefaultValue': '0'
            },
            {
                'Key': 'default_wait_time_minutes',
                'Value': '10',
                'DataType': 'int',
                'Category': 'queue',
                'Description': 'Tiempo de espera por defecto en minutos',
                'DefaultValue': '10'
            },
            {
                'Key': 'working_hours_start',
                'Value': '07:00',
                'DataType': 'string',
                'Category': 'queue',
                'Description': 'Hora de inicio de operaciones',
                'DefaultValue': '07:00'
            },
            {
                'Key': 'working_hours_end',
                'Value': '18:00',
                'DataType': 'string',
                'Category': 'queue',
                'Description': 'Hora de fin de operaciones',
                'DefaultValue': '18:00'
            },

            # Configuraciones de notificaciones
            {
                'Key': 'sms_enabled',
                'Value': 'true',
                'DataType': 'bool',
                'Category': 'notifications',
                'Description': 'Habilitar notificaciones SMS',
                'DefaultValue': 'true'
            },
            {
                'Key': 'email_enabled',
                'Value': 'false',
                'DataType': 'bool',
                'Category': 'notifications',
                'Description': 'Habilitar notificaciones por email',
                'DefaultValue': 'false'
            },
            {
                'Key': 'notification_advance_minutes',
                'Value': '5',
                'DataType': 'int',
                'Category': 'notifications',
                'Description': 'Minutos de anticipación para notificaciones',
                'DefaultValue': '5'
            },

            # Configuraciones de pantallas
            {
                'Key': 'display_refresh_interval',
                'Value': '5',
                'DataType': 'int',
                'Category': 'display',
                'Description': 'Intervalo de actualización de pantallas en segundos',
                'DefaultValue': '5'
            },
            {
                'Key': 'display_max_tickets_shown',
                'Value': '10',
                'DataType': 'int',
                'Category': 'display',
                'Description': 'Máximo número de tickets mostrados en pantalla',
                'DefaultValue': '10'
            },

            # Configuraciones de audio
            {
                'Key': 'audio_enabled',
                'Value': 'true',
                'DataType': 'bool',
                'Category': 'audio',
                'Description': 'Habilitar anuncios de audio',
                'DefaultValue': 'true'
            },
            {
                'Key': 'announcement_language',
                'Value': 'es',
                'DataType': 'string',
                'Category': 'audio',
                'Description': 'Idioma de los anuncios',
                'DefaultValue': 'es'
            }
        ]

    @classmethod
    def get_by_key(cls, key: str):
        """
        Obtiene una configuración por su clave

        Args:
            key: Clave de la configuración

        Returns:
            SystemConfig: Configuración encontrada
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        pass

    @classmethod
    def get_by_category(cls, category: str):
        """
        Obtiene todas las configuraciones de una categoría

        Args:
            category: Categoría de configuraciones

        Returns:
            Query: Query de configuraciones de la categoría
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        pass

    @classmethod
    def get_config_dict(cls, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene las configuraciones como diccionario clave-valor

        Args:
            category: Filtrar por categoría (opcional)

        Returns:
            Dict[str, Any]: Diccionario con configuraciones
        """
        # Esta función se completará cuando tengamos acceso a la sesión
        return {}

    def to_dict(self, include_metadata: bool = True) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_metadata: Si incluir metadatos de la configuración

        Returns:
            dict: Diccionario con los datos de la configuración
        """
        result = super().to_dict()

        # Agregar propiedades calculadas
        result['typed_value'] = self.typed_value
        result['typed_default_value'] = self.typed_default_value
        result['category_display'] = self.category_display
        result['is_default_value'] = self.is_default_value
        result['can_edit'] = self.can_edit

        if not include_metadata:
            # Solo incluir datos esenciales
            return {
                'Key': self.Key,
                'Value': self.typed_value,
                'DataType': self.DataType,
                'Category': self.Category
            }

        return result

    def __repr__(self) -> str:
        return f"<SystemConfig(Id={self.Id}, Key='{self.Key}', Category='{self.Category}')>"