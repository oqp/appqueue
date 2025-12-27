from sqlalchemy import Column, DateTime, Boolean, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from typing import Optional

# Base declarativa de SQLAlchemy (importada desde database.py)
from app.core.database import Base


class TimestampMixin:
    """
    Mixin para agregar timestamps automáticos a los modelos
    """

    @declared_attr
    #def created_at(cls):
    def CreatedAt(cls):
        return Column(
            'CreatedAt',
            DateTime,
            default=func.getdate(),
            nullable=False,
            comment="Fecha de creación del registro"
        )

    @declared_attr
    #def updated_at(cls):
    def UpdatedAt(cls):
        return Column(
            'UpdatedAt',
            DateTime,
            default=func.getdate(),
            onupdate=func.getdate(),
            nullable=True,
            comment="Fecha de última actualización"
        )


class ActiveMixin:
    """
    Mixin para agregar control de estado activo/inactivo
    """

    @declared_attr
    def IsActive(cls):
        return Column(
            'IsActive',
            Boolean,
            default=True,
            nullable=False,
            comment="Indica si el registro está activo"
        )


class BaseModel(Base):
    """
    Modelo base abstracto con funcionalidades comunes
    """
    __abstract__ = True

    def to_dict(self, exclude_fields: Optional[list] = None) -> dict:
        """
        Convierte el modelo a diccionario

        Args:
            exclude_fields: Lista de campos a excluir

        Returns:
            dict: Diccionario con los datos del modelo
        """
        exclude_fields = exclude_fields or []

        result = {}
        for column in self.__table__.columns:
            field_name = column.name
            if field_name not in exclude_fields:
                value = getattr(self, field_name)

                # Convertir datetime a string ISO
                if isinstance(value, datetime):
                    value = value.isoformat()
                # Convertir UUID a string
                elif hasattr(value, 'hex'):  # UUID objects
                    value = str(value)

                result[field_name] = value

        return result

    def update_from_dict(self, data: dict, exclude_fields: Optional[list] = None):
        """
        Actualiza el modelo desde un diccionario

        Args:
            data: Diccionario con los datos a actualizar
            exclude_fields: Lista de campos a excluir de la actualización
        """
        exclude_fields = exclude_fields or ['Id', 'CreatedAt']

        for key, value in data.items():
            if key not in exclude_fields and hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def get_table_name(cls) -> str:
        """
        Obtiene el nombre de la tabla

        Returns:
            str: Nombre de la tabla
        """
        return cls.__tablename__

    @classmethod
    def get_primary_key_name(cls) -> str:
        """
        Obtiene el nombre de la clave primaria

        Returns:
            str: Nombre de la clave primaria
        """
        return cls.__table__.primary_key.columns.keys()[0]

    def __repr__(self) -> str:
        """
        Representación string del modelo
        """
        pk_name = self.get_primary_key_name()
        pk_value = getattr(self, pk_name, 'N/A')
        return f"<{self.__class__.__name__}({pk_name}={pk_value})>"


class AuditMixin:
    """
    Mixin para campos de auditoría
    """

    @declared_attr
    def created_by(cls):
        return Column(
            'CreatedBy',
            String(50),
            nullable=True,
            comment="Usuario que creó el registro"
        )

    @declared_attr
    def updated_by(cls):
        return Column(
            'UpdatedBy',
            String(50),
            nullable=True,
            comment="Usuario que actualizó el registro"
        )


class SoftDeleteMixin:
    """
    Mixin para soft delete (eliminación lógica)
    """

    @declared_attr
    def deleted_at(cls):
        return Column(
            'DeletedAt',
            DateTime,
            nullable=True,
            comment="Fecha de eliminación lógica"
        )

    @declared_attr
    def deleted_by(cls):
        return Column(
            'DeletedBy',
            String(50),
            nullable=True,
            comment="Usuario que eliminó el registro"
        )

    @property
    def is_deleted(self) -> bool:
        """
        Verifica si el registro está eliminado lógicamente
        """
        return self.deleted_at is not None

    def soft_delete(self, deleted_by: Optional[str] = None):
        """
        Realiza eliminación lógica del registro
        """
        self.deleted_at = func.getdate()
        if deleted_by:
            self.deleted_by = deleted_by

    def restore(self):
        """
        Restaura un registro eliminado lógicamente
        """
        self.deleted_at = None
        self.deleted_by = None


def generate_uuid() -> str:
    """
    Genera un UUID como string

    Returns:
        str: UUID generado
    """
    return str(uuid.uuid4())