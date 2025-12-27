"""
Pruebas unitarias para los endpoints de QueueState
Compatible con FastAPI TestClient y la estructura del proyecto
"""

import pytest
import sys
import os
from datetime import datetime, timedelta, date
from typing import Dict, Any, List
import uuid
import json

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import get_db
from app.models.queue_state import QueueState
from app.models.service_type import ServiceType
from app.models.station import Station
from app.models.ticket import Ticket
from app.models.patient import Patient
from app.models.user import User
from app.models.role import Role
from app.schemas.queue import (
    QueueStateResponse,
    QueueSummary,
    AdvanceQueueRequest,
    ResetQueueRequest,
    UpdateWaitTimeRequest,
    BatchQueueUpdate
)
from app.crud.queue import queue_crud
from app.core.security import create_password_hash, create_access_token


# ========================================
# CONFIGURACIÓN DE BASE DE DATOS DE TEST
# ========================================

TEST_DATABASE_URL = "mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """Sesión de base de datos para pruebas"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Limpiar tablas relevantes
    try:
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

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Cliente de prueba con override de la dependencia de BD"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def setup_roles(db_session: Session) -> Dict[str, Role]:
    """Crea roles necesarios para las pruebas"""
    roles = {}

    # Rol Admin
    admin_role = Role(
        Name="Admin",
        Description="Administrador del sistema",
        Permissions=json.dumps(["*"])
    )
    db_session.add(admin_role)
    roles['admin'] = admin_role

    # Rol Supervisor
    supervisor_role = Role(
        Name="Supervisor",
        Description="Supervisor",
        Permissions=json.dumps(["queue.*", "tickets.*", "patients.*"])
    )
    db_session.add(supervisor_role)
    roles['supervisor'] = supervisor_role

    # Rol Técnico
    technician_role = Role(
        Name="Technician",
        Description="Técnico de laboratorio",
        Permissions=json.dumps(["queue.attend", "tickets.update"])
    )
    db_session.add(technician_role)
    roles['technician'] = technician_role

    # Rol Usuario básico
    user_role = Role(
        Name="User",
        Description="Usuario básico",
        Permissions=json.dumps(["queue.view"])
    )
    db_session.add(user_role)
    roles['user'] = user_role

    db_session.commit()
    return roles


@pytest.fixture
def setup_users(db_session: Session, setup_roles: Dict[str, Role]) -> Dict[str, User]:
    """Crea usuarios de prueba con diferentes roles"""
    users = {}

    # Usuario Admin
    admin_user = User(
        Username="admin_test",
        Email="admin@test.com",
        FullName="Admin Test",
        PasswordHash=create_password_hash("admin123"),
        RoleId=setup_roles['admin'].Id,
        IsActive=True
    )
    db_session.add(admin_user)
    users['admin'] = admin_user

    # Usuario Supervisor
    supervisor_user = User(
        Username="supervisor_test",
        Email="supervisor@test.com",
        FullName="Supervisor Test",
        PasswordHash=create_password_hash("super123"),
        RoleId=setup_roles['supervisor'].Id,
        IsActive=True
    )
    db_session.add(supervisor_user)
    users['supervisor'] = supervisor_user

    # Usuario Técnico
    technician_user = User(
        Username="tech_test",
        Email="tech@test.com",
        FullName="Technician Test",
        PasswordHash=create_password_hash("tech123"),
        RoleId=setup_roles['technician'].Id,
        IsActive=True
    )
    db_session.add(technician_user)
    users['technician'] = technician_user

    # Usuario básico
    basic_user = User(
        Username="user_test",
        Email="user@test.com",
        FullName="User Test",
        PasswordHash=create_password_hash("user123"),
        RoleId=setup_roles['user'].Id,
        IsActive=True
    )
    db_session.add(basic_user)
    users['user'] = basic_user

    db_session.commit()
    return users


@pytest.fixture
def auth_headers(setup_users: Dict[str, User]) -> Dict[str, Dict[str, str]]:
    """Genera headers de autenticación para cada tipo de usuario"""
    headers = {}

    for role, user in setup_users.items():
        # create_access_token espera un diccionario 'data', no 'subject'
        token = create_access_token(
            data={"sub": str(user.Id)},
            expires_delta=timedelta(hours=1)
        )
        headers[role] = {"Authorization": f"Bearer {token}"}

    return headers


