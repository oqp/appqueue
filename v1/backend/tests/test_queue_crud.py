"""
Pruebas unitarias para el CRUD de QueueState
Compatible con SQL Server y toda la estructura existente del proyecto
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import List
import uuid

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.crud.queue import queue_crud
from app.models.queue_state import QueueState
from app.models.service_type import ServiceType
from app.models.station import Station
from app.models.ticket import Ticket
from app.models.patient import Patient
from app.models.user import User
from app.models.role import Role
from app.schemas.queue import QueueStateCreate, QueueStateUpdate
from app.core.security import create_password_hash


# ========================================
# CONFIGURACIÓN DE BASE DE DATOS DE TEST
# ========================================

TEST_DATABASE_URL = "mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"


# ========================================
# FIXTURES
# ========================================

@pytest.fixture(scope="function")
def db_session():
    """
    Crea una sesión de base de datos de test en SQL Server
    """
    # Crear engine
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Crear sesión
    session = TestSessionLocal()

    try:
        # Limpiar tablas en orden correcto (por foreign keys)
        session.execute(text("DELETE FROM ActivityLog"))
        session.execute(text("DELETE FROM NotificationLog"))
        session.execute(text("DELETE FROM DailyMetrics"))
        session.execute(text("DELETE FROM QueueState"))
        session.execute(text("DELETE FROM Tickets"))
        session.execute(text("DELETE FROM Users"))
        session.execute(text("DELETE FROM Stations"))
        session.execute(text("DELETE FROM Patients"))
        session.execute(text("DELETE FROM MessageTemplates"))
        session.execute(text("DELETE FROM ServiceTypes"))
        session.execute(text("DELETE FROM Roles"))
        session.commit()

        yield session

    finally:
        session.close()


@pytest.fixture
def sample_service_type(db_session: Session) -> ServiceType:
    """
    Crea un tipo de servicio de prueba
    """
    service = ServiceType(
        Code="LAB",
        Name="Análisis de Laboratorio",
        Description="Análisis de sangre y orina",
        TicketPrefix="A",
        Priority=1,
        AverageTimeMinutes=15,
        IsActive=True
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


@pytest.fixture
def sample_station(db_session: Session) -> Station:
    """
    Crea una estación de prueba
    """
    station = Station(
        Code="V01",
        Name="Ventanilla 1",
        Description="Ventanilla principal",
        Location="Planta Baja",
        Status="Available",
        IsActive=True
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station


@pytest.fixture
def sample_patient(db_session: Session) -> Patient:
    """
    Crea un paciente de prueba con los campos correctos del modelo
    """
    patient = Patient(
        DocumentNumber="12345678",
        FullName="Juan Pérez",
        BirthDate=datetime(1990, 1, 1).date(),
        Gender="M",
        Phone="999888777",
        Email="juan@test.com",
        IsActive=True
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture
def sample_tickets(
    db_session: Session,
    sample_patient: Patient,
    sample_service_type: ServiceType
) -> List[Ticket]:
    """
    Crea varios tickets de prueba
    """
    tickets = []
    for i in range(5):
        ticket = Ticket(
            TicketNumber=f"A{str(i+1).zfill(3)}",
            ServiceTypeId=sample_service_type.Id,
            PatientId=sample_patient.Id,
            Status="Waiting" if i > 0 else "Called",
            Position=i+1,  # Position es requerido
            CreatedAt=datetime.now() - timedelta(minutes=30-i*5)
        )
        db_session.add(ticket)
        tickets.append(ticket)

    db_session.commit()
    for ticket in tickets:
        db_session.refresh(ticket)

    return tickets


@pytest.fixture
def sample_queue_state(
    db_session: Session,
    sample_service_type: ServiceType,
    sample_station: Station,
    sample_tickets: List[Ticket]
) -> QueueState:
    """
    Crea un estado de cola de prueba
    """
    queue_state = QueueState(
        ServiceTypeId=sample_service_type.Id,
        StationId=sample_station.Id,
        CurrentTicketId=str(sample_tickets[0].Id),
        NextTicketId=str(sample_tickets[1].Id),
        QueueLength=4,
        AverageWaitTime=15,
        LastUpdateAt=datetime.now()
    )
    db_session.add(queue_state)
    db_session.commit()
    db_session.refresh(queue_state)
    return queue_state


# ========================================
# TESTS DE CREACIÓN
# ========================================

class TestCreateQueueState:
    """Tests para crear estados de cola"""

    def test_get_or_create_new(
        self,
        db_session: Session,
        sample_service_type: ServiceType
    ):
        """Prueba crear un nuevo estado de cola"""
        queue_state = queue_crud.get_or_create(
            db_session,
            service_type_id=sample_service_type.Id
        )

        assert queue_state is not None
        assert queue_state.ServiceTypeId == sample_service_type.Id
        assert queue_state.StationId is None
        assert queue_state.QueueLength == 0
        assert queue_state.AverageWaitTime == 0
        assert queue_state.CurrentTicketId is None
        assert queue_state.NextTicketId is None

    def test_get_or_create_existing(
        self,
        db_session: Session,
        sample_queue_state: QueueState
    ):
        """Prueba obtener un estado de cola existente"""
        queue_state = queue_crud.get_or_create(
            db_session,
            service_type_id=sample_queue_state.ServiceTypeId,
            station_id=sample_queue_state.StationId
        )

        assert queue_state is not None
        assert queue_state.Id == sample_queue_state.Id
        assert queue_state.QueueLength == 4

    def test_create_with_station(
        self,
        db_session: Session,
        sample_service_type: ServiceType,
        sample_station: Station
    ):
        """Prueba crear estado de cola con estación"""
        queue_state = queue_crud.get_or_create(
            db_session,
            service_type_id=sample_service_type.Id,
            station_id=sample_station.Id
        )

        assert queue_state is not None
        assert queue_state.StationId == sample_station.Id


# ========================================
# TESTS DE LECTURA
# ========================================

class TestReadQueueState:
    """Tests para leer estados de cola"""

    def test_get_by_service_and_station(
        self,
        db_session: Session,
        sample_queue_state: QueueState
    ):
        """Prueba obtener estado por servicio y estación"""
        queue_state = queue_crud.get_by_service_and_station(
            db_session,
            service_type_id=sample_queue_state.ServiceTypeId,
            station_id=sample_queue_state.StationId
        )

        assert queue_state is not None
        assert queue_state.Id == sample_queue_state.Id

    def test_get_by_service_only(
        self,
        db_session: Session,
        sample_service_type: ServiceType
    ):
        """Prueba obtener estado solo por servicio (sin estación)"""
        # Crear estado sin estación
        queue_state_no_station = QueueState(
            ServiceTypeId=sample_service_type.Id,
            StationId=None,
            QueueLength=2,
            AverageWaitTime=10
        )
        db_session.add(queue_state_no_station)
        db_session.commit()

        result = queue_crud.get_by_service_and_station(
            db_session,
            service_type_id=sample_service_type.Id,
            station_id=None
        )

        assert result is not None
        assert result.StationId is None
        assert result.QueueLength == 2

    def test_get_all_active_queues(
        self,
        db_session: Session,
        sample_queue_state: QueueState
    ):
        """Prueba obtener todas las colas activas"""
        queues = queue_crud.get_all_active_queues(
            db_session,
            include_empty=False
        )

        assert len(queues) > 0
        assert any(q.Id == sample_queue_state.Id for q in queues)

    def test_get_all_active_queues_exclude_empty(
        self,
        db_session: Session,
        sample_service_type: ServiceType
    ):
        """Prueba excluir colas vacías"""
        # Crear cola vacía
        empty_queue = QueueState(
            ServiceTypeId=sample_service_type.Id,
            QueueLength=0,
            AverageWaitTime=0
        )
        db_session.add(empty_queue)
        db_session.commit()

        # Obtener solo colas no vacías
        queues = queue_crud.get_all_active_queues(
            db_session,
            include_empty=False
        )

        # La cola vacía no debe estar incluida
        assert not any(q.Id == empty_queue.Id for q in queues)

    def test_get_by_station(
        self,
        db_session: Session,
        sample_queue_state: QueueState,
        sample_station: Station
    ):
        """Prueba obtener colas por estación"""
        queues = queue_crud.get_by_station(
            db_session,
            station_id=sample_station.Id
        )

        assert len(queues) > 0
        assert any(q.Id == sample_queue_state.Id for q in queues)


# ========================================
# TESTS DE ACTUALIZACIÓN
# ========================================

class TestUpdateQueueState:
    """Tests para actualizar estados de cola"""

    def test_update_queue_state(
        self,
        db_session: Session,
        sample_queue_state: QueueState,
        sample_tickets: List[Ticket]
    ):
        """Prueba actualizar estado de cola"""
        updated = queue_crud.update_queue_state(
            db_session,
            queue_id=sample_queue_state.Id,
            queue_length=10,
            current_ticket_id=str(sample_tickets[2].Id),
            average_wait_time=20
        )

        assert updated is not None
        assert updated.QueueLength == 10
        # Comparar ambos como strings
        assert str(updated.CurrentTicketId) == str(sample_tickets[2].Id)
        assert updated.AverageWaitTime == 20

    def test_update_partial(
        self,
        db_session: Session,
        sample_queue_state: QueueState
    ):
        """Prueba actualización parcial"""
        original_current = sample_queue_state.CurrentTicketId

        updated = queue_crud.update_queue_state(
            db_session,
            queue_id=sample_queue_state.Id,
            queue_length=7
        )

        assert updated is not None
        assert updated.QueueLength == 7
        assert updated.CurrentTicketId == original_current  # No cambió

    def test_update_nonexistent(
        self,
        db_session: Session
    ):
        """Prueba actualizar cola inexistente"""
        result = queue_crud.update_queue_state(
            db_session,
            queue_id=99999,
            queue_length=5
        )

        assert result is None


# ========================================
# TESTS DE OPERACIONES DE COLA
# ========================================

class TestQueueOperations:
    """Tests para operaciones de cola"""

    def test_advance_queue(
        self,
        db_session: Session,
        sample_queue_state: QueueState,
        sample_tickets: List[Ticket]
    ):
        """Prueba avanzar la cola"""
        initial_current = sample_queue_state.CurrentTicketId
        initial_next = sample_queue_state.NextTicketId
        initial_length = sample_queue_state.QueueLength

        advanced = queue_crud.advance_queue(
            db_session,
            service_type_id=sample_queue_state.ServiceTypeId,
            station_id=sample_queue_state.StationId
        )

        assert advanced is not None
        assert advanced.CurrentTicketId == initial_next
        assert advanced.QueueLength == initial_length - 1

    def test_reset_queue(
        self,
        db_session: Session,
        sample_queue_state: QueueState
    ):
        """Prueba reiniciar cola"""
        reset = queue_crud.reset_queue(
            db_session,
            service_type_id=sample_queue_state.ServiceTypeId,
            station_id=sample_queue_state.StationId
        )

        assert reset is not None
        assert reset.CurrentTicketId is None
        assert reset.NextTicketId is None
        assert reset.QueueLength == 0
        assert reset.AverageWaitTime == 0

    def test_reset_nonexistent_creates_new(
        self,
        db_session: Session,
        sample_service_type: ServiceType
    ):
        """Prueba que reset crea nueva cola si no existe"""
        reset = queue_crud.reset_queue(
            db_session,
            service_type_id=sample_service_type.Id,
            station_id=None
        )

        assert reset is not None
        assert reset.ServiceTypeId == sample_service_type.Id
        assert reset.QueueLength == 0


# ========================================
# TESTS DE CÁLCULO DE TIEMPOS
# ========================================

class TestWaitTimeCalculation:
    """Tests para cálculo de tiempos de espera"""

    def test_calculate_wait_time_with_tickets(
        self,
        db_session: Session,
        sample_queue_state: QueueState,
        sample_service_type: ServiceType,
        sample_patient: Patient
    ):
        """Prueba calcular tiempo con tickets completados"""
        # Crear tickets completados con tiempos
        for i in range(3):
            ticket = Ticket(
                TicketNumber=f"C{str(i+1).zfill(3)}",
                ServiceTypeId=sample_service_type.Id,
                PatientId=sample_patient.Id,
                Status="Completed",
                Position=i+1,  # Position es requerido y no puede ser NULL
                CreatedAt=datetime.now() - timedelta(minutes=30),
                CalledAt=datetime.now() - timedelta(minutes=20),
                CompletedAt=datetime.now() - timedelta(minutes=5)
            )
            db_session.add(ticket)
        db_session.commit()

        avg_time = queue_crud.calculate_and_update_wait_time(
            db_session,
            queue_state_id=sample_queue_state.Id
        )

        assert avg_time is not None
        assert avg_time > 0

    def test_calculate_wait_time_no_tickets(
        self,
        db_session: Session,
        sample_queue_state: QueueState,
        sample_service_type: ServiceType
    ):
        """Prueba calcular tiempo sin tickets completados"""
        avg_time = queue_crud.calculate_and_update_wait_time(
            db_session,
            queue_state_id=sample_queue_state.Id
        )

        assert avg_time is not None
        assert avg_time == sample_service_type.AverageTimeMinutes


# ========================================
# TESTS DE ESTADÍSTICAS
# ========================================

class TestQueueStatistics:
    """Tests para estadísticas de cola"""

    def test_get_queue_summary(
        self,
        db_session: Session,
        sample_queue_state: QueueState
    ):
        """Prueba obtener resumen de colas"""
        summary = queue_crud.get_queue_summary(db_session)

        assert summary is not None
        assert 'total_queues' in summary
        assert 'active_queues' in summary
        assert 'total_waiting' in summary
        assert 'stations_busy' in summary
        assert 'average_wait_time' in summary

        assert summary['total_queues'] > 0
        assert summary['total_waiting'] >= 0

    def test_get_queue_summary_empty(
        self,
        db_session: Session
    ):
        """Prueba resumen con sistema vacío"""
        # Limpiar todas las colas
        db_session.query(QueueState).delete()
        db_session.commit()

        summary = queue_crud.get_queue_summary(db_session)

        assert summary['total_queues'] == 0
        assert summary['active_queues'] == 0
        assert summary['total_waiting'] == 0


# ========================================
# TESTS DE MANTENIMIENTO
# ========================================

class TestQueueMaintenance:
    """Tests para mantenimiento de colas"""

    def test_refresh_all_states(
        self,
        db_session: Session,
        sample_service_type: ServiceType,
        sample_tickets: List[Ticket]
    ):
        """Prueba refrescar todos los estados"""
        count = queue_crud.refresh_all_states(db_session)

        assert count > 0

        # Verificar que se actualizó el estado
        queue_state = queue_crud.get_by_service_and_station(
            db_session,
            service_type_id=sample_service_type.Id,
            station_id=None
        )

        assert queue_state is not None

    def test_cleanup_stale_states(
        self,
        db_session: Session,
        sample_service_type: ServiceType
    ):
        """Prueba limpiar estados obsoletos"""
        # Crear estado obsoleto
        stale_queue = QueueState(
            ServiceTypeId=sample_service_type.Id,
            QueueLength=0,
            CurrentTicketId=None,
            LastUpdateAt=datetime.now() - timedelta(hours=2)
        )
        db_session.add(stale_queue)
        db_session.commit()

        # Limpiar estados de más de 30 minutos
        cleaned = queue_crud.cleanup_stale_states(
            db_session,
            minutes=30
        )

        assert cleaned > 0

        # Verificar que se eliminó
        result = db_session.query(QueueState).filter(
            QueueState.Id == stale_queue.Id
        ).first()
        assert result is None

    def test_cleanup_keeps_active(
        self,
        db_session: Session,
        sample_queue_state: QueueState
    ):
        """Prueba que cleanup no elimina colas activas"""
        initial_count = db_session.query(QueueState).count()

        cleaned = queue_crud.cleanup_stale_states(
            db_session,
            minutes=30
        )

        # La cola activa no debe ser eliminada
        final_count = db_session.query(QueueState).count()
        assert final_count == initial_count


# ========================================
# TESTS DE ESCENARIOS COMPLEJOS
# ========================================

class TestComplexScenarios:
    """Tests para escenarios complejos"""

    def test_multiple_services_queues(
        self,
        db_session: Session,
        sample_patient: Patient
    ):
        """Prueba manejar múltiples servicios con colas"""
        # Crear múltiples servicios con prioridades válidas (1-5)
        services = []
        for i in range(3):
            service = ServiceType(
                Code=f"SRV{i}",
                Name=f"Servicio {i}",
                TicketPrefix=chr(65 + i),  # A, B, C
                Priority=min(i + 1, 5),  # Asegurar que está entre 1 y 5
                AverageTimeMinutes=10 + i * 5,
                IsActive=True
            )
            db_session.add(service)
            services.append(service)
        db_session.commit()

        # Crear colas para cada servicio
        for service in services:
            queue_state = queue_crud.get_or_create(
                db_session,
                service_type_id=service.Id
            )
            assert queue_state is not None

        # Verificar que todas las colas existen
        all_queues = queue_crud.get_all_active_queues(
            db_session,
            include_empty=True
        )

        assert len(all_queues) >= 3

    def test_concurrent_queue_advance(
        self,
        db_session: Session,
        sample_queue_state: QueueState,
        sample_tickets: List[Ticket]
    ):
        """Prueba avance concurrente de cola"""
        # Simular múltiples avances
        for _ in range(3):
            if sample_queue_state.QueueLength > 0:
                advanced = queue_crud.advance_queue(
                    db_session,
                    service_type_id=sample_queue_state.ServiceTypeId,
                    station_id=sample_queue_state.StationId
                )
                if advanced:
                    sample_queue_state = advanced

        # Verificar que la cola se actualizó correctamente
        assert sample_queue_state.QueueLength <= 1

    def test_queue_state_consistency(
        self,
        db_session: Session,
        sample_service_type: ServiceType,
        sample_patient: Patient
    ):
        """Prueba consistencia del estado de cola"""
        # Crear tickets
        tickets = []
        for i in range(10):
            ticket = Ticket(
                TicketNumber=f"T{str(i+1).zfill(3)}",
                ServiceTypeId=sample_service_type.Id,
                PatientId=sample_patient.Id,
                Status="Waiting",
                Position=i+1  # Position es requerido, no Priority
            )
            db_session.add(ticket)
            tickets.append(ticket)
        db_session.commit()

        # Refrescar estados
        queue_crud.refresh_all_states(db_session)

        # Obtener estado actualizado
        queue_state = queue_crud.get_by_service_and_station(
            db_session,
            service_type_id=sample_service_type.Id,
            station_id=None
        )

        assert queue_state is not None
        assert queue_state.QueueLength == 10

        # Cambiar estado de algunos tickets
        for i in range(3):
            tickets[i].Status = "Completed"
        db_session.commit()

        # Refrescar nuevamente
        queue_crud.refresh_all_states(db_session)

        # Verificar actualización
        queue_state = queue_crud.get_by_service_and_station(
            db_session,
            service_type_id=sample_service_type.Id,
            station_id=None
        )

        assert queue_state.QueueLength == 7


# ========================================
# TESTS DE VALIDACIÓN Y ERRORES
# ========================================

class TestValidationAndErrors:
    """Tests para validación y manejo de errores"""

    def test_invalid_service_type_id(
        self,
        db_session: Session
    ):
        """Prueba con ID de servicio inválido"""
        result = queue_crud.get_by_service_and_station(
            db_session,
            service_type_id=99999,
            station_id=None
        )

        assert result is None

    def test_invalid_queue_id_update(
        self,
        db_session: Session
    ):
        """Prueba actualizar con ID de cola inválido"""
        result = queue_crud.update_queue_state(
            db_session,
            queue_id=99999,
            queue_length=5
        )

        assert result is None

    def test_advance_empty_queue(
        self,
        db_session: Session,
        sample_service_type: ServiceType
    ):
        """Prueba avanzar cola vacía"""
        # Crear cola vacía
        empty_queue = queue_crud.get_or_create(
            db_session,
            service_type_id=sample_service_type.Id
        )

        # Intentar avanzar
        result = queue_crud.advance_queue(
            db_session,
            service_type_id=sample_service_type.Id
        )

        # Si la cola está vacía, advance_queue retorna el estado sin cambios
        assert result is not None
        assert result.QueueLength == 0
        assert result.CurrentTicketId is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])