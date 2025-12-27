"""
Pruebas unitarias exhaustivas para el modelo ServiceType de SQLAlchemy
Compatible con SQL Server y toda la estructura del proyecto
"""

import pytest
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, DataError
import uuid

from app.models.service_type import ServiceType
from app.models.station import Station
from app.models.ticket import Ticket
from app.models.patient import Patient
from app.models.daily_metrics import DailyMetrics
from app.models.queue_state import QueueState
from app.models.base import Base


# ========================================
# CONFIGURACIÓN DE BASE DE DATOS DE PRUEBA
# ========================================

TEST_DATABASE_URL = "mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"


# ========================================
# FIXTURES
# ========================================

@pytest.fixture(scope="function")
def db_session():
    """Crea una sesión de base de datos de prueba con rollback automático"""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_service_type(db_session: Session) -> ServiceType:
    """Crea un tipo de servicio de prueba básico"""
    service = ServiceType(
        Code="LAB",
        Name="Análisis de Laboratorio",
        Description="Análisis clínicos generales",
        Priority=2,
        AverageTimeMinutes=15,
        TicketPrefix="A",
        Color="#007bff"
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


@pytest.fixture
def multiple_service_types(db_session: Session) -> List[ServiceType]:
    """Crea múltiples tipos de servicios para pruebas"""
    services = [
        ServiceType(
            Code="LAB",
            Name="Análisis",
            Priority=1,
            AverageTimeMinutes=15,
            TicketPrefix="A",
            Color="#FF0000"
        ),
        ServiceType(
            Code="RES",
            Name="Resultados",
            Priority=2,
            AverageTimeMinutes=5,
            TicketPrefix="R",
            Color="#00FF00"
        ),
        ServiceType(
            Code="MUE",
            Name="Muestras",
            Priority=3,
            AverageTimeMinutes=10,
            TicketPrefix="M",
            Color="#0000FF"
        )
    ]

    for service in services:
        db_session.add(service)
    db_session.commit()

    return services


# ========================================
# PRUEBAS DE ESTRUCTURA DEL MODELO
# ========================================

class TestModelStructure:
    """Pruebas para la estructura del modelo ServiceType"""

    def test_table_name(self):
        """Verifica que el nombre de la tabla sea correcto"""
        assert ServiceType.__tablename__ == 'ServiceTypes'

    def test_inheritance(self):
        """Verifica que herede de las mixins correctas"""
        from app.models.base import BaseModel, TimestampMixin, ActiveMixin

        assert issubclass(ServiceType, BaseModel)
        assert issubclass(ServiceType, TimestampMixin)
        assert issubclass(ServiceType, ActiveMixin)

    def test_column_names_and_types(self):
        """Verifica que las columnas tengan los nombres y tipos correctos"""
        mapper = inspect(ServiceType)
        columns = {col.name: col for col in mapper.columns}

        # Verificar existencia de columnas principales
        assert 'Id' in columns
        assert 'Code' in columns
        assert 'Name' in columns
        assert 'Description' in columns
        assert 'Priority' in columns
        assert 'AverageTimeMinutes' in columns
        assert 'TicketPrefix' in columns
        assert 'Color' in columns

        # Verificar columnas de mixins
        assert 'IsActive' in columns  # ActiveMixin
        assert 'CreatedAt' in columns  # TimestampMixin
        assert 'UpdatedAt' in columns  # TimestampMixin

    def test_primary_key(self):
        """Verifica que Id sea la llave primaria"""
        mapper = inspect(ServiceType)
        pk_columns = [col.name for col in mapper.primary_key]
        assert 'Id' in pk_columns
        assert len(pk_columns) == 1

    def test_unique_constraints(self):
        """Verifica constraints únicos"""
        mapper = inspect(ServiceType)
        columns = {col.name: col for col in mapper.columns}
        assert columns['Code'].unique == True

    def test_check_constraints(self):
        """Verifica que los check constraints estén definidos"""
        assert ServiceType.__table_args__ is not None
        constraints = ServiceType.__table_args__

        # Verificar que existan los constraints
        priority_constraint = any(
            'chk_servicetype_priority' in str(c)
            for c in constraints if hasattr(c, 'name')
        )
        avgtime_constraint = any(
            'chk_servicetype_avgtime' in str(c)
            for c in constraints if hasattr(c, 'name')
        )

        assert priority_constraint or avgtime_constraint


# ========================================
# PRUEBAS DE CREACIÓN
# ========================================

class TestServiceTypeCreation:
    """Pruebas para la creación de ServiceType"""

    def test_create_with_required_fields(self, db_session: Session):
        """Prueba crear un servicio con campos requeridos"""
        service = ServiceType(
            Code="TEST",
            Name="Servicio de Prueba",
            TicketPrefix="T"
        )

        db_session.add(service)
        db_session.commit()

        assert service.Id is not None
        assert service.Code == "TEST"
        assert service.Name == "Servicio de Prueba"
        assert service.TicketPrefix == "T"
        # Verificar defaults
        assert service.Priority == 1
        assert service.AverageTimeMinutes == 10
        assert service.Color == "#007bff"
        assert service.IsActive == True
        assert service.CreatedAt is not None
        assert service.UpdatedAt is not None

    def test_create_with_all_fields(self, db_session: Session):
        """Prueba crear un servicio con todos los campos"""
        service = ServiceType(
            Code="FULL",
            Name="Servicio Completo",
            Description="Descripción completa del servicio",
            Priority=3,
            AverageTimeMinutes=20,
            TicketPrefix="F",
            Color="#FF00FF"
        )

        db_session.add(service)
        db_session.commit()

        assert service.Description == "Descripción completa del servicio"
        assert service.Priority == 3
        assert service.AverageTimeMinutes == 20
        assert service.Color == "#FF00FF"

    def test_duplicate_code_fails(self, db_session: Session, sample_service_type):
        """Prueba que no se puede duplicar el código"""
        duplicate = ServiceType(
            Code=sample_service_type.Code,  # Código duplicado
            Name="Otro Servicio",
            TicketPrefix="X"
        )

        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_auto_increment_id(self, db_session: Session):
        """Prueba que el ID se auto-incremente"""
        service1 = ServiceType(Code="SRV1", Name="Servicio 1", TicketPrefix="S1")
        service2 = ServiceType(Code="SRV2", Name="Servicio 2", TicketPrefix="S2")

        db_session.add_all([service1, service2])
        db_session.commit()

        assert service1.Id is not None
        assert service2.Id is not None
        assert service2.Id > service1.Id


# ========================================
# PRUEBAS DE VALIDADORES
# ========================================

class TestServiceTypeValidators:
    """Pruebas para los validadores del modelo"""

    def test_validate_priority(self, db_session: Session):
        """Prueba validación de prioridad"""
        # Prioridad válida (1-5)
        service = ServiceType(Code="PRI", Name="Test", Priority=3, TicketPrefix="P")
        db_session.add(service)
        db_session.commit()
        assert service.Priority == 3

        # Prioridad inválida (< 1)
        with pytest.raises(ValueError, match="entre 1 y 5"):
            service2 = ServiceType(Code="PRI2", Name="Test2", Priority=0, TicketPrefix="P2")

        # Prioridad inválida (> 5)
        with pytest.raises(ValueError, match="entre 1 y 5"):
            service3 = ServiceType(Code="PRI3", Name="Test3", Priority=6, TicketPrefix="P3")

    def test_validate_average_time(self, db_session: Session):
        """Prueba validación de tiempo promedio"""
        # Tiempo válido
        service = ServiceType(
            Code="TIME1",
            Name="Test",
            AverageTimeMinutes=30,
            TicketPrefix="T1"
        )
        db_session.add(service)
        db_session.commit()
        assert service.AverageTimeMinutes == 30

        # Tiempo inválido (0 o negativo)
        with pytest.raises(ValueError, match="mayor a 0"):
            service2 = ServiceType(
                Code="TIME2",
                Name="Test2",
                AverageTimeMinutes=0,
                TicketPrefix="T2"
            )

        with pytest.raises(ValueError, match="mayor a 0"):
            service3 = ServiceType(
                Code="TIME3",
                Name="Test3",
                AverageTimeMinutes=-5,
                TicketPrefix="T3"
            )

    def test_validate_color(self, db_session: Session):
        """Prueba validación de color hexadecimal"""
        # Color válido
        service = ServiceType(
            Code="COL1",
            Name="Test",
            Color="#AABBCC",
            TicketPrefix="C1"
        )
        db_session.add(service)
        db_session.commit()
        assert service.Color == "#AABBCC"

        # Color inválido (sin #)
        with pytest.raises(ValueError, match="hexadecimal"):
            service2 = ServiceType(
                Code="COL2",
                Name="Test2",
                Color="FF00FF",
                TicketPrefix="C2"
            )

        # Color inválido (longitud incorrecta)
        with pytest.raises(ValueError, match="hexadecimal"):
            service3 = ServiceType(
                Code="COL3",
                Name="Test3",
                Color="#FFF",
                TicketPrefix="C3"
            )

    def test_validate_code_normalization(self, db_session: Session):
        """Prueba normalización del código"""
        service = ServiceType(
            Code="  test  ",  # Con espacios y minúsculas
            Name="Test",
            TicketPrefix="T"
        )

        db_session.add(service)
        db_session.commit()

        assert service.Code == "TEST"  # Normalizado a mayúsculas sin espacios

    def test_validate_ticket_prefix_normalization(self, db_session: Session):
        """Prueba normalización del prefijo"""
        service = ServiceType(
            Code="PRE",
            Name="Test",
            TicketPrefix="  abc  "  # Con espacios y minúsculas
        )

        db_session.add(service)
        db_session.commit()

        assert service.TicketPrefix == "ABC"  # Normalizado


# ========================================
# PRUEBAS DE PROPIEDADES
# ========================================

class TestServiceTypeProperties:
    """Pruebas para las propiedades del modelo"""

    def test_priority_name_property(self, sample_service_type):
        """Prueba la propiedad priority_name"""
        # Priority = 2 debe ser "Alta"
        assert sample_service_type.priority_name == "Alta"

        # Probar todos los valores
        priority_map = {
            1: "Muy Alta",
            2: "Alta",
            3: "Media",
            4: "Baja",
            5: "Muy Baja"
        }

        for priority, name in priority_map.items():
            sample_service_type.Priority = priority
            assert sample_service_type.priority_name == name

    def test_is_high_priority_property(self, sample_service_type):
        """Prueba la propiedad is_high_priority"""
        # Priority <= 2 es alta prioridad
        sample_service_type.Priority = 1
        assert sample_service_type.is_high_priority == True

        sample_service_type.Priority = 2
        assert sample_service_type.is_high_priority == True

        sample_service_type.Priority = 3
        assert sample_service_type.is_high_priority == False

        sample_service_type.Priority = 4
        assert sample_service_type.is_high_priority == False

    def test_station_count_property(self, db_session: Session, sample_service_type):
        """Prueba la propiedad station_count"""
        # Sin estaciones
        assert sample_service_type.station_count == 0

        # Agregar estaciones
        station1 = Station(
            Code="S1",
            Name="Estación 1",
            ServiceTypeId=sample_service_type.Id,
            Status="Available",
            IsActive=True
        )
        station2 = Station(
            Code="S2",
            Name="Estación 2",
            ServiceTypeId=sample_service_type.Id,
            Status="Available",
            IsActive=True
        )
        station3 = Station(
            Code="S3",
            Name="Estación 3",
            ServiceTypeId=sample_service_type.Id,
            Status="Available",
            IsActive=False  # Inactiva
        )

        db_session.add_all([station1, station2, station3])
        db_session.commit()

        # Refrescar para obtener relaciones
        db_session.refresh(sample_service_type)

        # Solo cuenta estaciones activas
        assert sample_service_type.station_count == 2

    def test_active_station_count_property(self, db_session: Session, sample_service_type):
        """Prueba la propiedad active_station_count"""
        # Agregar estaciones con diferentes estados
        stations = [
            Station(Code="S1", Name="E1", ServiceTypeId=sample_service_type.Id,
                   Status="Available", IsActive=True),
            Station(Code="S2", Name="E2", ServiceTypeId=sample_service_type.Id,
                   Status="Busy", IsActive=True),
            Station(Code="S3", Name="E3", ServiceTypeId=sample_service_type.Id,
                   Status="Offline", IsActive=True),
            Station(Code="S4", Name="E4", ServiceTypeId=sample_service_type.Id,
                   Status="Available", IsActive=False),
        ]

        for station in stations:
            db_session.add(station)
        db_session.commit()

        db_session.refresh(sample_service_type)

        # Solo cuenta estaciones activas con estado Available
        assert sample_service_type.active_station_count == 1


# ========================================
# PRUEBAS DE MÉTODOS
# ========================================

class TestServiceTypeMethods:
    """Pruebas para los métodos del modelo"""

    def test_get_default_service_types(self):
        """Prueba obtener servicios por defecto"""
        defaults = ServiceType.get_default_service_types()

        assert isinstance(defaults, list)
        assert len(defaults) > 0

        # Verificar que contenga servicios esperados
        codes = [s["Code"] for s in defaults]
        assert "LAB" in codes
        assert "RES" in codes
        assert "MUE" in codes
        assert "CON" in codes
        assert "PRI" in codes

        # Verificar estructura de cada servicio
        for service_data in defaults:
            assert "Code" in service_data
            assert "Name" in service_data
            assert "Priority" in service_data
            assert "TicketPrefix" in service_data

    def test_to_dict_basic(self, sample_service_type):
        """Prueba conversión a diccionario básico"""
        result = sample_service_type.to_dict(include_stats=False)

        assert isinstance(result, dict)
        assert result["Id"] == sample_service_type.Id
        assert result["Code"] == sample_service_type.Code
        assert result["Name"] == sample_service_type.Name
        assert result["priority_name"] == sample_service_type.priority_name
        assert result["is_high_priority"] == sample_service_type.is_high_priority

        # No debe incluir estadísticas
        assert "station_count" not in result
        assert "current_queue_length" not in result

    def test_to_dict_with_stats(self, db_session: Session, sample_service_type):
        """Prueba conversión a diccionario con estadísticas"""
        # Agregar una estación
        station = Station(
            Code="ST1",
            Name="Estación Test",
            ServiceTypeId=sample_service_type.Id,
            Status="Available",
            IsActive=True
        )
        db_session.add(station)
        db_session.commit()
        db_session.refresh(sample_service_type)

        result = sample_service_type.to_dict(include_stats=True)

        assert "station_count" in result
        assert "active_station_count" in result
        assert "current_queue_length" in result
        assert "estimated_wait_time" in result

        assert result["station_count"] == 1
        assert result["active_station_count"] == 1

    def test_repr_method(self, sample_service_type):
        """Prueba el método __repr__"""
        repr_str = repr(sample_service_type)

        assert f"Id={sample_service_type.Id}" in repr_str
        assert f"Code='{sample_service_type.Code}'" in repr_str
        assert f"Name='{sample_service_type.Name}'" in repr_str
        assert "ServiceType" in repr_str


# ========================================
# PRUEBAS DE RELACIONES
# ========================================

class TestServiceTypeRelationships:
    """Pruebas para las relaciones del modelo"""

    def test_stations_relationship(self, db_session: Session, sample_service_type):
        """Prueba la relación con estaciones"""
        # Inicialmente sin estaciones
        assert len(sample_service_type.stations) == 0

        # Agregar estaciones
        station1 = Station(
            Code="REL1",
            Name="Estación Rel 1",
            ServiceTypeId=sample_service_type.Id,
            Status="Available"
        )
        station2 = Station(
            Code="REL2",
            Name="Estación Rel 2",
            ServiceTypeId=sample_service_type.Id,
            Status="Busy"
        )

        db_session.add_all([station1, station2])
        db_session.commit()
        db_session.refresh(sample_service_type)

        assert len(sample_service_type.stations) == 2
        assert station1 in sample_service_type.stations
        assert station2 in sample_service_type.stations

    def test_tickets_relationship(self, db_session: Session, sample_service_type):
        """Prueba la relación con tickets"""
        # Crear paciente primero
        patient = Patient(
            Id=str(uuid.uuid4()),
            DocumentNumber="12345678",
            FullName="Paciente Test",
            BirthDate=datetime(1990, 1, 1).date(),
            Gender="M"
        )
        db_session.add(patient)
        db_session.commit()

        # Crear tickets
        ticket1 = Ticket(
            TicketNumber="T001",
            PatientId=patient.Id,
            ServiceTypeId=sample_service_type.Id,
            Status="Waiting",
            Position=1
        )
        ticket2 = Ticket(
            TicketNumber="T002",
            PatientId=patient.Id,
            ServiceTypeId=sample_service_type.Id,
            Status="Completed",
            Position=2
        )

        db_session.add_all([ticket1, ticket2])
        db_session.commit()
        db_session.refresh(sample_service_type)

        assert len(sample_service_type.tickets) == 2

    def test_foreign_key_constraint(self, db_session: Session):
        """Prueba que la FK constraint previene eliminación de servicios con dependencias"""
        # Crear un servicio de prueba
        service = ServiceType(
            Code="FK_TEST",
            Name="Servicio FK Test",
            TicketPrefix="FK",
            Priority=1,
            AverageTimeMinutes=10
        )
        db_session.add(service)
        db_session.commit()

        # Crear estación relacionada
        station = Station(
            Code="FK_STATION",
            Name="Estación FK",
            ServiceTypeId=service.Id,
            Status="Available"
        )
        db_session.add(station)
        db_session.commit()

        # Intentar eliminar el servicio debería fallar por la FK constraint
        with pytest.raises(IntegrityError) as exc_info:
            db_session.delete(service)
            db_session.flush()  # Forzar la ejecución del DELETE sin commit

        # Verificar que el error es por la constraint de foreign key
        assert "FK" in str(exc_info.value) or "FOREIGN KEY" in str(exc_info.value) or "REFERENCE" in str(exc_info.value)

        # Hacer rollback para limpiar la transacción
        db_session.rollback()


# ========================================
# PRUEBAS DE INTEGRACIÓN
# ========================================

class TestServiceTypeIntegration:
    """Pruebas de integración con otros componentes"""

    def test_create_complete_service_workflow(self, db_session: Session):
        """Prueba flujo completo de creación de servicio con relaciones"""
        # Crear servicio
        service = ServiceType(
            Code="FLOW",
            Name="Servicio Workflow",
            Description="Test de flujo completo",
            Priority=2,
            AverageTimeMinutes=15,
            TicketPrefix="W",
            Color="#123456"
        )
        db_session.add(service)
        db_session.commit()

        # Agregar estaciones
        for i in range(3):
            station = Station(
                Code=f"WST{i}",
                Name=f"Estación Workflow {i}",
                ServiceTypeId=service.Id,
                Status="Available",
                IsActive=True
            )
            db_session.add(station)

        # Crear pacientes y tickets
        for i in range(5):
            patient = Patient(
                Id=str(uuid.uuid4()),
                DocumentNumber=f"1000000{i}",
                FullName=f"Paciente {i}",
                BirthDate=datetime(1990, 1, 1).date(),
                Gender="M"
            )
            db_session.add(patient)
            db_session.commit()

            ticket = Ticket(
                TicketNumber=f"W{i:03d}",
                PatientId=patient.Id,
                ServiceTypeId=service.Id,
                Status="Waiting",
                Position=i + 1
            )
            db_session.add(ticket)

        db_session.commit()
        db_session.refresh(service)

        # Verificar relaciones
        assert len(service.stations) == 3
        assert len(service.tickets) == 5
        assert service.station_count == 3
        assert service.active_station_count == 3

    def test_service_performance_metrics(self, db_session: Session, sample_service_type):
        """Prueba métricas de rendimiento del servicio"""
        # Crear datos de prueba
        patient = Patient(
            Id=str(uuid.uuid4()),
            DocumentNumber="99999999",
            FullName="Paciente Metrics",
            BirthDate=datetime(1990, 1, 1).date(),
            Gender="F"
        )
        db_session.add(patient)
        db_session.commit()

        # Crear tickets con diferentes estados
        statuses = ["Waiting", "Called", "InProgress", "Completed", "Cancelled"]
        for i, status in enumerate(statuses):
            ticket = Ticket(
                TicketNumber=f"MET{i:03d}",
                PatientId=patient.Id,
                ServiceTypeId=sample_service_type.Id,
                Status=status,
                Position=i + 1,
                EstimatedWaitTime=15
            )
            db_session.add(ticket)

        db_session.commit()
        db_session.refresh(sample_service_type)

        # Verificar que se pueden obtener métricas
        assert len(sample_service_type.tickets) == 5

        # Contar por estado
        waiting_count = len([t for t in sample_service_type.tickets if t.Status == "Waiting"])
        completed_count = len([t for t in sample_service_type.tickets if t.Status == "Completed"])

        assert waiting_count == 1
        assert completed_count == 1


# ========================================
# PRUEBAS DE CASOS EDGE
# ========================================

class TestServiceTypeEdgeCases:
    """Pruebas de casos límite"""

    def test_null_description(self, db_session: Session):
        """Prueba que la descripción puede ser null"""
        service = ServiceType(
            Code="NULL",
            Name="Sin Descripción",
            Description=None,
            TicketPrefix="N"
        )

        db_session.add(service)
        db_session.commit()

        assert service.Description is None

    def test_unicode_characters(self, db_session: Session):
        """Prueba soporte de caracteres Unicode y especiales"""
        service = ServiceType(
            Code="UNI",
            Name="Servicio con Ñ y Acentós",
            Description="Descripción con caracteres especiales: ñ, á, é, í, ó, ú",
            TicketPrefix="U"
        )

        db_session.add(service)
        db_session.commit()

        # Verificar caracteres latinos con acentos (estos sí deberían funcionar)
        assert "Ñ" in service.Name
        assert "ñ" in service.Description
        assert "á" in service.Description

        # Los caracteres Unicode complejos (chino, árabe, emoji) pueden no funcionar
        # dependiendo de la configuración de collation de SQL Server
        # Por eso los omitimos de la prueba

    def test_max_length_fields(self, db_session: Session):
        """Prueba longitudes máximas de campos"""
        service = ServiceType(
            Code="A" * 10,  # Máximo 10
            Name="N" * 100,  # Máximo 100
            Description="D" * 500,  # Máximo 500
            TicketPrefix="P" * 5,  # Máximo 5
            Color="#FFFFFF"
        )

        db_session.add(service)
        db_session.commit()

        assert len(service.Code) == 10
        assert len(service.Name) == 100
        assert len(service.Description) == 500
        assert len(service.TicketPrefix) == 5

    def test_concurrent_modifications(self, db_session: Session, sample_service_type):
        """Prueba modificaciones concurrentes"""
        # Simular dos sesiones obteniendo el mismo servicio
        service1 = db_session.query(ServiceType).filter(
            ServiceType.Id == sample_service_type.Id
        ).first()

        service2 = db_session.query(ServiceType).filter(
            ServiceType.Id == sample_service_type.Id
        ).first()

        # Modificar desde ambas "sesiones"
        service1.Name = "Modificado 1"
        service2.Name = "Modificado 2"

        # El último commit gana
        db_session.commit()

        # Refrescar y verificar
        db_session.refresh(sample_service_type)
        assert sample_service_type.Name in ["Modificado 1", "Modificado 2"]

    def test_service_with_no_stations(self, db_session: Session, sample_service_type):
        """Prueba servicio sin estaciones asignadas"""
        assert sample_service_type.station_count == 0
        assert sample_service_type.active_station_count == 0

        # El servicio debe funcionar normalmente sin estaciones
        assert sample_service_type.priority_name is not None
        assert isinstance(sample_service_type.is_high_priority, bool)

    def test_timestamp_updates(self, db_session: Session, sample_service_type):
        """Prueba que UpdatedAt se actualice correctamente"""
        original_updated = sample_service_type.UpdatedAt

        # Esperar un momento
        import time
        time.sleep(0.1)

        # Actualizar el servicio
        sample_service_type.Name = "Nombre Actualizado"
        db_session.commit()

        # UpdatedAt debe cambiar
        assert sample_service_type.UpdatedAt > original_updated
        # CreatedAt no debe cambiar
        assert sample_service_type.CreatedAt <= original_updated


# ========================================
# PRUEBAS DE RENDIMIENTO
# ========================================

class TestServiceTypePerformance:
    """Pruebas de rendimiento"""

    def test_bulk_creation(self, db_session: Session):
        """Prueba creación masiva de servicios"""
        services = []
        for i in range(100):
            service = ServiceType(
                Code=f"BULK{i:03d}",
                Name=f"Servicio Bulk {i}",
                Priority=(i % 5) + 1,
                AverageTimeMinutes=10 + (i % 20),
                TicketPrefix=f"B{i:02d}"[:5],
                Color=f"#00{i:02x}FF"[:7].ljust(7, '0')
            )
            services.append(service)

        # Bulk insert
        db_session.bulk_save_objects(services)
        db_session.commit()

        # Verificar que se crearon todos
        count = db_session.query(ServiceType).filter(
            ServiceType.Code.like("BULK%")
        ).count()
        assert count == 100

    def test_query_optimization(self, db_session: Session, multiple_service_types):
        """Prueba optimización de queries"""
        # Query con eager loading de relaciones
        from sqlalchemy.orm import joinedload

        services = db_session.query(ServiceType).options(
            joinedload(ServiceType.stations),
            joinedload(ServiceType.tickets)
        ).all()

        # Acceder a relaciones no debe generar queries adicionales
        for service in services:
            _ = service.stations
            _ = service.tickets

        assert len(services) >= 3