@pytest.fixture
def setup_service_types(db_session: Session) -> List[ServiceType]:
    """Crea tipos de servicio de prueba"""
    services = []

    service1 = ServiceType(
        Code="LAB",
        Name="Análisis de Laboratorio",
        Description="Análisis de sangre y orina",
        Priority=1,
        AverageTimeMinutes=15,
        TicketPrefix="A",  # Agregado: campo requerido
        Color="#007bff",  # Agregado: campo con default
        IsActive=True
    )
    db_session.add(service1)
    services.append(service1)

    service2 = ServiceType(
        Code="RES",
        Name="Entrega de Resultados",
        Description="Entrega de resultados de análisis",
        Priority=2,
        AverageTimeMinutes=5,
        TicketPrefix="B",  # Agregado: campo requerido
        Color="#28a745",  # Agregado: campo con default
        IsActive=True
    )
    db_session.add(service2)
    services.append(service2)

    service3 = ServiceType(
        Code="MUE",
        Name="Entrega de Muestras",
        Description="Recepción de muestras",
        Priority=3,
        AverageTimeMinutes=10,
        TicketPrefix="C",  # Agregado: campo requerido
        Color="#ffc107",  # Agregado: campo con default
        IsActive=True
    )
    db_session.add(service3)
    services.append(service3)

    db_session.commit()
    return services


@pytest.fixture
def setup_stations(db_session: Session) -> List[Station]:
    """Crea estaciones de prueba"""
    stations = []

    station1 = Station(
        Code="V01",
        Name="Ventanilla 1",
        Description="Ventanilla principal",
        Status="Available",  # Corregido: debe ser uno de: Available, Busy, Break, Maintenance, Offline
        CurrentTicketId=None
    )
    db_session.add(station1)
    stations.append(station1)

    station2 = Station(
        Code="V02",
        Name="Ventanilla 2",
        Description="Ventanilla secundaria",
        Status="Available",  # Corregido: debe ser uno de: Available, Busy, Break, Maintenance, Offline
        CurrentTicketId=None
    )
    db_session.add(station2)
    stations.append(station2)

    db_session.commit()
    return stations


@pytest.fixture
def setup_queue_states(
    db_session: Session,
    setup_service_types: List[ServiceType],
    setup_stations: List[Station]
) -> List[QueueState]:
    """Crea estados de cola de prueba"""
    queue_states = []

    # Cola para servicio 1 sin estación
    queue1 = QueueState(
        ServiceTypeId=setup_service_types[0].Id,
        StationId=None,
        QueueLength=5,
        AverageWaitTime=15,
        LastUpdateAt=datetime.now()
    )
    db_session.add(queue1)
    queue_states.append(queue1)

    # Cola para servicio 1 con estación 1
    queue2 = QueueState(
        ServiceTypeId=setup_service_types[0].Id,
        StationId=setup_stations[0].Id,
        QueueLength=3,
        AverageWaitTime=10,
        LastUpdateAt=datetime.now()
    )
    db_session.add(queue2)
    queue_states.append(queue2)

    # Cola para servicio 2 con estación 2
    queue3 = QueueState(
        ServiceTypeId=setup_service_types[1].Id,
        StationId=setup_stations[1].Id,
        QueueLength=0,
        AverageWaitTime=5,
        LastUpdateAt=datetime.now()
    )
    db_session.add(queue3)
    queue_states.append(queue3)

    db_session.commit()
    return queue_states


@pytest.fixture
def setup_patients(db_session: Session) -> List[Patient]:
    """Crea pacientes de prueba"""
    patients = []

    patient1 = Patient(
        DocumentNumber="12345678",
        FirstName="Juan",
        LastName="Pérez",
        BirthDate=date(1990, 1, 1),
        Gender="M",
        Phone="987654321",
        Email="juan@test.com",
        IsActive=True
    )
    db_session.add(patient1)
    patients.append(patient1)

    patient2 = Patient(
        DocumentNumber="87654321",
        FirstName="María",
        LastName="García",
        BirthDate=date(1985, 5, 15),
        Gender="F",
        Phone="912345678",
        Email="maria@test.com",
        IsActive=True
    )
    db_session.add(patient2)
    patients.append(patient2)

    db_session.commit()
    return patients


