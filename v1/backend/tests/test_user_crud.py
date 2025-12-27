"""
Tests unitarios para operaciones CRUD de usuarios
Usando SQL Server directamente
"""

import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.database import Base
from app.models.user import User
from app.models.role import Role
from app.models.station import Station
from app.models.service_type import ServiceType
from app.crud.user import user_crud
from app.core.security import create_password_hash, verify_password
from app.core.config import settings


# ========================================
# CONFIGURACIÓN DE FIXTURES
# ========================================

@pytest.fixture(scope="function")
def db_session():
    """
    Crea una sesión de base de datos de test en SQL Server
    """
    # Usar base de datos de test en SQL Server
    DATABASE_URL = f"mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"

    # Crear engine
    engine = create_engine(DATABASE_URL, echo=False)  # echo=True para debug

    # Limpiar tablas existentes en orden correcto (por foreign keys)
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM ActivityLog"))
        conn.execute(text("DELETE FROM NotificationLog"))
        conn.execute(text("DELETE FROM DailyMetrics"))
        conn.execute(text("DELETE FROM QueueState"))
        conn.execute(text("DELETE FROM Tickets"))
        conn.execute(text("DELETE FROM Users"))
        conn.execute(text("DELETE FROM Stations"))
        conn.execute(text("DELETE FROM Patients"))
        conn.execute(text("DELETE FROM MessageTemplates"))
        conn.execute(text("DELETE FROM ServiceTypes"))
        conn.execute(text("DELETE FROM Roles"))
        conn.commit()

    # Crear sesión
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    # Crear datos iniciales necesarios
    _create_initial_data(session)

    yield session

    # Limpiar después del test
    session.rollback()
    session.close()

    # Limpiar tablas nuevamente
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM ActivityLog"))
        conn.execute(text("DELETE FROM NotificationLog"))
        conn.execute(text("DELETE FROM DailyMetrics"))
        conn.execute(text("DELETE FROM QueueState"))
        conn.execute(text("DELETE FROM Tickets"))
        conn.execute(text("DELETE FROM Users"))
        conn.execute(text("DELETE FROM Stations"))
        conn.execute(text("DELETE FROM Patients"))
        conn.execute(text("DELETE FROM MessageTemplates"))
        conn.execute(text("DELETE FROM ServiceTypes"))
        conn.execute(text("DELETE FROM Roles"))
        conn.commit()

    engine.dispose()


