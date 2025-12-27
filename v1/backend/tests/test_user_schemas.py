"""
Tests unitarios para schemas de usuarios
Valida todas las transformaciones y validaciones de Pydantic
"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, Any
from pydantic import ValidationError

from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserResponse,
    UserListResponse, UserSearchFilters, ChangePasswordRequest,
    ResetPasswordRequest, UserStationAssignment, UserRoleAssignment,
    UserStats, UserDashboard, UserActivityLog, BulkUserCreate,
    BulkUserResponse, UserExportRequest, UserImportRequest,
    UserStatus, ActivityType
)


# ========================================
# TESTS PARA ENUMS
# ========================================

class TestEnums:
    """Tests para los enums definidos"""

    def test_user_status_enum(self):
        """Test que UserStatus tiene los valores correctos"""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"

    def test_activity_type_enum(self):
        """Test que ActivityType tiene los valores correctos"""
        assert ActivityType.LOGIN.value == "login"
        assert ActivityType.LOGOUT.value == "logout"
        assert ActivityType.PASSWORD_CHANGE.value == "password_change"
        assert ActivityType.PROFILE_UPDATE.value == "profile_update"
        assert ActivityType.STATION_ASSIGNMENT.value == "station_assignment"
        assert ActivityType.ROLE_CHANGE.value == "role_change"


# ========================================
# TESTS PARA UserBase
# ========================================

class TestUserBase:
    """Tests para el schema UserBase"""

    def test_valid_user_base(self):
        """Test crear UserBase con datos válidos"""
        user = UserBase(
            Username="TestUser",
            Email="Test@Example.COM",
            FullName="john doe smith"
        )

        # Verificar transformaciones
        assert user.Username == "testuser"  # lowercase
        assert user.Email == "test@example.com"  # lowercase
        assert user.FullName == "John Doe Smith"  # capitalizado

    def test_username_too_short(self):
        """Test username menor a 3 caracteres"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(
                Username="ab",  # menos de 3 caracteres
                Email="test@example.com",
                FullName="Test User"
            )
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('Username',) for error in errors)

    def test_username_too_long(self):
        """Test username mayor a 50 caracteres"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(
                Username="a" * 51,  # más de 50 caracteres
                Email="test@example.com",
                FullName="Test User"
            )
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('Username',) for error in errors)

    def test_invalid_email(self):
        """Test email inválido"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(
                Username="testuser",
                Email="invalid-email",  # email inválido
                FullName="Test User"
            )
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('Email',) for error in errors)

    def test_fullname_too_short(self):
        """Test nombre completo menor a 2 caracteres"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(
                Username="testuser",
                Email="test@example.com",
                FullName="A"  # menos de 2 caracteres
            )
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('FullName',) for error in errors)

    def test_fullname_too_long(self):
        """Test nombre completo mayor a 200 caracteres"""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(
                Username="testuser",
                Email="test@example.com",
                FullName="A" * 201  # más de 200 caracteres
            )
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('FullName',) for error in errors)

    def test_whitespace_stripping(self):
        """Test que se eliminan espacios en blanco"""
        user = UserBase(
            Username="  testuser  ",
            Email="  test@example.com  ",
            FullName="  john doe  "
        )

        assert user.Username == "testuser"
        assert user.Email == "test@example.com"
        assert user.FullName == "John Doe"


# ========================================
# TESTS PARA UserCreate
# ========================================

class TestUserCreate:
    """Tests para el schema UserCreate"""

    def test_valid_user_create(self):
        """Test crear UserCreate con datos válidos"""
        user = UserCreate(
            Username="testuser",
            Email="test@example.com",
            FullName="Test User",
            Password="SecurePass123!",
            RoleId=1,
            StationId=2,
            IsActive=True
        )

        assert user.Username == "testuser"
        assert user.Password == "SecurePass123!"
        assert user.RoleId == 1
        assert user.StationId == 2
        assert user.IsActive is True

    def test_user_create_without_station(self):
        """Test crear usuario sin estación"""
        user = UserCreate(
            Username="testuser",
            Email="test@example.com",
            FullName="Test User",
            Password="SecurePass123!",
            RoleId=1
        )

        assert user.StationId is None
        assert user.IsActive is True  # default value

    def test_password_too_short(self):
        """Test contraseña menor a 8 caracteres"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                Username="testuser",
                Email="test@example.com",
                FullName="Test User",
                Password="Pass1!",  # menos de 8 caracteres
                RoleId=1
            )
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('Password',) for error in errors)

    def test_password_too_long(self):
        """Test contraseña mayor a 128 caracteres"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                Username="testuser",
                Email="test@example.com",
                FullName="Test User",
                Password="P" * 129,  # más de 128 caracteres
                RoleId=1
            )
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('Password',) for error in errors)

    def test_missing_required_fields(self):
        """Test campos requeridos faltantes"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate()  # sin ningún campo

        errors = exc_info.value.errors()
        required_fields = ['Username', 'Email', 'FullName', 'Password', 'RoleId']
        for field in required_fields:
            assert any(error['loc'] == (field,) for error in errors)


