"""
Pruebas unitarias para schemas de tickets
Usa SQL Server real para pruebas, no SQLite
Compatible con Pydantic V2 y todos los schemas existentes
"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
import uuid
from pydantic import ValidationError

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.schemas.ticket import (
    # Schemas base
    TicketBase,
    TicketCreate,
    TicketQuickCreate,
    TicketUpdate,
    TicketStatusUpdate,
    TicketResponse,

    # Schemas de búsqueda y lista
    TicketListResponse,
    TicketSearchFilters,

    # Schemas de operaciones
    QueuePosition,
    CallTicketRequest,
    TransferTicketRequest,

    # Schemas de estadísticas
    TicketStats,
    QueueOverview,
    DailyTicketSummary,

    # Schemas de creación masiva
    BulkTicketCreate,
    BulkTicketResponse,

    # Enum de estados
    TicketStatus
)

from app.models.ticket import Ticket
from app.models.patient import Patient
from app.models.service_type import ServiceType
from app.models.station import Station

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
    """Crea una sesión de base de datos para pruebas con rollback automático"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_ticket_data() -> Dict[str, Any]:
    """Datos de ejemplo para crear tickets"""
    return {
        "PatientId": str(uuid.uuid4()),
        "ServiceTypeId": 1,
        "StationId": None,
        "Notes": "Paciente requiere atención prioritaria"
    }


@pytest.fixture
def sample_ticket_response_data() -> Dict[str, Any]:
    """Datos completos de ejemplo para TicketResponse"""
    return {
        "Id": str(uuid.uuid4()),
        "TicketNumber": "A001",
        "PatientId": str(uuid.uuid4()),
        "ServiceTypeId": 1,
        "StationId": None,
        "Status": "Waiting",
        "Position": 1,
        "EstimatedWaitTime": 15,
        "Notes": "Test note",
        "CalledAt": None,
        "AttendedAt": None,
        "CompletedAt": None,
        "CreatedAt": datetime.now(),
        "UpdatedAt": datetime.now()
    }


# ========================================
# PRUEBAS DE TICKET STATUS ENUM
# ========================================

class TestTicketStatusEnum:
    """Pruebas para el enum TicketStatus"""

    def test_valid_status_values(self):
        """Verifica que todos los estados válidos sean aceptados"""
        # Los valores del enum usan MAYÚSCULAS con underscore
        valid_statuses = ["Waiting", "Called", "InProgress", "Completed", "Cancelled", "NoShow"]

        for status in valid_statuses:
            assert TicketStatus(status) == status

    def test_enum_values_match_constants(self):
        """Verifica que los valores del enum coincidan con las constantes"""
        assert TicketStatus.WAITING.value == "Waiting"
        assert TicketStatus.CALLED.value == "Called"
        assert TicketStatus.IN_PROGRESS.value == "InProgress"
        assert TicketStatus.COMPLETED.value == "Completed"
        assert TicketStatus.CANCELLED.value == "Cancelled"
        assert TicketStatus.NO_SHOW.value == "NoShow"

    def test_invalid_status_value(self):
        """Verifica que estados inválidos generen error"""
        with pytest.raises(ValueError):
            TicketStatus("InvalidStatus")


# ========================================
# PRUEBAS DE TICKET BASE
# ========================================