def _create_initial_data(db: Session):
    """
    Crea datos iniciales necesarios para los tests
    """
    # Crear tipos de servicio primero (requerido para estaciones)
    service_type1 = ServiceType(
        Code="LAB",
        Name="Análisis",
        Description="Análisis de laboratorio",
        Priority=2,
        AverageTimeMinutes=15,
        TicketPrefix="A",
        Color="#4CAF50",
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    service_type2 = ServiceType(
        Code="RES",
        Name="Entrega de Resultados",
        Description="Entrega de resultados de análisis",
        Priority=3,
        AverageTimeMinutes=10,
        TicketPrefix="R",
        Color="#2196F3",
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    # Crear roles básicos
    admin_role = Role(
        Name="Admin",
        Description="Administrador del sistema",
        Permissions='{"all": true}',
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    supervisor_role = Role(
        Name="Supervisor",
        Description="Supervisor del sistema",
        Permissions='{"read": true, "write": true, "manage": true}',
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    technician_role = Role(
        Name="Technician",
        Description="Técnico de laboratorio",
        Permissions='{"read": true, "write": true}',
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    receptionist_role = Role(
        Name="Receptionist",
        Description="Recepcionista",
        Permissions='{"read": true}',
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    # Agregar tipos de servicio y roles primero
    db.add_all([service_type1, service_type2])
    db.add_all([admin_role, supervisor_role, technician_role, receptionist_role])
    db.commit()

    # Refrescar para obtener IDs generados
    db.refresh(service_type1)
    db.refresh(service_type2)
    db.refresh(admin_role)
    db.refresh(supervisor_role)
    db.refresh(technician_role)
    db.refresh(receptionist_role)

    # Crear estaciones
    station1 = Station(
        Code="V01",
        Name="Ventanilla 1",
        Description="Ventanilla de análisis",
        ServiceTypeId=service_type1.Id,
        Location="Planta Baja",
        Status="Available",
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    station2 = Station(
        Code="V02",
        Name="Ventanilla 2",
        Description="Ventanilla de resultados",
        ServiceTypeId=service_type2.Id,
        Location="Planta Baja",
        Status="Available",
        CreatedAt=datetime.utcnow(),
        IsActive=True
    )

    station3 = Station(
        Code="V03",
        Name="Ventanilla 3",
        Description="Ventanilla de muestras",
        ServiceTypeId=service_type1.Id,
        Location="Planta Baja",
        Status="Offline",
        CreatedAt=datetime.utcnow(),
        IsActive=False
    )

    # Agregar estaciones
    db.add_all([station1, station2, station3])
    db.commit()

    # Refrescar estaciones para obtener IDs
    db.refresh(station1)
    db.refresh(station2)

    # Guardar IDs para uso en fixtures
    db.role_admin_id = admin_role.Id
    db.role_supervisor_id = supervisor_role.Id
    db.role_technician_id = technician_role.Id
    db.role_receptionist_id = receptionist_role.Id
    db.station1_id = station1.Id
    db.station2_id = station2.Id


@pytest.fixture
def sample_user_data(db_session):
    """
    Datos de ejemplo para crear usuarios
    """
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Test123!@#",
        "full_name": "Test User",
        "role_id": db_session.role_technician_id,  # Usar ID real del rol
        "station_id": db_session.station1_id  # Usar ID real de la estación
    }


@pytest.fixture
def created_user(db_session, sample_user_data):
    """
    Crea un usuario para usar en tests
    """
    user = user_crud.create_user(
        db_session,
        **sample_user_data
    )
    db_session.commit()
    return user


# ========================================
# TESTS DE CREACIÓN
# ========================================

class TestUserCreation:
    """Tests para creación de usuarios"""

    def test_create_user_success(self, db_session, sample_user_data):
        """Test crear usuario exitosamente"""
        # Crear usuario
        user = user_crud.create_user(
            db_session,
            **sample_user_data
        )
        db_session.commit()

        # Verificar que se creó
        assert user is not None
        assert user.Username == sample_user_data["username"].lower()
        assert user.Email == sample_user_data["email"].lower()
        assert user.FullName == sample_user_data["full_name"]
        assert user.RoleId == sample_user_data["role_id"]
        assert user.StationId == sample_user_data["station_id"]
        assert user.IsActive is True
        assert verify_password(sample_user_data["password"], user.PasswordHash)

    def test_create_user_duplicate_username(self, db_session, sample_user_data):
        """Test crear usuario con username duplicado"""
        # Crear primer usuario
        user1 = user_crud.create_user(db_session, **sample_user_data)
        db_session.commit()
        assert user1 is not None

        # Intentar crear otro con mismo username
        sample_user_data["email"] = "different@example.com"
        user2 = user_crud.create_user(db_session, **sample_user_data)
        assert user2 is None

    def test_create_user_duplicate_email(self, db_session, sample_user_data):
        """Test crear usuario con email duplicado"""
        # Crear primer usuario
        user1 = user_crud.create_user(db_session, **sample_user_data)
        db_session.commit()
        assert user1 is not None

        # Intentar crear otro con mismo email
        sample_user_data["username"] = "differentuser"
        user2 = user_crud.create_user(db_session, **sample_user_data)
        assert user2 is None

    def test_create_user_invalid_role(self, db_session, sample_user_data):
        """Test crear usuario con rol inválido"""
        sample_user_data["role_id"] = 999  # Rol que no existe
        user = user_crud.create_user(db_session, **sample_user_data)
        assert user is None

    def test_create_user_invalid_station(self, db_session, sample_user_data):
        """Test crear usuario con estación inválida"""
        sample_user_data["station_id"] = 999  # Estación que no existe
        user = user_crud.create_user(db_session, **sample_user_data)
        assert user is None

    def test_create_user_without_station(self, db_session, sample_user_data):
        """Test crear usuario sin estación asignada"""
        sample_user_data["station_id"] = None
        user = user_crud.create_user(db_session, **sample_user_data)
        db_session.commit()
        assert user is not None
        assert user.StationId is None

    def test_create_user_case_insensitive(self, db_session, sample_user_data):
        """Test que username y email se normalizan a minúsculas"""
        sample_user_data["username"] = "TestUser"
        sample_user_data["email"] = "Test@Example.COM"

        user = user_crud.create_user(db_session, **sample_user_data)
        db_session.commit()
        assert user.Username == "testuser"
        assert user.Email == "test@example.com"

# El resto de las clases de tests continúan igual...
# Solo asegúrate de hacer commit() después de crear/modificar datos

# ========================================
# TESTS DE OBTENCIÓN
# ========================================

class TestUserRetrieval:
    """Tests para obtención de usuarios"""

    def test_get_user_by_id(self, db_session, created_user):
        """Test obtener usuario por ID"""
        user = user_crud.get(db_session, created_user.Id)
        assert user is not None
        assert user.Id == created_user.Id

    def test_get_user_by_username(self, db_session, created_user):
        """Test obtener usuario por username"""
        user = user_crud.get_by_username(db_session, username=created_user.Username)
        assert user is not None
        assert user.Id == created_user.Id

    def test_get_user_by_username_case_insensitive(self, db_session, created_user):
        """Test obtener usuario por username sin importar mayúsculas"""
        user = user_crud.get_by_username(db_session, username="TESTUSER")
        assert user is not None
        assert user.Id == created_user.Id

    def test_get_user_by_email(self, db_session, created_user):
        """Test obtener usuario por email"""
        user = user_crud.get_by_email(db_session, email=created_user.Email)
        assert user is not None
        assert user.Id == created_user.Id

    def test_get_user_by_email_case_insensitive(self, db_session, created_user):
        """Test obtener usuario por email sin importar mayúsculas"""
        user = user_crud.get_by_email(db_session, email="TEST@EXAMPLE.COM")
        assert user is not None
        assert user.Id == created_user.Id

    def test_get_nonexistent_user(self, db_session):
        """Test obtener usuario que no existe"""
        fake_id = str(uuid.uuid4())
        user = user_crud.get(db_session, fake_id)
        assert user is None

    def test_get_active_users(self, db_session, created_user):
        """Test obtener solo usuarios activos"""
        users = user_crud.get_active_users(db_session)
        assert len(users) >= 1
        assert all(u.IsActive for u in users)

    def test_get_users_by_role(self, db_session, created_user):
        """Test obtener usuarios por rol"""
        users = user_crud.get_users_by_role(
            db_session,
            role_id=created_user.RoleId
        )
        assert len(users) >= 1
        assert all(u.RoleId == created_user.RoleId for u in users)

    def test_get_users_by_station(self, db_session, created_user):
        """Test obtener usuarios por estación"""
        users = user_crud.get_users_by_station(
            db_session,
            station_id=created_user.StationId
        )
        assert len(users) >= 1
        assert all(u.StationId == created_user.StationId for u in users)

    def test_get_users_without_station(self, db_session, sample_user_data):
        """Test obtener usuarios sin estación"""
        # Crear usuario sin estación
        sample_user_data["username"] = "nostation"
        sample_user_data["email"] = "nostation@example.com"
        sample_user_data["station_id"] = None
        user = user_crud.create_user(db_session, **sample_user_data)

        # Buscar usuarios sin estación
        users = user_crud.get_users_without_station(db_session)
        assert len(users) >= 1
        assert any(u.Id == user.Id for u in users)

# ========================================
# TESTS DE ACTUALIZACIÓN
# ========================================

class TestUserUpdate:
    """Tests para actualización de usuarios"""

    def test_update_user_email(self, db_session, created_user):
        """Test actualizar email de usuario"""
        new_email = "newemail@example.com"
        updated = user_crud.update_user(
            db_session,
            user_id=str(created_user.Id),
            email=new_email
        )
        assert updated is not None
        assert updated.Email == new_email.lower()

    def test_update_user_duplicate_email(self, db_session, created_user, sample_user_data):
        """Test actualizar usuario con email duplicado"""
        # Crear otro usuario
        sample_user_data["username"] = "otheruser"
        sample_user_data["email"] = "other@example.com"
        other_user = user_crud.create_user(db_session, **sample_user_data)
        db_session.commit()

        # Intentar actualizar con email duplicado
        updated = user_crud.update_user(
            db_session,
            user_id=str(created_user.Id),
            email=other_user.Email
        )
        assert updated is None

    def test_update_user_full_name(self, db_session, created_user):
        """Test actualizar nombre completo"""
        new_name = "Updated Name"
        updated = user_crud.update_user(
            db_session,
            user_id=str(created_user.Id),
            full_name=new_name
        )
        assert updated is not None
        assert updated.FullName == new_name

    def test_update_user_role(self, db_session, created_user):
        """Test actualizar rol de usuario"""
        # Usar el ID real del rol Supervisor que se guardó en db_session
        new_role_id = db_session.role_supervisor_id
        updated = user_crud.update_user(
            db_session,
            user_id=str(created_user.Id),
            role_id=new_role_id
        )
        assert updated is not None
        assert updated.RoleId == new_role_id

    def test_update_user_station(self, db_session, created_user):
        """Test actualizar estación de usuario"""
        # Usar el ID real de station2 que se guardó en db_session
        new_station_id = db_session.station2_id
        updated = user_crud.update_user(
            db_session,
            user_id=str(created_user.Id),
            station_id=new_station_id
        )
        assert updated is not None
        assert updated.StationId == new_station_id

    def test_update_user_remove_station(self, db_session, created_user):
        """Test desasignar estación de usuario"""
        updated = user_crud.update_user(
            db_session,
            user_id=str(created_user.Id),
            station_id=0  # 0 significa desasignar
        )
        assert updated is not None
        assert updated.StationId is None

    def test_update_password(self, db_session, created_user):
        """Test actualizar contraseña"""
        new_password = "NewPassword123!"
        updated = user_crud.update_password(
            db_session,
            user_id=str(created_user.Id),
            new_password=new_password
        )
        assert updated is not None
        assert verify_password(new_password, updated.PasswordHash)

    def test_update_last_login(self, db_session, created_user):
        """Test actualizar último login"""
        before = datetime.utcnow()
        updated = user_crud.update_last_login(
            db_session,
            user_id=str(created_user.Id)
        )
        assert updated is not None
        assert updated.LastLogin is not None
        assert updated.LastLogin >= before


# ========================================
# TESTS DE BÚSQUEDA
# ========================================

class TestUserSearch:
    """Tests para búsqueda de usuarios"""

    def test_search_users_by_username(self, db_session, created_user):
        """Test buscar usuarios por username"""
        users = user_crud.search_users(
            db_session,
            query="test"
        )
        assert len(users) >= 1
        assert any(u.Id == created_user.Id for u in users)

    def test_search_users_by_email(self, db_session, created_user):
        """Test buscar usuarios por email"""
        users = user_crud.search_users(
            db_session,
            query="example.com"
        )
        assert len(users) >= 1
        assert any(u.Id == created_user.Id for u in users)

    def test_search_users_by_name(self, db_session, created_user):
        """Test buscar usuarios por nombre"""
        users = user_crud.search_users(
            db_session,
            query="Test User"
        )
        assert len(users) >= 1
        assert any(u.Id == created_user.Id for u in users)

    def test_search_users_case_insensitive(self, db_session, created_user):
        """Test búsqueda sin importar mayúsculas"""
        users = user_crud.search_users(
            db_session,
            query="TEST"
        )
        assert len(users) >= 1

    def test_search_users_partial_match(self, db_session, created_user):
        """Test búsqueda con coincidencia parcial"""
        users = user_crud.search_users(
            db_session,
            query="tes"
        )
        assert len(users) >= 1

    def test_search_inactive_users(self, db_session, created_user):
        """Test excluir usuarios inactivos de búsqueda"""
        # Desactivar usuario
        user_crud.deactivate_user(db_session, user_id=str(created_user.Id))

        # Buscar con active_only=True
        users = user_crud.search_users(
            db_session,
            query="test",
            active_only=True
        )
        assert not any(u.Id == created_user.Id for u in users)

        # Buscar con active_only=False
        users = user_crud.search_users(
            db_session,
            query="test",
            active_only=False
        )
        assert any(u.Id == created_user.Id for u in users)


# ========================================
# TESTS DE AUTENTICACIÓN
# ========================================

class TestUserAuthentication:
    """Tests para autenticación de usuarios"""

    def test_authenticate_valid_credentials(self, db_session, created_user, sample_user_data):
        """Test autenticación con credenciales válidas"""
        user = user_crud.authenticate(
            db_session,
            username=sample_user_data["username"],
            password=sample_user_data["password"]
        )
        assert user is not None
        assert user.Id == created_user.Id
        assert user.LastLogin is not None

    def test_authenticate_invalid_password(self, db_session, created_user, sample_user_data):
        """Test autenticación con contraseña incorrecta"""
        user = user_crud.authenticate(
            db_session,
            username=sample_user_data["username"],
            password="WrongPassword123"
        )
        assert user is None

    def test_authenticate_invalid_username(self, db_session, sample_user_data):
        """Test autenticación con usuario inexistente"""
        user = user_crud.authenticate(
            db_session,
            username="nonexistent",
            password=sample_user_data["password"]
        )
        assert user is None

    def test_authenticate_inactive_user(self, db_session, created_user, sample_user_data):
        """Test autenticación de usuario inactivo"""
        # Desactivar usuario
        user_crud.deactivate_user(db_session, user_id=str(created_user.Id))

        # Intentar autenticar
        user = user_crud.authenticate(
            db_session,
            username=sample_user_data["username"],
            password=sample_user_data["password"]
        )
        assert user is None

    def test_authenticate_case_insensitive_username(self, db_session, created_user, sample_user_data):
        """Test autenticación con username en mayúsculas"""
        user = user_crud.authenticate(
            db_session,
            username=sample_user_data["username"].upper(),
            password=sample_user_data["password"]
        )
        assert user is not None


# ========================================
# TESTS DE VALIDACIÓN
# ========================================

# ========================================
# TESTS DE VALIDACIÓN - MEJORES PRÁCTICAS
# ========================================

class TestUserValidation:
    """Tests para validación de usuarios"""

    def test_is_active(self, db_session, created_user):
        """Test verificar si usuario está activo"""
        assert user_crud.is_active(created_user) is True

        # Desactivar y verificar
        user_crud.deactivate_user(db_session, user_id=str(created_user.Id))
        db_session.refresh(created_user)
        assert user_crud.is_active(created_user) is False

    def test_is_admin(self, db_session):
        """Test verificar si usuario es admin"""
        # Obtener el rol Admin de la BD
        admin_role = db_session.query(Role).filter(Role.Name == "Admin").first()
        assert admin_role is not None, "Rol Admin debe existir"

        # Crear usuario con rol Admin
        admin_user = user_crud.create_user(
            db_session,
            username="admintest",
            email="admintest@example.com",
            password="Test123!@#",
            full_name="Admin Test User",
            role_id=admin_role.Id,  # Usar el ID real del rol
            station_id=None
        )
        db_session.commit()

        assert admin_user is not None, "Usuario admin debe crearse exitosamente"
        assert user_crud.is_admin(db_session, admin_user) is True

    def test_is_supervisor(self, db_session):
        """Test verificar si usuario es supervisor"""
        # Obtener el rol Supervisor de la BD
        supervisor_role = db_session.query(Role).filter(Role.Name == "Supervisor").first()
        assert supervisor_role is not None, "Rol Supervisor debe existir"

        # Crear usuario con rol Supervisor
        supervisor_user = user_crud.create_user(
            db_session,
            username="supervisortest",
            email="supervisortest@example.com",
            password="Test123!@#",
            full_name="Supervisor Test User",
            role_id=supervisor_role.Id,  # Usar el ID real del rol
            station_id=None
        )
        db_session.commit()

        assert supervisor_user is not None, "Usuario supervisor debe crearse exitosamente"
        assert user_crud.is_supervisor(db_session, supervisor_user) is True

    def test_admin_is_also_supervisor(self, db_session):
        """Test que admin también cuenta como supervisor"""
        # Obtener el rol Admin de la BD
        admin_role = db_session.query(Role).filter(Role.Name == "Admin").first()
        assert admin_role is not None, "Rol Admin debe existir"

        # Crear usuario con rol Admin
        admin_user = user_crud.create_user(
            db_session,
            username="admintest2",
            email="admintest2@example.com",
            password="Test123!@#",
            full_name="Admin Test User 2",
            role_id=admin_role.Id,  # Usar el ID real del rol
            station_id=None
        )
        db_session.commit()

        assert admin_user is not None, "Usuario admin debe crearse exitosamente"
        # Admin también debe contar como supervisor
        assert user_crud.is_supervisor(db_session, admin_user) is True

    def test_technician_is_not_admin(self, db_session):
        """Test que técnico NO es admin"""
        # Obtener el rol Technician de la BD
        tech_role = db_session.query(Role).filter(Role.Name == "Technician").first()
        assert tech_role is not None, "Rol Technician debe existir"

        # Crear usuario técnico
        tech_user = user_crud.create_user(
            db_session,
            username="techtest",
            email="techtest@example.com",
            password="Test123!@#",
            full_name="Tech Test User",
            role_id=tech_role.Id,
            station_id=None
        )
        db_session.commit()

        assert tech_user is not None
        assert user_crud.is_admin(db_session, tech_user) is False
        assert user_crud.is_supervisor(db_session, tech_user) is False

    def test_receptionist_is_not_supervisor(self, db_session):
        """Test que recepcionista NO es supervisor"""
        # Obtener el rol Receptionist de la BD
        recep_role = db_session.query(Role).filter(Role.Name == "Receptionist").first()
        assert recep_role is not None, "Rol Receptionist debe existir"

        # Crear usuario recepcionista
        recep_user = user_crud.create_user(
            db_session,
            username="receptest",
            email="receptest@example.com",
            password="Test123!@#",
            full_name="Receptionist Test User",
            role_id=recep_role.Id,
            station_id=None
        )
        db_session.commit()

        assert recep_user is not None
        assert user_crud.is_admin(db_session, recep_user) is False
        assert user_crud.is_supervisor(db_session, recep_user) is False
# ========================================
# TESTS DE ELIMINACIÓN
# ========================================

class TestUserDeactivation:
    """Tests para desactivación de usuarios"""

    def test_deactivate_user(self, db_session, created_user):
        """Test desactivar usuario"""
        deactivated = user_crud.deactivate_user(
            db_session,
            user_id=str(created_user.Id)
        )
        assert deactivated is not None
        assert deactivated.IsActive is False
        assert deactivated.StationId is None  # Se desasigna la estación

    def test_reactivate_user(self, db_session, created_user):
        """Test reactivar usuario"""
        # Primero desactivar
        user_crud.deactivate_user(db_session, user_id=str(created_user.Id))

        # Luego reactivar
        reactivated = user_crud.reactivate_user(
            db_session,
            user_id=str(created_user.Id)
        )
        assert reactivated is not None
        assert reactivated.IsActive is True

    def test_deactivate_nonexistent_user(self, db_session):
        """Test desactivar usuario inexistente"""
        fake_id = str(uuid.uuid4())
        result = user_crud.deactivate_user(db_session, user_id=fake_id)
        assert result is None


# ========================================
# TESTS DE ESTADÍSTICAS
# ========================================

class TestUserStatistics:
    """Tests para estadísticas de usuarios"""

    def test_count_users(self, db_session, created_user):
        """Test contar usuarios"""
        # Contar todos
        total = user_crud.count_users(db_session, active_only=False)
        assert total >= 1

        # Contar solo activos
        active = user_crud.count_users(db_session, active_only=True)
        assert active >= 1
        assert active <= total

    def test_count_by_role(self, db_session, created_user):
        """Test contar usuarios por rol"""
        counts = user_crud.count_by_role(db_session)
        assert isinstance(counts, dict)
        assert len(counts) >= 1
        assert "Technician" in counts
        assert counts["Technician"] >= 1

    def test_get_recent_logins(self, db_session, created_user, sample_user_data):
        """Test obtener logins recientes"""
        # Hacer login para actualizar LastLogin
        user_crud.authenticate(
            db_session,
            username=sample_user_data["username"],
            password=sample_user_data["password"]
        )

        # Obtener logins recientes
        recent = user_crud.get_recent_logins(db_session, days=7)
        assert len(recent) >= 1
        assert any(u.Id == created_user.Id for u in recent)

    def test_get_dashboard_stats(self, db_session, created_user):
        """Test obtener estadísticas del dashboard"""
        stats = user_crud.get_dashboard_stats(db_session)

        assert isinstance(stats, dict)
        assert "total_users" in stats
        assert "active_users" in stats
        assert "inactive_users" in stats
        assert "users_by_role" in stats
        assert "users_with_station" in stats
        assert "users_without_station" in stats
        assert "recent_logins_7d" in stats

        assert stats["total_users"] >= 1
        assert stats["active_users"] >= 0
        assert stats["inactive_users"] >= 0
        assert stats["active_users"] + stats["inactive_users"] == stats["total_users"]


# ========================================
# TESTS DE CASOS ESPECIALES
# ========================================

class TestEdgeCases:
    """Tests para casos especiales y límites"""

    def test_create_user_with_whitespace(self, db_session, sample_user_data):
        """Test crear usuario con espacios en blanco"""
        sample_user_data["username"] = "  testuser2  "
        sample_user_data["email"] = "  test2@example.com  "
        sample_user_data["full_name"] = "  Test User 2  "

        user = user_crud.create_user(db_session, **sample_user_data)

        assert user.Username == "testuser2"
        assert user.Email == "test2@example.com"
        assert user.FullName == "Test User 2"

    def test_update_nonexistent_user(self, db_session):
        """Test actualizar usuario inexistente"""
        fake_id = str(uuid.uuid4())
        result = user_crud.update_user(
            db_session,
            user_id=fake_id,
            full_name="New Name"
        )
        assert result is None

    def test_pagination(self, db_session, sample_user_data):
        """Test paginación de usuarios"""
        # Crear varios usuarios
        for i in range(5):
            data = sample_user_data.copy()
            data["username"] = f"user{i}"
            data["email"] = f"user{i}@example.com"
            user_crud.create_user(db_session, **data)

        # Probar paginación
        page1 = user_crud.get_active_users(db_session, skip=0, limit=3)
        page2 = user_crud.get_active_users(db_session, skip=3, limit=3)

        assert len(page1) <= 3
        assert len(page2) >= 1

        # Verificar que no hay duplicados entre páginas
        page1_ids = {u.Id for u in page1}
        page2_ids = {u.Id for u in page2}
        assert page1_ids.isdisjoint(page2_ids)


# ========================================
# CONFIGURACIÓN PYTEST
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])