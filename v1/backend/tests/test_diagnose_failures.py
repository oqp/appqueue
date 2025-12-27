"""
Diagnóstico específico para las 2 pruebas que fallan
"""

import pytest
import sys
import os
from datetime import datetime
import uuid
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import Base, get_db
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.role import Role
from app.core.security import create_password_hash, create_access_token

# Base de datos de prueba
TEST_DATABASE_URL = "mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Sesión de base de datos para pruebas"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    # Limpiar tablas
    session.execute(text("DELETE FROM Tickets"))
    session.execute(text("DELETE FROM Stations"))
    session.execute(text("DELETE FROM Users"))
    session.execute(text("DELETE FROM ServiceTypes"))
    session.execute(text("DELETE FROM Roles"))
    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Cliente de prueba"""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_setup(db_session):
    """Setup completo de autenticación"""
    # Crear rol
    role = Role(
        Name="Admin",
        Description="Admin",
        Permissions=json.dumps({"all": True}),
        IsActive=True
    )
    db_session.add(role)
    db_session.commit()

    # Crear usuario con UUID
    user = User(
        Id=str(uuid.uuid4()),
        Username="test_admin",
        Email="admin@test.com",
        FullName="Test Admin",
        PasswordHash=create_password_hash("admin123"),
        RoleId=role.Id,
        IsActive=True
    )
    db_session.add(user)
    db_session.commit()

    # Token con UUID
    token = create_access_token({"sub": str(user.Id)})
    headers = {"Authorization": f"Bearer {token}"}

    return user, headers


@pytest.fixture
def sample_services(db_session):
    """Crear servicios de muestra"""
    services = [
        ServiceType(
            Code="LAB",
            Name="Análisis de Laboratorio",
            Description="Análisis general",
            TicketPrefix="L",
            Priority=3,
            AverageTimeMinutes=15,
            IsActive=True,
            Color="#007bff"
        ),
        ServiceType(
            Code="RES",
            Name="Entrega de Resultados",
            Description="Retiro de estudios",
            TicketPrefix="R",
            Priority=2,
            AverageTimeMinutes=5,
            IsActive=True,
            Color="#28a745"
        ),
        ServiceType(
            Code="INAC",
            Name="Servicio Inactivo",
            Description="Este está inactivo",
            TicketPrefix="I",
            Priority=1,
            AverageTimeMinutes=10,
            IsActive=False,
            Color="#dc3545"
        )
    ]

    for service in services:
        db_session.add(service)
    db_session.commit()

    return services


class TestDiagnoseFailing:
    """Diagnóstico de las pruebas que fallan"""

    def test_1_list_endpoint_detailed(self, client, auth_setup, sample_services, db_session):
        """Test 1: Diagnóstico detallado del endpoint de listado"""
        user, headers = auth_setup

        print("\n=== DIAGNÓSTICO DE LISTADO ===")
        print(f"Usuario: {user.Username} (ID: {user.Id})")
        print(f"Servicios creados: {len(sample_services)}")

        # Test 1: Sin parámetros
        print("\n1. GET sin parámetros:")
        response = client.get("/api/v1/service-types/", headers=headers)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Response keys: {data.keys()}")
            print(f"   Service types count: {len(data.get('service_types', []))}")
            if 'error' in data:
                print(f"   Error: {data['error']}")
        else:
            print(f"   Error response: {response.text}")

        # Test 2: Con parámetros explícitos
        print("\n2. GET con parámetros explícitos:")
        response = client.get(
            "/api/v1/service-types/?skip=0&limit=10&active_only=true",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error: {response.text}")

        # Test 3: Sin filtro active_only
        print("\n3. GET todos (activos e inactivos):")
        response = client.get(
            "/api/v1/service-types/?active_only=false",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total services: {data.get('total', 'N/A')}")
        else:
            print(f"   Error: {response.text}")

        # Test 4: Verificar directamente en BD
        print("\n4. Verificación directa en BD:")
        db_services = db_session.query(ServiceType).all()
        print(f"   Total en BD: {len(db_services)}")
        active_services = db_session.query(ServiceType).filter(ServiceType.IsActive == True).all()
        print(f"   Activos en BD: {len(active_services)}")

        # Test 5: Probar endpoint alternativo si existe
        print("\n5. Probar endpoint alternativo /active:")
        response = client.get("/api/v1/service-types/active", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")

    def test_2_quick_setup_detailed(self, client, auth_setup, db_session):
        """Test 2: Diagnóstico detallado del quick-setup"""
        user, headers = auth_setup

        print("\n=== DIAGNÓSTICO DE QUICK-SETUP ===")

        # Verificar si ya hay servicios
        existing = db_session.query(ServiceType).count()
        print(f"Servicios existentes antes: {existing}")

        # Test 1: Quick setup básico
        print("\n1. Quick setup con servicios por defecto:")
        setup_data = {
            "include_default_services": True,
            "custom_services": []
        }

        response = client.post(
            "/api/v1/service-types/quick-setup",
            json=setup_data,
            headers=headers
        )
        print(f"   Status: {response.status_code}")

        if response.status_code == 404:
            print("   ✗ Endpoint no existe")
            return
        elif response.status_code == 200:
            data = response.json()
            print(f"   ✓ Response type: {type(data)}")
            if isinstance(data, list):
                print(f"   Services created: {len(data)}")
                if data:
                    print(f"   First service: {data[0]}")
            else:
                print(f"   Response: {data}")
        else:
            print(f"   Error: {response.text}")

            # Intentar diagnosticar el error
            if response.status_code == 500:
                print("\n   Posibles causas del error 500:")

                # Verificar si el método existe en CRUD
                from app.crud.service_type import service_type_crud

                if hasattr(service_type_crud, 'setup_default_services'):
                    print("   - setup_default_services existe en CRUD")
                    try:
                        # Intentar llamar directamente
                        result = service_type_crud.setup_default_services(db_session)
                        print(f"   - Llamada directa funciona: {len(result)} servicios")
                    except Exception as e:
                        print(f"   - Error en llamada directa: {e}")
                else:
                    print("   - setup_default_services NO existe en CRUD")

                # Verificar si el modelo tiene get_default_service_types
                if hasattr(ServiceType, 'get_default_service_types'):
                    print("   - get_default_service_types existe en modelo")
                else:
                    print("   - get_default_service_types NO existe en modelo")

        # Test 2: Quick setup con servicios personalizados
        print("\n2. Quick setup con servicios personalizados:")
        setup_data = {
            "include_default_services": False,
            "custom_services": [
                {
                    "Code": "CUST1",
                    "Name": "Custom Service",
                    "Description": "Test",
                    "TicketPrefix": "CS",
                    "Priority": 3,
                    "AverageTimeMinutes": 10,
                    "Color": "#007bff"
                }
            ]
        }

        response = client.post(
            "/api/v1/service-types/quick-setup",
            json=setup_data,
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        elif response.status_code != 404:
            print(f"   Error: {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])