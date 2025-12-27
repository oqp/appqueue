# pytest configuration 
"""
Configuración global de pytest con fixtures compartidas
Para pruebas de endpoints y CRUD
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import Generator, Dict, Any

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import get_db, Base
from app.models.user import User
from app.models.role import Role
from app.models.station import Station
from app.models.service_type import ServiceType
from app.models.patient import Patient
from app.core.security import create_password_hash
from app.core.config import settings

# ========================================
# CONFIGURACIÓN DE BASE DE DATOS DE TEST
# ========================================

# URL de la base de datos de test
TEST_DATABASE_URL = "mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"

# Crear engine para tests
test_engine = create_engine(TEST_DATABASE_URL, echo=False)

# Crear sesión de test
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ========================================
# FIXTURES DE SESIÓN Y CLIENTE
# ========================================

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Crea una sesión de base de datos limpia para cada test
    """
    # Crear conexión y transacción
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Limpiar tablas en orden correcto (por foreign keys)
    try:
        session.execute(text("DELETE FROM ActivityLog"))
        session.execute(text("DELETE FROM NotificationLog"))
        session.execute(text("DELETE FROM DailyMetrics"))
        session.execute(text("DELETE FROM QueueState"))
        session.execute(text("DELETE FROM Tickets"))
        session.execute(text("DELETE FROM Users"))
        session.execute(text("DELETE FROM Stations"))
        session.execute(text("DELETE FROM Patients"))
        session.execute(text("DELETE FROM ServiceTypes"))
        session.execute(text("DELETE FROM Roles"))
        session.commit()
    except:
        session.rollback()

    # Crear datos básicos de test
    setup_test_data(session)

    yield session

    # Limpiar después del test
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Crea un cliente de test que usa la sesión de test
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ========================================
# FIXTURES DE DATOS DE TEST
# ========================================