@pytest.fixture
def setup_tickets(
    db_session: Session,
    setup_patients: List[Patient],
    setup_service_types: List[ServiceType],
    setup_stations: List[Station]
) -> List[Ticket]:
    """Crea tickets de prueba"""
    tickets = []

    # Ticket en espera
    ticket1 = Ticket(
        TicketNumber="A001",
        ServiceTypeId=setup_service_types[0].Id,
        PatientId=setup_patients[0].Id,
        Status="Waiting",
        Position=1,
        EstimatedWaitTime=15,
        CreatedAt=datetime.now()
    )
    db_session.add(ticket1)
    tickets.append(ticket1)

    # Ticket llamado
    ticket2 = Ticket(
        TicketNumber="A002",
        ServiceTypeId=setup_service_types[0].Id,
        PatientId=setup_patients[1].Id,
        StationId=setup_stations[0].Id,
        Status="Called",
        Position=2,
        EstimatedWaitTime=10,
        CreatedAt=datetime.now() - timedelta(minutes=5),
        CalledAt=datetime.now()
    )
    db_session.add(ticket2)
    tickets.append(ticket2)

    # Ticket en progreso
    ticket3 = Ticket(
        TicketNumber="B001",
        ServiceTypeId=setup_service_types[1].Id,
        PatientId=setup_patients[0].Id,
        StationId=setup_stations[1].Id,
        Status="InProgress",
        Position=1,
        EstimatedWaitTime=5,
        CreatedAt=datetime.now() - timedelta(minutes=10),
        CalledAt=datetime.now() - timedelta(minutes=5),
        AttendedAt=datetime.now() - timedelta(minutes=3)
    )
    db_session.add(ticket3)
    tickets.append(ticket3)

    db_session.commit()

    # Actualizar referencias en queue_states
    queue_states = db_session.query(QueueState).all()
    if queue_states:
        queue_states[0].CurrentTicketId = ticket2.Id
        queue_states[0].NextTicketId = ticket1.Id
        db_session.commit()

    return tickets


# ========================================
# TESTS DE ENDPOINTS DE CONSULTA
# ========================================

