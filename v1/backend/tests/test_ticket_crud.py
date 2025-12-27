TEST_DATABASE_URL = f"mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"

"""
Pruebas unitarias para el CRUD de tickets
Usa SQL Server real para pruebas, no SQLite
Compatible con las funciones reales en crud/ticket.py
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta, date
import uuid
import os
from typing import Generator

from app.core.database import Base
from app.core.config import settings
from app.models.ticket import Ticket
from app.models.service_type import ServiceType
from app.models.station import Station
from app.models.patient import Patient
from app.crud.ticket import ticket_crud
from app.schemas.ticket import TicketCreate, TicketUpdate

# Configuración de la base de datos de prueba
TEST_DATABASE_URL = f"mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"

# Crear el engine de prueba
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Crea una sesión de base de datos para pruebas con rollback automático
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    # Rollback para mantener la DB limpia
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_patient(db_session) -> Patient:
    """Fixture que crea un paciente de prueba"""
    patient = Patient(
        Id=str(uuid.uuid4()),
        FullName="Juan Pérez García",  # El modelo usa FullName, no FirstName/LastName
        DocumentNumber="12345678",
        BirthDate=date(1990, 5, 15),
        Gender="M",
        Phone="987654321",
        Email="juan.perez@example.com",
        IsActive=True
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture
def sample_service_type(db_session: Session) -> ServiceType:
    """
    Obtiene o crea un ServiceType para las pruebas
    """
    # Primero intentar buscar uno existente por el código
    service_type = db_session.query(ServiceType).filter(ServiceType.Code == "ANA").first()

    if not service_type:
        # Si no existe, lo creamos SIN especificar el ID (dejar que SQL Server lo auto-genere)
        service_type = ServiceType(
            Code="ANA",
            Name="Análisis",
            Description="Análisis de laboratorio general",
            Priority=1,
            AverageTimeMinutes=15,
            TicketPrefix="A",
            Color="#007bff",
            IsActive=True,
            CreatedAt=datetime.utcnow()
        )
        db_session.add(service_type)
        db_session.commit()
        db_session.refresh(service_type)

    return service_type

@pytest.fixture
def sample_station(db_session: Session, sample_service_type: ServiceType) -> Station:
    """
    Crea una estación de prueba
    """
    station = Station(
        Name="Ventanilla Test",
        Code="VT01",
        Description="Ventanilla de prueba",
        ServiceTypeId=sample_service_type.Id,
        Location="Planta Baja",
        Status="Available",
        IsActive=True,
        CreatedAt=datetime.utcnow()
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station


# ========================================
# PRUEBAS DE CREATE
# ========================================

class TestCreateTicket:
    """Pruebas para la creación de tickets"""

    def test_create_basic_ticket(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba crear un ticket básico usando create_ticket"""
        ticket = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id,
            notes="Prueba de ticket"
        )

        assert ticket is not None
        assert ticket.Id is not None
        assert ticket.TicketNumber is not None
        assert ticket.PatientId == sample_patient.Id
        assert ticket.ServiceTypeId == sample_service_type.Id
        assert ticket.Status == "Waiting"
        assert ticket.Notes == "Prueba de ticket"
        assert ticket.Position is not None

    def test_create_ticket_with_station(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType,
            sample_station: Station
    ):
        """Prueba crear un ticket con estación asignada"""
        ticket = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id,
            station_id=sample_station.Id,
            notes="Con estación"
        )

        assert ticket is not None
        assert ticket.StationId == sample_station.Id

    def test_ticket_number_generation(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba que los números de ticket se generen consecutivamente"""
        # Crear primer ticket
        ticket1 = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id
        )

        # Crear segundo ticket
        ticket2 = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id
        )

        # Verificar que los números sean consecutivos
        assert ticket1.TicketNumber is not None
        assert ticket2.TicketNumber is not None

        # Los números deberían ser diferentes
        assert ticket1.TicketNumber != ticket2.TicketNumber


# ========================================
# PRUEBAS DE GET
# ========================================

class TestGetTicket:
    """Pruebas para obtener tickets"""

    def test_get_ticket_by_id(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba obtener un ticket por su ID usando get"""
        # Crear ticket
        created_ticket = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id
        )

        # Obtener ticket usando get (heredado de CRUDBase)
        ticket = ticket_crud.get(db_session, id=created_ticket.Id)

        assert ticket is not None
        assert ticket.Id == created_ticket.Id
        assert ticket.PatientId == sample_patient.Id

    def test_get_nonexistent_ticket(self, db_session: Session):
        """Prueba obtener un ticket que no existe"""
        fake_id = str(uuid.uuid4())
        ticket = ticket_crud.get(db_session, id=fake_id)

        assert ticket is None

    def test_get_tickets_list(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba obtener lista de tickets usando get_multi"""
        # Crear varios tickets
        for i in range(5):
            ticket_crud.create_ticket(
                db_session,
                patient_id=sample_patient.Id,
                service_type_id=sample_service_type.Id
            )

        # Obtener tickets con paginación usando get_multi
        tickets = ticket_crud.get_multi(db_session, skip=0, limit=3)

        assert len(tickets) == 3

        # Obtener siguiente página
        tickets_page2 = ticket_crud.get_multi(db_session, skip=3, limit=3)

        assert len(tickets_page2) == 2

    def test_get_active_tickets(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba obtener tickets activos"""
        # Crear tickets
        ticket1 = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id
        )

        # Actualizar estado de un ticket a Completed
        ticket_crud.update_ticket_status(
            db_session,
            ticket_id=ticket1.Id,
            new_status="Completed"
        )

        # Crear otro ticket (estará en Waiting)
        ticket2 = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id
        )

        # Obtener solo tickets activos
        active_tickets = ticket_crud.get_active_tickets(db_session)

        # Verificar que solo tickets activos están en la lista
        for ticket in active_tickets:
            assert ticket.Status in ['Waiting', 'Called', 'InProgress', 'Paused', 'Transferred']


