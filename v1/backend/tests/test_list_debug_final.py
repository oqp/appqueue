"""
Diagnóstico final para el endpoint de listado después de correcciones
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
    session.execute(text("DELETE FROM ServiceTypes"))
    session.execute(text("DELETE FROM Users"))
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


class TestListDebugFinal:
    """Diagnóstico final del endpoint de listado"""

    def test_list_with_detailed_debug(self, client, db_session):
        """Test detallado del listado con todas las variantes"""

        print("\n=== DIAGNÓSTICO FINAL DE LISTADO ===")

        # 1. Crear datos de prueba
        print("\n1. Creando datos de prueba...")

        # Crear rol
        role = Role(
            Name="Admin",
            Description="Admin",
            Permissions=json.dumps({"all": True}),
            IsActive=True
        )
        db_session.add(role)
        db_session.commit()

        # Crear usuario
        user = User(
            Id=str(uuid.uuid4()),
            Username="test_user",
            Email="test@test.com",
            FullName="Test User",
            PasswordHash=create_password_hash("test123"),
            RoleId=role.Id,
            IsActive=True
        )
        db_session.add(user)
        db_session.commit()

        # Token
        token = create_access_token({"sub": str(user.Id)})
        headers = {"Authorization": f"Bearer {token}"}

        # Crear servicios
        services = []
        for i in range(3):
            service = ServiceType(
                Code=f"SRV{i}",
                Name=f"Service {i}",
                Description=f"Description {i}",
                TicketPrefix=f"S{i}",
                Priority=i + 1,
                AverageTimeMinutes=10 + i,
                IsActive=True if i < 2 else False,  # Uno inactivo
                Color="#007bff"
            )
            db_session.add(service)
            services.append(service)
        db_session.commit()

        print(f"   Creados {len(services)} servicios (2 activos, 1 inactivo)")

        # 2. Probar query directo en BD
        print("\n2. Query directo en BD...")

        # Query simple
        result = db_session.query(ServiceType).all()
        print(f"   Total en BD: {len(result)}")

        # Query con filtro y ORDER BY
        result = db_session.query(ServiceType) \
            .filter(ServiceType.IsActive == True) \
            .order_by(ServiceType.Id) \
            .all()
        print(f"   Activos con ORDER BY: {len(result)}")

        # Query con OFFSET y LIMIT
        try:
            result = db_session.query(ServiceType) \
                .filter(ServiceType.IsActive == True) \
                .order_by(ServiceType.Id) \
                .offset(0).limit(10) \
                .all()
            print(f"   Con OFFSET/LIMIT: {len(result)} ✓")
        except Exception as e:
            print(f"   Error con OFFSET/LIMIT: {e}")

        # 3. Probar endpoint
        print("\n3. Probando endpoint...")

        # Test sin parámetros
        print("\n   a) Sin parámetros:")
        response = client.get("/api/v1/service-types/", headers=headers)
        print(f"      Status: {response.status_code}")
        if response.status_code != 200:
            print(f"      Error: {response.json()}")
        else:
            data = response.json()
            print(f"      Servicios: {len(data.get('service_types', []))}")
            print(f"      Total: {data.get('total')}")

        # Test con parámetros explícitos
        print("\n   b) Con skip=0, limit=10:")
        response = client.get(
            "/api/v1/service-types/?skip=0&limit=10",
            headers=headers
        )
        print(f"      Status: {response.status_code}")
        if response.status_code != 200:
            print(f"      Error: {response.json()}")

        # Test con active_only=false
        print("\n   c) Con active_only=false:")
        response = client.get(
            "/api/v1/service-types/?active_only=false",
            headers=headers
        )
        print(f"      Status: {response.status_code}")
        if response.status_code != 200:
            error = response.json()
            print(f"      Error: {error}")

            # Si hay error de validación Pydantic
            if "validation error" in str(error).lower():
                print("\n      PROBLEMA: El schema ServiceTypeListResponse no coincide")
                print("      La respuesta del endpoint no tiene la estructura esperada")
        else:
            data = response.json()
            print(f"      Total (activos+inactivos): {data.get('total')}")

        # 4. Verificar estructura del response
        print("\n4. Verificando estructura de respuesta...")

        # Importar schema
        from app.schemas.service_type import ServiceTypeListResponse

        # Crear respuesta de prueba
        test_response = {
            "service_types": [],
            "total": 0,
            "skip": 0,
            "limit": 20,
            "has_more": False
        }

        try:
            validated = ServiceTypeListResponse(**test_response)
            print("   Schema básico válido ✓")
        except Exception as e:
            print(f"   Error en schema: {e}")
            print("   El schema espera campos adicionales que no se están enviando")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])