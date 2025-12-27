"""
Pruebas unitarias para el modelo Station
Verifica todas las funcionalidades del modelo de estaciones/ventanillas
Compatible con SQL Server y la estructura real del proyecto
"""

import pytest
import sys
import os
from datetime import datetime, date, timedelta
from typing import Any, Optional
import uuid

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, DataError

from app.models.station import Station
from app.models.service_type import ServiceType
from app.models.user import User
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.patient import Patient
from app.models.base import Base
from app.core.security import create_password_hash


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

    # Limpiar tablas en orden correcto (por foreign keys)
    try:
        session.execute(text("DELETE FROM ActivityLog"))
        session.execute(text("DELETE FROM NotificationLog"))
        session.execute(text("DELETE FROM DailyMetrics"))
        session.execute(text("DELETE FROM QueueState"))
        session.execute(text("DELETE FROM Tickets"))
        session.execute(text("DELETE FROM Users"))
        session.execute(text("DELETE FROM Stations"))
        session.execute(text("DELETE FROM Patients"))
        session.execute(text("DELETE FROM ServiceTypes"))
        session.execute(text("DELETE FROM Roles"))
        session.commit()
    except:
        session.rollback()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_station_data():
    """Datos de muestra para crear una estación"""
    return {
        "Name": "Ventanilla Test",
        "Code": "VT01",
        "Description": "Ventanilla de prueba para tests",
        "Location": "Planta Baja",
        "Status": "Available",
        "IsActive": True
    }


@pytest.fixture
def created_service_type(db_session):
    """Crea un ServiceType para usar en tests"""
    service_type = ServiceType(
        Code="TST",
        Name="Test Service",
        Description="Servicio de prueba",
        TicketPrefix="T",
        Priority=1,
        AverageTimeMinutes=10,
        IsActive=True
    )
    db_session.add(service_type)
    db_session.commit()
    db_session.refresh(service_type)
    return service_type


@pytest.fixture
def created_station(db_session, created_service_type):
    """Crea una estación para usar en tests"""
    station = Station(
        Name="Ventanilla Test",
        Code="VT01",
        Description="Ventanilla de prueba",
        ServiceTypeId=created_service_type.Id,
        Location="Planta Baja",
        Status="Available",
        IsActive=True
    )
    db_session.add(station)
    db_session.commit()
    db_session.refresh(station)
    return station


