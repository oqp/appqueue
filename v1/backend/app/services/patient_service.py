from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date

from app.crud.patient import patient as crud_patient
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.dni_service import consultar_dni


class PatientService:
    """
    Servicio para gestionar la lógica de negocio de pacientes.
    Adaptado para trabajar con el modelo que usa PascalCase.
    """

    async def get_or_create_by_document(
            self,
            db: Session,
            document_number: str
    ) -> Optional[Patient]:
        """
        Busca un paciente por número de documento.
        1. Primero consulta en BD local usando CRUD
        2. Si no existe, consulta el servicio externo de DNI
        3. Si encuentra datos válidos, crea el paciente en BD

        Args:
            db: Sesión de base de datos
            document_number: Número de documento a buscar

        Returns:
            Patient o None si no se encuentra

        Raises:
            ValueError: Si hay error en el servicio externo
        """
        # Paso 1: Buscar en BD local usando CRUD
        patient = crud_patient.get_by_document(db, document_number)

        if patient:
            return patient

        # Paso 2: Si no existe localmente, consultar servicio externo DNI
        try:
            dni_response = consultar_dni(document_number)

            # Verificar si la respuesta fue exitosa
            if dni_response.get("status") == "success" and dni_response.get("data"):
                data = dni_response["data"]

                # Preparar datos para crear el paciente
                # Convertir la respuesta del DNI al formato del schema
                patient_dict = {
                    "document_type": "DNI",
                    "document_number": data.get("DNI", document_number),
                    "first_name": data.get("Nombres", "").strip(),
                    "last_name": f"{data.get('ApellidoPaterno', '')} {data.get('ApellidoMaterno', '')}".strip(),
                    "birth_date": None,  # El servicio DNI no proporciona fecha de nacimiento
                    "gender": None,  # El servicio DNI no proporciona género
                    "phone": None,
                    "email": None
                }

                # Crear el objeto PatientCreate desde el diccionario
                patient_data = PatientCreate(**patient_dict)

                # Paso 3: Crear el paciente en BD usando CRUD
                try:
                    new_patient = crud_patient.create(db, obj_in=patient_data)
                    return new_patient
                except Exception as e:
                    # Si ya existe (race condition), intentar obtenerlo
                    existing = crud_patient.get_by_document(db, document_number)
                    if existing:
                        return existing
                    raise e

            elif dni_response.get("status") == "error":
                # Si hay error en el servicio externo
                error_info = dni_response.get("error", {})
                raise ValueError(error_info.get("message", "Error al consultar el DNI"))
            else:
                # No se encontró información
                return None

        except ValueError:
            # Re-lanzar los errores de valor
            raise
        except Exception as e:
            # Manejar cualquier otro error del servicio externo
            raise ValueError(f"Error al consultar el servicio externo: {str(e)}")

    def create_patient(
            self,
            db: Session,
            patient_data: PatientCreate
    ) -> Patient:
        """
        Crea un nuevo paciente

        Args:
            db: Sesión de base de datos
            patient_data: Datos del paciente a crear

        Returns:
            Patient creado

        Raises:
            ValueError: Si ya existe un paciente con el mismo documento
        """
        # Verificar si ya existe
        existing = crud_patient.get_by_document(db, patient_data.document_number)
        if existing:
            raise ValueError(f"Ya existe un paciente con el documento {patient_data.document_number}")

        # Crear usando CRUD
        return crud_patient.create(db, obj_in=patient_data)

    def get_patient_by_id(
            self,
            db: Session,
            patient_id: str  # Cambiado a str porque usa UNIQUEIDENTIFIER
    ) -> Optional[Patient]:
        """
        Obtiene un paciente por ID

        Args:
            db: Sesión de base de datos
            patient_id: ID del paciente (GUID)

        Returns:
            Patient o None si no se encuentra
        """
        return crud_patient.get(db, patient_id)

    def get_patients(
            self,
            db: Session,
            skip: int = 0,
            limit: int = 100,
            search: Optional[str] = None,
            is_active: Optional[bool] = None
    ) -> List[Patient]:
        """
        Obtiene lista de pacientes con filtros y paginación

        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar
            limit: Límite de registros
            search: Término de búsqueda
            is_active: Filtro por estado activo

        Returns:
            Lista de pacientes
        """
        return crud_patient.get_multi(
            db,
            skip=skip,
            limit=limit,
            search=search,
            is_active=is_active
        )

    def search_patients(
            self,
            db: Session,
            search_term: str,
            limit: int = 10
    ) -> List[Patient]:
        """
        Búsqueda rápida de pacientes para autocompletado

        Args:
            db: Sesión de base de datos
            search_term: Término de búsqueda
            limit: Límite de resultados

        Returns:
            Lista de pacientes que coinciden
        """
        return crud_patient.search(db, search_term, limit)

    def update_patient(
            self,
            db: Session,
            patient_id: str,
            patient_data: PatientUpdate
    ) -> Patient:
        """
        Actualiza un paciente

        Args:
            db: Sesión de base de datos
            patient_id: ID del paciente (GUID)
            patient_data: Datos a actualizar

        Returns:
            Patient actualizado

        Raises:
            ValueError: Si el paciente no existe o el documento ya está en uso
        """
        # Obtener paciente existente
        patient = crud_patient.get(db, patient_id)
        if not patient:
            raise ValueError(f"Paciente con ID {patient_id} no encontrado")

        # Si está cambiando el documento, verificar que no exista
        if patient_data.document_number and patient_data.document_number != patient.DocumentNumber:
            existing = crud_patient.get_by_document(db, patient_data.document_number)
            if existing:
                raise ValueError(f"Ya existe otro paciente con el documento {patient_data.document_number}")

        # Actualizar usando CRUD
        return crud_patient.update(db, db_obj=patient, obj_in=patient_data)

    def delete_patient(
            self,
            db: Session,
            patient_id: str
    ) -> bool:
        """
        Elimina un paciente (soft delete)

        Args:
            db: Sesión de base de datos
            patient_id: ID del paciente (GUID)

        Returns:
            True si se eliminó, False si no se encontró
        """
        return crud_patient.delete(db, patient_id)

    def bulk_create_patients(
            self,
            db: Session,
            patients_data: List[PatientCreate]
    ) -> tuple[List[Patient], List[dict]]:
        """
        Crea múltiples pacientes en una operación

        Args:
            db: Sesión de base de datos
            patients_data: Lista de datos de pacientes

        Returns:
            Tupla con (pacientes creados, lista de errores)
        """
        created_patients = []
        errors = []

        for idx, patient_data in enumerate(patients_data):
            try:
                # Verificar si ya existe
                existing = crud_patient.get_by_document(db, patient_data.document_number)
                if existing:
                    errors.append({
                        "index": idx,
                        "document": patient_data.document_number,
                        "error": "Documento ya existe"
                    })
                    continue

                # Crear paciente
                patient = crud_patient.create(db, obj_in=patient_data)
                created_patients.append(patient)

            except Exception as e:
                errors.append({
                    "index": idx,
                    "document": getattr(patient_data, 'document_number', 'N/A'),
                    "error": str(e)
                })

        return created_patients, errors


    def get_patient_queue_stats(
            self,
            db: Session,
            patient_id: str,
            include_history: bool = False
    ) -> dict:
        """
        Obtiene estadísticas de cola del paciente

        Args:
            db: Sesión de base de datos
            patient_id: ID del paciente (GUID)
            include_history: Si incluir historial completo

        Returns:
            Diccionario con estadísticas
        """
        from app.models.ticket import Ticket
        from app.models.service_type import ServiceType
        from sqlalchemy import func
        from sqlalchemy.orm import joinedload

        # Obtener el paciente
        patient = crud_patient.get(db, patient_id)
        if not patient:
            raise ValueError(f"Paciente con ID {patient_id} no encontrado")

        # Obtener tickets activos del paciente con la relación service_type cargada
        active_tickets = db.query(Ticket).options(
            joinedload(Ticket.service_type)  # Cargar la relación ServiceType
        ).filter(
            Ticket.PatientId == patient_id,
            Ticket.Status.in_(['Waiting', 'Called', 'InProgress'])
        ).all()

        # Obtener el ticket actual (el más reciente de los activos)
        current_ticket = None
        if active_tickets:
            # Ordenar por fecha de creación y tomar el más reciente
            current_ticket = max(
                active_tickets,
                key=lambda x: x.CreatedAt if hasattr(x, 'CreatedAt') else x.CreatedAt
            )

        stats = {
            "patient": patient,
            "active_tickets_count": len(active_tickets),
            "active_tickets": active_tickets,
            "current_ticket": current_ticket
        }

        if include_history:
            # Obtener historial de tickets (últimos 30)
            recent_tickets = db.query(Ticket).options(
                joinedload(Ticket.service_type)
            ).filter(
                Ticket.PatientId == patient_id
            ).order_by(
                Ticket.CreatedAt.desc() if hasattr(Ticket, 'CreatedAt') else Ticket.CreatedAt.desc()
            ).limit(30).all()

            stats["history"] = recent_tickets[:10]

            # Contar total de visitas
            stats["total_visits"] = db.query(func.count(Ticket.Id)).filter(
                Ticket.PatientId == patient_id
            ).scalar()

        return stats


# Instancia del servicio
patient_service = PatientService()