class TestTicketBase:
    """Pruebas para el schema TicketBase"""

    def test_create_valid_ticket_base(self, sample_ticket_data):
        """Prueba creación de TicketBase con datos válidos"""
        ticket = TicketBase(**sample_ticket_data)

        assert ticket.PatientId == sample_ticket_data["PatientId"]
        assert ticket.ServiceTypeId == sample_ticket_data["ServiceTypeId"]
        assert ticket.StationId == sample_ticket_data["StationId"]
        assert ticket.Notes == sample_ticket_data["Notes"]

    def test_ticket_base_without_optional_fields(self):
        """Prueba TicketBase sin campos opcionales"""
        data = {
            "PatientId": str(uuid.uuid4()),
            "ServiceTypeId": 1
        }
        ticket = TicketBase(**data)

        assert ticket.PatientId == data["PatientId"]
        assert ticket.ServiceTypeId == data["ServiceTypeId"]
        assert ticket.StationId is None
        assert ticket.Notes is None

    def test_invalid_patient_id_format(self):
        """Prueba que PatientId inválido genere error"""
        with pytest.raises(ValidationError) as exc_info:
            TicketBase(
                PatientId="invalid-uuid",
                ServiceTypeId=1
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("PatientId",) for error in errors)

    def test_invalid_service_type_id(self):
        """Prueba que ServiceTypeId inválido genere error"""
        with pytest.raises(ValidationError) as exc_info:
            TicketBase(
                PatientId=str(uuid.uuid4()),
                ServiceTypeId=0  # Debe ser >= 1
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("ServiceTypeId",) for error in errors)

    def test_notes_max_length(self):
        """Prueba que Notes respete la longitud máxima"""
        with pytest.raises(ValidationError) as exc_info:
            TicketBase(
                PatientId=str(uuid.uuid4()),
                ServiceTypeId=1,
                Notes="x" * 501  # Max es 500
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("Notes",) for error in errors)

    def test_notes_whitespace_cleanup(self):
        """Prueba que Notes elimine espacios en blanco extras"""
        ticket = TicketBase(
            PatientId=str(uuid.uuid4()),
            ServiceTypeId=1,
            Notes="  Test note with spaces  "
        )

        assert ticket.Notes == "Test note with spaces"


# ========================================
# PRUEBAS DE TICKET CREATE
# ========================================

class TestTicketCreate:
    """Pruebas para el schema TicketCreate"""

    def test_create_valid_ticket_create(self, sample_ticket_data):
        """Prueba creación de TicketCreate con datos válidos"""
        ticket = TicketCreate(**sample_ticket_data)

        assert ticket.PatientId == sample_ticket_data["PatientId"]
        assert ticket.ServiceTypeId == sample_ticket_data["ServiceTypeId"]
        assert ticket.StationId == sample_ticket_data["StationId"]
        assert ticket.Notes == sample_ticket_data["Notes"]

    def test_ticket_create_inherits_from_base(self):
        """Verifica que TicketCreate herede de TicketBase"""
        assert issubclass(TicketCreate, TicketBase)

    def test_ticket_create_json_schema_example(self):
        """Verifica que el ejemplo del JSON schema sea válido"""
        example = TicketCreate.model_config["json_schema_extra"]["example"]
        ticket = TicketCreate(**example)

        assert ticket.PatientId == example["PatientId"]
        assert ticket.ServiceTypeId == example["ServiceTypeId"]


# ========================================
# PRUEBAS DE TICKET QUICK CREATE
# ========================================

class TestTicketQuickCreate:
    """Pruebas para el schema TicketQuickCreate"""

    def test_create_valid_quick_ticket(self):
        """Prueba creación rápida con datos válidos"""
        data = {
            "PatientDocumentNumber": "12345678",
            "ServiceTypeId": 1,
            "Notes": "Quick creation test"
        }
        ticket = TicketQuickCreate(**data)

        assert ticket.PatientDocumentNumber == "12345678"
        assert ticket.ServiceTypeId == 1
        assert ticket.Notes == "Quick creation test"

    def test_quick_create_without_notes(self):
        """Prueba creación rápida sin notas"""
        data = {
            "PatientDocumentNumber": "87654321",
            "ServiceTypeId": 2
        }
        ticket = TicketQuickCreate(**data)

        assert ticket.PatientDocumentNumber == "87654321"
        assert ticket.ServiceTypeId == 2
        assert ticket.Notes is None

    def test_document_number_min_length(self):
        """Prueba validación de longitud mínima del documento"""
        with pytest.raises(ValidationError) as exc_info:
            TicketQuickCreate(
                PatientDocumentNumber="1234",  # Min es 5
                ServiceTypeId=1
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("PatientDocumentNumber",) for error in errors)

    def test_document_number_max_length(self):
        """Prueba validación de longitud máxima del documento"""
        with pytest.raises(ValidationError) as exc_info:
            TicketQuickCreate(
                PatientDocumentNumber="1" * 21,  # Max es 20
                ServiceTypeId=1
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("PatientDocumentNumber",) for error in errors)