class TestQueueStateQuery:
    """Pruebas para endpoints de consulta de estados de cola"""

    def test_get_queue_states(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba obtener lista de estados de cola"""
        response = client.get(
            "/api/v1/queue-states/",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= len(setup_queue_states)

        # Verificar estructura de respuesta
        if data:
            queue = data[0]
            assert 'id' in queue
            assert 'service_type_id' in queue
            assert 'queue_length' in queue
            assert 'average_wait_time' in queue

    def test_get_queue_states_with_filters(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState],
        setup_service_types: List[ServiceType]
    ):
        """Prueba obtener estados de cola con filtros"""
        # Filtrar por tipo de servicio
        response = client.get(
            f"/api/v1/queue-states/?service_type_id={setup_service_types[0].Id}",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()
        assert all(q['service_type_id'] == setup_service_types[0].Id for q in data)

    def test_get_queue_states_exclude_empty(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba excluir colas vacías"""
        response = client.get(
            "/api/v1/queue-states/?include_empty=false",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()
        assert all(q['queue_length'] > 0 or q['current_ticket_id'] is not None for q in data)

    def test_get_queue_summary(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba obtener resumen de colas"""
        response = client.get(
            "/api/v1/queue-states/summary",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()

        assert 'total_queues' in data
        assert 'active_queues' in data
        assert 'total_waiting' in data
        assert 'stations_busy' in data
        assert 'average_wait_time' in data

        assert data['total_queues'] >= 0
        assert data['active_queues'] >= 0

    def test_get_queue_state_by_id(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba obtener un estado de cola específico"""
        queue_id = setup_queue_states[0].Id

        response = client.get(
            f"/api/v1/queue-states/{queue_id}",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()
        assert data['id'] == queue_id

    def test_get_queue_state_not_found(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Prueba obtener estado de cola inexistente"""
        response = client.get(
            "/api/v1/queue-states/99999",
            headers=auth_headers['user']
        )

        assert response.status_code == 404
        assert 'detail' in response.json()

    def test_get_queue_with_tickets(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState],
        setup_tickets: List[Ticket]
    ):
        """Prueba obtener estado de cola con tickets"""
        queue_id = setup_queue_states[0].Id

        response = client.get(
            f"/api/v1/queue-states/{queue_id}/tickets",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()

        assert 'id' in data
        assert 'waiting_tickets' in data
        assert isinstance(data['waiting_tickets'], list)

        if data.get('current_ticket_id'):
            assert 'current_ticket_number' in data

    def test_get_queue_by_service(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_service_types: List[ServiceType]
    ):
        """Prueba obtener cola por servicio"""
        service_id = setup_service_types[0].Id

        response = client.get(
            f"/api/v1/queue-states/service/{service_id}",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()
        assert data['service_type_id'] == service_id

    def test_get_queues_by_station(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_stations: List[Station],
        setup_queue_states: List[QueueState]
    ):
        """Prueba obtener colas por estación"""
        station_id = setup_stations[0].Id

        response = client.get(
            f"/api/v1/queue-states/station/{station_id}/all",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(q.get('station_id') == station_id for q in data)


# ========================================
# TESTS DE CREACIÓN Y ACTUALIZACIÓN
# ========================================

class TestQueueStateCreationUpdate:
    """Pruebas para creación y actualización de estados de cola"""

    def test_create_queue_state(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_service_types: List[ServiceType],
        db_session: Session  # Agregado para verificar datos
    ):
        """Prueba crear un nuevo estado de cola"""
        # Verificar que el servicio existe antes de la prueba
        service = db_session.query(ServiceType).filter(
            ServiceType.Id == setup_service_types[2].Id
        ).first()

        assert service is not None, f"ServiceType con ID {setup_service_types[2].Id} no encontrado"

        queue_data = {
            "service_type_id": setup_service_types[2].Id,
            "queue_length": 0,
            "average_wait_time": 10
        }

        # Primero probar con admin para ver si es problema de permisos
        response = client.post(
            "/api/v1/queue-states/",
            json=queue_data,
            headers=auth_headers['admin']  # Cambiar a admin primero
        )

        # Si hay error, imprimir detalles para debugging
        if response.status_code != 200:
            print(f"\nError en test_create_queue_state:")
            print(f"Status Code: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Response: {error_detail}")
            except:
                print(f"Response Text: {response.text}")

            # Verificar si es problema de autenticación
            if response.status_code == 401:
                print("Error de autenticación - verificar token")
            elif response.status_code == 403:
                print("Error de permisos - usuario no tiene permisos suficientes")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data['service_type_id'] == setup_service_types[2].Id
        assert data['queue_length'] == 0

    def test_create_queue_state_unauthorized(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_service_types: List[ServiceType],
        db_session: Session  # Agregado para consistencia
    ):
        """Prueba crear cola sin permisos"""
        queue_data = {
            "service_type_id": setup_service_types[0].Id
        }

        response = client.post(
            "/api/v1/queue-states/",
            json=queue_data,
            headers=auth_headers['user']
        )

        assert response.status_code == 403

    def test_create_duplicate_queue_state(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState],
        db_session: Session  # Agregado para consistencia
    ):
        """Prueba crear estado de cola duplicado"""
        queue_data = {
            "service_type_id": setup_queue_states[0].ServiceTypeId,
            "station_id": setup_queue_states[0].StationId
        }

        response = client.post(
            "/api/v1/queue-states/",
            json=queue_data,
            headers=auth_headers['admin']
        )

        assert response.status_code == 400
        assert "ya existe" in response.json()['detail'].lower()

    def test_update_queue_state(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState],
        db_session: Session  # Agregado para consistencia
    ):
        """Prueba actualizar estado de cola"""
        queue_id = setup_queue_states[0].Id
        update_data = {
            "queue_length": 10,
            "average_wait_time": 20
        }

        response = client.patch(
            f"/api/v1/queue-states/{queue_id}",
            json=update_data,
            headers=auth_headers['technician']
        )

        if response.status_code != 200:
            print(f"\nError en test_update_queue_state:")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert data['queue_length'] == 10
        assert data['average_wait_time'] == 20


# ========================================
# TESTS DE OPERACIONES DE COLA
# ========================================

class TestQueueOperations:
    """Pruebas para operaciones de cola"""

    def test_advance_queue(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState],
        setup_service_types: List[ServiceType],
        setup_tickets: List[Ticket]
    ):
        """Prueba avanzar la cola"""
        request_data = {
            "service_type_id": setup_service_types[0].Id,
            "mark_completed": False
        }

        response = client.post(
            "/api/v1/queue-states/advance",
            json=request_data,
            headers=auth_headers['technician']
        )

        assert response.status_code == 200
        data = response.json()
        assert 'id' in data

    def test_advance_empty_queue(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_service_types: List[ServiceType]
    ):
        """Prueba avanzar cola vacía"""
        request_data = {
            "service_type_id": 99999,  # Servicio inexistente
            "mark_completed": False
        }

        response = client.post(
            "/api/v1/queue-states/advance",
            json=request_data,
            headers=auth_headers['technician']
        )

        assert response.status_code == 404

    def test_reset_queue(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState],
        setup_service_types: List[ServiceType]
    ):
        """Prueba resetear cola"""
        request_data = {
            "service_type_id": setup_service_types[0].Id,
            "reason": "Fin de jornada",
            "cancel_pending_tickets": False
        }

        response = client.post(
            "/api/v1/queue-states/reset",
            json=request_data,
            headers=auth_headers['supervisor']
        )

        assert response.status_code == 200
        data = response.json()
        assert data['queue_length'] == 0

    def test_reset_queue_unauthorized(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_service_types: List[ServiceType]
    ):
        """Prueba resetear cola sin permisos"""
        request_data = {
            "service_type_id": setup_service_types[0].Id,
            "reason": "Intento no autorizado"
        }

        response = client.post(
            "/api/v1/queue-states/reset",
            json=request_data,
            headers=auth_headers['user']
        )

        assert response.status_code == 403

    def test_update_wait_time_recalculate(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba actualizar tiempo de espera recalculando"""
        queue_id = setup_queue_states[0].Id
        request_data = {
            "recalculate": True
        }

        response = client.post(
            f"/api/v1/queue-states/{queue_id}/update-wait-time",
            json=request_data,
            headers=auth_headers['technician']
        )

        assert response.status_code == 200
        data = response.json()
        assert 'average_wait_time' in data

    def test_update_wait_time_manual(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba actualizar tiempo de espera manualmente"""
        queue_id = setup_queue_states[0].Id
        request_data = {
            "recalculate": False,
            "manual_time": 25
        }

        response = client.post(
            f"/api/v1/queue-states/{queue_id}/update-wait-time",
            json=request_data,
            headers=auth_headers['technician']
        )

        assert response.status_code == 200
        data = response.json()
        assert data['average_wait_time'] == 25


# ========================================
# TESTS DE OPERACIONES MASIVAS
# ========================================

class TestBatchOperations:
    """Pruebas para operaciones masivas"""

    def test_batch_update_reset(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba actualización masiva - reset"""
        queue_ids = [q.Id for q in setup_queue_states[:2]]
        request_data = {
            "queue_ids": queue_ids,
            "action": "reset",
            "reason": "Reset masivo de prueba"
        }

        response = client.post(
            "/api/v1/queue-states/batch-update",
            json=request_data,
            headers=auth_headers['admin']
        )

        assert response.status_code == 200
        data = response.json()
        assert 'success' in data
        assert 'failed' in data
        assert data['total'] == len(queue_ids)

    def test_batch_update_refresh(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba actualización masiva - refresh"""
        queue_ids = [setup_queue_states[0].Id]
        request_data = {
            "queue_ids": queue_ids,
            "action": "refresh"
        }

        response = client.post(
            "/api/v1/queue-states/batch-update",
            json=request_data,
            headers=auth_headers['admin']
        )

        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 1

    def test_batch_update_unauthorized(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba actualización masiva sin permisos"""
        request_data = {
            "queue_ids": [setup_queue_states[0].Id],
            "action": "reset"
        }

        response = client.post(
            "/api/v1/queue-states/batch-update",
            json=request_data,
            headers=auth_headers['technician']
        )

        assert response.status_code == 403

    def test_cleanup_stale_states(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Prueba limpiar estados obsoletos"""
        response = client.post(
            "/api/v1/queue-states/cleanup-stale?minutes=60",
            headers=auth_headers['admin']
        )

        assert response.status_code == 200
        data = response.json()
        assert 'deleted_count' in data
        assert 'criteria_minutes' in data
        assert data['criteria_minutes'] == 60


# ========================================
# TESTS DE ELIMINACIÓN
# ========================================

class TestQueueDeletion:
    """Pruebas para eliminación de estados de cola"""

    def test_delete_empty_queue_state(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        db_session: Session,
        setup_service_types: List[ServiceType]
    ):
        """Prueba eliminar estado de cola vacío"""
        # Crear cola vacía
        empty_queue = QueueState(
            ServiceTypeId=setup_service_types[2].Id,
            QueueLength=0,
            AverageWaitTime=0
        )
        db_session.add(empty_queue)
        db_session.commit()

        response = client.delete(
            f"/api/v1/queue-states/{empty_queue.Id}",
            headers=auth_headers['admin']
        )

        assert response.status_code == 200
        assert 'message' in response.json()

    def test_delete_active_queue_state(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba eliminar cola con tickets pendientes"""
        # Usar cola con tickets
        queue_id = setup_queue_states[0].Id  # Esta tiene QueueLength > 0

        response = client.delete(
            f"/api/v1/queue-states/{queue_id}",
            headers=auth_headers['admin']
        )

        assert response.status_code == 400
        assert "tickets pendientes" in response.json()['detail'].lower()

    def test_delete_queue_unauthorized(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba eliminar cola sin permisos"""
        queue_id = setup_queue_states[0].Id

        response = client.delete(
            f"/api/v1/queue-states/{queue_id}",
            headers=auth_headers['supervisor']
        )

        assert response.status_code == 403

    def test_delete_nonexistent_queue(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Prueba eliminar cola inexistente"""
        response = client.delete(
            "/api/v1/queue-states/99999",
            headers=auth_headers['admin']
        )

        assert response.status_code == 404


# ========================================
# TESTS DE CASOS EDGE Y ERRORES
# ========================================

class TestEdgeCases:
    """Pruebas para casos edge y manejo de errores"""

    def test_pagination(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_queue_states: List[QueueState]
    ):
        """Prueba paginación de resultados"""
        response = client.get(
            "/api/v1/queue-states/?skip=0&limit=2",
            headers=auth_headers['user']
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    def test_invalid_service_type(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Prueba con tipo de servicio inválido"""
        queue_data = {
            "service_type_id": 99999,
            "queue_length": 0
        }

        response = client.post(
            "/api/v1/queue-states/",
            json=queue_data,
            headers=auth_headers['admin']
        )

        assert response.status_code == 404
        assert "servicio no encontrado" in response.json()['detail'].lower()

    def test_invalid_station(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_service_types: List[ServiceType]
    ):
        """Prueba con estación inválida"""
        queue_data = {
            "service_type_id": setup_service_types[0].Id,
            "station_id": 99999
        }

        response = client.post(
            "/api/v1/queue-states/",
            json=queue_data,
            headers=auth_headers['admin']
        )

        assert response.status_code == 404
        assert "estación no encontrada" in response.json()['detail'].lower()

    def test_no_authentication(
        self,
        client: TestClient,
        setup_queue_states: List[QueueState]
    ):
        """Prueba acceso sin autenticación"""
        response = client.get("/api/v1/queue-states/")

        assert response.status_code == 401

    def test_expired_token(
        self,
        client: TestClient
    ):
        """Prueba con token expirado"""
        # Crear token expirado - create_access_token espera 'data' como diccionario
        expired_token = create_access_token(
            data={"sub": "test_user"},
            expires_delta=timedelta(seconds=-1)
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/queue-states/", headers=headers)

        assert response.status_code == 401


# ========================================
# TEST RUNNER
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])