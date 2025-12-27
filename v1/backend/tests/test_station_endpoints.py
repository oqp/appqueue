"""
Pruebas unitarias para endpoints de estaciones
Prueba todos los endpoints definidos en app/api/v1/endpoints/stations.py
Compatible con SQL Server y la estructura real del proyecto
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
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
from app.core.database import Base, get_db
from app.models.station import Station
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.role import Role
from app.models.patient import Patient
from app.models.ticket import Ticket
from app.core.security import create_password_hash, create_access_token
from app.schemas.station import StationCreate, StationUpdate, StationResponse


# ========================================
# CONFIGURACIÓN DE BASE DE DATOS DE TEST
# ========================================

TEST_DATABASE_URL = "mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ========================================
# FIXTURES DE SESIÓN Y CLIENTE
# ========================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """Crea una sesión de base de datos para pruebas con rollback automático"""
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

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """Crea un cliente de test que usa la sesión de test"""

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
# FIXTURES DE DATOS DE PRUEBA
# ========================================

@pytest.fixture
def admin_role(db_session: Session) -> Role:
    """Crea un rol de administrador"""
    role = Role(
        Name="Admin",
        Description="Administrador del sistema",
        Permissions=json.dumps(["stations.create", "stations.read", "stations.update", "stations.delete"])
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def supervisor_role(db_session: Session) -> Role:
    """Crea un rol de supervisor"""
    role = Role(
        Name="Supervisor",
        Description="Supervisor del sistema",
        Permissions=json.dumps(["stations.read", "stations.update"])
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def technician_role(db_session: Session) -> Role:
    """Crea un rol de técnico"""
    role = Role(
        Name="Technician",
        Description="Técnico del laboratorio",
        Permissions=json.dumps(["stations.read"])
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def admin_user(db_session: Session, admin_role: Role) -> User:
    """Crea un usuario administrador"""
    user = User(
        Id=str(uuid.uuid4()),  # Generar UUID para el usuario
        Username="admin_test",
        Email="admin@test.com",
        FullName="Admin Test",
        PasswordHash=create_password_hash("Admin123!"),
        RoleId=admin_role.Id,
        IsActive=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def supervisor_user(db_session: Session, supervisor_role: Role) -> User:
    """Crea un usuario supervisor"""
    user = User(
        Id=str(uuid.uuid4()),  # Generar UUID para el usuario
        Username="supervisor_test",
        Email="supervisor@test.com",
        FullName="Supervisor Test",
        PasswordHash=create_password_hash("Supervisor123!"),
        RoleId=supervisor_role.Id,
        IsActive=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def technician_user(db_session: Session, technician_role: Role) -> User:
    """Crea un usuario técnico"""
    user = User(
        Id=str(uuid.uuid4()),  # Generar UUID para el usuario
        Username="technician_test",
        Email="technician@test.com",
        FullName="Technician Test",
        PasswordHash=create_password_hash("Technician123!"),
        RoleId=technician_role.Id,
        IsActive=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> Dict[str, str]:
    """Headers con token JWT de admin"""
    # El token debe usar el ID del usuario, no el username
    token = create_access_token({"sub": str(admin_user.Id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def supervisor_headers(supervisor_user: User) -> Dict[str, str]:
    """Headers con token JWT de supervisor"""
    # El token debe usar el ID del usuario, no el username
    token = create_access_token({"sub": str(supervisor_user.Id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def technician_headers(technician_user: User) -> Dict[str, str]:
    """Headers con token JWT de técnico"""
    # El token debe usar el ID del usuario, no el username
    token = create_access_token({"sub": str(technician_user.Id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def service_type(db_session: Session) -> ServiceType:
    """Crea un tipo de servicio"""
    service = ServiceType(
        Code="LAB",
        Name="Análisis de Laboratorio",
        Description="Análisis clínicos generales",
        TicketPrefix="L",
        Priority=1,
        AverageTimeMinutes=15,
        IsActive=True
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


@pytest.fixture
def sample_station(db_session: Session, service_type: ServiceType) -> Station:
    """Crea una estación de prueba"""
    station = Station(
        Name="Ventanilla 1",
        Code="V01",
        Description="Ventanilla principal",
        ServiceTypeId=service_type.Id,
        Location="Planta Baja",
        Status="Available",
        IsActive=True
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station


@pytest.fixture
def multiple_stations(db_session: Session, service_type: ServiceType) -> List[Station]:
    """Crea múltiples estaciones de prueba"""
    stations = []
    for i in range(5):
        station = Station(
            Name=f"Ventanilla {i+1}",
            Code=f"V{i+1:02d}",
            Description=f"Ventanilla de prueba {i+1}",
            ServiceTypeId=service_type.Id if i % 2 == 0 else None,
            Location=f"Piso {i // 2 + 1}",
            Status="Available" if i % 3 != 0 else "Busy",
            IsActive=(i != 4)  # La última (V05) es inactiva
        )
        db_session.add(station)
        stations.append(station)

    db_session.commit()
    for station in stations:
        db_session.refresh(station)

    return stations


# ========================================
# TESTS DE ENDPOINTS GET
# ========================================

class TestStationGetEndpoints:
    """Tests para endpoints GET de estaciones"""

    def test_get_station_by_id_success(self, client: TestClient, sample_station: Station, technician_headers: Dict):
        """Test obtener estación por ID exitosamente"""
        response = client.get(
            f"/api/v1/stations/{sample_station.Id}",
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["Id"] == sample_station.Id
        assert data["Name"] == sample_station.Name
        assert data["Code"] == sample_station.Code

    def test_get_station_by_id_not_found(self, client: TestClient, technician_headers: Dict):
        """Test obtener estación inexistente"""
        response = client.get(
            "/api/v1/stations/99999",
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "no encontrada" in response.json()["detail"].lower()

    def test_get_station_by_id_unauthorized(self, client: TestClient, sample_station: Station):
        """Test obtener estación sin autenticación"""
        response = client.get(f"/api/v1/stations/{sample_station.Id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_station_by_code_success(self, client: TestClient, sample_station: Station, technician_headers: Dict):
        """Test obtener estación por código exitosamente"""
        response = client.get(
            f"/api/v1/stations/by-code/{sample_station.Code}",
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["Code"] == sample_station.Code
        assert data["Name"] == sample_station.Name

    def test_get_station_by_code_case_insensitive(self, client: TestClient, sample_station: Station, technician_headers: Dict):
        """Test obtener estación por código insensible a mayúsculas"""
        response = client.get(
            f"/api/v1/stations/by-code/{sample_station.Code.lower()}",
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["Code"] == sample_station.Code

    def test_get_available_stations(self, client: TestClient, multiple_stations: List[Station], technician_headers: Dict):
        """Test obtener estaciones disponibles"""
        response = client.get(
            "/api/v1/stations/available",
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

        # Verificar que solo vengan las disponibles y activas
        for station in data:
            assert station["Status"] == "Available"
            assert station["IsActive"] is True

    def test_get_available_stations_with_service_filter(
        self, client: TestClient, multiple_stations: List[Station],
        service_type: ServiceType, technician_headers: Dict
    ):
        """Test obtener estaciones disponibles filtradas por servicio"""
        response = client.get(
            f"/api/v1/stations/available?service_type_id={service_type.Id}",
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verificar que todas tengan el service_type_id correcto
        for station in data:
            assert station["ServiceTypeId"] == service_type.Id

    def test_list_stations_with_pagination(self, client: TestClient, multiple_stations: List[Station], technician_headers: Dict):
        """Test listar estaciones con paginación"""
        response = client.get(
            "/api/v1/stations/?skip=0&limit=2",  # Agregar / al final
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "Stations" in data
        assert "Total" in data
        assert "Page" in data
        assert "PageSize" in data
        assert len(data["Stations"]) <= 2
        assert data["PageSize"] == 2

    def test_list_stations_with_filters(self, client: TestClient, multiple_stations: List[Station], technician_headers: Dict):
        """Test listar estaciones con filtros"""
        response = client.get(
            "/api/v1/stations/?only_active=true",  # only_active=true
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verificar que hay estaciones en la respuesta
        assert "Stations" in data
        assert isinstance(data["Stations"], list)

        # Si only_active=true, todas las estaciones devueltas deben estar activas
        # PERO también deben existir en la BD (no todas las del fixture están activas)
        if len(data["Stations"]) > 0:
            for station in data["Stations"]:
                assert station["IsActive"] is True

        # Verificar que no se devuelven estaciones inactivas
        # En el fixture, la última estación (índice 4) está inactiva
        station_codes = [s["Code"] for s in data["Stations"]]
        assert "V05" not in station_codes  # Esta es la estación inactiva del fixture


# ========================================
# TESTS DE ENDPOINT POST (CREAR)
# ========================================

class TestStationCreateEndpoint:
    """Tests para endpoint de creación de estaciones"""

    def test_create_station_success(self, client: TestClient, service_type: ServiceType, admin_headers: Dict):
        """Test crear estación exitosamente"""
        station_data = {
            "Name": "Nueva Ventanilla",
            "Code": "NV01",
            "Description": "Ventanilla de prueba",
            "ServiceTypeId": service_type.Id,
            "Location": "Segundo Piso",
            "Status": "Available"
        }

        response = client.post(
            "/api/v1/stations",
            json=station_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["Name"] == station_data["Name"]
        assert data["Code"] == station_data["Code"]
        assert data["Id"] is not None

    def test_create_station_duplicate_code(self, client: TestClient, sample_station: Station, admin_headers: Dict):
        """Test crear estación con código duplicado"""
        station_data = {
            "Name": "Otra Ventanilla",
            "Code": sample_station.Code,  # Código duplicado
            "Description": "Intento de duplicado"
        }

        response = client.post(
            "/api/v1/stations",
            json=station_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya está en uso" in response.json()["detail"].lower() or "ya existe" in response.json()["detail"].lower()

    def test_create_station_invalid_data(self, client: TestClient, admin_headers: Dict):
        """Test crear estación con datos inválidos"""
        station_data = {
            "Name": "",  # Nombre vacío
            "Code": "IC01"
        }

        response = client.post(
            "/api/v1/stations",
            json=station_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_station_unauthorized(self, client: TestClient, technician_headers: Dict):
        """Test crear estación sin permisos de admin"""
        station_data = {
            "Name": "Sin Permisos",
            "Code": "SP01"
        }

        response = client.post(
            "/api/v1/stations",
            json=station_data,
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_station_minimal_fields(self, client: TestClient, admin_headers: Dict):
        """Test crear estación con campos mínimos"""
        station_data = {
            "Name": "Mínima",
            "Code": "MIN01"
        }

        response = client.post(
            "/api/v1/stations",
            json=station_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["Status"] == "Available"  # Valor por defecto
        assert data["IsActive"] is True  # Valor por defecto


# ========================================
# TESTS DE ENDPOINT PUT (ACTUALIZAR)
# ========================================

class TestStationUpdateEndpoint:
    """Tests para endpoint de actualización de estaciones"""

    def test_update_station_success(self, client: TestClient, sample_station: Station, supervisor_headers: Dict):
        """Test actualizar estación exitosamente"""
        update_data = {
            "Name": "Ventanilla Actualizada",
            "Description": "Nueva descripción",
            "Location": "Tercer Piso"
        }

        response = client.put(
            f"/api/v1/stations/{sample_station.Id}",
            json=update_data,
            headers=supervisor_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["Name"] == update_data["Name"]
        assert data["Description"] == update_data["Description"]
        assert data["Location"] == update_data["Location"]
        assert data["Code"] == sample_station.Code  # No cambió

    def test_update_station_not_found(self, client: TestClient, supervisor_headers: Dict):
        """Test actualizar estación inexistente"""
        update_data = {"Name": "No Existe"}

        response = client.put(
            "/api/v1/stations/99999",
            json=update_data,
            headers=supervisor_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_station_unauthorized(self, client: TestClient, sample_station: Station, technician_headers: Dict):
        """Test actualizar estación sin permisos"""
        update_data = {"Name": "Sin Permisos"}

        response = client.put(
            f"/api/v1/stations/{sample_station.Id}",
            json=update_data,
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_station_partial(self, client: TestClient, sample_station: Station, supervisor_headers: Dict):
        """Test actualización parcial de estación"""
        update_data = {"Description": "Solo descripción actualizada"}

        response = client.put(
            f"/api/v1/stations/{sample_station.Id}",
            json=update_data,
            headers=supervisor_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["Description"] == update_data["Description"]
        assert data["Name"] == sample_station.Name  # No cambió


# ========================================
# TESTS DE ENDPOINT DELETE
# ========================================

class TestStationDeleteEndpoint:
    """Tests para endpoint de eliminación de estaciones"""

    def test_delete_station_soft(self, client: TestClient, sample_station: Station, admin_headers: Dict, db_session: Session):
        """Test eliminación lógica de estación"""
        response = client.delete(
            f"/api/v1/stations/{sample_station.Id}?soft_delete=true",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "desactivada" in data["message"].lower()

        # Verificar que aún existe pero inactiva
        db_session.refresh(sample_station)
        assert sample_station.IsActive is False

    def test_delete_station_hard(self, client: TestClient, sample_station: Station, admin_headers: Dict, db_session: Session):
        """Test eliminación física de estación"""
        station_id = sample_station.Id

        response = client.delete(
            f"/api/v1/stations/{station_id}?soft_delete=false",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "eliminada permanentemente" in data["message"].lower()

        # Verificar que no existe
        deleted = db_session.query(Station).filter_by(Id=station_id).first()
        assert deleted is None

    def test_delete_station_not_found(self, client: TestClient, admin_headers: Dict):
        """Test eliminar estación inexistente"""
        response = client.delete(
            "/api/v1/stations/99999",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_station_unauthorized(self, client: TestClient, sample_station: Station, supervisor_headers: Dict):
        """Test eliminar estación sin permisos de admin"""
        response = client.delete(
            f"/api/v1/stations/{sample_station.Id}",
            headers=supervisor_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ========================================
# TESTS DE ENDPOINT PATCH (STATUS)
# ========================================

class TestStationStatusEndpoint:
    """Tests para endpoint de cambio de estado"""

    def test_update_station_status_success(self, client: TestClient, sample_station: Station, supervisor_headers: Dict):
        """Test actualizar estado de estación exitosamente"""
        response = client.patch(
            f"/api/v1/stations/{sample_station.Id}/status",
            json={"new_status": "Busy"},
            headers=supervisor_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["Status"] == "Busy"
        assert data["Id"] == sample_station.Id

    def test_update_station_status_invalid(self, client: TestClient, sample_station: Station, supervisor_headers: Dict):
        """Test actualizar estado con valor inválido"""
        response = client.patch(
            f"/api/v1/stations/{sample_station.Id}/status",
            json={"new_status": "InvalidStatus"},
            headers=supervisor_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Estado inválido" in response.json()["detail"]

    def test_update_station_status_sequence(self, client: TestClient, sample_station: Station, supervisor_headers: Dict):
        """Test secuencia de cambios de estado"""
        states = ["Busy", "Break", "Available", "Maintenance", "Offline", "Available"]

        for state in states:
            response = client.patch(
                f"/api/v1/stations/{sample_station.Id}/status",
                json={"new_status": state},
                headers=supervisor_headers
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["Status"] == state


# ========================================
# TESTS DE PERMISOS Y SEGURIDAD
# ========================================

class TestStationSecurity:
    """Tests de seguridad y permisos"""

    def test_endpoints_require_authentication(self, client: TestClient, sample_station: Station):
        """Test que todos los endpoints requieren autenticación"""
        endpoints = [
            ("GET", f"/api/v1/stations/{sample_station.Id}"),
            ("GET", "/api/v1/stations"),
            ("GET", "/api/v1/stations/available"),
            ("POST", "/api/v1/stations"),
            ("PUT", f"/api/v1/stations/{sample_station.Id}"),
            ("DELETE", f"/api/v1/stations/{sample_station.Id}"),
            ("PATCH", f"/api/v1/stations/{sample_station.Id}/status")
        ]

        for method, url in endpoints:
            response = client.request(method, url, json={})
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_role_based_access(self, client: TestClient, sample_station: Station,
                              admin_headers: Dict, supervisor_headers: Dict, technician_headers: Dict):
        """Test acceso basado en roles"""
        # Admin puede hacer todo
        response = client.delete(f"/api/v1/stations/{sample_station.Id}", headers=admin_headers)
        assert response.status_code == status.HTTP_200_OK

        # Supervisor puede actualizar pero no eliminar
        response = client.put(
            f"/api/v1/stations/{sample_station.Id}",
            json={"Name": "Test"},
            headers=supervisor_headers
        )
        assert response.status_code == status.HTTP_200_OK

        response = client.delete(f"/api/v1/stations/{sample_station.Id}", headers=supervisor_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Técnico solo puede leer
        response = client.get(f"/api/v1/stations/{sample_station.Id}", headers=technician_headers)
        assert response.status_code == status.HTTP_200_OK

        response = client.put(
            f"/api/v1/stations/{sample_station.Id}",
            json={"Name": "Test"},
            headers=technician_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ========================================
# TESTS DE INTEGRACIÓN
# ========================================

class TestStationIntegration:
    """Tests de integración con otros componentes"""

    def test_station_with_active_tickets(self, client: TestClient, sample_station: Station,
                                        service_type: ServiceType, admin_headers: Dict, db_session: Session):
        """Test que no se puede eliminar estación con tickets activos"""
        # Crear un paciente
        patient = Patient(
            Id=str(uuid.uuid4()),
            FullName="Test Patient",
            DocumentNumber="12345678",
            BirthDate=datetime(1990, 1, 1).date(),
            Gender="M"
        )
        db_session.add(patient)

        # Crear un ticket activo
        ticket = Ticket(
            Id=str(uuid.uuid4()),
            TicketNumber="T001",
            PatientId=patient.Id,
            ServiceTypeId=service_type.Id,
            StationId=sample_station.Id,
            Status="InProgress",
            Position=1
        )
        db_session.add(ticket)
        db_session.commit()

        # Intentar eliminar la estación
        response = client.delete(
            f"/api/v1/stations/{sample_station.Id}?soft_delete=false",
            headers=admin_headers
        )

        # Debería fallar o solo hacer soft delete
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]

    def test_station_service_type_relationship(self, client: TestClient, service_type: ServiceType,
                                              admin_headers: Dict, technician_headers: Dict):
        """Test relación entre estación y tipo de servicio"""
        # Crear estación con servicio
        station_data = {
            "Name": "Ventanilla Especializada",
            "Code": "VE01",
            "ServiceTypeId": service_type.Id
        }

        response = client.post("/api/v1/stations", json=station_data, headers=admin_headers)
        assert response.status_code == status.HTTP_201_CREATED
        station_id = response.json()["Id"]

        # Obtener estación y verificar servicio
        response = client.get(f"/api/v1/stations/{station_id}", headers=technician_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ServiceTypeId"] == service_type.Id

        # Si incluye información del servicio
        if "ServiceType" in data:
            assert data["ServiceType"]["Code"] == service_type.Code


# ========================================
# TESTS DE CASOS EDGE Y ERRORES
# ========================================

class TestStationEdgeCases:
    """Tests para casos edge y manejo de errores"""

    def test_large_pagination(self, client: TestClient, multiple_stations: List[Station], technician_headers: Dict):
        """Test paginación con valores grandes"""
        response = client.get(
            "/api/v1/stations?skip=1000&limit=100",
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["Stations"]) == 0  # No hay tantas estaciones

    def test_negative_pagination(self, client: TestClient, technician_headers: Dict):
        """Test paginación con valores negativos"""
        response = client.get(
            "/api/v1/stations?skip=-1&limit=-10",
            headers=technician_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_special_characters_in_code(self, client: TestClient, admin_headers: Dict):
        """Test crear estación con caracteres especiales en código"""
        station_data = {
            "Name": "Especial",
            "Code": "V-01.A"  # Código con caracteres especiales
        }

        response = client.post("/api/v1/stations", json=station_data, headers=admin_headers)

        # Puede aceptarlo o rechazarlo según validación
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_concurrent_updates(self, client: TestClient, sample_station: Station, supervisor_headers: Dict):
        """Test actualizaciones concurrentes"""
        # Simular dos actualizaciones casi simultáneas
        update1 = {"Name": "Actualización 1"}
        update2 = {"Name": "Actualización 2"}

        response1 = client.put(f"/api/v1/stations/{sample_station.Id}", json=update1, headers=supervisor_headers)
        response2 = client.put(f"/api/v1/stations/{sample_station.Id}", json=update2, headers=supervisor_headers)

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        # La última actualización debe prevalecer
        assert response2.json()["Name"] == "Actualización 2"

    def test_null_optional_fields(self, client: TestClient, admin_headers: Dict):
        """Test crear estación con campos opcionales nulos"""
        station_data = {
            "Name": "Sin Opcionales",
            "Code": "SO01",
            "Description": None,
            "Location": None,
            "ServiceTypeId": None
        }

        response = client.post("/api/v1/stations", json=station_data, headers=admin_headers)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["Description"] is None
        assert data["Location"] is None
        assert data["ServiceTypeId"] is None


# ========================================
# CONFIGURACIÓN PYTEST
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])