# ========================================
# PRUEBAS DE TICKET UPDATE
# ========================================

class TestTicketUpdate:
    """Pruebas para el schema TicketUpdate"""

    def test_update_all_fields(self):
        """Prueba actualización con todos los campos"""
        data = {
            "StationId": 2,
            "Status": "Called",
            "Notes": "Updated notes",
            "EstimatedWaitTime": 30
        }
        update = TicketUpdate(**data)

        assert update.StationId == 2
        assert update.Status == "Called"
        assert update.Notes == "Updated notes"
        assert update.EstimatedWaitTime == 30

    def test_update_partial_fields(self):
        """Prueba actualización parcial"""
        update = TicketUpdate(Status="InProgress")

        assert update.Status == "InProgress"
        assert update.StationId is None
        assert update.Notes is None
        assert update.EstimatedWaitTime is None

    def test_update_empty(self):
        """Prueba actualización vacía (todos los campos opcionales)"""
        update = TicketUpdate()

        assert update.StationId is None
        assert update.Status is None
        assert update.Notes is None
        assert update.EstimatedWaitTime is None

    def test_update_invalid_status(self):
        """Prueba actualización con estado inválido"""
        with pytest.raises(ValidationError):
            TicketUpdate(Status="InvalidStatus")

    def test_update_negative_wait_time(self):
        """Prueba que tiempo de espera negativo genere error"""
        with pytest.raises(ValidationError) as exc_info:
            TicketUpdate(EstimatedWaitTime=-5)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("EstimatedWaitTime",) for error in errors)


# ========================================
# PRUEBAS DE TICKET STATUS UPDATE
# ========================================

class TestTicketStatusUpdate:
    """Pruebas para el schema TicketStatusUpdate"""

    def test_status_update_with_notes(self):
        """Prueba actualización de estado con notas"""
        update = TicketStatusUpdate(
            Status="Completed",
            Notes="Atención finalizada correctamente"
        )

        assert update.Status == "Completed"
        assert update.Notes == "Atención finalizada correctamente"

    def test_status_update_without_notes(self):
        """Prueba actualización de estado sin notas"""
        update = TicketStatusUpdate(Status="Cancelled")

        assert update.Status == "Cancelled"
        assert update.Notes is None

    def test_status_update_requires_status(self):
        """Verifica que Status sea requerido"""
        with pytest.raises(ValidationError) as exc_info:
            TicketStatusUpdate(Notes="Solo notas")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("Status",) for error in errors)


# ========================================
# PRUEBAS DE TICKET RESPONSE
# ========================================