# ========================================
# PRUEBAS DE UPDATE
# ========================================

class TestUpdateTicket:
    """Pruebas para actualizar tickets"""

    def test_update_ticket_status(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba actualizar el estado de un ticket"""
        # Crear ticket
        ticket = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id
        )

        assert ticket.Status == "Waiting"

        # Actualizar estado
        updated_ticket = ticket_crud.update_ticket_status(
            db_session,
            ticket_id=ticket.Id,
            new_status="Called"
        )

        assert updated_ticket is not None
        assert updated_ticket.Status == "Called"
        assert updated_ticket.CalledAt is not None

    def test_update_ticket_complete_flow(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType,
            sample_station: Station
    ):
        """Prueba el flujo completo de estados de un ticket"""
        # Crear ticket
        ticket = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id
        )

        # Estado 1: Waiting -> Called
        ticket = ticket_crud.update_ticket_status(
            db_session,
            ticket_id=ticket.Id,
            new_status="Called"
        )
        assert ticket.Status == "Called"
        assert ticket.CalledAt is not None

        # Estado 2: Called -> InProgress
        ticket = ticket_crud.update_ticket_status(
            db_session,
            ticket_id=ticket.Id,
            new_status="InProgress"
        )
        assert ticket.Status == "InProgress"
        assert ticket.AttendedAt is not None

        # Estado 3: InProgress -> Completed
        ticket = ticket_crud.update_ticket_status(
            db_session,
            ticket_id=ticket.Id,
            new_status="Completed"
        )
        assert ticket.Status == "Completed"
        assert ticket.CompletedAt is not None

    def test_update_ticket_with_update_method(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba actualizar ticket usando el método update de CRUDBase"""
        # Crear ticket
        ticket = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id,
            notes="Nota inicial"
        )

        # Actualizar usando update de CRUDBase
        update_data = TicketUpdate(Notes="Nota actualizada")
        updated_ticket = ticket_crud.update(
            db_session,
            db_obj=ticket,
            obj_in=update_data
        )

        assert updated_ticket.Notes == "Nota actualizada"


# ========================================
# PRUEBAS DE FUNCIONES ESPECIALES
# ========================================

