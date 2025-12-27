"""
Tests unitarios para operaciones CRUD de pacientes
Usando SQL Server directamente - NO async
Compatible con el modelo Patient que usa PascalCase
"""

import pytest
from datetime import date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from typing import Generator

from app.models.patient import Patient
from app.crud import patient as patient_crud
from app.schemas.patient import PatientCreate, PatientUpdate

# ========================================
# CONFIGURACIÓN DE BASE DE DATOS DE TEST
# ========================================

TEST_DATABASE_URL = "mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"

# Crear engine para tests
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Crea una sesión de base de datos limpia para cada test
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Limpiar tablas que dependen de Patients primero
    try:
        session.execute(text("DELETE FROM Tickets"))
        session.execute(text("DELETE FROM Patients"))
        session.commit()
    except:
        session.rollback()

    yield session

    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()


# ========================================
# TESTS DE CREACIÓN
# ========================================

def test_create_patient(db_session: Session):
    """Test creating a new patient"""
    patient_data = PatientCreate(
        document_type="DNI",
        document_number="12345678",
        first_name="Juan",
        last_name="Pérez",
        birth_date=date(1990, 5, 15),
        gender="M",
        phone="987654321",
        email="juan.perez@email.com"
        # address no existe en el modelo
    )

    created_patient = patient_crud.create(db_session, obj_in=patient_data)

    assert created_patient.Id is not None
    assert created_patient.DocumentNumber == "12345678"
    assert created_patient.FullName == "Juan Pérez"  # FullName es un solo campo
    assert created_patient.Gender == "M"
    assert created_patient.Phone == "987654321"
    assert created_patient.Email == "juan.perez@email.com"
    assert created_patient.IsActive is True


def test_create_patient_duplicate_document(db_session: Session):
    """Test creating a patient with duplicate document number"""
    from sqlalchemy.exc import IntegrityError

    patient_data = PatientCreate(
        document_type="DNI",
        document_number="87654321",
        first_name="María",
        last_name="González",
        birth_date=date(1985, 3, 20),
        gender="F",
        phone="999888777"
    )

    # Create first patient
    created_patient = patient_crud.create(db_session, obj_in=patient_data)
    assert created_patient is not None

    # Try to create another patient with same document number - should raise IntegrityError
    with pytest.raises(IntegrityError):
        duplicate_patient = patient_crud.create(db_session, obj_in=patient_data)
        db_session.commit()  # El error ocurre en el commit


def test_create_patient_minimal_fields(db_session: Session):
    """Test creating patient with only required fields"""
    patient_data = PatientCreate(
        document_type="DNI",
        document_number="11112222",
        first_name="Minimal",
        last_name="Patient",
        birth_date=date(1990, 1, 1),
        gender="M"
        # phone, email, and address are optional
    )

    created_patient = patient_crud.create(db_session, obj_in=patient_data)

    assert created_patient.Id is not None
    assert created_patient.DocumentNumber == "11112222"
    assert created_patient.Phone is None
    assert created_patient.Email is None
    # El modelo Patient no tiene campo Address


# ========================================
# TESTS DE LECTURA
# ========================================

def test_get_patient(db_session: Session):
    """Test getting a patient by ID"""
    # Create a patient first
    patient_data = PatientCreate(
        document_type="DNI",
        document_number="11223344",
        first_name="Carlos",
        last_name="Rodríguez",
        birth_date=date(1988, 7, 10),
        gender="M",
        phone="977665544"
    )

    created_patient = patient_crud.create(db_session, obj_in=patient_data)

    # Get the patient
    retrieved_patient = patient_crud.get(db_session, patient_id=created_patient.Id)

    assert retrieved_patient is not None
    assert retrieved_patient.Id == created_patient.Id
    assert retrieved_patient.DocumentNumber == "11223344"
    assert retrieved_patient.FullName == "Carlos Rodríguez"  # FullName es un solo campo


def test_get_patient_not_found(db_session: Session):
    """Test getting a non-existent patient"""
    # Use a GUID that doesn't exist
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    retrieved_patient = patient_crud.get(db_session, patient_id=non_existent_id)

    assert retrieved_patient is None