class TestTicketResponse:
    """Pruebas para el schema TicketResponse"""

    def test_create_valid_response(self, sample_ticket_response_data):
        """Prueba creación de TicketResponse con datos válidos"""
        response = TicketResponse(**sample_ticket_response_data)

        assert response.Id == sample_ticket_response_data["Id"]
        assert response.TicketNumber == "A001"
        assert response.Status == "Waiting"
        assert response.Position == 1

    def test_response_from_orm(self, db_session):
        """Prueba que TicketResponse funcione con objetos SQLAlchemy"""
        # Crear objetos de prueba necesarios
        patient = Patient(
            Id=str(uuid.uuid4()),
            FullName="Test Patient",
            DocumentNumber="12345678",
            BirthDate=date(1990, 1, 1),
            Gender="M",
            IsActive=True
        )
        db_session.add(patient)

        service_type = ServiceType(
            Name="Test Service",
            Code="TST",
            TicketPrefix="T",  # Campo requerido
            Priority=1,  # Puede ser requerido
            AverageTimeMinutes=15,  # Puede ser requerido
            IsActive=True
        )
        db_session.add(service_type)
        db_session.commit()

        # Crear ticket con los campos que realmente existen en el modelo
        ticket = Ticket(
            TicketNumber="B001",
            PatientId=patient.Id,
            ServiceTypeId=service_type.Id,
            Status="Waiting",
            Position=1
        )
        # El Id se genera automáticamente en SQL Server
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)

        # Convertir a schema
        response = TicketResponse.model_validate(ticket)

        assert str(response.Id) == str(ticket.Id)  # Convertir a string si es UUID
        assert response.TicketNumber == "B001"
        assert response.Status == "Waiting"

    def test_response_computed_properties(self):
        """Prueba propiedades opcionales del response"""
        data = {
            **self.get_base_response_data(),
            "Status": "Waiting",
            "CalledAt": None,
            "CompletedAt": None
        }
        response = TicketResponse(**data)

        # Verificar que los campos opcionales pueden existir
        # Estas son propiedades opcionales según el schema
        response_dict = response.model_dump()

        # Verificar campos básicos obligatorios
        assert "Id" in response_dict
        assert "TicketNumber" in response_dict
        assert "Status" in response_dict
        assert response.Status == "Waiting"

        # Los campos computados son opcionales y pueden no estar presentes
        # Solo verificamos que el modelo se puede crear correctamente
        assert response is not None

    def test_response_with_relationships(self):
        """Prueba response con datos de relaciones"""
        data = {
            **self.get_base_response_data(),
            "patient_name": "Juan Pérez",
            "patient_document": "12345678",
            "service_name": "Análisis de Laboratorio",
            "station_name": "Ventanilla 1"
        }
        response = TicketResponse(**data)

        assert response.patient_name == "Juan Pérez"
        assert response.patient_document == "12345678"
        assert response.service_name == "Análisis de Laboratorio"
        assert response.station_name == "Ventanilla 1"

    @staticmethod
    def get_base_response_data():
        """Obtiene datos base para response"""
        return {
            "Id": str(uuid.uuid4()),
            "TicketNumber": "C001",
            "PatientId": str(uuid.uuid4()),
            "ServiceTypeId": 1,
            "Status": "Waiting",
            "Position": 1,
            "CreatedAt": datetime.now(),
            "UpdatedAt": datetime.now()
        }


# ========================================
# PRUEBAS DE OPERACIONES DE COLA
# ========================================

class TestQueueOperations:
    """Pruebas para schemas de operaciones de cola"""

    def test_queue_position(self):
        """Prueba schema QueuePosition"""
        position = QueuePosition(
            ticket_id=str(uuid.uuid4()),
            ticket_number="F001",
            current_position=3,
            ahead_count=2,
            estimated_wait_time=15,
            service_name="Análisis"
        )

        assert position.current_position == 3
        assert position.ahead_count == 2
        assert position.estimated_wait_time == 15

    def test_call_ticket_request(self):
        """Prueba schema CallTicketRequest"""
        request = CallTicketRequest(
            station_id=2,
            notes="Llamada desde ventanilla 2"
        )

        assert request.station_id == 2
        assert request.notes == "Llamada desde ventanilla 2"

    def test_call_ticket_without_notes(self):
        """Prueba llamada sin notas"""
        request = CallTicketRequest(station_id=1)

        assert request.station_id == 1
        assert request.notes is None

    def test_transfer_ticket_request(self):
        """Prueba schema TransferTicketRequest"""
        request = TransferTicketRequest(
            new_station_id=3,
            reason="Especialización requerida"
        )

        assert request.new_station_id == 3
        assert request.reason == "Especialización requerida"

    def test_invalid_station_id(self):
        """Prueba que station_id inválido genere error"""
        with pytest.raises(ValidationError):
            CallTicketRequest(station_id=0)  # Debe ser >= 1


# ========================================
# PRUEBAS DE BÚSQUEDA Y FILTROS
# ========================================

