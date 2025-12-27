"""
Pruebas de diagnóstico para identificar el problema con los endpoints de service_types
"""

import pytest
import sys
import os
from datetime import datetime
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
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.role import Role
from app.crud.service_type import service_type_crud
from app.schemas.service_type import ServiceTypeCreate
from app.core.security import create_password_hash, create_access_token
from app.api.dependencies.auth import get_current_user, require_supervisor_or_admin

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


class TestDiagnostic:
    """Pruebas de diagnóstico paso a paso"""

    def test_1_crud_direct(self, db_session):
        """Test 1: CRUD directo funciona"""
        print("\n=== TEST 1: CRUD DIRECTO ===")

        # Crear usando CRUD directamente
        service_data = ServiceTypeCreate(
            Code="TEST",
            Name="Test Service",
            Description="Test",
            TicketPrefix="T",
            Priority=3,
            AverageTimeMinutes=15,
            Color="#007bff"
        )

        try:
            service = service_type_crud.create_with_validation(db_session, obj_in=service_data)
            print(f"✓ CRUD create exitoso: {service.Name} (ID: {service.Id})")
            assert service.Code == "TEST"
            assert service.Name == "Test Service"
        except Exception as e:
            print(f"✗ Error en CRUD: {e}")
            raise

    def test_2_endpoint_without_auth(self, client):
        """Test 2: Endpoint sin autenticación"""
        print("\n=== TEST 2: ENDPOINT SIN AUTH ===")

        service_data = {
            "Code": "TEST2",
            "Name": "Test Service 2",
            "Description": "Test",
            "TicketPrefix": "T2",
            "Priority": 3,
            "AverageTimeMinutes": 15
        }

        response = client.post("/api/v1/service-types/", json=service_data)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 401:
            print("✓ Rechaza correctamente sin auth (401)")
        else:
            print(f"✗ Status inesperado: {response.status_code}")
            try:
                print(f"Response: {response.json()}")
            except:
                print(f"Response text: {response.text}")

    def test_3_create_user_and_auth(self, db_session):
        """Test 3: Crear usuario y generar token"""
        print("\n=== TEST 3: CREAR USUARIO Y TOKEN ===")

        # Crear rol
        role = Role(
            Name="Admin",
            Description="Admin",
            Permissions=json.dumps({"all": True}),
            IsActive=True
        )
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)
        print(f"✓ Rol creado: {role.Name} (ID: {role.Id})")

        # Crear usuario
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
        db_session.refresh(user)
        print(f"✓ Usuario creado: {user.Username}")

        # Verificar relación
        user_check = db_session.query(User).filter(User.Username == "test_admin").first()
        assert user_check is not None
        assert user_check.role is not None
        print(f"✓ Usuario tiene rol: {user_check.role.Name}")

        # Generar token
        token = create_access_token({"sub": user.Username})
        print(f"✓ Token generado: {token[:20]}...")

        return token

    def test_4_endpoint_with_auth(self, client, db_session):
        """Test 4: Endpoint con autenticación"""
        print("\n=== TEST 4: ENDPOINT CON AUTH ===")

        # Primero crear usuario y token
        token = self.test_3_create_user_and_auth(db_session)
        headers = {"Authorization": f"Bearer {token}"}

        # Intentar listar (GET debería funcionar para cualquier usuario autenticado)
        response = client.get("/api/v1/service-types/", headers=headers)
        print(f"GET Status: {response.status_code}")

        if response.status_code == 200:
            print("✓ GET funciona con auth")
        else:
            print(f"✗ GET falla con auth")
            try:
                print(f"Response: {response.json()}")
            except:
                print(f"Response text: {response.text}")

        # Intentar crear (POST requiere supervisor o admin)
        service_data = {
            "Code": "TEST4",
            "Name": "Test Service 4",
            "Description": "Test",
            "TicketPrefix": "T4",
            "Priority": 3,
            "AverageTimeMinutes": 15
        }

        response = client.post("/api/v1/service-types/", json=service_data, headers=headers)
        print(f"\nPOST Status: {response.status_code}")

        if response.status_code == 200:
            print("✓ POST funciona con auth admin")
            data = response.json()
            print(f"  Creado: {data.get('Name')} (ID: {data.get('Id')})")
        elif response.status_code == 403:
            print("✗ POST rechazado por permisos (403)")
            print(f"Response: {response.json()}")
        elif response.status_code == 500:
            print("✗ ERROR 500 - Problema en el endpoint")
            try:
                error = response.json()
                print(f"  Detail: {error.get('detail')}")
            except:
                print(f"  Response text: {response.text}")
        else:
            print(f"✗ Status inesperado: {response.status_code}")
            try:
                print(f"Response: {response.json()}")
            except:
                print(f"Response text: {response.text}")

    def test_5_dependency_isolation(self, db_session):
        """Test 5: Probar dependencia require_supervisor_or_admin aislada"""
        print("\n=== TEST 5: DEPENDENCIA AISLADA ===")

        # Crear usuario admin
        role = db_session.query(Role).filter(Role.Name == "Admin").first()
        if not role:
            role = Role(Name="Admin", Description="Admin", Permissions=json.dumps({"all": True}), IsActive=True)
            db_session.add(role)
            db_session.commit()

        user = db_session.query(User).filter(User.Username == "test_admin").first()
        if not user:
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
            db_session.refresh(user)

        # Verificar propiedades del usuario
        print(f"Usuario: {user.Username}")
        print(f"Role ID: {user.RoleId}")
        print(f"Role: {user.role.Name if user.role else 'None'}")
        print(f"role_name property: {user.role_name}")
        print(f"is_admin: {user.is_admin}")
        print(f"is_supervisor: {user.is_supervisor}")

        # Probar la función checker
        try:
            checker = require_supervisor_or_admin()
            print(f"✓ Dependencia creada: {type(checker)}")

            # Simular llamada con el usuario
            result = checker(user)
            print(f"✓ Checker acepta al usuario admin: {result.Username}")
        except Exception as e:
            print(f"✗ Error en checker: {e}")

        # Probar con usuario sin permisos
        tech_role = Role(Name="Technician", Description="Tech", Permissions=json.dumps({"basic": True}), IsActive=True)
        db_session.add(tech_role)
        db_session.commit()

        tech_user = User(
            Id=str(uuid.uuid4()),
            Username="tech_user",
            Email="tech@test.com",
            FullName="Tech User",
            PasswordHash=create_password_hash("tech123"),
            RoleId=tech_role.Id,
            IsActive=True
        )
        db_session.add(tech_user)
        db_session.commit()
        db_session.refresh(tech_user)

        print(f"\nUsuario técnico: {tech_user.Username}")
        print(f"is_admin: {tech_user.is_admin}")
        print(f"is_supervisor: {tech_user.is_supervisor}")

        try:
            result = checker(tech_user)
            print(f"✗ Checker acepta incorrectamente al técnico")
        except Exception as e:
            print(f"✓ Checker rechaza correctamente al técnico: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])