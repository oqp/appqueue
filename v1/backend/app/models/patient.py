from sqlalchemy import Column, String, Date, Boolean, DateTime, CheckConstraint, Computed, Integer
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func, text
from datetime import datetime, date, timedelta
from typing import Optional, List
import uuid
import re
from .base import BaseModel, TimestampMixin, ActiveMixin


class Patient(BaseModel, TimestampMixin, ActiveMixin):
    """
    Modelo para pacientes del laboratorio clínico
    """
    __tablename__ = 'Patients'

    # Campos principales
    Id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        server_default=text('newid()'),
        comment="ID único del paciente"
    )

    DocumentNumber = Column(
        String(20),
        nullable=False,
        unique=True,
        comment="Número de documento de identidad"
    )

    FullName = Column(
        String(200),
        nullable=False,
        comment="Nombre completo del paciente"
    )

    BirthDate = Column(
        Date,
        nullable=False,
        comment="Fecha de nacimiento"
    )

    Gender = Column(
        String(10),
        nullable=False,
        comment="Género del paciente (M/F/Otro)"
    )

    Phone = Column(
        String(20),
        nullable=True,
        comment="Número de teléfono para notificaciones"
    )

    Email = Column(
        String(100),
        nullable=True,
        comment="Correo electrónico"
    )

    # Columna calculada (como en SQL Server)
    Age = Column(
        Integer,
        Computed("datediff(year, [BirthDate], getdate())"),
        comment="Edad calculada automáticamente"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "Gender IN ('M', 'F', 'Otro')",
            name='chk_patient_gender'
        ),
    )

    # Relaciones
    tickets = relationship(
        "Ticket",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __init__(self, **kwargs):
        """
        Constructor del modelo Patient
        """
        super().__init__(**kwargs)

    @validates('DocumentNumber')
    def validate_document_number(self, key, document):
        """
        Valida y normaliza el número de documento
        """
        if document:
            # Remover espacios y caracteres especiales innecesarios
            cleaned_document = re.sub(r'[^\w\-\.]', '', document.strip())

            # Validar longitud
            if len(cleaned_document) < 5 or len(cleaned_document) > 20:
                raise ValueError("El número de documento debe tener entre 5 y 20 caracteres")

            return cleaned_document.upper()
        return document

    @validates('FullName')
    def validate_full_name(self, key, name):
        """
        Valida y normaliza el nombre completo
        """
        if name:
            # Capitalizar cada palabra y remover espacios extra
            normalized_name = ' '.join(word.capitalize() for word in name.strip().split())

            if len(normalized_name) < 2:
                raise ValueError("El nombre completo debe tener al menos 2 caracteres")

            return normalized_name
        return name

    @validates('Gender')
    def validate_gender(self, key, gender):
        """
        Valida el género
        """
        if gender and gender not in ['M', 'F', 'Otro']:
            raise ValueError("El género debe ser 'M', 'F' o 'Otro'")
        return gender

    @validates('Phone')
    def validate_phone(self, key, phone):
        """
        Valida y normaliza el número de teléfono
        """
        if phone:
            # Remover caracteres no numéricos excepto + al inicio
            cleaned_phone = re.sub(r'[^\d\+]', '', phone.strip())

            # Validar formato básico
            if not re.match(r'^[\+]?[1-9][\d]{7,15}$', cleaned_phone):
                raise ValueError("Formato de teléfono inválido")

            return cleaned_phone
        return phone

    @validates('Email')
    def validate_email(self, key, email):
        """
        Valida el formato del email
        """
        if email:
            email = email.strip().lower()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

            if not re.match(email_pattern, email):
                raise ValueError("Formato de email inválido")

            return email
        return email

    @validates('BirthDate')
    def validate_birth_date(self, key, birth_date):
        """
        Valida la fecha de nacimiento
        """
        if birth_date:
            if isinstance(birth_date, str):
                try:
                    birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError("Formato de fecha inválido (usar YYYY-MM-DD)")

            # Verificar que no sea fecha futura
            if birth_date > date.today():
                raise ValueError("La fecha de nacimiento no puede ser futura")

            # Verificar edad mínima y máxima razonables
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            if age > 150:
                raise ValueError("Fecha de nacimiento no válida (edad > 150 años)")

            return birth_date
        return birth_date

    @property
    def current_age(self) -> int:
        """
        Calcula la edad actual del paciente (método alternativo)
        Nota: La edad también está disponible como columna calculada Age

        Returns:
            int: Edad en años
        """
        if not self.BirthDate:
            return 0

        today = date.today()
        return today.year - self.BirthDate.year - (
                    (today.month, today.day) < (self.BirthDate.month, self.BirthDate.day))

    @property
    def gender_display(self) -> str:
        """
        Obtiene el nombre completo del género

        Returns:
            str: Género en formato completo
        """
        gender_map = {
            'M': 'Masculino',
            'F': 'Femenino',
            'Otro': 'Otro'
        }
        return gender_map.get(self.Gender, 'No especificado')

    @property
    def is_senior(self) -> bool:
        """
        Verifica si es adulto mayor (>= 65 años)

        Returns:
            bool: True si es adulto mayor
        """
        return (self.Age or 0) >= 65

    @property
    def is_minor(self) -> bool:
        """
        Verifica si es menor de edad (< 18 años)

        Returns:
            bool: True si es menor de edad
        """
        return (self.Age or 0) < 18

    @property
    def requires_priority(self) -> bool:
        """
        Verifica si requiere atención prioritaria

        Returns:
            bool: True si requiere prioridad
        """
        return self.is_senior or self.is_minor

    @property
    def phone_formatted(self) -> Optional[str]:
        """
        Obtiene el teléfono en formato presentable

        Returns:
            str: Teléfono formateado
        """
        if not self.Phone:
            return None

        # Si es número peruano (9 dígitos sin código país)
        if len(self.Phone) == 9 and self.Phone.startswith('9'):
            return f"+51 {self.Phone[:3]} {self.Phone[3:6]} {self.Phone[6:]}"

        # Si ya tiene código país
        if self.Phone.startswith('+51') and len(self.Phone) == 12:
            clean_phone = self.Phone[3:]  # Remover +51
            return f"+51 {clean_phone[:3]} {clean_phone[3:6]} {clean_phone[6:]}"

        return self.Phone

    def get_active_tickets(self) -> List:
        """
        Obtiene los tickets activos del paciente

        Returns:
            List: Lista de tickets activos
        """
        if not self.tickets:
            return []

        active_statuses = ['Waiting', 'Called', 'InProgress']
        return [t for t in self.tickets if t.Status in active_statuses]

    def get_recent_tickets(self, days: int = 30) -> List:
        """
        Obtiene los tickets recientes del paciente

        Args:
            days: Número de días hacia atrás

        Returns:
            List: Lista de tickets recientes
        """
        if not self.tickets:
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        return [t for t in self.tickets if t.CreatedAt >= cutoff_date]

    @property
    def total_visits(self) -> int:
        """
        Obtiene el número total de visitas del paciente

        Returns:
            int: Número de visitas
        """
        return len(self.tickets) if self.tickets else 0

    @property
    def last_visit(self) -> Optional[datetime]:
        """
        Obtiene la fecha de la última visita

        Returns:
            datetime: Fecha de última visita
        """
        if not self.tickets:
            return None

        return max(t.CreatedAt for t in self.tickets)

    def to_dict(self, include_stats: bool = False, include_sensitive: bool = True) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            include_stats: Si incluir estadísticas de visitas
            include_sensitive: Si incluir datos sensibles (documento, teléfono)

        Returns:
            dict: Diccionario con los datos del paciente
        """
        exclude_fields = []
        if not include_sensitive:
            exclude_fields.extend(['DocumentNumber', 'Phone', 'Email'])

        result = super().to_dict(exclude_fields=exclude_fields)

        # Agregar propiedades calculadas
        result['current_age'] = self.current_age
        result['age'] = self.Age or 0  # Usar la columna calculada
        result['gender_display'] = self.gender_display
        result['is_senior'] = self.is_senior
        result['is_minor'] = self.is_minor
        result['requires_priority'] = self.requires_priority

        if include_sensitive and self.Phone:
            result['phone_formatted'] = self.phone_formatted

        if include_stats:
            result['total_visits'] = self.total_visits
            result['last_visit'] = self.last_visit.isoformat() if self.last_visit else None
            result['active_tickets_count'] = len(self.get_active_tickets())

        return result

    def __repr__(self) -> str:
        return f"<Patient(Id={self.Id}, Document='{self.DocumentNumber}', Name='{self.FullName}')>"