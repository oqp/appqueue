"""
Operaciones CRUD base para todos los modelos
Compatible con SQLAlchemy y SQL Server
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, Tuple
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
import logging

from app.core.database import Base

# ========================================
# TIPOS GENÉRICOS
# ========================================

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

logger = logging.getLogger(__name__)


# ========================================
# CLASE BASE CRUD
# ========================================

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Clase base con operaciones CRUD genéricas
    Compatible con modelos SQLAlchemy y schemas Pydantic
    """

    def __init__(self, model: Type[ModelType]):
        """
        Inicializa el CRUD con el modelo SQLAlchemy

        Args:
            model: Clase del modelo SQLAlchemy
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Obtiene un registro por ID

        Args:
            db: Sesión de base de datos
            id: ID del registro (puede ser int, str, UUID)

        Returns:
            ModelType: Registro encontrado o None
        """
        try:
            return db.query(self.model).filter(self.model.Id == id).first()
        except Exception as e:
            logger.error(f"Error obteniendo {self.model.__name__} con ID {id}: {e}")
            return None

    def get_multi(
            self,
            db: Session,
            *,
            skip: int = 0,
            limit: int = 100,
            active_only: bool = True
    ) -> List[ModelType]:
        """
        Obtiene múltiples registros con paginación

        Args:
            db: Sesión de base de datos
            skip: Registros a omitir
            limit: Límite de registros
            active_only: Solo registros activos (si el modelo tiene IsActive)

        Returns:
            List[ModelType]: Lista de registros
        """
        try:
            query = db.query(self.model)

            # Filtrar por activos si el modelo tiene el campo IsActive
            if active_only and hasattr(self.model, 'IsActive'):
                query = query.filter(self.model.IsActive == True)

            # Ordenar por fecha de creación descendente si existe
            if hasattr(self.model, 'CreatedAt'):
                query = query.order_by(desc(self.model.CreatedAt))
            elif hasattr(self.model, 'Id'):
                query = query.order_by(desc(self.model.Id))

            return query.offset(skip).limit(limit).all()

        except Exception as e:
            logger.error(f"Error obteniendo múltiples {self.model.__name__}: {e}")
            return []

    def get_multi_with_count(
            self,
            db: Session,
            *,
            skip: int = 0,
            limit: int = 100,
            active_only: bool = True
    ) -> Tuple[List[ModelType], int]:
        """
        Obtiene múltiples registros con conteo total para paginación

        Args:
            db: Sesión de base de datos
            skip: Registros a omitir
            limit: Límite de registros
            active_only: Solo registros activos

        Returns:
            Tuple[List[ModelType], int]: (registros, total_count)
        """
        try:
            query = db.query(self.model)

            # Filtrar por activos si el modelo tiene el campo IsActive
            if active_only and hasattr(self.model, 'IsActive'):
                query = query.filter(self.model.IsActive == True)

            # Obtener conteo total
            total = query.count()

            # Ordenar y paginar
            if hasattr(self.model, 'CreatedAt'):
                query = query.order_by(desc(self.model.CreatedAt))
            elif hasattr(self.model, 'Id'):
                query = query.order_by(desc(self.model.Id))

            records = query.offset(skip).limit(limit).all()

            return records, total

        except Exception as e:
            logger.error(f"Error obteniendo múltiples {self.model.__name__} con conteo: {e}")
            return [], 0

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Crea un nuevo registro

        Args:
            db: Sesión de base de datos
            obj_in: Datos de entrada (schema Pydantic)

        Returns:
            ModelType: Registro creado
        """
        try:
            # Convertir schema Pydantic a dict
            obj_in_data = jsonable_encoder(obj_in)

            # Crear instancia del modelo
            db_obj = self.model(**obj_in_data)

            # Guardar en base de datos
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            logger.info(f"{self.model.__name__} creado correctamente con ID: {db_obj.Id}")
            return db_obj

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando {self.model.__name__}: {e}")
            raise

    def update(
            self,
            db: Session,
            *,
            db_obj: ModelType,
            obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Actualiza un registro existente

        Args:
            db: Sesión de base de datos
            db_obj: Objeto existente en la base de datos
            obj_in: Datos de actualización (schema Pydantic o dict)

        Returns:
            ModelType: Registro actualizado
        """
        try:
            # Convertir a dict si es un schema Pydantic
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.dict(exclude_unset=True)

            # Actualizar campos que no sean None
            for field, value in update_data.items():
                if value is not None and hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            # Actualizar timestamp si existe
            if hasattr(db_obj, 'UpdatedAt'):
                setattr(db_obj, 'UpdatedAt', func.getdate())

            # Guardar cambios
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            logger.info(f"{self.model.__name__} actualizado correctamente: {db_obj.Id}")
            return db_obj

        except Exception as e:
            db.rollback()
            logger.error(f"Error actualizando {self.model.__name__}: {e}")
            raise

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """
        Elimina un registro (eliminación física)

        Args:
            db: Sesión de base de datos
            id: ID del registro a eliminar

        Returns:
            ModelType: Registro eliminado o None
        """
        try:
            obj = db.query(self.model).get(id)
            if obj:
                db.delete(obj)
                db.commit()
                logger.warning(f"{self.model.__name__} eliminado físicamente: {id}")
                return obj
            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error eliminando {self.model.__name__}: {e}")
            raise

    def deactivate(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """
        Desactiva un registro (eliminación lógica)
        Solo funciona si el modelo tiene campo IsActive

        Args:
            db: Sesión de base de datos
            id: ID del registro a desactivar

        Returns:
            ModelType: Registro desactivado o None
        """
        try:
            obj = db.query(self.model).get(id)
            if obj and hasattr(obj, 'IsActive'):
                obj.IsActive = False

                # Actualizar timestamp si existe
                if hasattr(obj, 'UpdatedAt'):
                    obj.UpdatedAt = func.getdate()

                db.add(obj)
                db.commit()
                db.refresh(obj)

                logger.info(f"{self.model.__name__} desactivado: {id}")
                return obj
            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error desactivando {self.model.__name__}: {e}")
            raise

    def activate(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """
        Activa un registro desactivado
        Solo funciona si el modelo tiene campo IsActive

        Args:
            db: Sesión de base de datos
            id: ID del registro a activar

        Returns:
            ModelType: Registro activado o None
        """
        try:
            obj = db.query(self.model).get(id)
            if obj and hasattr(obj, 'IsActive'):
                obj.IsActive = True

                # Actualizar timestamp si existe
                if hasattr(obj, 'UpdatedAt'):
                    obj.UpdatedAt = func.getdate()

                db.add(obj)
                db.commit()
                db.refresh(obj)

                logger.info(f"{self.model.__name__} activado: {id}")
                return obj
            return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error activando {self.model.__name__}: {e}")
            raise

    def get_count(self, db: Session, *, active_only: bool = True) -> int:
        """
        Obtiene el conteo total de registros

        Args:
            db: Sesión de base de datos
            active_only: Solo contar registros activos

        Returns:
            int: Número total de registros
        """
        try:
            query = db.query(self.model)

            if active_only and hasattr(self.model, 'IsActive'):
                query = query.filter(self.model.IsActive == True)

            return query.count()

        except Exception as e:
            logger.error(f"Error contando {self.model.__name__}: {e}")
            return 0

    def exists(self, db: Session, *, id: Any) -> bool:
        """
        Verifica si existe un registro con el ID dado

        Args:
            db: Sesión de base de datos
            id: ID a verificar

        Returns:
            bool: True si existe, False si no
        """
        try:
            return db.query(self.model).filter(self.model.Id == id).first() is not None
        except Exception as e:
            logger.error(f"Error verificando existencia de {self.model.__name__}: {e}")
            return False

    def get_active(self, db: Session) -> List[ModelType]:
        """
        Obtiene todos los registros activos
        Solo funciona si el modelo tiene campo IsActive

        Args:
            db: Sesión de base de datos

        Returns:
            List[ModelType]: Lista de registros activos
        """
        try:
            if hasattr(self.model, 'IsActive'):
                query = db.query(self.model).filter(self.model.IsActive == True)

                if hasattr(self.model, 'CreatedAt'):
                    query = query.order_by(desc(self.model.CreatedAt))

                return query.all()
            else:
                return self.get_multi(db, skip=0, limit=10000, active_only=False)

        except Exception as e:
            logger.error(f"Error obteniendo {self.model.__name__} activos: {e}")
            return []

    def search_by_field(
            self,
            db: Session,
            *,
            field_name: str,
            value: Any,
            exact_match: bool = True
    ) -> List[ModelType]:
        """
        Busca registros por un campo específico

        Args:
            db: Sesión de base de datos
            field_name: Nombre del campo a buscar
            value: Valor a buscar
            exact_match: Si usar coincidencia exacta o LIKE

        Returns:
            List[ModelType]: Registros encontrados
        """
        try:
            if not hasattr(self.model, field_name):
                logger.warning(f"Campo {field_name} no existe en {self.model.__name__}")
                return []

            field = getattr(self.model, field_name)

            if exact_match:
                query = db.query(self.model).filter(field == value)
            else:
                query = db.query(self.model).filter(field.like(f"%{value}%"))

            # Filtrar activos si es posible
            if hasattr(self.model, 'IsActive'):
                query = query.filter(self.model.IsActive == True)

            return query.all()

        except Exception as e:
            logger.error(f"Error buscando {self.model.__name__} por {field_name}: {e}")
            return []

    def get_by_ids(self, db: Session, *, ids: List[Any]) -> List[ModelType]:
        """
        Obtiene múltiples registros por lista de IDs

        Args:
            db: Sesión de base de datos
            ids: Lista de IDs a buscar

        Returns:
            List[ModelType]: Registros encontrados
        """
        try:
            if not ids:
                return []

            return db.query(self.model).filter(self.model.Id.in_(ids)).all()

        except Exception as e:
            logger.error(f"Error obteniendo {self.model.__name__} por IDs: {e}")
            return []

    def bulk_update(
            self,
            db: Session,
            *,
            filters: Dict[str, Any],
            update_data: Dict[str, Any]
    ) -> int:
        """
        Actualización masiva de registros

        Args:
            db: Sesión de base de datos
            filters: Filtros para seleccionar registros
            update_data: Datos a actualizar

        Returns:
            int: Número de registros actualizados
        """
        try:
            query = db.query(self.model)

            # Aplicar filtros
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

            # Agregar timestamp de actualización
            if hasattr(self.model, 'UpdatedAt'):
                update_data['UpdatedAt'] = func.getdate()

            # Ejecutar actualización
            count = query.update(update_data)
            db.commit()

            logger.info(f"Actualización masiva de {self.model.__name__}: {count} registros")
            return count

        except Exception as e:
            db.rollback()
            logger.error(f"Error en actualización masiva de {self.model.__name__}: {e}")
            raise