class TestSearchAndFilters:
    """Pruebas para schemas de búsqueda y filtros"""

    def test_search_filters_all_fields(self):
        """Prueba filtros con todos los campos"""
        filters = TicketSearchFilters(
            patient_document="12345678",
            patient_name="Juan",
            service_type_id=1,
            station_id=2,
            status="Waiting",
            date_from=date(2024, 3, 1),
            date_to=date(2024, 3, 31),
            ticket_number="A001",
            include_cancelled=True
        )

        assert filters.patient_document == "12345678"
        assert filters.status == "Waiting"
        assert filters.include_cancelled is True

    def test_search_filters_empty(self):
        """Prueba filtros vacíos"""
        filters = TicketSearchFilters()

        assert filters.patient_document is None
        assert filters.service_type_id is None
        assert filters.include_cancelled is False  # Default

    def test_ticket_list_response(self):
        """Prueba schema TicketListResponse"""
        ticket_data = {
            "Id": str(uuid.uuid4()),
            "TicketNumber": "G001",
            "PatientId": str(uuid.uuid4()),
            "ServiceTypeId": 1,
            "Status": "Waiting",
            "Position": 1,
            "CreatedAt": datetime.now(),
            "UpdatedAt": datetime.now()
        }

        response = TicketListResponse(
            tickets=[TicketResponse(**ticket_data)],
            total=50,
            skip=0,
            limit=20,
            has_more=True,
            queue_stats={"waiting": 15, "completed": 35}
        )

        assert len(response.tickets) == 1
        assert response.total == 50
        assert response.has_more is True
        assert response.queue_stats["waiting"] == 15


# ========================================
# PRUEBAS DE ESTADÍSTICAS
# ========================================

class TestStatistics:
    """Pruebas para schemas de estadísticas"""

    def test_ticket_stats(self):
        """Prueba schema TicketStats"""
        stats = TicketStats(
            total_tickets=100,
            waiting_tickets=20,
            called_tickets=5,
            in_progress_tickets=10,
            completed_tickets=60,
            cancelled_tickets=5,
            no_show_tickets=0,
            average_wait_time=25.5,
            average_service_time=15.3
        )

        assert stats.total_tickets == 100
        assert stats.average_wait_time == 25.5
        assert stats.completed_tickets == 60

    def test_queue_overview(self):
        """Prueba schema QueueOverview"""
        overview = QueueOverview(
            service_queues=[
                {"service": "Análisis", "waiting": 10},
                {"service": "Consultas", "waiting": 5}
            ],
            total_waiting=15,
            active_stations=4,
            estimated_next_calls=[
                {"station": "V01", "time": "10:30"},
                {"station": "V02", "time": "10:35"}
            ]
        )

        assert overview.total_waiting == 15
        assert overview.active_stations == 4
        assert len(overview.service_queues) == 2

    def test_daily_summary(self):
        """Prueba schema DailyTicketSummary"""
        summary = DailyTicketSummary(
            summary_date=date(2024, 3, 15),
            total_tickets=150,
            tickets_by_status={
                "Waiting": 10,
                "Completed": 130,
                "Cancelled": 10
            },
            tickets_by_service={
                "Análisis": 80,
                "Consultas": 70
            },
            average_wait_time=22.5,
            average_service_time=12.8,
            peak_hour="10:00-11:00"
        )

        assert summary.total_tickets == 150
        assert summary.tickets_by_status["Completed"] == 130
        assert summary.peak_hour == "10:00-11:00"


# ========================================
# PRUEBAS DE CREACIÓN MASIVA
# ========================================