def setup_test_data(db: Session) -> Dict[str, Any]:
    """
    Configura datos básicos necesarios para los tests
    Retorna un diccionario con los IDs creados
    """
    # Crear roles básicos
    admin_role = Role(
        Name="Administrador",
        Description="Administrador del sistema",
        Permissions='{"all": true}',
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    supervisor_role = Role(
        Name="Supervisor",
        Description="Supervisor del laboratorio",
        Permissions='{"users": ["view", "edit"], "reports": ["view"]}',
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    technician_role = Role(
        Name="Técnico",
        Description="Técnico de laboratorio",
        Permissions='{"queue": ["manage"], "tickets": ["create", "update"]}',
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    receptionist_role = Role(
        Name="Recepcionista",
        Description="Recepcionista",
        Permissions='{"tickets": ["create"], "patients": ["create", "view"]}',
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    db.add_all([admin_role, supervisor_role, technician_role, receptionist_role])
    db.commit()
    db.refresh(admin_role)
    db.refresh(supervisor_role)
    db.refresh(technician_role)
    db.refresh(receptionist_role)

    # Crear tipos de servicio
    service_type1 = ServiceType(
        Code="LAB",
        Name="Análisis de Laboratorio",
        Description="Análisis clínicos generales",
        TicketPrefix="LAB",
        AverageTimeMinutes=15,
        Priority=1,
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    service_type2 = ServiceType(
        Code="RES",
        Name="Entrega de Resultados",
        Description="Entrega de resultados de análisis",
        TicketPrefix="RES",
        AverageTimeMinutes=5,
        Priority=2,
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    db.add_all([service_type1, service_type2])
    db.commit()
    db.refresh(service_type1)
    db.refresh(service_type2)

    # Crear estaciones
    station1 = Station(
        Code="V01",
        Name="Ventanilla 1",
        Description="Ventanilla de análisis",
        ServiceTypeId=service_type1.Id,
        Location="Planta Baja",
        Status="Available",
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    station2 = Station(
        Code="V02",
        Name="Ventanilla 2",
        Description="Ventanilla de resultados",
        ServiceTypeId=service_type2.Id,
        Location="Planta Baja",
        Status="Available",
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    db.add_all([station1, station2])
    db.commit()
    db.refresh(station1)
    db.refresh(station2)

    # Guardar IDs en atributos de la sesión para uso en tests
    db.admin_role_id = admin_role.Id
    db.supervisor_role_id = supervisor_role.Id
    db.technician_role_id = technician_role.Id
    db.receptionist_role_id = receptionist_role.Id
    db.station1_id = station1.Id
    db.station2_id = station2.Id
    db.service_type1_id = service_type1.Id
    db.service_type2_id = service_type2.Id

    return {
        "admin_role_id": admin_role.Id,
        "supervisor_role_id": supervisor_role.Id,
        "technician_role_id": technician_role.Id,
        "receptionist_role_id": receptionist_role.Id,
        "station1_id": station1.Id,
        "station2_id": station2.Id,
        "service_type1_id": service_type1.Id,
        "service_type2_id": service_type2.Id
    }


@pytest.fixture
def sample_user_data(db_session: Session) -> Dict[str, Any]:
    """
    Datos de ejemplo para crear usuarios
    """
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Test123!",
        "full_name": "Test User",
        "role_id": db_session.technician_role_id,
        "station_id": db_session.station1_id,
        "phone": "+51999888777",
        "is_active": True
    }


@pytest.fixture
def created_user(db_session: Session) -> User:
    """
    Crea un usuario de test en la base de datos
    """
    user = User(
        Username="existinguser",
        Email="existing@test.com",
        FullName="Existing User",
        PasswordHash=create_password_hash("Password123!"),
        RoleId=db_session.technician_role_id,
        StationId=db_session.station1_id,
        Phone="+51999000111",
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """
    Crea un usuario administrador de test
    """
    admin = User(
        Username="admin",
        Email="admin@test.com",
        FullName="Admin User",
        PasswordHash=create_password_hash("Admin123!"),
        RoleId=db_session.admin_role_id,
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def supervisor_user(db_session: Session) -> User:
    """
    Crea un usuario supervisor de test
    """
    supervisor = User(
        Username="supervisor",
        Email="supervisor@test.com",
        FullName="Supervisor User",
        PasswordHash=create_password_hash("Supervisor123!"),
        RoleId=db_session.supervisor_role_id,
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )
    db_session.add(supervisor)
    db_session.commit()
    db_session.refresh(supervisor)
    return supervisor


@pytest.fixture
def technician_user(db_session: Session) -> User:
    """
    Crea un usuario técnico de test
    """
    technician = User(
        Username="technician",
        Email="technician@test.com",
        FullName="Technician User",
        PasswordHash=create_password_hash("Technician123!"),
        RoleId=db_session.technician_role_id,
        StationId=db_session.station1_id,
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )
    db_session.add(technician)
    db_session.commit()
    db_session.refresh(technician)
    return technician


# ========================================
# FIXTURES DE AUTENTICACIÓN
# ========================================

@pytest.fixture
def headers_admin(client: TestClient, admin_user: User) -> Dict[str, str]:
    """
    Headers con token JWT de admin
    """
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_supervisor(client: TestClient, supervisor_user: User) -> Dict[str, str]:
    """
    Headers con token JWT de supervisor
    """
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "supervisor", "password": "Supervisor123!"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers_technician(client: TestClient, technician_user: User) -> Dict[str, str]:
    """
    Headers con token JWT de técnico
    """
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "technician", "password": "Technician123!"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ========================================
# FIXTURES DE PACIENTES (para tickets)
# ========================================

@pytest.fixture
def sample_patient(db_session: Session) -> Patient:
    """
    Crea un paciente de ejemplo para tests
    """
    patient = Patient(
        DocumentNumber="12345678",
        FullName="Juan Pérez",
        BirthDate=datetime(1990, 1, 1).date(),
        Gender="M",
        Phone="+51999888777",
        Email="juan@example.com",
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


# 2. FIXTURE sample_service_type (alrededor de línea 400)
@pytest.fixture
def sample_service_type(db_session: Session) -> ServiceType:
    """
    Crea un tipo de servicio de ejemplo
    Campos correctos según app/models/service_type.py
    """
    # Verificar si ya existe uno con el mismo código
    existing = db_session.query(ServiceType).filter(ServiceType.Code == "ANA").first()
    if existing:
        return existing

    service_type = ServiceType(
        Code="ANA",  # Campo requerido
        Name="Análisis",  # Campo requerido
        Description="Análisis de laboratorio general",  # Opcional
        Priority=1,  # Campo requerido (default=1)
        AverageTimeMinutes=15,  # NO AverageServiceTime, campo requerido (default=10)
        TicketPrefix="A",  # Campo requerido
        Color="#007bff",  # Campo requerido (default='#007bff')
        IsActive=True  # De ActiveMixin
        # CreatedAt y UpdatedAt se generan automáticamente
    )
    db_session.add(service_type)
    db_session.commit()
    db_session.refresh(service_type)
    return service_type


# 3. FIXTURE sample_station (alrededor de línea 420)
@pytest.fixture
def sample_station(db_session: Session, sample_service_type: ServiceType) -> Station:
    """
    Crea una estación de prueba
    Campos correctos según app/models/station.py
    """
    station = Station(
        Name="Ventanilla Test",  # Campo requerido
        Code="VT01",  # Campo requerido, único
        Description="Ventanilla de prueba",  # Opcional
        ServiceTypeId=sample_service_type.Id,  # Opcional (FK a ServiceTypes)
        Location="Planta Baja",  # Opcional
        Status="Available",  # Campo requerido (default='Available')
        CurrentTicketId=None,  # Opcional
        IsActive=True  # De ActiveMixin
        # CreatedAt y UpdatedAt se generan automáticamente
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station



# ========================================
# UTILIDADES DE TEST
# ========================================

@pytest.fixture
def mock_redis(monkeypatch):
    """
    Mock de Redis para tests que no requieren Redis real
    """

    class MockRedis:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value, ex=None):
            self.data[key] = value
            return True

        def delete(self, key):
            if key in self.data:
                del self.data[key]
                return 1
            return 0

        def exists(self, key):
            return key in self.data

    mock = MockRedis()
    monkeypatch.setattr("app.core.redis.redis_client", mock)
    return mock