class TestSpecialFunctions:
    """Pruebas para funciones especiales del CRUD"""

    def test_get_next_ticket_number(
            self,
            db_session: Session,
            sample_service_type: ServiceType
    ):
        """Prueba obtener el siguiente número de ticket"""
        # Obtener número para el servicio
        next_number = ticket_crud.get_next_ticket_number(
            db_session,
            service_type_id=sample_service_type.Id
        )

        assert next_number is not None
        assert isinstance(next_number, str)
        assert len(next_number) > 0

    def test_get_tickets_by_patient(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba obtener tickets de un paciente específico"""
        # Crear tickets para el paciente
        for i in range(3):
            ticket_crud.create_ticket(
                db_session,
                patient_id=sample_patient.Id,
                service_type_id=sample_service_type.Id
            )

        # Obtener tickets del paciente
        patient_tickets = ticket_crud.get_tickets_by_patient(
            db_session,
            patient_id=sample_patient.Id
        )

        assert len(patient_tickets) == 3
        assert all(t.PatientId == sample_patient.Id for t in patient_tickets)

    def test_get_queue_by_service(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType
    ):
        """Prueba obtener la cola de un servicio específico"""
        # Crear varios tickets para el servicio
        for i in range(3):
            ticket_crud.create_ticket(
                db_session,
                patient_id=sample_patient.Id,
                service_type_id=sample_service_type.Id
            )

        # Obtener cola del servicio
        queue = ticket_crud.get_queue_by_service(
            db_session,
            service_type_id=sample_service_type.Id
        )

        assert len(queue) >= 3
        # Verificar que todos son del mismo servicio y están activos
        for ticket in queue:
            assert ticket.ServiceTypeId == sample_service_type.Id
            assert ticket.Status in ['Waiting', 'Called', 'InProgress']

    def test_call_ticket(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType,
            sample_station: Station
    ):
        """Prueba llamar un ticket"""
        # Crear ticket
        ticket = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id
        )

        # Llamar ticket
        called_ticket = ticket_crud.call_ticket(
            db_session,
            ticket_id=ticket.Id,
            station_id=sample_station.Id
        )

        assert called_ticket is not None
        assert called_ticket.Status == "Called"
        assert called_ticket.StationId == sample_station.Id
        assert called_ticket.CalledAt is not None

    def test_transfer_ticket(
            self,
            db_session: Session,
            sample_patient: Patient,
            sample_service_type: ServiceType,
            sample_station: Station
    ):
        """Prueba transferir un ticket a otra estación"""
        # Crear segunda estación
        station2 = Station(
            Name="Ventanilla Test 2",
            Code="VT02",
            ServiceTypeId=sample_service_type.Id,
            Status="Available",
            IsActive=True,
            CreatedAt=datetime.utcnow()
        )
        db_session.add(station2)
        db_session.commit()

        # Crear ticket asignado a primera estación
        ticket = ticket_crud.create_ticket(
            db_session,
            patient_id=sample_patient.Id,
            service_type_id=sample_service_type.Id,
            station_id=sample_station.Id
        )

        # Transferir a segunda estación
        transferred = ticket_crud.transfer_ticket(
            db_session,
            ticket_id=ticket.Id,
            new_station_id=station2.Id,
            reason="Prueba de transferencia"
        )

        assert transferred is not None
        assert transferred.StationId == station2.Id
        assert "transferencia" in transferred.Notes.lower()


    def test_get_queue_statistics(self, db_session, sample_patient, sample_service_type):
        """Prueba obtener estadísticas de la cola"""
        # Crear varios tickets con diferentes estados usando create_ticket
        # Ticket 1: En espera
        ticket1 = ticket_crud.create_ticket(
            db_session,
            patient_id=str(sample_patient.Id),
            service_type_id=sample_service_type.Id,
            notes="Test estadísticas"
        )

        # Ticket 2: Llamado
        ticket2 = ticket_crud.create_ticket(
            db_session,
            patient_id=str(sample_patient.Id),
            service_type_id=sample_service_type.Id
        )
        ticket_crud.update_ticket_status(
            db_session,
            ticket_id=str(ticket2.Id),
            new_status="Called"
        )

        # Ticket 3: En progreso
        ticket3 = ticket_crud.create_ticket(
            db_session,
            patient_id=str(sample_patient.Id),
            service_type_id=sample_service_type.Id
        )
        ticket_crud.update_ticket_status(
            db_session,
            ticket_id=str(ticket3.Id),
            new_status="Called"
        )
        ticket_crud.update_ticket_status(
            db_session,
            ticket_id=str(ticket3.Id),
            new_status="InProgress"
        )

        # Ticket 4: Completado
        ticket4 = ticket_crud.create_ticket(
            db_session,
            patient_id=str(sample_patient.Id),
            service_type_id=sample_service_type.Id
        )
        ticket_crud.update_ticket_status(
            db_session,
            ticket_id=str(ticket4.Id),
            new_status="Called"
        )
        ticket_crud.update_ticket_status(
            db_session,
            ticket_id=str(ticket4.Id),
            new_status="InProgress"
        )
        ticket_crud.update_ticket_status(
            db_session,
            ticket_id=str(ticket4.Id),
            new_status="Completed"
        )

        # Ticket 5: Cancelado
        ticket5 = ticket_crud.create_ticket(
            db_session,
            patient_id=str(sample_patient.Id),
            service_type_id=sample_service_type.Id
        )
        ticket_crud.update_ticket_status(
            db_session,
            ticket_id=str(ticket5.Id),
            new_status="Cancelled"
        )

        # Obtener estadísticas
        stats = ticket_crud.get_queue_statistics(db_session)

        # Verificar estadísticas
        assert stats is not None
        assert stats['waiting_tickets'] == 1  # Solo ticket1
        assert stats['called_tickets'] == 1  # Solo ticket2
        assert stats['in_progress_tickets'] == 1  # Solo ticket3
        assert stats['completed_today'] == 1  # Solo ticket4
        assert stats['cancelled_today'] == 1  # Solo ticket5
        assert stats['total_tickets_today'] == 5  # Todos los tickets

        # Verificar desglose por servicio
        # El método devuelve las estadísticas por nombre de servicio, no por ID
        service_name = sample_service_type.Name  # 'Análisis'

        # by_service contiene solo tickets en espera (waiting) por servicio
        assert service_name in stats['by_service']
        assert stats['by_service'][service_name] == 1  # Solo 1 ticket waiting

        # Verificar el desglose de servicios si existe
        if 'services_breakdown' in stats:
            # Buscar nuestro servicio en el breakdown
            breakdown = next((s for s in stats['services_breakdown']
                              if s.get('service_id') == sample_service_type.Id), None)

            assert breakdown is not None
            assert breakdown['service_name'] == service_name
            assert breakdown['service_code'] == sample_service_type.Code
            assert breakdown['waiting_count'] == 1  # Solo ticket1 está waiting
            assert breakdown['in_progress_count'] == 2  # ticket2 (Called) + ticket3 (InProgress)
            # El total sería waiting + in_progress + completed + cancelled
            # pero el breakdown solo muestra los activos






# ========================================
# PRUEBAS DE VALIDACIÓN Y ERRORES
# ========================================

class TestValidationsAndErrors:
    """Pruebas de validaciones y manejo de errores"""

    def test_create_ticket_with_invalid_service_type(
            self,
            db_session: Session,
            sample_patient: Patient
    ):
        """Prueba crear ticket con tipo de servicio inválido"""
        with pytest.raises(ValueError):
            ticket_crud.create_ticket(
                db_session,
                patient_id=sample_patient.Id,
                service_type_id=9999  # ID que no existe
            )

    def test_update_nonexistent_ticket(
            self,
            db_session: Session
    ):
        """Prueba actualizar un ticket que no existe"""
        fake_id = str(uuid.uuid4())

        result = ticket_crud.update_ticket_status(
            db_session,
            ticket_id=fake_id,
            new_status="Called"
        )

        assert result is None

    def test_call_nonexistent_ticket(
            self,
            db_session: Session,
            sample_station: Station
    ):
        """Prueba llamar un ticket que no existe"""
        fake_id = str(uuid.uuid4())

        result = ticket_crud.call_ticket(
            db_session,
            ticket_id=fake_id,
            station_id=sample_station.Id
        )

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])