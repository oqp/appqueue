from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
from datetime import datetime, date

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


class CRUDPatient:
    """
    CRUD operations for Patient model.
    Adaptado para usar los nombres correctos:
    - created_at y UpdatedAt (snake_case por los mixins)
    - IsActive (PascalCase)
    - DocumentNumber, FullName, etc. (PascalCase)
    """

    def create(
            self,
            db: Session,
            obj_in: PatientCreate
    ) -> Patient:
        """
        Crear un nuevo paciente en BD
        """
        # Mapear los campos del schema (snake_case) a los del modelo (PascalCase)
        patient_data = {
            "DocumentNumber": obj_in.document_number,
            "FullName": f"{obj_in.first_name} {obj_in.last_name}",
            "Gender": obj_in.gender or "Otro",
            "Phone": obj_in.phone,
            "Email": obj_in.email
        }

        # Solo agregar BirthDate si existe (el modelo lo requiere, pero desde DNI no lo tenemos)
        if obj_in.birth_date:
            patient_data["BirthDate"] = obj_in.birth_date
        else:
            # Usar una fecha por defecto temporal (1900-01-01) si no se proporciona
            # Esto es necesario porque el modelo requiere BirthDate
            patient_data["BirthDate"] = date(1900, 1, 1)

        db_obj = Patient(**patient_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(
            self,
            db: Session,
            patient_id: str  # Cambiado a str porque usa UNIQUEIDENTIFIER
    ) -> Optional[Patient]:
        """
        Obtener paciente por ID
        """
        return db.query(Patient).filter(
            Patient.Id == patient_id,
            Patient.IsActive == True  # IsActive está en PascalCase
        ).first()

    def get_by_document(
            self,
            db: Session,
            document_number: str
    ) -> Optional[Patient]:
        """
        Obtener paciente por número de documento
        """
        return db.query(Patient).filter(
            Patient.DocumentNumber == document_number,  # PascalCase
            Patient.IsActive == True  # PascalCase
        ).first()

    def get_multi(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100,
            search: Optional[str] = None,
            is_active: Optional[bool] = None
    ) -> List[Patient]:
        """
        Obtener múltiples pacientes con filtros
        """
        query = db.query(Patient)

        # Aplicar filtros usando los nombres correctos de campos
        if search:
            search_filter = or_(
                Patient.FullName.ilike(f"%{search}%"),
                Patient.DocumentNumber.ilike(f"%{search}%"),
                Patient.Email.ilike(f"%{search}%"),
                Patient.Phone.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        if is_active is not None:
            query = query.filter(Patient.IsActive == is_active)  # PascalCase

        # Ordenar por fecha de creación descendente
        # IMPORTANTE: usar created_at (snake_case) no CreatedAt
        query = query.order_by(Patient.CreatedAt.desc())

        # Aplicar paginación
        return query.offset(skip).limit(limit).all()

    def search(
            self,
            db: Session,
            search_term: str,
            limit: int = 10
    ) -> List[Patient]:
        """
        Búsqueda rápida para autocompletado
        """
        search_pattern = f"%{search_term}%"

        return db.query(Patient).filter(
            or_(
                Patient.DocumentNumber.ilike(search_pattern),
                Patient.FullName.ilike(search_pattern),
                Patient.Email.ilike(search_pattern)
            ),
            Patient.IsActive == True  # PascalCase
        ).limit(limit).all()

    def update(
            self,
            db: Session,
            db_obj: Patient,
            obj_in: PatientUpdate
    ) -> Patient:
        """
        Actualizar paciente en BD
        """
        # Mapear campos del schema a los del modelo
        if obj_in.document_number is not None:
            db_obj.DocumentNumber = obj_in.document_number

        if obj_in.first_name is not None or obj_in.last_name is not None:
            # Reconstruir el FullName si se actualizan los nombres
            first = obj_in.first_name if obj_in.first_name is not None else db_obj.FullName.split()[0]
            last = obj_in.last_name if obj_in.last_name is not None else ' '.join(db_obj.FullName.split()[1:])
            db_obj.FullName = f"{first} {last}"

        if obj_in.birth_date is not None:
            db_obj.BirthDate = obj_in.birth_date

        if obj_in.gender is not None:
            db_obj.Gender = obj_in.gender

        if obj_in.phone is not None:
            db_obj.Phone = obj_in.phone

        if obj_in.email is not None:
            db_obj.Email = obj_in.email

        if obj_in.is_active is not None:
            db_obj.IsActive = obj_in.is_active

        # Actualizar UpdatedAt (snake_case por el mixin)
        db_obj.UpdatedAt = datetime.utcnow()

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(
            self,
            db: Session,
            patient_id: str
    ) -> bool:
        """
        Eliminar paciente (soft delete)
        """
        patient = db.query(Patient).filter(Patient.Id == patient_id).first()

        if not patient:
            return False

        # Soft delete
        patient.IsActive = False

        # Actualizar UpdatedAt (snake_case por el mixin)
        patient.UpdatedAt = datetime.utcnow()

        db.commit()
        return True

    def get_all_by_ids(
            self,
            db: Session,
            patient_ids: List[str]
    ) -> List[Patient]:
        """
        Obtener múltiples pacientes por lista de IDs
        """
        return db.query(Patient).filter(
            Patient.Id.in_(patient_ids),
            Patient.IsActive == True  # PascalCase
        ).all()

    def count(
            self,
            db: Session,
            is_active: Optional[bool] = None
    ) -> int:
        """
        Contar total de pacientes
        """
        query = db.query(func.count(Patient.Id))

        if is_active is not None:
            query = query.filter(Patient.IsActive == is_active)  # PascalCase

        return query.scalar()

    def exists_by_document(
            self,
            db: Session,
            document_number: str
    ) -> bool:
        """
        Verificar si existe un paciente con el documento
        """
        return db.query(
            db.query(Patient).filter(
                Patient.DocumentNumber == document_number
            ).exists()
        ).scalar()


# Instancia singleton del CRUD
patient = CRUDPatient()