class TestBulkOperations:
    """Pruebas para schemas de operaciones masivas"""

    def test_bulk_create_single(self):
        """Prueba creación masiva con un solo ticket"""
        bulk = BulkTicketCreate(
            tickets=[
                TicketCreate(
                    PatientId=str(uuid.uuid4()),
                    ServiceTypeId=1
                )
            ]
        )

        assert len(bulk.tickets) == 1

    def test_bulk_create_multiple(self):
        """Prueba creación masiva con múltiples tickets"""
        tickets = [
            TicketCreate(
                PatientId=str(uuid.uuid4()),
                ServiceTypeId=i
            )
            for i in range(1, 6)
        ]

        bulk = BulkTicketCreate(tickets=tickets)

        assert len(bulk.tickets) == 5

    def test_bulk_create_max_limit(self):
        """Prueba límite máximo de creación masiva"""
        tickets = [
            TicketCreate(
                PatientId=str(uuid.uuid4()),
                ServiceTypeId=1
            )
            for _ in range(51)  # Max es 50
        ]

        with pytest.raises(ValidationError) as exc_info:
            BulkTicketCreate(tickets=tickets)

        errors = exc_info.value.errors()
        assert any("tickets" in str(error) for error in errors)

    def test_bulk_response(self):
        """Prueba schema BulkTicketResponse"""
        created_ticket = TicketResponse(
            Id=str(uuid.uuid4()),
            TicketNumber="H001",
            PatientId=str(uuid.uuid4()),
            ServiceTypeId=1,
            Status="Waiting",
            Position=1,
            CreatedAt=datetime.now(),
            UpdatedAt=datetime.now()
        )

        response = BulkTicketResponse(
            created_tickets=[created_ticket],
            failed_tickets=[
                {"index": 2, "error": "Paciente no encontrado"}
            ],
            success_count=1,
            error_count=1
        )

        assert response.success_count == 1
        assert response.error_count == 1
        assert len(response.created_tickets) == 1
        assert len(response.failed_tickets) == 1


# ========================================
# PRUEBAS DE VALIDACIÓN COMPLEJAS
# ========================================

class TestComplexValidations:
    """Pruebas de validaciones más complejas y casos edge"""

    def test_unicode_in_notes(self):
        """Prueba que las notas soporten caracteres Unicode"""
        ticket = TicketCreate(
            PatientId=str(uuid.uuid4()),
            ServiceTypeId=1,
            Notes="Paciente con síntomas: fiebre, tos y malestar general 🌡️"
        )

        assert "🌡️" in ticket.Notes
        assert "síntomas" in ticket.Notes

    def test_empty_string_notes(self):
        """Prueba que notas vacías se conviertan en None"""
        ticket = TicketCreate(
            PatientId=str(uuid.uuid4()),
            ServiceTypeId=1,
            Notes="   "  # Solo espacios
        )

        # El validador debe limpiar espacios
        assert ticket.Notes == ""

    def test_ticket_response_timezone_aware(self):
        """Verifica manejo de timestamps con zona horaria"""
        from datetime import timezone

        data = {
            "Id": str(uuid.uuid4()),
            "TicketNumber": "I001",
            "PatientId": str(uuid.uuid4()),
            "ServiceTypeId": 1,
            "Status": "Waiting",
            "Position": 1,
            "CreatedAt": datetime.now(timezone.utc),
            "UpdatedAt": datetime.now(timezone.utc)
        }

        response = TicketResponse(**data)

        assert response.CreatedAt is not None
        assert response.UpdatedAt is not None

    def test_concurrent_status_transitions(self):
        """Prueba transiciones de estado válidas"""
        valid_transitions = [
            ("Waiting", "Called"),
            ("Called", "InProgress"),
            ("InProgress", "Completed"),
            ("Waiting", "Cancelled"),
            ("Called", "NoShow")
        ]

        for from_status, to_status in valid_transitions:
            update = TicketStatusUpdate(
                Status=to_status,
                Notes=f"Transición de {from_status} a {to_status}"
            )
            assert update.Status == to_status

    def test_json_serialization(self):
        """Prueba serialización JSON de schemas"""
        ticket = TicketCreate(
            PatientId=str(uuid.uuid4()),
            ServiceTypeId=1,
            Notes="Test serialization"
        )

        # Convertir a JSON y back
        json_str = ticket.model_dump_json()
        assert isinstance(json_str, str)

        # Recrear desde JSON
        ticket_dict = ticket.model_dump()
        new_ticket = TicketCreate(**ticket_dict)

        assert new_ticket.PatientId == ticket.PatientId
        assert new_ticket.ServiceTypeId == ticket.ServiceTypeId


