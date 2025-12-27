"""
Pruebas unitarias para los schemas de QueueState
Compatible con Pydantic v2 y la estructura del proyecto
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError

from app.schemas.queue import (
    # Base
    QueueStateBase,
    QueueStateInDB,

    # CRUD
    QueueStateCreate,
    QueueStateUpdate,
    QueueStateResponse,

    # Operations
    AdvanceQueueRequest,
    ResetQueueRequest,
    UpdateWaitTimeRequest,

    # Query & Stats
    QueueSummary,
    QueueStateWithTickets,
    QueueFilters,
    BatchQueueUpdate,

    # Notifications
    QueueStateChangeNotification
)


# ========================================
# TESTS DE SCHEMAS BASE
# ========================================

class TestQueueStateBase:
    """Tests para el schema base de QueueState"""

    def test_queue_state_base_valid(self):
        """Prueba crear un QueueStateBase válido"""
        data = {
            "service_type_id": 1,
            "station_id": 2,
            "queue_length": 5,
            "average_wait_time": 15
        }

        queue_base = QueueStateBase(**data)

        assert queue_base.service_type_id == 1
        assert queue_base.station_id == 2
        assert queue_base.queue_length == 5
        assert queue_base.average_wait_time == 15

    def test_queue_state_base_minimal(self):
        """Prueba crear QueueStateBase con datos mínimos"""
        data = {
            "service_type_id": 1
        }

        queue_base = QueueStateBase(**data)

        assert queue_base.service_type_id == 1
        assert queue_base.station_id is None
        assert queue_base.queue_length == 0
        assert queue_base.average_wait_time == 0

    def test_queue_state_base_validation_errors(self):
        """Prueba validaciones del schema base"""
        # service_type_id debe ser mayor que 0
        with pytest.raises(ValidationError) as exc_info:
            QueueStateBase(service_type_id=0)

        assert "greater than 0" in str(exc_info.value).lower()

        # queue_length no puede ser negativo
        with pytest.raises(ValidationError) as exc_info:
            QueueStateBase(service_type_id=1, queue_length=-1)

        assert "greater than or equal to 0" in str(exc_info.value).lower()


# ========================================
# TESTS DE SCHEMAS CRUD
# ========================================

class TestQueueStateCRUD:
    """Tests para schemas de operaciones CRUD"""

    def test_queue_state_create_valid(self):
        """Prueba crear QueueStateCreate válido"""
        data = {
            "service_type_id": 1,
            "station_id": 2,
            "current_ticket_id": str(uuid.uuid4()),
            "next_ticket_id": str(uuid.uuid4())
        }

        queue_create = QueueStateCreate(**data)

        assert queue_create.service_type_id == 1
        assert queue_create.station_id == 2
        assert queue_create.current_ticket_id is not None
        assert queue_create.next_ticket_id is not None

    def test_queue_state_create_invalid_uuid(self):
        """Prueba validación de UUID en QueueStateCreate"""
        with pytest.raises(ValidationError) as exc_info:
            QueueStateCreate(
                service_type_id=1,
                current_ticket_id="not-a-valid-uuid"
            )

        assert "uuid" in str(exc_info.value).lower()

    def test_queue_state_update_valid(self):
        """Prueba QueueStateUpdate con campos válidos"""
        data = {
            "queue_length": 10,
            "average_wait_time": 20,
            "current_ticket_id": str(uuid.uuid4())
        }

        queue_update = QueueStateUpdate(**data)

        assert queue_update.queue_length == 10
        assert queue_update.average_wait_time == 20
        assert queue_update.current_ticket_id is not None

    def test_queue_state_update_at_least_one_field(self):
        """Prueba que QueueStateUpdate requiere al menos un campo"""
        # Debe fallar si no se proporciona ningún campo
        with pytest.raises(ValidationError) as exc_info:
            QueueStateUpdate()

        # El mensaje real dice "Al menos un campo debe ser proporcionado para actualización"
        error_str = str(exc_info.value).lower()
        assert "al menos un campo" in error_str or "at least one field" in error_str

    def test_queue_state_response_complete(self):
        """Prueba QueueStateResponse con todos los campos"""
        data = {
            "id": 1,
            "service_type_id": 1,
            "station_id": 2,
            "current_ticket_id": str(uuid.uuid4()),
            "next_ticket_id": str(uuid.uuid4()),
            "queue_length": 5,
            "average_wait_time": 15,
            "last_update_at": datetime.now(),
            "service_name": "Análisis de Sangre",
            "service_code": "LAB",
            "station_name": "Ventanilla 2",
            "station_code": "V02",
            "is_active": True,
            "estimated_wait_time": 50
        }

        response = QueueStateResponse(**data)

        assert response.id == 1
        assert response.service_name == "Análisis de Sangre"
        assert response.estimated_wait_time == 50

    def test_queue_state_in_db(self):
        """Prueba QueueStateInDB"""
        data = {
            "id": 1,
            "service_type_id": 1,
            "station_id": None,
            "current_ticket_id": str(uuid.uuid4()),
            "queue_length": 3,
            "average_wait_time": 10,
            "last_update_at": datetime.now()
        }

        queue_db = QueueStateInDB(**data)

        assert queue_db.id == 1
        assert queue_db.station_id is None
        assert queue_db.queue_length == 3


# ========================================
# TESTS DE SCHEMAS DE OPERACIONES
# ========================================

class TestQueueOperations:
    """Tests para schemas de operaciones de cola"""

    def test_advance_queue_request_valid(self):
        """Prueba AdvanceQueueRequest válido"""
        data = {
            "service_type_id": 1,
            "station_id": 2,
            "mark_completed": True
        }

        request = AdvanceQueueRequest(**data)

        assert request.service_type_id == 1
        assert request.station_id == 2
        assert request.mark_completed is True

    def test_advance_queue_request_minimal(self):
        """Prueba AdvanceQueueRequest con datos mínimos"""
        data = {
            "service_type_id": 1
        }

        request = AdvanceQueueRequest(**data)

        assert request.service_type_id == 1
        assert request.station_id is None
        assert request.mark_completed is True  # Default

    def test_reset_queue_request(self):
        """Prueba ResetQueueRequest"""
        data = {
            "service_type_id": 1,
            "station_id": 2,
            "reason": "Inicio de jornada"
        }

        request = ResetQueueRequest(**data)

        assert request.service_type_id == 1
        assert request.reason == "Inicio de jornada"

    def test_update_wait_time_request_recalculate(self):
        """Prueba UpdateWaitTimeRequest con recálculo"""
        data = {
            "queue_state_id": 1,
            "recalculate": True
        }

        request = UpdateWaitTimeRequest(**data)

        assert request.queue_state_id == 1
        assert request.recalculate is True
        assert request.manual_time is None

    def test_update_wait_time_request_manual(self):
        """Prueba UpdateWaitTimeRequest con tiempo manual"""
        data = {
            "queue_state_id": 1,
            "recalculate": False,
            "manual_time": 25
        }

        request = UpdateWaitTimeRequest(**data)

        assert request.queue_state_id == 1
        assert request.recalculate is False
        assert request.manual_time == 25

    def test_update_wait_time_request_validation(self):
        """Prueba validación de UpdateWaitTimeRequest"""
        # Debe fallar si recalculate=False y no hay manual_time
        with pytest.raises(ValidationError) as exc_info:
            UpdateWaitTimeRequest(
                queue_state_id=1,
                recalculate=False
            )

        assert "manual_time" in str(exc_info.value).lower()

        # manual_time no puede exceder 480 minutos (8 horas)
        with pytest.raises(ValidationError) as exc_info:
            UpdateWaitTimeRequest(
                queue_state_id=1,
                recalculate=False,
                manual_time=500
            )

        assert "less than or equal to 480" in str(exc_info.value).lower()


# ========================================
# TESTS DE SCHEMAS DE CONSULTA
# ========================================

class TestQueueQuery:
    """Tests para schemas de consulta y estadísticas"""

    def test_queue_summary(self):
        """Prueba QueueSummary"""
        data = {
            "total_queues": 5,
            "active_queues": 3,
            "total_waiting": 25,
            "stations_busy": 4,
            "average_wait_time": 12.5
        }

        summary = QueueSummary(**data)

        assert summary.total_queues == 5
        assert summary.active_queues == 3
        assert summary.total_waiting == 25
        assert summary.average_wait_time == 12.5

    def test_queue_state_with_tickets(self):
        """Prueba QueueStateWithTickets"""
        data = {
            "id": 1,
            "service_type_id": 1,
            "station_id": 2,
            "queue_length": 5,
            "average_wait_time": 10,
            "last_update_at": datetime.now(),
            "current_ticket_number": "A045",
            "next_ticket_number": "A046",
            "waiting_tickets": [
                {
                    "id": str(uuid.uuid4()),
                    "ticket_number": "A047",
                    "priority": 1,
                    "estimated_time": 60
                },
                {
                    "id": str(uuid.uuid4()),
                    "ticket_number": "A048",
                    "priority": 0,
                    "estimated_time": 70
                }
            ]
        }

        queue_with_tickets = QueueStateWithTickets(**data)

        assert queue_with_tickets.current_ticket_number == "A045"
        assert queue_with_tickets.next_ticket_number == "A046"
        assert len(queue_with_tickets.waiting_tickets) == 2
        assert queue_with_tickets.waiting_tickets[0]["ticket_number"] == "A047"

    def test_queue_filters_valid(self):
        """Prueba QueueFilters con filtros válidos"""
        data = {
            "service_type_id": 1,
            "station_id": 2,
            "include_empty": False,
            "only_active": True,
            "min_queue_length": 1,
            "max_queue_length": 10
        }

        filters = QueueFilters(**data)

        assert filters.service_type_id == 1
        assert filters.include_empty is False
        assert filters.min_queue_length == 1
        assert filters.max_queue_length == 10

    def test_queue_filters_defaults(self):
        """Prueba valores por defecto de QueueFilters"""
        filters = QueueFilters()

        assert filters.service_type_id is None
        assert filters.station_id is None
        assert filters.include_empty is False  # Default
        assert filters.only_active is True  # Default

    def test_queue_filters_validation(self):
        """Prueba validación de rangos en QueueFilters"""
        # min_queue_length no puede ser mayor que max_queue_length
        with pytest.raises(ValidationError) as exc_info:
            QueueFilters(
                min_queue_length=10,
                max_queue_length=5
            )

        assert "min_queue_length" in str(exc_info.value).lower()

    def test_batch_queue_update(self):
        """Prueba BatchQueueUpdate"""
        data = {
            "queue_ids": [1, 2, 3],
            "action": "reset",
            "reason": "Cierre de jornada"
        }

        batch_update = BatchQueueUpdate(**data)

        assert len(batch_update.queue_ids) == 3
        assert batch_update.action == "reset"
        assert batch_update.reason == "Cierre de jornada"

    def test_batch_queue_update_validation(self):
        """Prueba validaciones de BatchQueueUpdate"""
        # queue_ids no puede estar vacío
        with pytest.raises(ValidationError) as exc_info:
            BatchQueueUpdate(
                queue_ids=[],
                action="reset"
            )

        assert "at least 1 item" in str(exc_info.value).lower()

        # action debe ser válido (reset|refresh|cleanup)
        with pytest.raises(ValidationError) as exc_info:
            BatchQueueUpdate(
                queue_ids=[1],
                action="invalid_action"
            )

        # El mensaje real dice "string should match pattern"
        error_str = str(exc_info.value).lower()
        assert "string should match pattern" in error_str or "pattern" in error_str


# ========================================
# TESTS DE SCHEMAS DE NOTIFICACIÓN
# ========================================

class TestQueueNotifications:
    """Tests para schemas de notificación"""

    def test_queue_state_change_notification(self):
        """Prueba QueueStateChangeNotification"""
        data = {
            "queue_state_id": 1,
            "change_type": "advanced",
            "previous_ticket": "A044",
            "current_ticket": "A045",
            "next_ticket": "A046",
            "timestamp": datetime.now()
        }

        notification = QueueStateChangeNotification(**data)

        assert notification.queue_state_id == 1
        assert notification.change_type == "advanced"
        assert notification.previous_ticket == "A044"
        assert notification.current_ticket == "A045"

    def test_queue_state_change_notification_minimal(self):
        """Prueba notificación con datos mínimos"""
        data = {
            "queue_state_id": 1,
            "change_type": "reset"
        }

        notification = QueueStateChangeNotification(**data)

        assert notification.queue_state_id == 1
        assert notification.change_type == "reset"
        assert notification.previous_ticket is None
        assert notification.timestamp is not None  # Se genera automáticamente

    def test_queue_state_change_notification_validation(self):
        """Prueba validación de tipo de cambio"""
        with pytest.raises(ValidationError) as exc_info:
            QueueStateChangeNotification(
                queue_state_id=1,
                change_type="invalid_type"
            )

        # El mensaje real dice "string should match pattern"
        error_str = str(exc_info.value).lower()
        assert "string should match pattern" in error_str or "pattern" in error_str


# ========================================
# TESTS DE CASOS EDGE
# ========================================

class TestQueueSchemasEdgeCases:
    """Tests para casos edge y escenarios especiales"""

    def test_uuid_string_conversion(self):
        """Prueba conversión de UUID a string y viceversa"""
        uuid_obj = uuid.uuid4()

        # Debe aceptar tanto UUID como string
        data1 = {
            "service_type_id": 1,
            "current_ticket_id": str(uuid_obj)
        }

        create1 = QueueStateCreate(**data1)
        assert create1.current_ticket_id == str(uuid_obj)

    def test_none_values_handling(self):
        """Prueba manejo de valores None"""
        data = {
            "service_type_id": 1,
            "station_id": None,
            "current_ticket_id": None,
            "next_ticket_id": None
        }

        create = QueueStateCreate(**data)

        assert create.station_id is None
        assert create.current_ticket_id is None
        assert create.next_ticket_id is None

    def test_from_attributes_compatibility(self):
        """Prueba compatibilidad con from_attributes para ORM"""
        # Simular un objeto ORM
        class MockQueueState:
            service_type_id = 1
            station_id = 2
            queue_length = 5
            average_wait_time = 15

        mock_obj = MockQueueState()

        # Debe poder crear desde el objeto
        queue_base = QueueStateBase.model_validate(mock_obj)

        assert queue_base.service_type_id == 1
        assert queue_base.station_id == 2
        assert queue_base.queue_length == 5

    def test_json_schema_examples(self):
        """Prueba que los ejemplos en json_schema_extra sean válidos"""
        # Probar ejemplo de QueueStateCreate
        example = {
            "service_type_id": 1,
            "station_id": 2,
            "current_ticket_id": "550e8400-e29b-41d4-a716-446655440000",
            "next_ticket_id": "550e8400-e29b-41d4-a716-446655440001"
        }

        create = QueueStateCreate(**example)
        assert create.service_type_id == 1

        # Probar ejemplo de AdvanceQueueRequest
        example = {
            "service_type_id": 1,
            "station_id": 2,
            "mark_completed": True
        }

        request = AdvanceQueueRequest(**example)
        assert request.mark_completed is True

    def test_field_descriptions(self):
        """Verifica que los campos tengan descripciones"""
        # Verificar que los campos tengan metadatos de descripción
        assert QueueStateBase.model_fields['service_type_id'].description is not None
        assert QueueStateUpdate.model_fields['queue_length'].description is not None
        assert QueueSummary.model_fields['total_queues'].description is not None

    def test_validation_error_messages(self):
        """Prueba que los mensajes de error sean descriptivos"""
        try:
            QueueStateBase(service_type_id=-1)
        except ValidationError as e:
            errors = e.errors()
            assert len(errors) > 0
            assert 'service_type_id' in str(errors[0])

    def test_large_queue_values(self):
        """Prueba con valores grandes pero válidos"""
        data = {
            "service_type_id": 999999,
            "queue_length": 1000,
            "average_wait_time": 480  # Máximo 8 horas
        }

        queue_base = QueueStateBase(**data)

        assert queue_base.service_type_id == 999999
        assert queue_base.queue_length == 1000
        assert queue_base.average_wait_time == 480


# ========================================
# TESTS DE SERIALIZACIÓN
# ========================================

class TestQueueSchemasSerialization:
    """Tests para serialización/deserialización JSON"""

    def test_json_serialization(self):
        """Prueba serialización a JSON"""
        queue_create = QueueStateCreate(
            service_type_id=1,
            station_id=2,
            current_ticket_id=str(uuid.uuid4())
        )

        # Convertir a JSON
        json_str = queue_create.model_dump_json()
        assert isinstance(json_str, str)
        assert '"service_type_id":1' in json_str

    def test_json_deserialization(self):
        """Prueba deserialización desde JSON"""
        json_str = '''
        {
            "service_type_id": 1,
            "station_id": 2,
            "queue_length": 5,
            "average_wait_time": 15
        }
        '''

        queue_base = QueueStateBase.model_validate_json(json_str)

        assert queue_base.service_type_id == 1
        assert queue_base.queue_length == 5

    def test_dict_conversion(self):
        """Prueba conversión a diccionario"""
        summary = QueueSummary(
            total_queues=5,
            active_queues=3,
            total_waiting=25,
            stations_busy=4,
            average_wait_time=12.5
        )

        data_dict = summary.model_dump()

        assert isinstance(data_dict, dict)
        assert data_dict['total_queues'] == 5
        assert data_dict['average_wait_time'] == 12.5

    def test_exclude_unset(self):
        """Prueba exclusión de campos no establecidos"""
        update = QueueStateUpdate(queue_length=10)

        # Excluir campos no establecidos
        data = update.model_dump(exclude_unset=True)

        assert 'queue_length' in data
        assert 'current_ticket_id' not in data
        assert 'average_wait_time' not in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])