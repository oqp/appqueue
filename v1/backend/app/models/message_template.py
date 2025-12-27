from sqlalchemy import Column, Integer, String, Text, Boolean, CheckConstraint
from sqlalchemy.orm import validates
from typing import Optional, Dict, List
import json
import re
from .base import BaseModel, TimestampMixin, ActiveMixin


class MessageTemplate(BaseModel, TimestampMixin, ActiveMixin):
    """
    Modelo para plantillas de mensajes del sistema
    """
    __tablename__ = 'MessageTemplates'

    # Campos principales
    Id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="ID único de la plantilla"
    )

    Name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Nombre único de la plantilla"
    )

    Type = Column(
        String(20),
        nullable=False,
        comment="Tipo de mensaje (Display, Audio, Email, SMS)"
    )

    Subject = Column(
        String(200),
        nullable=True,
        comment="Asunto del mensaje (para Email)"
    )

    Content = Column(
        Text,
        nullable=False,
        comment="Contenido de la plantilla con variables"
    )

    Variables = Column(
        Text,
        nullable=True,
        comment="Variables disponibles en formato JSON"
    )

    Language = Column(
        String(5),
        nullable=False,
        default='es',
        comment="Idioma de la plantilla"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "Type IN ('Display', 'Audio', 'Email', 'SMS')",
            name='chk_messagetemplate_type'
        ),
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo MessageTemplate
        """
        super().__init__(**kwargs)

    @validates('Type')
    def validate_type(self, key, message_type):
        """
        Valida el tipo de mensaje
        """
        valid_types = ['Display', 'Audio', 'Email', 'SMS']
        if message_type and message_type not in valid_types:
            raise ValueError(f"Tipo inválido. Debe ser uno de: {', '.join(valid_types)}")
        return message_type

    @validates('Name')
    def validate_name(self, key, name):
        """
        Valida y normaliza el nombre de la plantilla
        """
        if name:
            # Normalizar a snake_case y eliminar caracteres especiales
            normalized_name = re.sub(r'[^\w\s-]', '', name.strip())
            normalized_name = re.sub(r'[-\s]+', '_', normalized_name).lower()

            if len(normalized_name) < 3:
                raise ValueError("El nombre debe tener al menos 3 caracteres")

            return normalized_name
        return name

    @validates('Language')
    def validate_language(self, key, language):
        """
        Valida el código de idioma
        """
        valid_languages = ['es', 'en', 'pt', 'fr']  # Expandir según necesidades
        if language and language not in valid_languages:
            raise ValueError(f"Idioma inválido. Debe ser uno de: {', '.join(valid_languages)}")
        return language

    @validates('Content')
    def validate_content(self, key, content):
        """
        Valida el contenido de la plantilla
        """
        if content:
            content = content.strip()
            if len(content) < 5:
                raise ValueError("El contenido debe tener al menos 5 caracteres")
            return content
        return content

    @property
    def type_display(self) -> str:
        """
        Obtiene el nombre descriptivo del tipo

        Returns:
            str: Tipo en formato legible
        """
        type_map = {
            'Display': 'Pantalla',
            'Audio': 'Audio/Voz',
            'Email': 'Correo electrónico',
            'SMS': 'Mensaje de texto'
        }
        return type_map.get(self.Type, 'Desconocido')

    @property
    def language_display(self) -> str:
        """
        Obtiene el nombre del idioma

        Returns:
            str: Nombre del idioma
        """
        language_map = {
            'es': 'Español',
            'en': 'Inglés',
            'pt': 'Portugués',
            'fr': 'Francés'
        }
        return language_map.get(self.Language, 'Desconocido')

    @property
    def variables_list(self) -> List[str]:
        """
        Obtiene la lista de variables desde el campo JSON

        Returns:
            List[str]: Lista de variables disponibles
        """
        if not self.Variables:
            return []

        try:
            variables = json.loads(self.Variables)
            return variables if isinstance(variables, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @variables_list.setter
    def variables_list(self, variables: List[str]):
        """
        Establece la lista de variables en formato JSON

        Args:
            variables: Lista de variables
        """
        if isinstance(variables, list):
            self.Variables = json.dumps(variables)
        else:
            self.Variables = "[]"

    @property
    def extracted_variables(self) -> List[str]:
        """
        Extrae las variables del contenido de la plantilla

        Returns:
            List[str]: Variables encontradas en el contenido
        """
        if not self.Content:
            return []

        # Buscar patrones como {variable} o {{variable}}
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, self.Content)

        # Limpiar y deduplicar
        variables = []
        for match in matches:
            cleaned = match.strip()
            if cleaned and cleaned not in variables:
                variables.append(cleaned)

        return variables

    def validate_variables(self) -> Dict[str, bool]:
        """
        Valida que las variables declaradas coincidan con las usadas

        Returns:
            Dict[str, bool]: Resultado de validación
        """
        declared_vars = set(self.variables_list)
        extracted_vars = set(self.extracted_variables)

        return {
            'is_valid': declared_vars == extracted_vars,
            'missing_declarations': list(extracted_vars - declared_vars),
            'unused_declarations': list(declared_vars - extracted_vars),
            'total_variables': len(extracted_vars)
        }

    def render(self, context: Dict[str, any]) -> str:
        """
        Renderiza la plantilla con los valores proporcionados

        Args:
            context: Diccionario con valores para las variables

        Returns:
            str: Contenido renderizado
        """
        if not self.Content:
            return ""

        rendered_content = self.Content

        # Reemplazar variables con formato {variable}
        for variable in self.extracted_variables:
            placeholder = f"{{{variable}}}"
            value = context.get(variable, f"[{variable}]")  # Valor por defecto si no se encuentra
            rendered_content = rendered_content.replace(placeholder, str(value))

        return rendered_content

    def get_preview(self, sample_context: Optional[Dict[str, any]] = None) -> str:
        """
        Obtiene una vista previa de la plantilla con datos de ejemplo

        Args:
            sample_context: Contexto de ejemplo (opcional)

        Returns:
            str: Vista previa renderizada
        """
        if sample_context is None:
            sample_context = self.get_sample_context()

        return self.render(sample_context)

    def get_sample_context(self) -> Dict[str, any]:
        """
        Genera un contexto de ejemplo para preview

        Returns:
            Dict[str, any]: Contexto con valores de ejemplo
        """
        sample_values = {
            'patient_name': 'Juan Pérez',
            'patient_document': '12345678',
            'ticket_number': 'A001',
            'service_name': 'Análisis de Laboratorio',
            'station_name': 'Ventanilla 1',
            'station_code': 'V1',
            'wait_time': '10',
            'position': '5',
            'current_time': '14:30',
            'estimated_time': '15:45',
            'lab_name': 'Laboratorio Clínico XYZ',
            'phone': '+51 987 654 321',
            'date': '2024-03-15'
        }

        # Solo incluir variables que están en la plantilla
        return {
            var: sample_values.get(var, f'[{var}]')
            for var in self.extracted_variables
        }

    def clone(self, new_name: str) -> 'MessageTemplate':
        """
        Crea una copia de la plantilla con un nuevo nombre

        Args:
            new_name: Nombre para la nueva plantilla

        Returns:
            MessageTemplate: Nueva instancia clonada
        """
        return MessageTemplate(
            Name=new_name,
            Type=self.Type,
            Subject=self.Subject,
            Content=self.Content,
            Variables=self.Variables,
            Language=self.Language,
            IsActive=True
        )

    @classmethod
    def get_default_templates(cls) -> List[Dict]:
        """
        Obtiene las plantillas por defecto del sistema

        Returns:
            List[Dict]: Lista de plantillas predeterminadas
        """
        return [
            {
                'Name': 'ticket_created_sms',
                'Type': 'SMS',
                'Content': 'Su turno {ticket_number} para {service_name} ha sido generado. Posición en cola: {position}. Tiempo estimado: {estimated_time}.',
                'Variables': json.dumps(['ticket_number', 'service_name', 'position', 'estimated_time']),
                'Language': 'es'
            },
            {
                'Name': 'ticket_called_sms',
                'Type': 'SMS',
                'Content': 'Su turno {ticket_number} está siendo llamado. Diríjase a {station_name} ({station_code}).',
                'Variables': json.dumps(['ticket_number', 'station_name', 'station_code']),
                'Language': 'es'
            },
            {
                'Name': 'ticket_reminder_sms',
                'Type': 'SMS',
                'Content': 'Recordatorio: Su turno {ticket_number} será atendido en aproximadamente {wait_time} minutos.',
                'Variables': json.dumps(['ticket_number', 'wait_time']),
                'Language': 'es'
            },
            {
                'Name': 'display_current_ticket',
                'Type': 'Display',
                'Content': 'TURNO ACTUAL: {ticket_number}\nVENTANILLA: {station_name}\nSERVICIO: {service_name}',
                'Variables': json.dumps(['ticket_number', 'station_name', 'service_name']),
                'Language': 'es'
            },
            {
                'Name': 'audio_call_ticket',
                'Type': 'Audio',
                'Content': 'Turno {ticket_number}, diríjase a {station_name}.',
                'Variables': json.dumps(['ticket_number', 'station_name']),
                'Language': 'es'
            },
            {
                'Name': 'email_ticket_confirmation',
                'Type': 'Email',
                'Subject': 'Confirmación de turno - {lab_name}',
                'Content': 'Estimado/a {patient_name},\n\nSu turno {ticket_number} para {service_name} ha sido confirmado.\n\nFecha: {date}\nHora estimada: {estimated_time}\n\nGracias por elegir {lab_name}.',
                'Variables': json.dumps(
                    ['patient_name', 'ticket_number', 'service_name', 'date', 'estimated_time', 'lab_name']),
                'Language': 'es'
            }
        ]

    def to_dict(self, include_preview: bool = False) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_preview: Si incluir vista previa renderizada

        Returns:
            dict: Diccionario con los datos de la plantilla
        """
        result = super().to_dict()

        # Agregar propiedades calculadas
        result['type_display'] = self.type_display
        result['language_display'] = self.language_display
        result['variables_list'] = self.variables_list
        result['extracted_variables'] = self.extracted_variables
        result['validation'] = self.validate_variables()

        if include_preview:
            result['preview'] = self.get_preview()
            result['sample_context'] = self.get_sample_context()

        return result

    def __repr__(self) -> str:
        return f"<MessageTemplate(Id={self.Id}, Name='{self.Name}', Type='{self.Type}')>"