# ========================================
# TESTS PARA UserUpdate
# ========================================

class TestUserUpdate:
    """Tests para el schema UserUpdate"""

    def test_valid_user_update_all_fields(self):
        """Test actualizar todos los campos"""
        update = UserUpdate(
            Email="new@example.com",
            FullName="new name",
            RoleId=2,
            StationId=3,
            IsActive=False
        )

        assert update.Email == "new@example.com"
        assert update.FullName == "New Name"  # capitalizado
        assert update.RoleId == 2
        assert update.StationId == 3
        assert update.IsActive is False

    def test_user_update_partial(self):
        """Test actualización parcial"""
        update = UserUpdate(Email="new@example.com")

        assert update.Email == "new@example.com"
        assert update.FullName is None
        assert update.RoleId is None
        assert update.StationId is None
        assert update.IsActive is None

    def test_user_update_empty(self):
        """Test actualización vacía es válida"""
        update = UserUpdate()

        assert update.Email is None
        assert update.FullName is None
        assert update.RoleId is None
        assert update.StationId is None
        assert update.IsActive is None

    def test_email_normalization(self):
        """Test normalización de email en update"""
        update = UserUpdate(Email="  NEW@EXAMPLE.COM  ")
        assert update.Email == "new@example.com"

    def test_fullname_capitalization(self):
        """Test capitalización de nombre en update"""
        update = UserUpdate(FullName="  john michael doe  ")
        assert update.FullName == "John Michael Doe"


# ========================================
# TESTS PARA ChangePasswordRequest
# ========================================

class TestChangePasswordRequest:
    """Tests para el schema ChangePasswordRequest"""

    def test_valid_password_change(self):
        """Test cambio de contraseña válido"""
        request = ChangePasswordRequest(
            current_password="OldPass123!",
            new_password="NewPass456!",
            confirm_password="NewPass456!"
        )

        assert request.current_password == "OldPass123!"
        assert request.new_password == "NewPass456!"
        assert request.confirm_password == "NewPass456!"

    def test_passwords_dont_match(self):
        """Test contraseñas que no coinciden"""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="OldPass123!",
                new_password="NewPass456!",
                confirm_password="DifferentPass789!"  # no coincide
            )

        errors = exc_info.value.errors()
        assert any(
            'Las contraseñas no coinciden' in str(error['msg'])
            for error in errors
        )

    def test_new_password_too_short(self):
        """Test nueva contraseña muy corta"""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="OldPass123!",
                new_password="Pass1!",  # menos de 8 caracteres
                confirm_password="Pass1!"
            )

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('new_password',) for error in errors)


# ========================================
# TESTS PARA UserSearchFilters
# ========================================

class TestUserSearchFilters:
    """Tests para el schema UserSearchFilters"""

    def test_valid_search_filters(self):
        """Test filtros de búsqueda válidos"""
        filters = UserSearchFilters(
            search_term="test",
            role_id=1,
            is_active=True,
            station_id=2,
            has_station=True,
            created_from=date(2024, 1, 1),
            created_to=date(2024, 12, 31),
            last_login_from=datetime(2024, 1, 1),
            last_login_to=datetime(2024, 12, 31)
        )

        assert filters.search_term == "test"
        assert filters.role_id == 1
        assert filters.is_active is True
        assert filters.station_id == 2
        assert filters.has_station is True
        assert filters.created_from == date(2024, 1, 1)
        assert filters.created_to == date(2024, 12, 31)

    def test_empty_search_filters(self):
        """Test filtros vacíos"""
        filters = UserSearchFilters()

        assert filters.search_term is None
        assert filters.role_id is None
        assert filters.is_active is None
        assert filters.station_id is None
        assert filters.has_station is None
        assert filters.created_from is None
        assert filters.created_to is None

    def test_search_term_max_length(self):
        """Test término de búsqueda muy largo"""
        with pytest.raises(ValidationError) as exc_info:
            UserSearchFilters(search_term="a" * 101)  # más de 100 caracteres

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('search_term',) for error in errors)


# ========================================
# TESTS PARA UserStationAssignment
# ========================================

class TestUserStationAssignment:
    """Tests para el schema UserStationAssignment"""

    def test_assign_station(self):
        """Test asignar estación"""
        assignment = UserStationAssignment(
            station_id=5,
            reason="Rotación mensual"
        )

        assert assignment.station_id == 5
        assert assignment.reason == "Rotación mensual"

    def test_unassign_station(self):
        """Test desasignar estación"""
        assignment = UserStationAssignment(
            station_id=None,
            reason="Fin de turno"
        )

        assert assignment.station_id is None
        assert assignment.reason == "Fin de turno"

    def test_reason_max_length(self):
        """Test razón muy larga"""
        with pytest.raises(ValidationError) as exc_info:
            UserStationAssignment(
                station_id=1,
                reason="a" * 201  # más de 200 caracteres
            )

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('reason',) for error in errors)


# ========================================
# TESTS PARA BulkUserCreate
# ========================================