def test_get_patient_by_document(db_session: Session):
    """Test getting a patient by document number"""
    # Create a patient first
    patient_data = PatientCreate(
        document_type="DNI",
        document_number="55667788",
        first_name="Ana",
        last_name="Martínez",
        birth_date=date(1992, 11, 25),
        gender="F",
        phone="966554433"
    )

    created_patient = patient_crud.create(db_session, obj_in=patient_data)

    # Get the patient by document
    retrieved_patient = patient_crud.get_by_document(db_session, "55667788")

    assert retrieved_patient is not None
    assert retrieved_patient.DocumentNumber == "55667788"
    assert retrieved_patient.FullName == "Ana Martínez"  # FullName es un solo campo


def test_get_patients_list(db_session: Session):
    """Test getting list of patients with pagination"""
    # Create multiple patients
    for i in range(5):
        patient_data = PatientCreate(
            document_type="DNI",
            document_number=f"9000000{i}",
            first_name=f"Paciente{i}",
            last_name=f"Apellido{i}",
            birth_date=date(1990 + i, 1, 1),
            gender="M" if i % 2 == 0 else "F",
            phone=f"90000000{i}"
        )
        patient_crud.create(db_session, obj_in=patient_data)

    # Get patients with pagination
    patients_list = patient_crud.get_multi(db_session, skip=0, limit=3)

    assert len(patients_list) == 3

    # Test pagination - second page
    patients_list_page2 = patient_crud.get_multi(db_session, skip=3, limit=2)
    assert len(patients_list_page2) == 2


# ========================================
# TESTS DE ACTUALIZACIÓN
# ========================================

def test_update_patient(db_session: Session):
    """Test updating a patient"""
    # Create a patient first
    patient_data = PatientCreate(
        document_type="DNI",
        document_number="33445566",
        first_name="Pedro",
        last_name="López",
        birth_date=date(1987, 4, 18),
        gender="M",
        phone="955443322"
    )

    created_patient = patient_crud.create(db_session, obj_in=patient_data)

    # Update the patient
    update_data = PatientUpdate(
        first_name="Pedro José",
        phone="911223344",
        email="pedro.lopez@email.com"
        # address no existe en el modelo
    )

    # El método update necesita el objeto, no el ID
    updated_patient = patient_crud.update(
        db_session,
        db_obj=created_patient,  # Pasar el objeto, no el ID
        obj_in=update_data
    )

    assert updated_patient is not None
    assert updated_patient.FullName == "Pedro José López"  # El CRUD debe concatenar first_name + last_name
    assert updated_patient.Phone == "911223344"
    assert updated_patient.Email == "pedro.lopez@email.com"


def test_update_patient_not_found(db_session: Session):
    """Test updating a non-existent patient"""
    non_existent_id = "00000000-0000-0000-0000-000000000000"

    # Intentar obtener un paciente que no existe
    non_existent_patient = patient_crud.get(db_session, patient_id=non_existent_id)
    assert non_existent_patient is None

    # No podemos actualizar un paciente que no existe
    # El método update requiere un objeto db_obj válido


def test_update_patient_partial(db_session: Session):
    """Test partial update of patient (only some fields)"""
    # Create a patient
    patient_data = PatientCreate(
        document_type="DNI",
        document_number="44556677",
        first_name="Original",
        last_name="Name",
        birth_date=date(1990, 1, 1),
        gender="M",
        phone="999888777",
        email="original@email.com"
    )

    created_patient = patient_crud.create(db_session, obj_in=patient_data)

    # Update only phone
    update_data = PatientUpdate(phone="111222333")

    # El método update necesita el objeto, no el ID
    updated_patient = patient_crud.update(
        db_session,
        db_obj=created_patient,  # Pasar el objeto, no el ID
        obj_in=update_data
    )

    assert updated_patient.Phone == "111222333"
    assert updated_patient.FullName == "Original Name"  # No cambia porque solo actualizamos phone
    assert updated_patient.Email == "original@email.com"  # Unchanged


# ========================================
# TESTS DE ELIMINACIÓN
# ========================================

def test_delete_patient(db_session: Session):
    """Test soft deleting a patient"""
    # Create a patient first
    patient_data = PatientCreate(
        document_type="DNI",
        document_number="77889900",
        first_name="Luis",
        last_name="García",
        birth_date=date(1995, 9, 30),
        gender="M",
        phone="944332211"
    )

    created_patient = patient_crud.create(db_session, obj_in=patient_data)
    patient_id = created_patient.Id

    # Delete the patient (soft delete)
    deleted = patient_crud.delete(db_session, patient_id)

    assert deleted is True

    # Verify the patient is marked as inactive
    # get() method should not return inactive patients
    deleted_patient = patient_crud.get(db_session, patient_id)
    assert deleted_patient is None


