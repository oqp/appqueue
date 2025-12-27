"""
Script de pruebas de integración para el módulo Queue
Verifica que todos los componentes funcionen correctamente con PascalCase
Ejecutar con: python test_queue_integration.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid
import json
from colorama import init, Fore, Style

# Inicializar colorama para salida con colores
init()

# Importaciones del proyecto
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base
from app.main import app

# Modelos
from app.models.queue_state import QueueState
from app.models.service_type import ServiceType
from app.models.station import Station
from app.models.ticket import Ticket
from app.models.patient import Patient
from app.models.user import User
from app.models.role import Role

# Schemas
from app.schemas.queue import (
    QueueStateCreate,
    QueueStateUpdate,
    QueueStateResponse,
    AdvanceQueueRequest,
    ResetQueueRequest,
    UpdateWaitTimeRequest,
    QueueSummary
)

# CRUD
from app.crud.queue import queue_crud

# Security
from app.core.security import create_password_hash, create_access_token

# ========================================
# CONFIGURACIÓN
# ========================================

# Usar base de datos de test
TEST_DATABASE_URL = f"mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"

# Cliente de pruebas
client = TestClient(app)

# Colores para output
SUCCESS = Fore.GREEN + "✓" + Style.RESET_ALL
ERROR = Fore.RED + "✗" + Style.RESET_ALL
INFO = Fore.CYAN + "→" + Style.RESET_ALL
WARNING = Fore.YELLOW + "⚠" + Style.RESET_ALL


# ========================================
# FUNCIONES DE UTILIDAD
# ========================================

def print_test_header(test_name: str):
    """Imprime header de test"""
    print(f"\n{Fore.BLUE}{'=' * 60}")
    print(f"  {test_name}")
    print(f"{'=' * 60}{Style.RESET_ALL}")


def print_result(success: bool, message: str, details: str = None):
    """Imprime resultado de test"""
    icon = SUCCESS if success else ERROR
    print(f"{icon} {message}")
    if details and not success:
        print(f"   {Fore.YELLOW}{details}{Style.RESET_ALL}")


def create_test_session() -> Session:
    """Crea una sesión de base de datos de test"""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestSessionLocal()


def clean_test_database(session: Session):
    """Limpia las tablas de test en el orden correcto"""
    print(f"\n{INFO} Limpiando base de datos de test...")

    tables = [
        "ActivityLog",
        "NotificationLog",
        "QueueState",
        "Tickets",
        "Users",
        "Stations",
        "Patients",
        "ServiceTypes",
        "Roles"
    ]

    for table in tables:
        try:
            session.execute(text(f"DELETE FROM {table}"))
            session.commit()
        except Exception as e:
            session.rollback()
            # Ignorar si la tabla no existe
            pass


def create_test_data(session: Session) -> Dict[str, Any]:
    """Crea datos de prueba necesarios"""
    print(f"{INFO} Creando datos de prueba...")

    data = {}

    try:
        # 1. Crear rol
        role = Role(
            Name="Técnico",
            Description="Técnico de laboratorio",
            Permissions=json.dumps(["queue.view", "queue.update", "queue.advance"])
        )
        session.add(role)
        session.commit()
        data['role'] = role

        # 2. Crear tipo de servicio
        service = ServiceType(
            Code="LAB",
            Name="Análisis de Laboratorio",
            Description="Análisis de sangre y orina",
            Priority=1,
            AverageTimeMinutes=15,
            TicketPrefix="L",
            IsActive=True
        )
        session.add(service)
        session.commit()
        data['service'] = service

        # 3. Crear estación
        station = Station(
            Code="V01",
            Name="Ventanilla 1",
            Description="Ventanilla principal",
            ServiceTypeId=service.Id,
            Location="Planta baja",
            IsActive=True,
            Status="Available"
        )
        session.add(station)
        session.commit()
        data['station'] = station

        # 4. Crear usuario
        user = User(
            Id=str(uuid.uuid4()),
            Username="test_tech",
            Email="tech@test.com",
            PasswordHash=create_password_hash("test123"),
            FullName="Técnico de Prueba",
            RoleId=role.Id,
            StationId=station.Id,
            IsActive=True
        )
        session.add(user)
        session.commit()
        data['user'] = user

        # 5. Crear paciente
        patient = Patient(
            Id=str(uuid.uuid4()),
            FullName="Juan Pérez",
            DocumentNumber="12345678",
            BirthDate=datetime(1990, 5, 15).date(),
            Gender="M",
            Phone="987654321",
            Email="juan@test.com",
            IsActive=True
        )
        session.add(patient)
        session.commit()
        data['patient'] = patient

        # 6. Crear tickets
        tickets = []
        for i in range(5):
            ticket = Ticket(
                Id=str(uuid.uuid4()),
                TicketNumber=f"L{str(i + 1).zfill(3)}",
                PatientId=patient.Id,
                ServiceTypeId=service.Id,
                Status="Waiting",
                Position=i + 1
            )
            session.add(ticket)
            tickets.append(ticket)
        session.commit()
        data['tickets'] = tickets

        print(f"{SUCCESS} Datos de prueba creados exitosamente")
        return data

    except Exception as e:
        session.rollback()
        print(f"{ERROR} Error creando datos de prueba: {e}")
        raise


# ========================================
# PRUEBAS DE SCHEMAS
# ========================================

def test_schemas():
    """Prueba que los schemas manejen correctamente PascalCase"""
    print_test_header("PRUEBAS DE SCHEMAS")

    results = []

    # Test 1: QueueStateCreate con PascalCase
    try:
        queue_create = QueueStateCreate(
            ServiceTypeId=1,
            StationId=2,
            CurrentTicketId="550e8400-e29b-41d4-a716-446655440000",
            QueueLength=5,
            AverageWaitTime=15
        )

        # Verificar que los campos se mantienen en PascalCase
        assert hasattr(queue_create, 'ServiceTypeId')
        assert queue_create.ServiceTypeId == 1
        assert queue_create.QueueLength == 5

        results.append((True, "QueueStateCreate maneja PascalCase correctamente"))
    except Exception as e:
        results.append((False, "QueueStateCreate falló con PascalCase", str(e)))

    # Test 2: QueueStateUpdate con campos opcionales
    try:
        queue_update = QueueStateUpdate(
            QueueLength=10,
            AverageWaitTime=20
        )

        # Verificar model_dump
        data = queue_update.model_dump(exclude_unset=True)
        assert 'QueueLength' in data
        assert data['QueueLength'] == 10

        results.append((True, "QueueStateUpdate maneja campos opcionales"))
    except Exception as e:
        results.append((False, "QueueStateUpdate falló", str(e)))

    # Test 3: AdvanceQueueRequest
    try:
        advance_request = AdvanceQueueRequest(
            ServiceTypeId=1,
            StationId=2,
            MarkCompleted=True
        )

        assert advance_request.ServiceTypeId == 1
        assert advance_request.MarkCompleted is True

        results.append((True, "AdvanceQueueRequest funciona correctamente"))
    except Exception as e:
        results.append((False, "AdvanceQueueRequest falló", str(e)))

    # Test 4: ResetQueueRequest
    try:
        reset_request = ResetQueueRequest(
            ServiceTypeId=1,
            Reason="Fin de jornada",
            CancelPendingTickets=True
        )

        assert reset_request.ServiceTypeId == 1
        assert reset_request.CancelPendingTickets is True

        results.append((True, "ResetQueueRequest funciona correctamente"))
    except Exception as e:
        results.append((False, "ResetQueueRequest falló", str(e)))

    # Test 5: UpdateWaitTimeRequest con validación
    try:
        # Debe fallar si Recalculate=False y no hay ManualTime
        try:
            UpdateWaitTimeRequest(
                QueueStateId=1,
                Recalculate=False
            )
            results.append((False, "UpdateWaitTimeRequest no validó correctamente"))
        except:
            # Esperamos que falle
            pass

        # Debe funcionar con ManualTime
        update_time = UpdateWaitTimeRequest(
            QueueStateId=1,
            Recalculate=False,
            ManualTime=30
        )

        assert update_time.ManualTime == 30
        results.append((True, "UpdateWaitTimeRequest valida correctamente"))
    except Exception as e:
        results.append((False, "UpdateWaitTimeRequest falló", str(e)))

    # Imprimir resultados
    for success, message, *details in results:
        print_result(success, message, details[0] if details else None)

    return all(r[0] for r in results)


# ========================================
# PRUEBAS DE MODELOS
# ========================================

def test_models():
    """Prueba que los modelos SQLAlchemy funcionen con PascalCase"""
    print_test_header("PRUEBAS DE MODELOS")

    session = create_test_session()
    results = []

    try:
        # Test 1: Crear QueueState directamente
        queue_state = QueueState(
            ServiceTypeId=1,
            StationId=1,
            QueueLength=0,
            AverageWaitTime=15,
            LastUpdateAt=datetime.now()
        )

        # Verificar atributos
        assert queue_state.ServiceTypeId == 1
        assert queue_state.QueueLength == 0

        results.append((True, "Modelo QueueState acepta PascalCase"))

        # Test 2: Verificar relaciones
        # Esto requiere datos existentes, lo haremos en test_crud

    except Exception as e:
        results.append((False, "Modelo QueueState falló", str(e)))
    finally:
        session.close()

    # Imprimir resultados
    for success, message, *details in results:
        print_result(success, message, details[0] if details else None)

    return all(r[0] for r in results)


# ========================================
# PRUEBAS DE CRUD
# ========================================

def test_crud():
    """Prueba operaciones CRUD con PascalCase"""
    print_test_header("PRUEBAS DE CRUD")

    session = create_test_session()
    results = []

    try:
        # Limpiar y crear datos de prueba
        clean_test_database(session)
        test_data = create_test_data(session)

        # Test 1: Crear QueueState con schema
        try:
            queue_create = QueueStateCreate(
                ServiceTypeId=test_data['service'].Id,
                StationId=test_data['station'].Id,
                QueueLength=0,
                AverageWaitTime=15
            )

            queue_state = queue_crud.create(session, obj_in=queue_create)

            assert queue_state is not None
            assert queue_state.ServiceTypeId == test_data['service'].Id
            assert queue_state.QueueLength == 0

            results.append((True, "CRUD create con PascalCase funciona"))

            # Guardar para siguientes tests
            test_queue_id = queue_state.Id

        except Exception as e:
            results.append((False, "CRUD create falló", str(e)))
            test_queue_id = None

        # Test 2: Actualizar QueueState
        if test_queue_id:
            try:
                queue_update = QueueStateUpdate(
                    QueueLength=5,
                    AverageWaitTime=20
                )

                queue_state = session.query(QueueState).filter(
                    QueueState.Id == test_queue_id
                ).first()

                updated = queue_crud.update(
                    session,
                    db_obj=queue_state,
                    obj_in=queue_update
                )

                assert updated.QueueLength == 5
                assert updated.AverageWaitTime == 20

                results.append((True, "CRUD update con PascalCase funciona"))

            except Exception as e:
                results.append((False, "CRUD update falló", str(e)))

        # Test 3: get_by_service_and_station
        try:
            queue_state = queue_crud.get_by_service_and_station(
                session,
                service_type_id=test_data['service'].Id,
                station_id=test_data['station'].Id
            )

            assert queue_state is not None
            results.append((True, "CRUD get_by_service_and_station funciona"))

        except Exception as e:
            results.append((False, "CRUD get_by_service_and_station falló", str(e)))

        # Test 4: advance_queue
        try:
            # Asignar un ticket a la cola
            if test_data['tickets']:
                queue_state = session.query(QueueState).filter(
                    QueueState.Id == test_queue_id
                ).first()

                queue_state.NextTicketId = test_data['tickets'][0].Id
                queue_state.QueueLength = len(test_data['tickets'])
                session.commit()

                # Avanzar cola
                advanced = queue_crud.advance_queue(
                    session,
                    service_type_id=test_data['service'].Id,
                    station_id=test_data['station'].Id
                )

                assert advanced is not None
                assert advanced.CurrentTicketId == test_data['tickets'][0].Id

                results.append((True, "CRUD advance_queue funciona"))
        except Exception as e:
            results.append((False, "CRUD advance_queue falló", str(e)))

        # Test 5: reset_queue
        try:
            reset = queue_crud.reset_queue(
                session,
                service_type_id=test_data['service'].Id,
                station_id=test_data['station'].Id
            )

            assert reset is not None
            assert reset.QueueLength == 0
            assert reset.CurrentTicketId is None

            results.append((True, "CRUD reset_queue funciona"))

        except Exception as e:
            results.append((False, "CRUD reset_queue falló", str(e)))

        # Test 6: calculate_and_update_wait_time
        try:
            if test_queue_id:
                avg_time = queue_crud.calculate_and_update_wait_time(
                    session,
                    queue_state_id=test_queue_id
                )

                assert avg_time is not None
                results.append((True, "CRUD calculate_wait_time funciona"))
        except Exception as e:
            results.append((False, "CRUD calculate_wait_time falló", str(e)))

        # Test 7: get_queue_summary
        try:
            summary = queue_crud.get_queue_summary(session)

            assert 'total_queues' in summary
            assert 'active_queues' in summary
            assert 'average_wait_time' in summary

            results.append((True, "CRUD get_queue_summary funciona"))

        except Exception as e:
            results.append((False, "CRUD get_queue_summary falló", str(e)))

    except Exception as e:
        results.append((False, f"Error general en CRUD: {e}"))
    finally:
        session.close()

    # Imprimir resultados
    for success, message, *details in results:
        print_result(success, message, details[0] if details else None)

    return all(r[0] for r in results)


# ========================================
# PRUEBAS DE API ENDPOINTS
# ========================================

def test_api_endpoints():
    """Prueba los endpoints API con PascalCase"""
    print_test_header("PRUEBAS DE API ENDPOINTS")

    session = create_test_session()
    results = []

    try:
        # Preparar datos
        clean_test_database(session)
        test_data = create_test_data(session)

        # Crear token de autenticación
        access_token = create_access_token(
            data={"sub": test_data['user'].Username}
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        # Test 1: GET /queue-states
        try:
            response = client.get("/api/v1/queue-states/", headers=headers)

            if response.status_code == 200:
                data = response.json()
                # Verificar que devuelve lista
                assert isinstance(data, list)
                results.append((True, "GET /queue-states funciona"))
            else:
                results.append((False, f"GET /queue-states falló: {response.status_code}", response.text))

        except Exception as e:
            results.append((False, "GET /queue-states error", str(e)))

        # Test 2: POST /queue-states (crear)
        try:
            create_data = {
                "ServiceTypeId": test_data['service'].Id,
                "StationId": test_data['station'].Id,
                "QueueLength": 0,
                "AverageWaitTime": 15
            }

            response = client.post(
                "/api/v1/queue-states/",
                json=create_data,
                headers=headers
            )

            if response.status_code in [200, 201]:
                data = response.json()
                # Verificar respuesta en PascalCase
                assert 'Id' in data
                assert 'ServiceTypeId' in data
                assert data['ServiceTypeId'] == test_data['service'].Id

                queue_id = data['Id']
                results.append((True, "POST /queue-states funciona con PascalCase"))
            else:
                results.append((False, f"POST /queue-states falló: {response.status_code}", response.text))
                queue_id = None

        except Exception as e:
            results.append((False, "POST /queue-states error", str(e)))
            queue_id = None

        # Test 3: GET /queue-states/{id}
        if queue_id:
            try:
                response = client.get(f"/api/v1/queue-states/{queue_id}", headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    assert data['Id'] == queue_id
                    assert 'QueueLength' in data
                    results.append((True, "GET /queue-states/{id} funciona"))
                else:
                    results.append((False, f"GET /queue-states/{id} falló: {response.status_code}"))

            except Exception as e:
                results.append((False, "GET /queue-states/{id} error", str(e)))

        # Test 4: PATCH /queue-states/{id}
        if queue_id:
            try:
                update_data = {
                    "QueueLength": 10,
                    "AverageWaitTime": 25
                }

                response = client.patch(
                    f"/api/v1/queue-states/{queue_id}",
                    json=update_data,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    assert data['QueueLength'] == 10
                    assert data['AverageWaitTime'] == 25
                    results.append((True, "PATCH /queue-states/{id} funciona con PascalCase"))
                else:
                    results.append((False, f"PATCH /queue-states/{id} falló: {response.status_code}"))

            except Exception as e:
                results.append((False, "PATCH /queue-states/{id} error", str(e)))

        # Test 5: POST /queue-states/advance
        try:
            advance_data = {
                "ServiceTypeId": test_data['service'].Id,
                "StationId": test_data['station'].Id,
                "MarkCompleted": False
            }

            response = client.post(
                "/api/v1/queue-states/advance",
                json=advance_data,
                headers=headers
            )

            # Puede ser 200 o 404 si no hay tickets
            if response.status_code in [200, 404]:
                results.append((True, "POST /queue-states/advance acepta PascalCase"))
            else:
                results.append((False, f"POST /queue-states/advance falló: {response.status_code}"))

        except Exception as e:
            results.append((False, "POST /queue-states/advance error", str(e)))

        # Test 6: POST /queue-states/reset
        try:
            reset_data = {
                "ServiceTypeId": test_data['service'].Id,
                "Reason": "Test reset",
                "CancelPendingTickets": False
            }

            response = client.post(
                "/api/v1/queue-states/reset",
                json=reset_data,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                assert data['QueueLength'] == 0
                results.append((True, "POST /queue-states/reset funciona con PascalCase"))
            else:
                results.append((False, f"POST /queue-states/reset falló: {response.status_code}"))

        except Exception as e:
            results.append((False, "POST /queue-states/reset error", str(e)))

        # Test 7: GET /queue-states/summary
        try:
            response = client.get("/api/v1/queue-states/summary", headers=headers)

            if response.status_code == 200:
                data = response.json()
                # Verificar campos en PascalCase
                assert 'TotalQueues' in data
                assert 'ActiveQueues' in data
                assert 'TotalWaiting' in data
                assert 'AverageWaitTime' in data
                results.append((True, "GET /queue-states/summary devuelve PascalCase"))
            else:
                results.append((False, f"GET /queue-states/summary falló: {response.status_code}"))

        except Exception as e:
            results.append((False, "GET /queue-states/summary error", str(e)))

    except Exception as e:
        results.append((False, f"Error general en API: {e}"))
    finally:
        session.close()

    # Imprimir resultados
    for success, message, *details in results:
        print_result(success, message, details[0] if details else None)

    return all(r[0] for r in results)


# ========================================
# FUNCIÓN PRINCIPAL
# ========================================

def main():
    """Ejecuta todas las pruebas"""
    print(f"\n{Fore.MAGENTA}╔{'═' * 58}╗")
    print(f"║  PRUEBAS DE INTEGRACIÓN - MÓDULO QUEUE CON PASCALCASE  ║")
    print(f"╚{'═' * 58}╝{Style.RESET_ALL}")

    all_passed = True

    # Ejecutar pruebas
    tests = [
        ("Schemas", test_schemas),
        ("Modelos", test_models),
        ("CRUD", test_crud),
        ("API Endpoints", test_api_endpoints)
    ]

    results_summary = []

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results_summary.append((test_name, passed))
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"{ERROR} Error ejecutando pruebas de {test_name}: {e}")
            results_summary.append((test_name, False))
            all_passed = False

    # Resumen final
    print(f"\n{Fore.MAGENTA}{'=' * 60}")
    print("  RESUMEN DE PRUEBAS")
    print(f"{'=' * 60}{Style.RESET_ALL}")

    for test_name, passed in results_summary:
        icon = SUCCESS if passed else ERROR
        status = "PASÓ" if passed else "FALLÓ"
        color = Fore.GREEN if passed else Fore.RED
        print(f"{icon} {test_name}: {color}{status}{Style.RESET_ALL}")

    # Resultado final
    print(f"\n{Fore.MAGENTA}{'=' * 60}{Style.RESET_ALL}")
    if all_passed:
        print(f"{Fore.GREEN}✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ ALGUNAS PRUEBAS FALLARON{Style.RESET_ALL}")
        print(f"{WARNING} Revisa los errores anteriores para más detalles")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())