class TestBulkUserCreate:
    """Tests para el schema BulkUserCreate"""

    def test_valid_bulk_create(self):
        """Test creación masiva válida"""
        users_data = [
            UserCreate(
                Username=f"user{i}",
                Email=f"user{i}@example.com",
                FullName=f"User {i}",
                Password="Pass123!",
                RoleId=1
            )
            for i in range(3)
        ]

        bulk = BulkUserCreate(
            users=users_data,
            default_role_id=2,
            default_password="DefaultPass123!",
            send_welcome_emails=False
        )

        assert len(bulk.users) == 3
        assert bulk.default_role_id == 2
        assert bulk.default_password == "DefaultPass123!"
        assert bulk.send_welcome_emails is False

    def test_bulk_create_empty_list(self):
        """Test lista vacía de usuarios"""
        with pytest.raises(ValidationError) as exc_info:
            BulkUserCreate(users=[])  # lista vacía

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('users',) for error in errors)

    def test_bulk_create_too_many_users(self):
        """Test más de 100 usuarios"""
        users_data = [
            UserCreate(
                Username=f"user{i}",
                Email=f"user{i}@example.com",
                FullName=f"User {i}",
                Password="Pass123!",
                RoleId=1
            )
            for i in range(101)  # más de 100
        ]

        with pytest.raises(ValidationError) as exc_info:
            BulkUserCreate(users=users_data)

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('users',) for error in errors)


# ========================================
# TESTS PARA UserExportRequest
# ========================================

class TestUserExportRequest:
    """Tests para el schema UserExportRequest"""

    def test_valid_export_request(self):
        """Test solicitud de exportación válida"""
        request = UserExportRequest(
            format="excel",
            include_inactive=True,
            role_ids=[1, 2, 3],
            station_ids=[4, 5]
        )

        assert request.format == "excel"
        assert request.include_inactive is True
        assert request.role_ids == [1, 2, 3]
        assert request.station_ids == [4, 5]

    def test_default_export_format(self):
        """Test formato por defecto"""
        request = UserExportRequest()
        assert request.format == "csv"
        assert request.include_inactive is False

    def test_invalid_export_format(self):
        """Test formato de exportación inválido"""
        with pytest.raises(ValidationError) as exc_info:
            UserExportRequest(format="pdf")  # formato no soportado

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('format',) for error in errors)


# ========================================
# TESTS PARA UserImportRequest
# ========================================

class TestUserImportRequest:
    """Tests para el schema UserImportRequest"""

    def test_valid_import_request(self):
        """Test solicitud de importación válida"""
        request = UserImportRequest(
            file_format="csv",
            skip_errors=True,
            update_existing=False,
            default_role_id=1,
            default_password="DefaultPass123!"
        )

        assert request.file_format == "csv"
        assert request.skip_errors is True
        assert request.update_existing is False
        assert request.default_role_id == 1
        assert request.default_password == "DefaultPass123!"

    def test_invalid_file_format(self):
        """Test formato de archivo inválido"""
        with pytest.raises(ValidationError) as exc_info:
            UserImportRequest(
                file_format="txt",  # formato no soportado
                default_role_id=1
            )

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('file_format',) for error in errors)

    def test_default_password_too_short(self):
        """Test contraseña por defecto muy corta"""
        with pytest.raises(ValidationError) as exc_info:
            UserImportRequest(
                file_format="csv",
                default_role_id=1,
                default_password="Pass1!"  # menos de 8 caracteres
            )

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('default_password',) for error in errors)


# ========================================
# TESTS PARA UserResponse
# ========================================

class TestUserResponse:
    """Tests para el schema UserResponse"""

    def test_valid_user_response(self):
        """Test respuesta de usuario válida"""
        response = UserResponse(
            Id="123e4567-e89b-12d3-a456-426614174000",
            Username="testuser",
            Email="test@example.com",
            FullName="Test User",
            IsActive=True,
            RoleId=1,
            role_name="Admin",
            StationId=2,
            station_name="Ventanilla 1",
            station_code="V01",
            CreatedAt=datetime.now(),
            UpdatedAt=datetime.now(),
            LastLogin=datetime.now(),
            permissions=["users.create", "users.read"],
            is_admin=True,
            is_supervisor=True,
            is_agente=False,
            can_attend_patients=True,
            days_since_last_login=0,
            is_recently_active=True
        )

        assert response.Id == "123e4567-e89b-12d3-a456-426614174000"
        assert response.Username == "testuser"
        assert response.is_admin is True
        assert len(response.permissions) == 2

    def test_user_response_minimal(self):
        """Test respuesta con campos mínimos"""
        response = UserResponse(
            Id="123e4567-e89b-12d3-a456-426614174000",
            Username="testuser",
            Email="test@example.com",
            FullName="Test User",
            IsActive=True,
            RoleId=1,
            CreatedAt=datetime.now(),
            UpdatedAt=datetime.now()
        )

        assert response.StationId is None
        assert response.station_name is None
        assert response.LastLogin is None
        assert response.permissions == []
        assert response.is_admin is False


# ========================================
# CONFIGURACIÓN PYTEST
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])