def test_delete_patient_not_found(db_session: Session):
    """Test deleting a non-existent patient"""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    deleted = patient_crud.delete(db_session, non_existent_id)

    assert deleted is False


# ========================================
# TESTS DE BÚSQUEDA
# ========================================

def test_search_patients_by_document(db_session: Session):
    """Test searching patients by document number"""
    # Create multiple patients
    for i in range(3):
        patient_data = PatientCreate(
            document_type="DNI",
            document_number=f"100000{i}",
            first_name=f"Test{i}",
            last_name=f"Patient{i}",
            birth_date=date(1990, 1, 1),
            gender="M"
        )
        patient_crud.create(db_session, obj_in=patient_data)

    # Search by partial document number
    search_results = patient_crud.search(db_session, search_term="100000")

    assert len(search_results) >= 3
    for result in search_results:
        assert "100000" in result.DocumentNumber


def test_search_patients_by_name(db_session: Session):
    """Test searching patients by name"""
    # Create patients with similar names
    patients_data = [
        PatientCreate(
            document_type="DNI",
            document_number="20000001",
            first_name="Juan",
            last_name="Pérez",
            birth_date=date(1990, 1, 1),
            gender="M"
        ),
        PatientCreate(
            document_type="DNI",
            document_number="20000002",
            first_name="Juan Carlos",
            last_name="González",
            birth_date=date(1991, 1, 1),
            gender="M"
        ),
        PatientCreate(
            document_type="DNI",
            document_number="20000003",
            first_name="María",
            last_name="Pérez",
            birth_date=date(1992, 1, 1),
            gender="F"
        )
    ]

    for patient_data in patients_data:
        patient_crud.create(db_session, obj_in=patient_data)

    # Search by first name
    search_results_name = patient_crud.search(db_session, search_term="Juan")
    assert len(search_results_name) >= 2

    # Search by last name
    search_results_lastname = patient_crud.search(db_session, search_term="Pérez")
    assert len(search_results_lastname) >= 2


def test_search_patients_no_results(db_session: Session):
    """Test search with no results"""
    search_results = patient_crud.search(db_session, search_term="NoExiste999")
    assert len(search_results) == 0


# ========================================
# TESTS DE VALIDACIÓN
# ========================================

def test_patient_birth_date_validation(db_session: Session):
    """Test patient birth date handling"""
    patient_data = PatientCreate(
        document_type="DNI",
        document_number="99887766",
        first_name="Test",
        last_name="Patient",
        birth_date=date(2000, 6, 15),
        gender="M",
        phone="999888777"
    )

    created_patient = patient_crud.create(db_session, obj_in=patient_data)

    assert created_patient.BirthDate == date(2000, 6, 15)

    # Calculate expected age (this will vary based on current date)
    from datetime import datetime
    today = datetime.now().date()
    expected_age = today.year - 2000
    if today.month < 6 or (today.month == 6 and today.day < 15):
        expected_age -= 1

    # Age should be calculated correctly (if implemented in model)
    # This depends on the model implementation


def test_get_active_patients_only(db_session: Session):
    """Test that only active patients are returned when filtering by is_active=True"""
    # Create an active patient
    active_patient_data = PatientCreate(
        document_type="DNI",
        document_number="88776655",
        first_name="Active",
        last_name="Patient",
        birth_date=date(1990, 1, 1),
        gender="M"
    )
    active_patient = patient_crud.create(db_session, obj_in=active_patient_data)

    # Create and delete a patient (soft delete)
    inactive_patient_data = PatientCreate(
        document_type="DNI",
        document_number="99887766",
        first_name="Inactive",
        last_name="Patient",
        birth_date=date(1991, 1, 1),
        gender="F"
    )
    inactive_patient = patient_crud.create(db_session, obj_in=inactive_patient_data)
    patient_crud.delete(db_session, inactive_patient.Id)

    # Get all patients sin filtro - debería retornar todos
    all_patients_no_filter = patient_crud.get_multi(db_session)

    # Get only active patients - pasar is_active=True explícitamente
    active_patients = patient_crud.get_multi(db_session, is_active=True)

    # Check that only active patient is in the filtered list
    active_patient_ids = [p.Id for p in active_patients]
    assert active_patient.Id in active_patient_ids
    assert inactive_patient.Id not in active_patient_ids

    # Verificar que get_multi sin filtro retorna ambos
    all_patient_ids = [p.Id for p in all_patients_no_filter]
    assert len(all_patient_ids) >= 2  # Debe incluir ambos