@pytest.fixture
def created_patient(db_session):
    """Crea un paciente para usar en tests"""
    patient = Patient(
        Id=str(uuid.uuid4()),
        FullName="Juan Perez",
        DocumentNumber="12345678",
        BirthDate=date(1990, 1, 1),
        Gender="M",
        Phone="987654321",
        Email="juan@test.com",
        IsActive=True
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture
def created_ticket(db_session, created_patient, created_service_type):
    """Crea un ticket para usar en tests"""
    ticket = Ticket(
        Id=str(uuid.uuid4()),
        TicketNumber="T001",
        PatientId=created_patient.Id,
        ServiceTypeId=created_service_type.Id,
        Status="Waiting",
        Position=1,
        EstimatedWaitTime=10
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


# ========================================
# TESTS DE CREACIÓN Y CAMPOS BÁSICOS
# ========================================

class TestStationCreation:
    """Tests para creación de estaciones"""

    def test_create_station_minimal(self, db_session):
        """Test crear estación con campos mínimos requeridos"""
        station = Station(
            Name="Ventanilla Mínima",
            Code="VM01"
        )
        db_session.add(station)
        db_session.commit()

        assert station.Id is not None
        assert station.Name == "Ventanilla Mínima"
        assert station.Code == "VM01"
        assert station.Status == "Available"  # Valor por defecto
        assert station.IsActive is True  # De ActiveMixin
        assert station.CreatedAt is not None  # De TimestampMixin
        assert station.UpdatedAt is not None  # De TimestampMixin

    def test_create_station_complete(self, db_session, created_service_type):
        """Test crear estación con todos los campos"""
        station = Station(
            Name="Ventanilla Completa",
            Code="VC01",
            Description="Descripción completa",
            ServiceTypeId=created_service_type.Id,
            Location="Segundo Piso",
            Status="Busy",
            IsActive=True
        )
        db_session.add(station)
        db_session.commit()

        assert station.Id is not None
        assert station.Name == "Ventanilla Completa"
        assert station.Code == "VC01"
        assert station.Description == "Descripción completa"
        assert station.ServiceTypeId == created_service_type.Id
        assert station.Location == "Segundo Piso"
        assert station.Status == "Busy"

    def test_create_station_duplicate_code(self, db_session):
        """Test que no se pueden crear estaciones con código duplicado"""
        station1 = Station(Name="Estación 1", Code="DUP01")
        db_session.add(station1)
        db_session.commit()

        station2 = Station(Name="Estación 2", Code="DUP01")
        db_session.add(station2)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_create_station_without_required_fields(self, db_session):
        """Test que los campos requeridos son obligatorios"""
        # Sin Name
        station = Station(Code="NF01")
        db_session.add(station)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Sin Code
        station = Station(Name="Sin Código")
        db_session.add(station)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()


# ========================================
# TESTS DE VALIDADORES
# ========================================

class TestStationValidators:
    """Tests para validadores del modelo"""

    def test_code_validator_uppercase(self, db_session):
        """Test que el código se convierte a mayúsculas"""
        station = Station(
            Name="Test Uppercase",
            Code="vt02"  # minúsculas
        )
        db_session.add(station)
        db_session.commit()

        assert station.Code == "VT02"  # Debe convertirse a mayúsculas

    def test_status_validator_valid_values(self, db_session):
        """Test que el validador acepta valores válidos de estado"""
        valid_statuses = ["Available", "Busy", "Break", "Maintenance"]

        for status in valid_statuses:
            station = Station(
                Name=f"Station {status}",
                Code=f"S{valid_statuses.index(status):02d}",
                Status=status
            )
            db_session.add(station)
            db_session.commit()
            assert station.Status == status

    def test_status_validator_invalid_value(self, db_session):
        """Test que el validador rechaza valores inválidos de estado"""
        station = Station(
            Name="Invalid Status",
            Code="IS01"
        )

        # El validador debe lanzar ValueError para estados inválidos
        with pytest.raises(ValueError) as exc_info:
            station.Status = "InvalidStatus"

        assert "Estado inválido" in str(exc_info.value)

    def test_code_format_validation(self, db_session):
        """Test diferentes formatos de código"""
        codes = ["A01", "VA001", "LAB01", "V1", "VENT10"]

        for code in codes:
            station = Station(
                Name=f"Station {code}",
                Code=code
            )
            db_session.add(station)
            db_session.commit()
            assert station.Code == code.upper()


# ========================================
# TESTS DE RELACIONES
# ========================================

class TestStationRelationships:
    """Tests para relaciones con otros modelos"""

    def test_station_service_type_relationship(self, db_session, created_service_type):
        """Test relación con ServiceType"""
        station = Station(
            Name="Station with Service",
            Code="SWS01",
            ServiceTypeId=created_service_type.Id
        )
        db_session.add(station)
        db_session.commit()
        db_session.refresh(station)

        # Verificar relación
        assert station.service_type is not None
        assert station.service_type.Id == created_service_type.Id
        assert station.service_type.Name == "Test Service"

    def test_station_users_relationship(self, db_session, created_station):
        """Test relación con usuarios asignados"""
        # Crear rol
        role = Role(
            Name="Técnico",
            Description="Rol de técnico"
        )
        db_session.add(role)
        db_session.commit()

        # Crear usuarios asignados a la estación
        user1 = User(
            Username="user1",
            Email="user1@test.com",
            FullName="Usuario 1",
            PasswordHash=create_password_hash("password"),
            RoleId=role.Id,
            StationId=created_station.Id
        )

        user2 = User(
            Username="user2",
            Email="user2@test.com",
            FullName="Usuario 2",
            PasswordHash=create_password_hash("password"),
            RoleId=role.Id,
            StationId=created_station.Id
        )

        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        db_session.refresh(created_station)

        # Verificar relación - users es un AppenderQuery, usar .all() o count()
        users_list = created_station.users.all() if hasattr(created_station.users, 'all') else list(created_station.users)
        assert len(users_list) == 2
        assert any(u.Username == "user1" for u in users_list)
        assert any(u.Username == "user2" for u in users_list)

    def test_station_current_ticket_relationship(self, db_session, created_station, created_ticket):
        """Test relación con ticket actual"""
        # Actualizar CurrentTicketId
        created_station.CurrentTicketId = created_ticket.Id
        db_session.commit()
        db_session.refresh(created_station)

        assert created_station.CurrentTicketId == created_ticket.Id


# ========================================
# TESTS DE MÉTODOS DEL MODELO
# ========================================

class TestStationMethods:
    """Tests para métodos del modelo Station"""

    def test_get_available_stations(self, db_session, created_service_type):
        """Test obtener estaciones disponibles"""
        # Crear estaciones con diferentes estados
        station1 = Station(
            Name="Available 1",
            Code="AV01",
            Status="Available",
            ServiceTypeId=created_service_type.Id
        )

        station2 = Station(
            Name="Available 2",
            Code="AV02",
            Status="Available",
            ServiceTypeId=created_service_type.Id
        )

        station3 = Station(
            Name="Busy Station",
            Code="BS01",
            Status="Busy",
            ServiceTypeId=created_service_type.Id
        )

        station4 = Station(
            Name="Inactive Station",
            Code="IN01",
            Status="Available",
            ServiceTypeId=created_service_type.Id,
            IsActive=False
        )

        db_session.add_all([station1, station2, station3, station4])
        db_session.commit()

        # Obtener estaciones disponibles
        available = Station.get_available_stations(db_session)

        assert len(available) == 2
        assert station1 in available
        assert station2 in available
        assert station3 not in available  # Busy
        assert station4 not in available  # Inactive

    def test_get_available_stations_by_service_type(self, db_session):
        """Test obtener estaciones disponibles filtradas por tipo de servicio"""
        # Crear dos tipos de servicio
        service1 = ServiceType(
            Code="SRV1",
            Name="Servicio 1",
            TicketPrefix="S1",
            Priority=1,
            AverageTimeMinutes=10
        )

        service2 = ServiceType(
            Code="SRV2",
            Name="Servicio 2",
            TicketPrefix="S2",
            Priority=2,
            AverageTimeMinutes=15
        )

        db_session.add_all([service1, service2])
        db_session.commit()

        # Crear estaciones para cada servicio
        station1 = Station(
            Name="Station Service 1",
            Code="SS1",
            Status="Available",
            ServiceTypeId=service1.Id
        )

        station2 = Station(
            Name="Station Service 2",
            Code="SS2",
            Status="Available",
            ServiceTypeId=service2.Id
        )

        station3 = Station(
            Name="Station No Service",
            Code="SNS",
            Status="Available",
            ServiceTypeId=None
        )

        db_session.add_all([station1, station2, station3])
        db_session.commit()

        # Filtrar por service_type_id
        available_srv1 = Station.get_available_stations(db_session, service1.Id)
        available_srv2 = Station.get_available_stations(db_session, service2.Id)
        available_all = Station.get_available_stations(db_session)

        assert len(available_srv1) == 1
        assert station1 in available_srv1

        assert len(available_srv2) == 1
        assert station2 in available_srv2

        assert len(available_all) == 3

    def test_assign_ticket_method(self, db_session, created_station, created_ticket):
        """Test método assign_ticket"""
        # Asignar ticket a la estación
        created_station.assign_ticket(created_ticket)

        assert created_station.CurrentTicketId == created_ticket.Id
        assert created_station.Status == "Busy"

    def test_release_ticket_method(self, db_session, created_station, created_ticket):
        """Test método release_ticket"""
        # Primero asignar un ticket
        created_station.CurrentTicketId = created_ticket.Id
        created_station.Status = "Busy"
        db_session.commit()

        # Liberar el ticket
        created_station.release_ticket()

        assert created_station.CurrentTicketId is None
        assert created_station.Status == "Available"

    def test_set_status_methods(self, db_session, created_station):
        """Test métodos para cambiar estado"""
        # Test set_busy
        created_station.set_busy()
        assert created_station.Status == "Busy"

        # Test set_available
        created_station.set_available()
        assert created_station.Status == "Available"

        # Test set_break
        created_station.set_break()
        assert created_station.Status == "Break"

        # Test set_maintenance
        created_station.set_maintenance()
        assert created_station.Status == "Maintenance"

        # Test set_offline
        created_station.set_offline()
        assert created_station.Status == "Offline"

    def test_station_properties(self, db_session, created_station):
        """Test propiedades calculadas de la estación"""
        # Estado inicial
        created_station.Status = "Available"
        created_station.IsActive = True
        created_station.CurrentTicketId = None
        db_session.commit()

        # Test is_available
        assert created_station.is_available is True

        # Test is_busy
        assert created_station.is_busy is False

        # Test can_receive_patients
        assert created_station.can_receive_patients is True

        # Cambiar a ocupado
        created_station.Status = "Busy"
        assert created_station.is_available is False
        assert created_station.is_busy is True
        assert created_station.can_receive_patients is False

        # Test display_name
        assert created_station.Code in created_station.display_name

        # Test status_display
        assert created_station.status_display == "Ocupada"

    def test_to_dict_method(self, db_session, created_station):
        """Test método to_dict"""
        station_dict = created_station.to_dict()

        assert isinstance(station_dict, dict)
        assert station_dict["Id"] == created_station.Id
        assert station_dict["Name"] == created_station.Name
        assert station_dict["Code"] == created_station.Code
        assert "CreatedAt" in station_dict
        assert "UpdatedAt" in station_dict

    def test_get_by_code_class_method(self, db_session):
        """Test método de clase get_by_code"""
        station = Station(
            Name="By Code Test",
            Code="BCT01"
        )
        db_session.add(station)
        db_session.commit()

        # Buscar por código exacto
        found = Station.get_by_code(db_session, "BCT01")
        assert found is not None
        assert found.Id == station.Id
        assert found.Code == "BCT01"

        # Buscar por código en minúsculas (debe convertir a mayúsculas)
        found_lower = Station.get_by_code(db_session, "bct01")
        assert found_lower is not None
        assert found_lower.Id == station.Id

        # Buscar código que no existe
        not_found = Station.get_by_code(db_session, "NOEXIST")
        assert not_found is None


# ========================================
# TESTS DE HERENCIA DE MIXINS
# ========================================

class TestStationMixins:
    """Tests para funcionalidades heredadas de mixins"""

    def test_timestamp_mixin(self, db_session):
        """Test que TimestampMixin funciona correctamente"""
        station = Station(
            Name="Timestamp Test",
            Code="TM01"
        )
        db_session.add(station)
        db_session.commit()

        assert station.CreatedAt is not None
        assert station.UpdatedAt is not None
        assert isinstance(station.CreatedAt, datetime)
        assert isinstance(station.UpdatedAt, datetime)

        # UpdatedAt debe ser igual o posterior a CreatedAt
        assert station.UpdatedAt >= station.CreatedAt

    def test_timestamp_update(self, db_session):
        """Test que UpdatedAt se actualiza automáticamente"""
        station = Station(
            Name="Update Test",
            Code="UT01"
        )
        db_session.add(station)
        db_session.commit()

        original_updated = station.UpdatedAt

        # Esperar un momento y actualizar
        import time
        time.sleep(0.1)

        station.Name = "Updated Name"
        db_session.commit()
        db_session.refresh(station)

        # UpdatedAt debe haber cambiado
        assert station.UpdatedAt > original_updated

    def test_active_mixin(self, db_session):
        """Test que ActiveMixin funciona correctamente"""
        station = Station(
            Name="Active Test",
            Code="AM01"
        )
        db_session.add(station)
        db_session.commit()

        # Por defecto debe estar activo
        assert station.IsActive is True

        # Desactivar
        station.IsActive = False
        db_session.commit()

        assert station.IsActive is False

    def test_base_model_inheritance(self, db_session):
        """Test que hereda correctamente de BaseModel"""
        station = Station(
            Name="Base Test",
            Code="BM01"
        )
        db_session.add(station)
        db_session.commit()

        # Debe tener __tablename__
        assert station.__tablename__ == 'Stations'

        # Debe tener los métodos base
        assert hasattr(station, 'to_dict')
        station_dict = station.to_dict()
        assert isinstance(station_dict, dict)


# ========================================
# TESTS DE CASOS EDGE
# ========================================

class TestStationEdgeCases:
    """Tests para casos límite y especiales"""

    def test_long_description(self, db_session):
        """Test descripción de longitud máxima"""
        long_desc = "D" * 200  # Máximo 200 caracteres
        station = Station(
            Name="Long Desc",
            Code="LD01",
            Description=long_desc
        )
        db_session.add(station)
        db_session.commit()

        assert len(station.Description) == 200

    def test_null_optional_fields(self, db_session):
        """Test que los campos opcionales pueden ser NULL"""
        station = Station(
            Name="Null Fields",
            Code="NF01",
            Description=None,
            ServiceTypeId=None,
            Location=None,
            CurrentTicketId=None
        )
        db_session.add(station)
        db_session.commit()

        assert station.Description is None
        assert station.ServiceTypeId is None
        assert station.Location is None
        assert station.CurrentTicketId is None

    def test_special_characters_in_name(self, db_session):
        """Test caracteres especiales en el nombre"""
        station = Station(
            Name="Ventanilla Ñ°#1 - Análisis",
            Code="SC01"
        )
        db_session.add(station)
        db_session.commit()

        assert "Ñ" in station.Name
        assert "#" in station.Name

    def test_concurrent_status_changes(self, db_session):
        """Test cambios de estado concurrentes"""
        station = Station(
            Name="Concurrent",
            Code="CC01",
            Status="Available"
        )
        db_session.add(station)
        db_session.commit()

        # Simular cambios rápidos de estado
        states = ["Busy", "Available", "Break", "Available", "Maintenance"]
        for state in states:
            station.Status = state
            db_session.commit()
            assert station.Status == state

    def test_station_lifecycle(self, db_session, created_service_type):
        """Test ciclo de vida completo de una estación"""
        # Crear
        station = Station(
            Name="Lifecycle Station",
            Code="LC01",
            ServiceTypeId=created_service_type.Id
        )
        db_session.add(station)
        db_session.commit()

        station_id = station.Id

        # Actualizar
        station.Name = "Updated Station"
        station.Location = "New Location"
        db_session.commit()

        # Verificar actualización
        updated = db_session.query(Station).filter_by(Id=station_id).first()
        assert updated.Name == "Updated Station"
        assert updated.Location == "New Location"

        # Soft delete (desactivar)
        station.IsActive = False
        db_session.commit()

        # Verificar soft delete
        deleted = db_session.query(Station).filter_by(Id=station_id).first()
        assert deleted is not None  # Todavía existe
        assert deleted.IsActive is False

    def test_empty_string_fields(self, db_session):
        """Test campos con strings vacíos vs NULL"""
        station = Station(
            Name="Empty String Test",
            Code="EST01",
            Description="",  # String vacío
            Location=""      # String vacío
        )
        db_session.add(station)
        db_session.commit()

        # SQL Server puede tratar strings vacíos diferente a NULL
        assert station.Description == ""
        assert station.Location == ""

    def test_unicode_support(self, db_session):
        """Test soporte para caracteres Unicode/especiales"""
        # SQL Server puede tener problemas con ciertos caracteres Unicode
        # Usar caracteres que SQL Server maneje correctamente
        station = Station(
            Name="Estación Especial ñ á é í ó ú",
            Code="UNI01",
            Description="Descripción con caracteres especiales: ñ, á, é, í, ó, ú"
        )
        db_session.add(station)
        db_session.commit()
        db_session.refresh(station)

        # Verificar que los caracteres especiales latinos se guardan correctamente
        assert "ñ" in station.Name
        assert "á" in station.Name
        assert "é" in station.Name
        assert "Descripción" in station.Description


# ========================================
# TESTS DE RENDIMIENTO Y CARGA
# ========================================

class TestStationPerformance:
    """Tests de rendimiento y carga"""

    def test_bulk_insert_stations(self, db_session):
        """Test inserción masiva de estaciones"""
        stations = []
        for i in range(50):
            station = Station(
                Name=f"Bulk Station {i:03d}",
                Code=f"BLK{i:03d}",
                Description=f"Descripción para estación {i}",
                Status="Available" if i % 2 == 0 else "Busy"
            )
            stations.append(station)

        db_session.bulk_save_objects(stations)
        db_session.commit()

        # Verificar que se insertaron todas
        count = db_session.query(Station).count()
        assert count == 50

    def test_query_performance_with_filters(self, db_session, created_service_type):
        """Test rendimiento de consultas con filtros"""
        # Crear varias estaciones
        for i in range(20):
            station = Station(
                Name=f"Perf Station {i:02d}",
                Code=f"PS{i:02d}",
                ServiceTypeId=created_service_type.Id if i % 3 == 0 else None,
                Status="Available" if i % 2 == 0 else "Busy",
                IsActive=i % 4 != 0
            )
            db_session.add(station)
        db_session.commit()

        # Consultas con diferentes filtros
        active_available = db_session.query(Station).filter(
            Station.IsActive == True,
            Station.Status == "Available"
        ).all()

        with_service = db_session.query(Station).filter(
            Station.ServiceTypeId == created_service_type.Id
        ).all()

        # Verificar resultados
        assert len(active_available) > 0
        assert len(with_service) > 0


# ========================================
# TESTS DE CONSTRAINTS Y VALIDACIONES BD
# ========================================

class TestStationDatabaseConstraints:
    """Tests para constraints a nivel de base de datos"""

    def test_unique_code_constraint(self, db_session):
        """Test constraint UNIQUE en Code"""
        station1 = Station(Name="Station 1", Code="UNIQ01")
        db_session.add(station1)
        db_session.commit()

        station2 = Station(Name="Station 2", Code="UNIQ01")
        db_session.add(station2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "UNIQUE" in str(exc_info.value) or "duplicate" in str(exc_info.value).lower()
        db_session.rollback()

    def test_foreign_key_constraint(self, db_session):
        """Test constraint de foreign key con ServiceTypeId"""
        station = Station(
            Name="FK Test",
            Code="FK01",
            ServiceTypeId=99999  # ID que no existe
        )
        db_session.add(station)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "FOREIGN KEY" in str(exc_info.value) or "ServiceTypes" in str(exc_info.value)
        db_session.rollback()

    def test_check_constraint_status(self, db_session):
        """Test constraint CHECK en Status"""
        station = Station(
            Name="Check Test",
            Code="CHK01"
        )
        db_session.add(station)
        db_session.commit()

        # Intentar actualizar con SQL directo para bypass del validador
        try:
            db_session.execute(
                text("UPDATE Stations SET Status = :status WHERE Id = :id"),
                {"status": "InvalidStatus", "id": station.Id}
            )
            db_session.commit()
            assert False, "Debería fallar el constraint CHECK"
        except IntegrityError:
            # Esperado - el constraint CHECK debe rechazar el valor
            db_session.rollback()
            pass


# ========================================
# CONFIGURACIÓN PYTEST
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])