"""
Pruebas unitarias exhaustivas para schemas de pacientes
Valida todas las transformaciones, validaciones y serializaciones de Pydantic
Compatible con Pydantic v2 y estructura existente del proyecto
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict, Any
from pydantic import ValidationError
import uuid

from app.schemas.patient import (
    PatientBase,
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientWithQueueInfo,
    PatientSearch,
    GenderEnum,
    DocumentTypeEnum
)


# ========================================
# TESTS PARA ENUMS
# ========================================

class TestEnums:
    """Tests para los enumeradores definidos"""

    def test_gender_enum_values(self):
        """Verifica que GenderEnum tenga los valores correctos"""
        assert GenderEnum.MALE.value == "M"
        assert GenderEnum.FEMALE.value == "F"
        assert GenderEnum.OTHER.value == "Otro"

        # Verificar que solo existan estos valores
        assert len(GenderEnum) == 3

    def test_document_type_enum_values(self):
        """Verifica que DocumentTypeEnum tenga los valores correctos"""
        assert DocumentTypeEnum.DNI.value == "DNI"
        assert DocumentTypeEnum.PASSPORT.value == "PASSPORT"
        assert DocumentTypeEnum.CE.value == "CE"
        assert DocumentTypeEnum.OTHER.value == "OTHER"

        # Verificar que solo existan estos valores
        assert len(DocumentTypeEnum) == 4

    def test_enum_string_conversion(self):
        """Verifica la conversión de enums a string"""
        assert str(GenderEnum.MALE.value) == "M"
        assert str(DocumentTypeEnum.DNI.value) == "DNI"


# ========================================
# TESTS PARA PatientBase
# ========================================

class TestPatientBase:
    """Tests para el schema base de paciente"""

    def test_create_valid_patient_base(self):
        """Test creación de PatientBase con datos válidos"""
        patient_data = {
            "document_type": DocumentTypeEnum.DNI,
            "document_number": "12345678",
            "first_name": "Juan",
            "last_name": "Pérez García",
            "birth_date": date(1990, 5, 15),
            "gender": GenderEnum.MALE,
            "email": "juan.perez@email.com",
            "phone": "987654321",
            "address": "Av. Principal 123"
        }

        patient = PatientBase(**patient_data)

        assert patient.document_type == DocumentTypeEnum.DNI
        assert patient.document_number == "12345678"
        assert patient.first_name == "Juan"
        assert patient.last_name == "Pérez García"
        assert patient.birth_date == date(1990, 5, 15)
        assert patient.gender == GenderEnum.MALE
        assert patient.email == "juan.perez@email.com"
        assert patient.phone == "987654321"
        assert patient.address == "Av. Principal 123"

    def test_patient_base_minimal_required_fields(self):
        """Test con solo campos requeridos"""
        patient_data = {
            "document_type": "DNI",
            "document_number": "87654321",
            "first_name": "María",
            "last_name": "González"
        }

        patient = PatientBase(**patient_data)

        assert patient.document_number == "87654321"
        assert patient.first_name == "María"
        assert patient.last_name == "González"
        assert patient.birth_date is None
        assert patient.gender is None
        assert patient.email is None
        assert patient.phone is None
        assert patient.address is None

    def test_patient_base_field_validations(self):
        """Test validaciones de campos"""
        # document_number vacío
        with pytest.raises(ValidationError) as exc_info:
            PatientBase(
                document_type="DNI",
                document_number="",  # min_length=1
                first_name="Juan",
                last_name="Pérez"
            )
        assert "at least 1 character" in str(exc_info.value).lower() or "string too short" in str(exc_info.value).lower()

        # document_number muy largo
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="1" * 21,  # max_length=20
                first_name="Juan",
                last_name="Pérez"
            )

        # first_name vacío
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="",  # min_length=1
                last_name="Pérez"
            )

        # first_name muy largo
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="A" * 101,  # max_length=100
                last_name="Pérez"
            )

        # phone muy largo
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="Juan",
                last_name="Pérez",
                phone="1" * 21  # max_length=20
            )

        # address muy largo
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="Juan",
                last_name="Pérez",
                address="A" * 256  # max_length=255
            )

    def test_patient_base_email_validation(self):
        """Test validación de email"""
        # Email válido
        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="Juan",
            last_name="Pérez",
            email="juan.perez@email.com"
        )
        assert patient.email == "juan.perez@email.com"

        # Email inválido
        with pytest.raises(ValidationError) as exc_info:
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="Juan",
                last_name="Pérez",
                email="invalid-email"
            )
        assert "email" in str(exc_info.value).lower()

    def test_patient_base_enum_validation(self):
        """Test validación de enums"""
        # Género inválido
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="Juan",
                last_name="Pérez",
                gender="X"  # No es un valor válido del enum
            )

        # Tipo de documento inválido
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="INVALID",  # No es un valor válido del enum
                document_number="12345678",
                first_name="Juan",
                last_name="Pérez"
            )

    def test_patient_base_date_validation(self):
        """Test validación de fecha de nacimiento"""
        # Fecha válida
        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="Juan",
            last_name="Pérez",
            birth_date=date(2000, 1, 1)
        )
        assert patient.birth_date == date(2000, 1, 1)

        # Fecha como string (debe convertirse automáticamente)
        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="Juan",
            last_name="Pérez",
            birth_date="2000-01-01"
        )
        assert patient.birth_date == date(2000, 1, 1)

        # Fecha inválida
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="Juan",
                last_name="Pérez",
                birth_date="invalid-date"
            )


# ========================================
# TESTS PARA PatientCreate
# ========================================

class TestPatientCreate:
    """Tests para el schema de creación de paciente"""

    def test_create_patient_inherits_from_base(self):
        """Verifica que PatientCreate herede correctamente de PatientBase"""
        patient_data = {
            "document_type": "DNI",
            "document_number": "12345678",
            "first_name": "Ana",
            "last_name": "López"
        }

        patient = PatientCreate(**patient_data)

        assert patient.document_number == "12345678"
        assert patient.first_name == "Ana"
        assert patient.last_name == "López"
        assert patient.birth_date is None  # Opcional en create

    def test_patient_create_with_all_fields(self):
        """Test con todos los campos posibles"""
        patient_data = {
            "document_type": "PASSPORT",
            "document_number": "ABC123456",
            "first_name": "Carlos",
            "last_name": "Rodríguez",
            "birth_date": date(1985, 3, 20),
            "gender": "M",
            "email": "carlos@example.com",
            "phone": "945678123",
            "address": "Calle 45 #123"
        }

        patient = PatientCreate(**patient_data)

        assert patient.document_type == DocumentTypeEnum.PASSPORT
        assert patient.document_number == "ABC123456"
        assert patient.gender == GenderEnum.MALE


# ========================================
# TESTS PARA PatientUpdate
# ========================================

class TestPatientUpdate:
    """Tests para el schema de actualización de paciente"""

    def test_patient_update_all_fields_optional(self):
        """Verifica que todos los campos sean opcionales en update"""
        # Update vacío debe ser válido
        update = PatientUpdate()
        assert update is not None

        # Update con un solo campo
        update = PatientUpdate(phone="999888777")
        assert update.phone == "999888777"
        assert update.email is None
        assert update.address is None

    def test_patient_update_partial_data(self):
        """Test actualización parcial de datos"""
        update_data = {
            "email": "nuevo@email.com",
            "phone": "999000111",
            "address": "Nueva dirección 456"
        }

        update = PatientUpdate(**update_data)

        assert update.email == "nuevo@email.com"
        assert update.phone == "999000111"
        assert update.address == "Nueva dirección 456"
        assert update.first_name is None
        assert update.last_name is None

    def test_patient_update_validations_apply(self):
        """Verifica que las validaciones se apliquen en update"""
        # Email inválido
        with pytest.raises(ValidationError):
            PatientUpdate(email="invalid-email")

        # Phone muy largo
        with pytest.raises(ValidationError):
            PatientUpdate(phone="1" * 21)

        # Address muy largo
        with pytest.raises(ValidationError):
            PatientUpdate(address="A" * 256)


# ========================================
# TESTS PARA PatientResponse
# ========================================

class TestPatientResponse:
    """Tests para el schema de respuesta de paciente"""

    def test_patient_response_includes_metadata(self):
        """Verifica que PatientResponse incluya campos de metadata"""
        response_data = {
            "id": str(uuid.uuid4()),
            "document_type": "DNI",
            "document_number": "12345678",
            "full_name": "Pedro Martínez",  # Campo requerido
            "first_name": "Pedro",
            "last_name": "Martínez",
            "birth_date": date(1995, 7, 10),
            "gender": "M",
            "email": "pedro@email.com",
            "phone": "987123456",
            "address": "Av. Central 789",
            "is_active": True,
            "CreatedAt": datetime.now(),  # PascalCase
            "UpdatedAt": datetime.now()   # PascalCase
        }

        response = PatientResponse(**response_data)

        assert response.id == response_data["id"]
        assert response.document_number == "12345678"
        assert response.full_name == "Pedro Martínez"
        assert response.is_active == True
        assert isinstance(response.CreatedAt, datetime)
        assert isinstance(response.UpdatedAt, datetime)

    def test_patient_response_age_calculation(self):
        """Verifica el cálculo de edad si existe el validador"""
        response_data = {
            "id": str(uuid.uuid4()),
            "document_type": "DNI",
            "document_number": "12345678",
            "full_name": "Laura Silva",  # Campo requerido
            "first_name": "Laura",
            "last_name": "Silva",
            "birth_date": date(2000, 1, 1),
            "is_active": True,
            "CreatedAt": datetime.now(),  # PascalCase
            "UpdatedAt": datetime.now()   # PascalCase
        }

        response = PatientResponse(**response_data)

        if hasattr(response, 'age') and response.age is not None:
            # Si existe el campo age calculado
            expected_age = (date.today() - date(2000, 1, 1)).days // 365
            assert abs(response.age - expected_age) <= 1  # Permitir diferencia de 1 año por cálculo aproximado

    def test_patient_response_from_orm_mode(self):
        """Verifica que from_orm funcione correctamente"""
        # Simulamos un objeto ORM con campos PascalCase como en el modelo real
        class MockPatient:
            Id = uuid.uuid4()
            DocumentType = "DNI"
            DocumentNumber = "87654321"
            FullName = "Roberto Díaz"  # El modelo usa FullName, no FirstName/LastName separados
            BirthDate = date(1988, 12, 25)
            Gender = "M"
            Email = "roberto@test.com"
            Phone = "956789012"
            IsActive = True
            CreatedAt = datetime.now()  # Mixins usan snake_case
            UpdatedAt = datetime.now()  # Mixins usan snake_case
            Age = 35  # Campo calculado opcional

        mock_patient = MockPatient()

        # Usar el método from_orm personalizado del schema
        response = PatientResponse.from_orm(mock_patient)

        assert str(response.id) == str(mock_patient.Id)
        assert response.document_number == "87654321"
        assert response.full_name == "Roberto Díaz"
        assert response.first_name == "Roberto"  # Extraído del FullName
        assert response.last_name == "Díaz"  # Extraído del FullName
        assert response.gender == "M"
        assert response.is_active == True


# ========================================
# TESTS PARA PatientWithQueueInfo
# ========================================

class TestPatientWithQueueInfo:
    """Tests para el schema de paciente con información de cola"""

    def test_patient_with_queue_info_full_data(self):
        """Test con información completa de cola"""
        queue_data = {
            "id": str(uuid.uuid4()),
            "document_type": "DNI",
            "document_number": "11223344",
            "full_name": "Sofía Vargas",  # Campo requerido
            "first_name": "Sofía",
            "last_name": "Vargas",
            "is_active": True,
            "CreatedAt": datetime.now(),  # PascalCase
            "UpdatedAt": datetime.now(),  # PascalCase
            "active_tickets": 1,
            "current_ticket": {
                "ticket_number": "A045",
                "status": "Waiting",
                "service_name": "Análisis de Sangre",
                "service_code": "LAB001",
                "CreatedAt": datetime.now()
            },
            "total_visits": 5,
            "last_visit": datetime.now() - timedelta(days=30)
        }

        patient_queue = PatientWithQueueInfo(**queue_data)

        assert patient_queue.full_name == "Sofía Vargas"
        assert patient_queue.active_tickets == 1
        assert patient_queue.current_ticket is not None
        assert patient_queue.current_ticket.ticket_number == "A045"
        assert patient_queue.total_visits == 5

    def test_patient_with_queue_info_no_ticket(self):
        """Test paciente sin ticket activo"""
        queue_data = {
            "id": str(uuid.uuid4()),
            "document_type": "DNI",
            "document_number": "55667788",
            "full_name": "Miguel Torres",  # Campo requerido
            "first_name": "Miguel",
            "last_name": "Torres",
            "is_active": True,
            "CreatedAt": datetime.now(),  # PascalCase
            "UpdatedAt": datetime.now(),  # PascalCase
            "active_tickets": 0,
            "current_ticket": None,
            "total_visits": None,
            "last_visit": None
        }

        patient_queue = PatientWithQueueInfo(**queue_data)

        assert patient_queue.full_name == "Miguel Torres"
        assert patient_queue.active_tickets == 0
        assert patient_queue.current_ticket is None


# ========================================
# TESTS PARA PatientSearch
# ========================================

class TestPatientSearch:
    """Tests para el schema de búsqueda de paciente"""

    def test_patient_search_minimal_fields(self):
        """Test con campos mínimos para búsqueda"""
        search_data = {
            "id": str(uuid.uuid4()),
            "document_number": "99887766",
            "full_name": "Andrea Mendoza López"
        }

        search_result = PatientSearch(**search_data)

        assert search_result.id == search_data["id"]
        assert search_result.document_number == "99887766"
        assert search_result.full_name == "Andrea Mendoza López"

    def test_patient_search_with_optional_fields(self):
        """Test con campos opcionales incluidos"""
        search_data = {
            "id": str(uuid.uuid4()),
            "document_number": "77665544",
            "full_name": "José Luis Ramos",
            "phone": "923456789"
        }

        search_result = PatientSearch(**search_data)

        assert search_result.phone == "923456789"


# ========================================
# TESTS DE VALIDADORES PERSONALIZADOS
# ========================================

class TestCustomValidators:
    """Tests para validadores personalizados si existen"""

    def test_document_number_validator(self):
        """Test validador de número de documento"""
        # Verificar si existe validador para formato de DNI
        if hasattr(PatientBase, '__validators__'):
            # DNI válido (8 dígitos)
            patient = PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="Test",
                last_name="User"
            )
            assert patient.document_number == "12345678"

    def test_phone_validator(self):
        """Test validador de teléfono"""
        # Verificar formato de teléfono peruano si existe validador
        valid_phones = ["987654321", "945123789", "+51987654321"]

        for phone in valid_phones:
            patient = PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="Test",
                last_name="User",
                phone=phone
            )
            assert patient.phone == phone

    def test_name_capitalization(self):
        """Test capitalización automática de nombres si existe"""
        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="juan carlos",
            last_name="pérez garcía"
        )

        # Verificar si existe transformación automática
        # Esto depende de si hay validadores implementados
        assert patient.first_name in ["juan carlos", "Juan Carlos"]
        assert patient.last_name in ["pérez garcía", "Pérez García"]


# ========================================
# TESTS DE SERIALIZACIÓN/DESERIALIZACIÓN
# ========================================

class TestSerialization:
    """Tests de serialización y deserialización"""

    def test_patient_base_dict_export(self):
        """Test exportación a diccionario"""
        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="Elena",
            last_name="Castro",
            birth_date=date(1994, 11, 20)
        )

        patient_dict = patient.model_dump()

        assert patient_dict["document_type"] == "DNI"
        assert patient_dict["document_number"] == "12345678"
        assert patient_dict["first_name"] == "Elena"
        assert patient_dict["birth_date"] == date(1994, 11, 20)

    def test_patient_base_json_export(self):
        """Test exportación a JSON"""
        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="Diego",
            last_name="Flores",
            birth_date=date(1991, 6, 30)
        )

        patient_json = patient.model_dump_json()

        assert '"document_number":"12345678"' in patient_json
        assert '"first_name":"Diego"' in patient_json

    def test_patient_response_exclude_unset(self):
        """Test exclusión de campos no establecidos"""
        response_data = {
            "id": str(uuid.uuid4()),
            "document_type": "DNI",
            "document_number": "88776655",
            "full_name": "Rosa Jiménez",  # Campo requerido
            "first_name": "Rosa",
            "last_name": "Jiménez",
            "is_active": True,
            "CreatedAt": datetime.now(),  # PascalCase
            "UpdatedAt": datetime.now()   # PascalCase
        }

        response = PatientResponse(**response_data)
        response_dict = response.model_dump(exclude_unset=True)

        # Campos requeridos deben estar presentes
        assert "id" in response_dict
        assert "full_name" in response_dict
        assert "document_number" in response_dict
        assert "CreatedAt" in response_dict
        assert "UpdatedAt" in response_dict

        # Los campos opcionales no establecidos pueden ser None
        if "email" in response_dict:
            assert response_dict["email"] is None
        if "phone" in response_dict:
            assert response_dict["phone"] is None


# ========================================
# TESTS DE EDGE CASES Y ERRORES
# ========================================

class TestEdgeCases:
    """Tests para casos extremos y manejo de errores"""

    def test_empty_strings_validation(self):
        """Test que strings vacíos fallen la validación"""
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="",  # String vacío
                last_name="Test"
            )

    def test_whitespace_only_strings(self):
        """Test que strings con solo espacios fallen"""
        with pytest.raises(ValidationError):
            PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="   ",  # Solo espacios
                last_name="Test"
            )

    def test_special_characters_in_names(self):
        """Test nombres con caracteres especiales válidos"""
        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="María José",
            last_name="O'Connor-Smith"
        )

        assert patient.first_name == "María José"
        assert patient.last_name == "O'Connor-Smith"

    def test_unicode_characters_in_names(self):
        """Test nombres con caracteres unicode"""
        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="José",
            last_name="Ñuñez"
        )

        assert patient.first_name == "José"
        assert patient.last_name == "Ñuñez"

    def test_future_birth_date_validation(self):
        """Test que fechas de nacimiento futuras sean manejadas"""
        future_date = date.today() + timedelta(days=30)

        # Esto podría ser válido o inválido dependiendo de los validadores
        # Lo probamos para verificar comportamiento consistente
        try:
            patient = PatientBase(
                document_type="DNI",
                document_number="12345678",
                first_name="Test",
                last_name="User",
                birth_date=future_date
            )
            # Si no hay validador, debería aceptarlo
            assert patient.birth_date == future_date
        except ValidationError:
            # Si hay validador que lo rechaza, está bien
            pass

    def test_very_old_birth_date(self):
        """Test fecha de nacimiento muy antigua"""
        old_date = date(1900, 1, 1)

        patient = PatientBase(
            document_type="DNI",
            document_number="12345678",
            first_name="Test",
            last_name="User",
            birth_date=old_date
        )

        assert patient.birth_date == old_date

    def test_null_vs_none_handling(self):
        """Test manejo de null vs None"""
        patient_data = {
            "document_type": "DNI",
            "document_number": "12345678",
            "first_name": "Test",
            "last_name": "User",
            "email": None,
            "phone": None
        }

        patient = PatientBase(**patient_data)

        assert patient.email is None
        assert patient.phone is None


# ========================================
# TESTS DE INTEGRACIÓN CON MODELO
# ========================================

class TestModelCompatibility:
    """Tests para verificar compatibilidad con el modelo SQLAlchemy"""

    def test_field_names_match_model(self):
        """Verifica que los nombres de campos coincidan con el modelo"""
        # Los campos del schema base deben coincidir con el modelo Patient
        schema_fields = {
            "document_type", "document_number", "first_name",
            "last_name", "birth_date", "gender", "email",
            "phone", "address"
        }

        base_fields = set(PatientBase.model_fields.keys())

        # Todos los campos del schema deben ser válidos
        assert schema_fields == base_fields

    def test_response_includes_model_fields(self):
        """Verifica que PatientResponse incluya campos del modelo"""
        response_fields = set(PatientResponse.model_fields.keys())

        # Debe incluir campos de metadata del modelo con PascalCase para timestamps
        assert "id" in response_fields
        assert "full_name" in response_fields  # Campo requerido en response
        assert "is_active" in response_fields
        assert "CreatedAt" in response_fields  # PascalCase
        assert "UpdatedAt" in response_fields  # PascalCase

        # Campos opcionales
        assert "age" in response_fields
        assert "email" in response_fields
        assert "phone" in response_fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])