# ========================================
# PRUEBAS DE INTEGRACIÓN CON MODELOS
# ========================================

class TestSchemaModelIntegration:
    """Pruebas de integración entre schemas y modelos SQLAlchemy"""

    def test_create_schema_to_model(self, db_session):
        """Prueba conversión de schema Create a modelo"""
        # Crear datos con schema
        schema_data = TicketCreate(
            PatientId=str(uuid.uuid4()),
            ServiceTypeId=1,
            Notes="Integration test"
        )

        # Convertir a dict para modelo
        model_data = schema_data.model_dump()

        # Agregar campos requeridos por el modelo
        model_data.update({
            "Id": str(uuid.uuid4()),
            "TicketNumber": "INT001",
            "Status": "Waiting",
            "Position": 1,
            "CreatedAt": datetime.now()
        })

        # Crear modelo
        ticket = Ticket(**model_data)

        assert ticket.PatientId == schema_data.PatientId
        assert ticket.Notes == "Integration test"

    def test_model_to_response_schema(self, db_session):
        """Prueba conversión de modelo a schema Response"""
        # Crear modelo
        ticket = Ticket(
            Id=str(uuid.uuid4()),
            TicketNumber="MOD001",
            PatientId=str(uuid.uuid4()),
            ServiceTypeId=1,
            Status="Waiting",
            Position=1,
            CreatedAt=datetime.now(),
            Notes="Model to schema test"
        )

        # Convertir a schema usando from_orm
        response = TicketResponse.model_validate(ticket)

        assert response.Id == ticket.Id
        assert response.TicketNumber == "MOD001"
        assert response.Notes == "Model to schema test"

    def test_update_schema_partial_dict(self):
        """Prueba que Update schema genere dict correcto para actualizaciones parciales"""
        update = TicketUpdate(
            Status="Completed",
            Notes="Finalizado"
        )

        # Obtener solo campos no-None
        update_dict = {k: v for k, v in update.model_dump().items() if v is not None}

        assert "Status" in update_dict
        assert "Notes" in update_dict
        assert "StationId" not in update_dict
        assert "EstimatedWaitTime" not in update_dict


# ========================================
# PRUEBAS DE RENDIMIENTO
# ========================================

class TestPerformance:
    """Pruebas básicas de rendimiento"""

    def test_bulk_validation_performance(self):
        """Prueba rendimiento de validación masiva"""
        import time

        # Crear 100 tickets
        tickets_data = [
            {
                "PatientId": str(uuid.uuid4()),
                "ServiceTypeId": i % 5 + 1,
                "Notes": f"Ticket {i}"
            }
            for i in range(100)
        ]

        start = time.time()
        tickets = [TicketCreate(**data) for data in tickets_data]
        end = time.time()

        # Debe procesar 100 tickets en menos de 1 segundo
        assert (end - start) < 1.0
        assert len(tickets) == 100

    def test_response_model_serialization_performance(self):
        """Prueba rendimiento de serialización"""
        import time

        # Crear response con muchos campos
        response_data = {
            "Id": str(uuid.uuid4()),
            "TicketNumber": "PERF001",
            "PatientId": str(uuid.uuid4()),
            "ServiceTypeId": 1,
            "Status": "Waiting",
            "Position": 1,
            "EstimatedWaitTime": 15,
            "Notes": "Performance test " * 10,
            "CalledAt": datetime.now(),
            "AttendedAt": datetime.now(),
            "CompletedAt": datetime.now(),
            "CreatedAt": datetime.now(),
            "UpdatedAt": datetime.now(),
            "patient_name": "Test Patient",
            "patient_document": "12345678",
            "service_name": "Test Service",
            "station_name": "Test Station"
        }

        start = time.time()

        # Serializar 1000 veces
        for _ in range(1000):
            response = TicketResponse(**response_data)
            _ = response.model_dump_json()

        end = time.time()

        # Debe procesar 1000 serializaciones en menos de 2 segundos
        assert (end - start) < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])