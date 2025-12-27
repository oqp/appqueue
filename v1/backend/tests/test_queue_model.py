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
from sqlalchemy import create_engine
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
        Permissions="all",
        IsActive=True
    )
    db_session.add(admin_role)
    roles['admin'] = admin_role

    # Rol Supervisor
    supervisor_role = Role(
        Name="Supervisor",
        Description="Supervisor de ventanillas",
        Permissions="queue.manage,queue.view,tickets.manage",
        IsActive=True
    )
    db_session.add(supervisor_role)
    roles['supervisor'] = supervisor_role

    # Rol Técnico
    technician_role = Role(
        Name="Technician",
        Description="Técnico de laboratorio",
        Permissions="queue.view,tickets.call",
        IsActive=True
    )
    db_session.add(technician_role)
    roles['technician'] = technician_role

    # Rol Usuario básico
    user_role = Role(
        Name="User",
        Description="Usuario básico",
        Permissions="queue.view",
        IsActive=True
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
    admin = User(
        Username="admin",
        Email="admin@test.com",
        FullName="Admin User",
        PasswordHash=create_password_hash("Admin123!"),
        RoleId=setup_roles['admin'].Id,
        IsActive=True
    )
    db_session.add(admin)
    users['admin'] = admin

    # Usuario Supervisor
    supervisor = User(
        Username="supervisor",
        Email="supervisor@test.com",
        FullName="Supervisor User",
        PasswordHash=create_password_hash("Supervisor123!"),
        RoleId=setup_roles['supervisor'].Id,
        IsActive=True
    )
    db_session.add(supervisor)
    users['supervisor'] = supervisor

    # Usuario Técnico
    technician = User(
        Username="technician",
        Email="technician@test.com",
        FullName="Technician User",
        PasswordHash=create_password_hash("Technician123!"),
        RoleId=setup_roles['technician'].Id,
        IsActive=True
    )
    db_session.add(technician)
    users['technician'] = technician

    # Usuario básico
    basic_user = User(
        Username="user",
        Email="user@test.com",
        FullName="Basic User",
        PasswordHash=create_password_hash("User123!"),
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

    for user_type, user in setup_users.items():
        token = create_access_token({"sub": user.Username})
        headers[user_type] = {"Authorization": f"Bearer {token}"}

    return headers


@pytest.fixture
def setup_test_data(db_session: Session) -> Dict[str, Any]:
    """Configura datos de prueba completos"""
    data = {}

    # Crear ServiceType
    service = ServiceType(
        Code="LAB",
        Name="Análisis de Laboratorio",
        Description="Análisis clínicos",
        Priority=2,
        AverageTimeMinutes=15,
        TicketPrefix="A",
        Color="#007bff",
        IsActive=True
    )
    db_session.add(service)
    data['service'] = service

    # Crear Station
    station = Station(
        Code="V01",
        Name="Ventanilla 1",
        Description="Ventanilla principal",
        Location="Planta Baja",
        Status="Available",
        IsActive=True
    )
    db_session.add(station)
    data['station'] = station

    # Crear Patient
    patient = Patient(
        DocumentNumber="12345678",
        FullName="Juan Pérez",
        BirthDate=date(1990, 1, 1),
        Gender="M",
        Phone="999888777",
        Email="juan@test.com",
        IsActive=True
    )
    db_session.add(patient)
    data['patient'] = patient

    db_session.commit()

    # Crear Tickets
    tickets = []
    for i in range(5):
        ticket = Ticket(
            TicketNumber=f"A{str(i+1).zfill(3)}",
            ServiceTypeId=service.Id,
            PatientId=patient.Id,
            Status="Waiting" if i > 0 else "Called",
            Position=i+1,
            CreatedAt=datetime.now() - timedelta(minutes=30-i*5)
        )
        db_session.add(ticket)
        tickets.append(ticket)

    db_session.commit()
    data['tickets'] = tickets

    # Crear QueueState
    queue_state = QueueState(
        ServiceTypeId=service.Id,
        StationId=station.Id,
        CurrentTicketId=str(tickets[0].Id),
        NextTicketId=str(tickets[1].Id),
        QueueLength=4,
        AverageWaitTime=15,
        LastUpdateAt=datetime.now()
    )
    db_session.add(queue_state)
    db_session.commit()
    db_session.refresh(queue_state)
    data['queue_state'] = queue_state

    return data


# ========================================
# TESTS DE ENDPOINTS DE CONSULTA
# ========================================

class TestQueueStateQuery:
    """Tests para endpoints de consulta"""

    def test_get_queue_states_list(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test obtener lista de estados de cola"""
        response = client.get(
            "/api/v1/queue-states/",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert 'service_type_id' in data[0]
        assert 'queue_length' in data[0]

    def test_get_queue_states_with_filters(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test obtener estados con filtros"""
        service_id = setup_test_data['service'].Id

        response = client.get(
            f"/api/v1/queue-states/?service_type_id={service_id}&include_empty=false",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(q['service_type_id'] == service_id for q in data)
        assert all(q['queue_length'] > 0 for q in data)

    def test_get_queue_summary(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test obtener resumen del sistema"""
        response = client.get(
            "/api/v1/queue-states/summary",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'total_queues' in data
        assert 'active_queues' in data
        assert 'total_waiting' in data
        assert 'stations_busy' in data
        assert 'average_wait_time' in data

    def test_get_queue_state_by_id(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test obtener estado específico por ID"""
        queue_id = setup_test_data['queue_state'].Id

        response = client.get(
            f"/api/v1/queue-states/{queue_id}",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['id'] == queue_id
        assert 'service_name' in data
        assert 'station_name' in data

    def test_get_queue_state_not_found(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Test obtener estado inexistente"""
        response = client.get(
            "/api/v1/queue-states/99999",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_queue_by_service(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test obtener cola por servicio"""
        service_id = setup_test_data['service'].Id

        response = client.get(
            f"/api/v1/queue-states/service/{service_id}",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['service_type_id'] == service_id
        assert 'queue_length' in data
        assert 'average_wait_time' in data

    def test_get_queue_with_tickets(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test obtener cola con información de tickets"""
        service_id = setup_test_data['service'].Id

        response = client.get(
            f"/api/v1/queue-states/service/{service_id}/with-tickets",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'waiting_tickets' in data
        assert isinstance(data['waiting_tickets'], list)
        if len(data['waiting_tickets']) > 0:
            assert 'ticket_number' in data['waiting_tickets'][0]
            assert 'estimated_time' in data['waiting_tickets'][0]


# ========================================
# TESTS DE OPERACIONES
# ========================================

class TestQueueStateOperations:
    """Tests para operaciones de cola"""

    def test_advance_queue_success(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test avanzar cola exitosamente"""
        request_data = {
            "service_type_id": setup_test_data['service'].Id,
            "station_id": setup_test_data['station'].Id,
            "mark_completed": True
        }

        response = client.post(
            "/api/v1/queue-states/advance",
            headers=auth_headers['technician'],
            json=request_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'queue_length' in data
        # La cola debe haber disminuido
        assert data['queue_length'] < setup_test_data['queue_state'].QueueLength

    def test_advance_queue_unauthorized(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test avanzar cola sin permisos"""
        request_data = {
            "service_type_id": setup_test_data['service'].Id,
            "mark_completed": True
        }

        # Usuario básico no puede avanzar cola
        response = client.post(
            "/api/v1/queue-states/advance",
            headers=auth_headers['user'],
            json=request_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reset_queue_success(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test reiniciar cola exitosamente"""
        request_data = {
            "service_type_id": setup_test_data['service'].Id,
            "station_id": setup_test_data['station'].Id,
            "reason": "Inicio de jornada"
        }

        response = client.post(
            "/api/v1/queue-states/reset",
            headers=auth_headers['supervisor'],
            json=request_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['queue_length'] == 0
        assert data['current_ticket_id'] is None
        assert data['next_ticket_id'] is None

    def test_reset_queue_admin_only(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test que solo supervisores/admin pueden reiniciar"""
        request_data = {
            "service_type_id": setup_test_data['service'].Id,
            "reason": "Test"
        }

        # Técnico no puede reiniciar
        response = client.post(
            "/api/v1/queue-states/reset",
            headers=auth_headers['technician'],
            json=request_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_wait_time_recalculate(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test recalcular tiempo de espera"""
        request_data = {
            "queue_state_id": setup_test_data['queue_state'].Id,
            "recalculate": True
        }

        response = client.put(
            "/api/v1/queue-states/update-wait-time",
            headers=auth_headers['supervisor'],
            json=request_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'average_wait_time' in data

    def test_update_wait_time_manual(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test establecer tiempo de espera manual"""
        manual_time = 25
        request_data = {
            "queue_state_id": setup_test_data['queue_state'].Id,
            "recalculate": False,
            "manual_time": manual_time
        }

        response = client.put(
            "/api/v1/queue-states/update-wait-time",
            headers=auth_headers['supervisor'],
            json=request_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['average_wait_time'] == manual_time


# ========================================
# TESTS DE ACTUALIZACIÓN
# ========================================

class TestQueueStateUpdate:
    """Tests para actualización de estados"""

    def test_update_queue_state(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test actualizar estado de cola"""
        queue_id = setup_test_data['queue_state'].Id
        update_data = {
            "queue_length": 10,
            "average_wait_time": 20
        }

        response = client.put(
            f"/api/v1/queue-states/{queue_id}",
            headers=auth_headers['supervisor'],
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['queue_length'] == 10
        assert data['average_wait_time'] == 20

    def test_update_queue_state_unauthorized(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test actualizar sin permisos"""
        queue_id = setup_test_data['queue_state'].Id
        update_data = {"queue_length": 10}

        response = client.put(
            f"/api/v1/queue-states/{queue_id}",
            headers=auth_headers['user'],
            json=update_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_queue_state_not_found(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Test actualizar estado inexistente"""
        update_data = {"queue_length": 5}

        response = client.put(
            "/api/v1/queue-states/99999",
            headers=auth_headers['admin'],
            json=update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ========================================
# TESTS DE MANTENIMIENTO
# ========================================

class TestQueueStateMaintenance:
    """Tests para operaciones de mantenimiento"""

    def test_refresh_all_states(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test refrescar todos los estados"""
        response = client.post(
            "/api/v1/queue-states/refresh-all",
            headers=auth_headers['admin']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'updated_count' in data
        assert data['updated_count'] >= 0

    def test_refresh_all_admin_only(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Test que solo admin puede refrescar todos"""
        response = client.post(
            "/api/v1/queue-states/refresh-all",
            headers=auth_headers['supervisor']
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cleanup_stale_states(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        db_session: Session,
        setup_test_data: Dict[str, Any]
    ):
        """Test limpiar estados obsoletos"""
        # Crear estado obsoleto con servicio válido
        old_queue = QueueState(
            ServiceTypeId=setup_test_data['service'].Id,  # Usar servicio existente
            QueueLength=0,
            AverageWaitTime=0,
            LastUpdateAt=datetime.now() - timedelta(hours=2)
        )
        db_session.add(old_queue)
        db_session.commit()

        response = client.delete(
            "/api/v1/queue-states/cleanup-stale?minutes=60",
            headers=auth_headers['admin']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'deleted_count' in data
        assert data['deleted_count'] >= 0

    def test_batch_update_queues(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test actualización en lote"""
        queue_id = setup_test_data['queue_state'].Id
        request_data = {
            "queue_ids": [queue_id],
            "action": "reset",
            "reason": "Test batch reset"
        }

        response = client.post(
            "/api/v1/queue-states/batch-update",
            headers=auth_headers['admin'],
            json=request_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'successful' in data
        assert 'failed' in data
        assert 'results' in data
        assert len(data['results']) == 1


# ========================================
# TESTS DE ESTADÍSTICAS
# ========================================

class TestQueueStateStatistics:
    """Tests para endpoints de estadísticas"""

    def test_get_stats_by_station(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test obtener estadísticas por estación"""
        station_id = setup_test_data['station'].Id

        response = client.get(
            f"/api/v1/queue-states/stats/by-station/{station_id}",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['station_id'] == station_id
        assert 'total_waiting' in data
        assert 'average_wait_time' in data
        assert 'queues' in data

    def test_get_stats_by_station_not_found(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Test estadísticas de estación inexistente"""
        response = client.get(
            "/api/v1/queue-states/stats/by-station/99999",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_active_queues_stats(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test obtener estadísticas de colas activas"""
        response = client.get(
            "/api/v1/queue-states/stats/active-queues",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'total_active' in data
        assert 'by_priority' in data
        assert 'total_people_waiting' in data
        assert 'longest_queue' in data
        assert 'highest_wait_time' in data

    def test_get_active_queues_stats_with_empty(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Test estadísticas incluyendo colas vacías"""
        response = client.get(
            "/api/v1/queue-states/stats/active-queues?include_empty=true",
            headers=auth_headers['user']
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['total_active'] >= 0


# ========================================
# TESTS DE VALIDACIÓN
# ========================================

class TestQueueStateValidation:
    """Tests para validación de datos"""

    def test_advance_queue_invalid_service(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Test avanzar cola con servicio inválido"""
        request_data = {
            "service_type_id": 99999,
            "mark_completed": True
        }

        response = client.post(
            "/api/v1/queue-states/advance",
            headers=auth_headers['technician'],
            json=request_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_wait_time_invalid_id(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]]
    ):
        """Test actualizar tiempo con ID inválido"""
        request_data = {
            "queue_state_id": 99999,
            "recalculate": True
        }

        response = client.put(
            "/api/v1/queue-states/update-wait-time",
            headers=auth_headers['supervisor'],
            json=request_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_wait_time_invalid_manual_time(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test tiempo manual fuera de rango"""
        request_data = {
            "queue_state_id": setup_test_data['queue_state'].Id,
            "recalculate": False,
            "manual_time": 500  # Excede el máximo de 480
        }

        response = client.put(
            "/api/v1/queue-states/update-wait-time",
            headers=auth_headers['supervisor'],
            json=request_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_batch_update_invalid_action(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test actualización en lote con acción inválida"""
        request_data = {
            "queue_ids": [setup_test_data['queue_state'].Id],
            "action": "invalid_action"
        }

        response = client.post(
            "/api/v1/queue-states/batch-update",
            headers=auth_headers['admin'],
            json=request_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ========================================
# TESTS DE HEALTH CHECK
# ========================================

class TestQueueStateHealth:
    """Tests para health check"""

    def test_health_check(
        self,
        client: TestClient,
        setup_test_data: Dict[str, Any]
    ):
        """Test health check del módulo"""
        response = client.get("/api/v1/queue-states/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['status'] in ['healthy', 'unhealthy']
        assert data['module'] == 'queue_states'
        assert 'database' in data
        assert 'total_queues' in data
        assert 'active_services' in data


# ========================================
# TESTS DE INTEGRACIÓN
# ========================================

class TestQueueStateIntegration:
    """Tests de integración con el sistema"""

    def test_complete_queue_workflow(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        setup_test_data: Dict[str, Any]
    ):
        """Test flujo completo de gestión de cola"""
        service_id = setup_test_data['service'].Id

        # 1. Obtener estado inicial
        response = client.get(
            f"/api/v1/queue-states/service/{service_id}",
            headers=auth_headers['user']
        )
        assert response.status_code == status.HTTP_200_OK
        initial_state = response.json()

        # 2. Avanzar la cola
        advance_request = {
            "service_type_id": service_id,
            "mark_completed": True
        }
        response = client.post(
            "/api/v1/queue-states/advance",
            headers=auth_headers['technician'],
            json=advance_request
        )
        assert response.status_code == status.HTTP_200_OK
        advanced_state = response.json()
        assert advanced_state['queue_length'] < initial_state['queue_length']

        # 3. Actualizar tiempo de espera
        wait_request = {
            "queue_state_id": advanced_state['id'],
            "recalculate": False,
            "manual_time": 30
        }
        response = client.put(
            "/api/v1/queue-states/update-wait-time",
            headers=auth_headers['supervisor'],
            json=wait_request
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['average_wait_time'] == 30

        # 4. Obtener resumen final
        response = client.get(
            "/api/v1/queue-states/summary",
            headers=auth_headers['user']
        )
        assert response.status_code == status.HTTP_200_OK
        summary = response.json()
        assert summary['total_queues'] > 0

    def test_pagination(
        self,
        client: TestClient,
        auth_headers: Dict[str, Dict[str, str]],
        db_session: Session
    ):
        """Test paginación de resultados"""
        # Crear múltiples estados de cola
        for i in range(15):
            service = ServiceType(
                Code=f"SRV{i}",
                Name=f"Servicio {i}",
                Priority=2,
                AverageTimeMinutes=10,
                TicketPrefix=chr(65 + i % 26),
                IsActive=True
            )
            db_session.add(service)
            db_session.commit()

            queue = QueueState(
                ServiceTypeId=service.Id,
                QueueLength=i,
                AverageWaitTime=10
            )
            db_session.add(queue)
        db_session.commit()

        # Primera página
        response = client.get(
            "/api/v1/queue-states/?skip=0&limit=10",
            headers=auth_headers['user']
        )
        assert response.status_code == status.HTTP_200_OK
        first_page = response.json()
        assert len(first_page) <= 10

        # Segunda página
        response = client.get(
            "/api/v1/queue-states/?skip=10&limit=10",
            headers=auth_headers['user']
        )
        assert response.status_code == status.HTTP_200_OK
        second_page = response.json()
        assert len(second_page) >= 5  # Al menos los 5 restantes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])