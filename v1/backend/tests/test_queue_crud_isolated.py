"""
Test aislado para diagnosticar el problema con QueueState CRUD
Ejecutar este test para identificar exactamente dónde está fallando
"""

import pytest
import sys
import os
from datetime import datetime
import uuid

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.models.queue_state import QueueState
from app.models.service_type import ServiceType
from app.models.station import Station
from app.schemas.queue import QueueStateCreate, QueueStateUpdate
from app.crud.queue import queue_crud

# ========================================
# CONFIGURACIÓN DE BASE DE DATOS DE TEST
# ========================================

TEST_DATABASE_URL = "mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"
test_engine = create_engine(TEST_DATABASE_URL, echo=True)  # echo=True para ver SQL
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Sesión de base de datos para pruebas"""
    session = TestSessionLocal()

    # Limpiar tablas relevantes en orden correcto (respetando FKs)
    try:
        print("\nLimpiando tablas de prueba...")

        # Primero QueueState (tiene FKs a ServiceTypes)
        try:
            result = session.execute(text("DELETE FROM QueueState"))
            count = result.rowcount
            session.commit()
            print(f"   - QueueState: {count} registros eliminados")
        except Exception as e:
            print(f"   - QueueState: Error limpiando - {e}")
            session.rollback()

        # Eliminar ServiceTypes de prueba anteriores
        try:
            result = session.execute(text("DELETE FROM ServiceTypes WHERE Code LIKE 'T%' AND LEN(Code) = 5"))
            count = result.rowcount
            session.commit()
            print(f"   - ServiceTypes de prueba: {count} registros eliminados")
        except Exception as e:
            print(f"   - ServiceTypes: Error limpiando - {e}")
            session.rollback()

        # También limpiar Stations si es necesario
        try:
            result = session.execute(text("DELETE FROM Stations WHERE Code LIKE 'TEST%'"))
            count = result.rowcount
            session.commit()
            print(f"   - Stations de prueba: {count} registros eliminados")
        except Exception as e:
            print(f"   - Stations: Error limpiando - {e}")
            session.rollback()

        print("✅ Limpieza completada")

    except Exception as e:
        print(f"⚠️ Error durante limpieza general: {e}")
        session.rollback()

    yield session

    # Limpieza final después de las pruebas
    try:
        print("\nLimpieza final...")
        session.execute(text("DELETE FROM QueueState"))
        session.execute(text("DELETE FROM ServiceTypes WHERE Code LIKE 'T%' AND LEN(Code) = 5"))
        session.commit()
        print("✅ Limpieza final completada")
    except:
        session.rollback()

    session.close()


def test_step_1_create_service_type(db_session: Session):
    """PASO 1: Crear un ServiceType directamente"""
    print("\n" + "="*60)
    print("PASO 1: Crear ServiceType")
    print("="*60)

    # Usar un código único basado en timestamp para evitar conflictos
    import time
    unique_code = f"T{int(time.time() % 10000)}"

    try:
        # Primero asegurarse de que no existe
        print(f"\nVerificando si ya existe ServiceType con Code='{unique_code}'...")
        existing = db_session.query(ServiceType).filter(ServiceType.Code == unique_code).first()
        if existing:
            print(f"   ⚠️ Ya existe ServiceType con Code='{unique_code}' (ID: {existing.Id})")
            print("   Eliminando registro existente...")
            db_session.delete(existing)
            db_session.commit()
            print("   ✅ Registro eliminado")
        else:
            print(f"   ✅ No existe ServiceType con Code='{unique_code}'")

        # Ahora crear el nuevo ServiceType
        print(f"\nCreando nuevo ServiceType con Code='{unique_code}'...")
        service = ServiceType(
            Code=unique_code,
            Name="Test Service",
            Description="Servicio de prueba",
            Priority=1,
            AverageTimeMinutes=10,
            TicketPrefix="T",
            Color="#007bff",
            IsActive=True
        )

        print(f"Objeto ServiceType creado en memoria:")
        print(f"   Code: {service.Code}")
        print(f"   Name: {service.Name}")
        print(f"   Priority: {service.Priority}")

        db_session.add(service)
        db_session.flush()
        db_session.commit()
        db_session.refresh(service)

        print(f"✅ ServiceType creado exitosamente")
        print(f"   ID: {service.Id}")
        print(f"   Name: {service.Name}")
        print(f"   Code: {service.Code}")

        # Verificar que se guardó
        saved = db_session.query(ServiceType).filter(ServiceType.Id == service.Id).first()
        assert saved is not None, "ServiceType no se guardó en BD"
        print(f"✅ ServiceType verificado en BD")

        # Limpiar después de verificar
        db_session.delete(saved)
        db_session.commit()
        print(f"✅ ServiceType de prueba eliminado (limpieza)")

        return service.Id

    except Exception as e:
        print(f"\n❌ Error creando ServiceType:")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")

        if hasattr(e, 'orig'):
            print(f"   Error original: {e.orig}")

        import traceback
        print("\nStack trace completo:")
        traceback.print_exc()

        db_session.rollback()
        raise


def test_step_2_create_queue_state_manual(db_session: Session):
    """PASO 2: Crear QueueState manualmente (sin CRUD)"""
    print("\n" + "="*60)
    print("PASO 2: Crear QueueState manualmente")
    print("="*60)

    # Primero crear el servicio
    service_id = test_step_1_create_service_type(db_session)

    try:
        # Verificar que el modelo QueueState tiene los campos esperados
        print("\nVerificando campos del modelo QueueState:")
        from sqlalchemy import inspect
        mapper = inspect(QueueState)
        for column in mapper.columns:
            print(f"   - {column.name}: {column.type} (nullable: {column.nullable})")

        # Crear QueueState con valores mínimos requeridos
        print("\nCreando QueueState con campos mínimos...")
        queue_state = QueueState()

        # Asignar valores uno por uno para ver cuál falla
        print("Asignando ServiceTypeId...")
        queue_state.ServiceTypeId = service_id

        print("Asignando QueueLength...")
        queue_state.QueueLength = 0

        print("Asignando AverageWaitTime...")
        queue_state.AverageWaitTime = 10

        print("Asignando LastUpdateAt...")
        queue_state.LastUpdateAt = datetime.now()

        print(f"\nObjeto QueueState creado en memoria:")
        print(f"   ServiceTypeId: {queue_state.ServiceTypeId}")
        print(f"   QueueLength: {queue_state.QueueLength}")
        print(f"   AverageWaitTime: {queue_state.AverageWaitTime}")
        print(f"   LastUpdateAt: {queue_state.LastUpdateAt}")

        print("\nAgregando a la sesión...")
        db_session.add(queue_state)
        print("✅ Agregado a la sesión")

        print("\nHaciendo commit...")
        db_session.flush()  # Usar flush primero para ver errores antes del commit
        print("✅ Flush exitoso")

        db_session.commit()
        print("✅ Commit exitoso")

        db_session.refresh(queue_state)
        print(f"✅ QueueState creado exitosamente")
        print(f"   ID: {queue_state.Id}")

        # Verificar que se guardó
        saved = db_session.query(QueueState).filter(QueueState.Id == queue_state.Id).first()
        assert saved is not None, "QueueState no se guardó en BD"
        print(f"✅ QueueState verificado en BD")

        return queue_state.Id

    except Exception as e:
        print(f"\n❌ Error creando QueueState manualmente:")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")

        # Si es un error de integridad, mostrar más detalles
        if hasattr(e, 'orig'):
            print(f"   Error original: {e.orig}")

        # Intentar identificar el problema específico
        error_msg = str(e).lower()
        if 'foreign key' in error_msg:
            print("\n   💡 Posible problema: Constraint de foreign key")
            print("      Verificando si ServiceTypeId existe...")
            service = db_session.query(ServiceType).filter(ServiceType.Id == service_id).first()
            print(f"      ServiceType con ID {service_id}: {'EXISTE' if service else 'NO EXISTE'}")
        elif 'not null' in error_msg or 'cannot insert null' in error_msg:
            print("\n   💡 Posible problema: Campo requerido con valor NULL")
        elif 'identity' in error_msg:
            print("\n   💡 Posible problema: Columna identity (autoincrement)")

        import traceback
        print("\nStack trace completo:")
        traceback.print_exc()

        db_session.rollback()
        raise


def test_step_3_create_with_schema(db_session: Session):
    """PASO 3: Crear QueueState usando schema"""
    print("\n" + "="*60)
    print("PASO 3: Crear QueueState con Schema")
    print("="*60)

    # Primero crear el servicio
    service_id = test_step_1_create_service_type(db_session)

    try:
        # Crear usando schema
        queue_data = QueueStateCreate(
            service_type_id=service_id,
            queue_length=0,
            average_wait_time=15
        )

        print(f"Schema QueueStateCreate creado:")
        print(f"   service_type_id: {queue_data.service_type_id}")
        print(f"   queue_length: {queue_data.queue_length}")
        print(f"   average_wait_time: {queue_data.average_wait_time}")

        # Convertir a dict
        data_dict = queue_data.model_dump(exclude_unset=True)
        print(f"Schema convertido a dict: {data_dict}")

        # Crear objeto QueueState desde dict
        queue_state = QueueState(**data_dict)
        print("QueueState creado desde schema dict")

        db_session.add(queue_state)
        db_session.commit()
        db_session.refresh(queue_state)

        print(f"✅ QueueState creado exitosamente con schema")
        print(f"   ID: {queue_state.Id}")

        return queue_state.Id

    except Exception as e:
        print(f"❌ Error creando QueueState con schema: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
        raise


def test_step_4_create_with_crud(db_session: Session):
    """PASO 4: Crear QueueState usando CRUD"""
    print("\n" + "="*60)
    print("PASO 4: Crear QueueState con CRUD")
    print("="*60)

    # Primero crear el servicio
    service_id = test_step_1_create_service_type(db_session)

    try:
        # Crear usando CRUD
        queue_data = QueueStateCreate(
            service_type_id=service_id,
            queue_length=5,
            average_wait_time=20
        )

        print(f"Intentando crear con queue_crud.create()")
        print(f"   Datos: {queue_data.model_dump()}")

        # Llamar al CRUD
        queue_state = queue_crud.create(db_session, obj_in=queue_data)

        if queue_state:
            print(f"✅ QueueState creado exitosamente con CRUD")
            print(f"   ID: {queue_state.Id}")
            print(f"   ServiceTypeId: {queue_state.ServiceTypeId}")
            print(f"   QueueLength: {queue_state.QueueLength}")
        else:
            print("❌ CRUD retornó None")

        return queue_state.Id if queue_state else None

    except Exception as e:
        print(f"❌ Error creando QueueState con CRUD: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
        raise


def test_step_5_check_database_structure(db_session: Session):
    """PASO 5: Verificar estructura de la base de datos"""
    print("\n" + "="*60)
    print("PASO 5: Verificar estructura de BD")
    print("="*60)

    try:
        # Verificar que la tabla existe
        result = db_session.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'QueueState'
        """))

        table = result.fetchone()
        if table:
            print(f"✅ Tabla 'QueueState' existe")
        else:
            print(f"❌ Tabla 'QueueState' NO existe")
            return

        # Verificar columnas con más detalle
        result = db_session.execute(text("""
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                IS_NULLABLE,
                COLUMN_DEFAULT,
                CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'QueueState'
            ORDER BY ORDINAL_POSITION
        """))

        columns = result.fetchall()
        print(f"\nColumnas de la tabla QueueState:")
        print("-" * 70)
        print(f"{'Columna':<25} {'Tipo':<15} {'Nullable':<10} {'Default':<20}")
        print("-" * 70)

        required_columns = []
        for col in columns:
            col_name = col[0]
            data_type = col[1]
            is_nullable = col[2]
            default_val = col[3] if col[3] else 'None'
            max_length = col[4] if col[4] else ''

            if data_type in ['varchar', 'nvarchar', 'char']:
                data_type = f"{data_type}({max_length})"

            print(f"{col_name:<25} {data_type:<15} {is_nullable:<10} {str(default_val):<20}")

            # Identificar columnas requeridas (NOT NULL sin default)
            if is_nullable == 'NO' and not col[3] and col_name != 'Id':
                required_columns.append(col_name)

        if required_columns:
            print(f"\n⚠️ Columnas REQUERIDAS (NOT NULL sin default):")
            for col in required_columns:
                print(f"   - {col}")

        # Verificar constraints
        result = db_session.execute(text("""
            SELECT 
                tc.CONSTRAINT_NAME,
                tc.CONSTRAINT_TYPE
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            WHERE tc.TABLE_NAME = 'QueueState'
        """))

        constraints = result.fetchall()
        if constraints:
            print(f"\nConstraints de la tabla:")
            for constraint in constraints:
                print(f"   - {constraint[0]}: {constraint[1]}")

        # Verificar foreign keys
        result = db_session.execute(text("""
            SELECT 
                fk.CONSTRAINT_NAME,
                cu.COLUMN_NAME,
                ku.TABLE_NAME as REFERENCED_TABLE,
                ku.COLUMN_NAME as REFERENCED_COLUMN
            FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS fk
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE cu
                ON fk.CONSTRAINT_NAME = cu.CONSTRAINT_NAME
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                ON fk.UNIQUE_CONSTRAINT_NAME = ku.CONSTRAINT_NAME
            WHERE cu.TABLE_NAME = 'QueueState'
        """))

        foreign_keys = result.fetchall()
        if foreign_keys:
            print(f"\nForeign Keys:")
            for fk in foreign_keys:
                print(f"   - {fk[1]} -> {fk[2]}.{fk[3]} (constraint: {fk[0]})")

        # Verificar si hay registros
        count = db_session.query(QueueState).count()
        print(f"\nRegistros actuales en QueueState: {count}")

    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_full_diagnostic(db_session: Session):
    """Test completo de diagnóstico"""
    print("\n" + "="*60)
    print("DIAGNÓSTICO COMPLETO DE QUEUE STATE")
    print("="*60)

    results = {}
    service_id = None  # Guardar el ID del ServiceType para reusar

    # Paso 5: Verificar estructura primero
    try:
        test_step_5_check_database_structure(db_session)
        results["Estructura BD"] = "✅ PASÓ"
    except:
        results["Estructura BD"] = "❌ FALLÓ"

    # Paso 1: ServiceType - Crear UNA SOLA VEZ
    try:
        service_id = test_step_1_create_service_type(db_session)
        results["Crear ServiceType"] = "✅ PASÓ"
        print(f"\n📌 ServiceType creado con ID: {service_id} - Se reusará en todos los tests")
    except:
        results["Crear ServiceType"] = "❌ FALLÓ"
        service_id = None

    # Solo continuar si ServiceType se creó
    if service_id:
        # Paso 2: QueueState manual - Pasar el service_id existente
        try:
            queue_id = test_step_2_create_queue_state_manual_with_service(db_session, service_id)
            results["QueueState Manual"] = "✅ PASÓ"
        except:
            results["QueueState Manual"] = "❌ FALLÓ"

        # Paso 3: QueueState con schema - Pasar el service_id existente
        try:
            queue_id = test_step_3_create_with_schema_with_service(db_session, service_id)
            results["QueueState con Schema"] = "✅ PASÓ"
        except:
            results["QueueState con Schema"] = "❌ FALLÓ"

        # Paso 4: QueueState con CRUD - Pasar el service_id existente
        try:
            queue_id = test_step_4_create_with_crud_with_service(db_session, service_id)
            results["QueueState con CRUD"] = "✅ PASÓ"
        except:
            results["QueueState con CRUD"] = "❌ FALLÓ"

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE RESULTADOS")
    print("="*60)

    for test, result in results.items():
        print(f"{test:.<30} {result}")

    passed = sum(1 for r in results.values() if "✅" in r)
    total = len(results)

    print(f"\nTotal: {passed}/{total} pruebas pasaron")

    if passed < total:
        print("\n⚠️ DIAGNÓSTICO:")
        if "❌" in results.get("Estructura BD", ""):
            print("   - La tabla QueueState puede no existir o tener estructura incorrecta")
        if "❌" in results.get("Crear ServiceType", ""):
            print("   - Problema creando ServiceType (requerido para QueueState)")
        if "❌" in results.get("QueueState Manual", ""):
            print("   - Problema con el modelo QueueState o constraints de BD")
        if "❌" in results.get("QueueState con Schema", ""):
            print("   - Problema con el schema QueueStateCreate o mapeo de campos")
        if "❌" in results.get("QueueState con CRUD", ""):
            print("   - Problema específico en el CRUD (revisar método create)")


def test_step_2_create_queue_state_manual_with_service(db_session: Session, service_id: int):
    """PASO 2: Crear QueueState manualmente con ServiceType existente"""
    print("\n" + "="*60)
    print("PASO 2: Crear QueueState manualmente")
    print("="*60)

    try:
        # Verificar que el ServiceType todavía existe
        print(f"\nVerificando que ServiceType {service_id} existe...")
        service = db_session.query(ServiceType).filter(ServiceType.Id == service_id).first()
        if service:
            print(f"   ✅ ServiceType encontrado: {service.Name} (ID: {service.Id})")
        else:
            print(f"   ❌ ServiceType {service_id} NO existe")
            raise ValueError(f"ServiceType {service_id} no existe en la BD")

        print("\nCreando QueueState con campos mínimos...")
        queue_state = QueueState()

        print(f"Asignando ServiceTypeId={service_id}...")
        queue_state.ServiceTypeId = service_id

        print("Asignando QueueLength...")
        queue_state.QueueLength = 0

        print("Asignando AverageWaitTime...")
        queue_state.AverageWaitTime = 10

        print("Asignando LastUpdateAt...")
        queue_state.LastUpdateAt = datetime.now()

        print(f"\nObjeto QueueState creado en memoria:")
        print(f"   ServiceTypeId: {queue_state.ServiceTypeId}")
        print(f"   QueueLength: {queue_state.QueueLength}")
        print(f"   AverageWaitTime: {queue_state.AverageWaitTime}")
        print(f"   LastUpdateAt: {queue_state.LastUpdateAt}")

        print("\nAgregando a la sesión...")
        db_session.add(queue_state)
        print("✅ Agregado a la sesión")

        print("\nHaciendo flush...")
        db_session.flush()
        print("✅ Flush exitoso")

        print("\nHaciendo commit...")
        db_session.commit()
        print("✅ Commit exitoso")

        db_session.refresh(queue_state)
        print(f"✅ QueueState creado exitosamente")
        print(f"   ID: {queue_state.Id}")

        # Limpiar este QueueState específico para no interferir con otros tests
        db_session.delete(queue_state)
        db_session.commit()
        print("✅ QueueState de prueba eliminado")

        return queue_state.Id

    except Exception as e:
        print(f"\n❌ Error creando QueueState manualmente:")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")

        if hasattr(e, 'orig'):
            print(f"   Error original: {e.orig}")

        import traceback
        print("\nStack trace completo:")
        traceback.print_exc()

        db_session.rollback()
        raise


def test_step_3_create_with_schema_with_service(db_session: Session, service_id: int):
    """PASO 3: Crear QueueState usando schema con ServiceType existente"""
    print("\n" + "="*60)
    print("PASO 3: Crear QueueState con Schema")
    print("="*60)

    try:
        # Verificar que el ServiceType existe
        service = db_session.query(ServiceType).filter(ServiceType.Id == service_id).first()
        if not service:
            raise ValueError(f"ServiceType {service_id} no existe")
        print(f"✅ ServiceType {service_id} verificado")

        # Crear usando schema con nombres de campos correctos (PascalCase)
        print("\nCreando schema con campos PascalCase...")
        queue_data = QueueStateCreate(
            ServiceTypeId=service_id,  # PascalCase, no snake_case
            QueueLength=0,
            AverageWaitTime=15
        )

        print(f"Schema QueueStateCreate creado:")
        print(f"   Datos: {queue_data.model_dump()}")

        # Convertir a dict
        data_dict = queue_data.model_dump(exclude_unset=True)
        print(f"Schema convertido a dict: {data_dict}")

        # Agregar LastUpdateAt que es requerido
        data_dict['LastUpdateAt'] = datetime.now()
        queue_state = QueueState(**data_dict)
        print("QueueState creado desde schema dict")

        db_session.add(queue_state)
        db_session.commit()
        db_session.refresh(queue_state)

        print(f"✅ QueueState creado exitosamente con schema")
        print(f"   ID: {queue_state.Id}")

        # Limpiar
        db_session.delete(queue_state)
        db_session.commit()
        print("✅ QueueState de prueba eliminado")

        return queue_state.Id

    except Exception as e:
        print(f"\n❌ Error creando QueueState con schema:")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")

        import traceback
        print("\nStack trace completo:")
        traceback.print_exc()

        db_session.rollback()
        raise


def test_step_4_create_with_crud_with_service(db_session: Session, service_id: int):
    """PASO 4: Crear QueueState usando CRUD con ServiceType existente"""
    print("\n" + "="*60)
    print("PASO 4: Crear QueueState con CRUD")
    print("="*60)

    try:
        # Verificar que el ServiceType existe
        service = db_session.query(ServiceType).filter(ServiceType.Id == service_id).first()
        if not service:
            raise ValueError(f"ServiceType {service_id} no existe")
        print(f"✅ ServiceType {service_id} verificado")

        print("\nCreando QueueStateCreate con campos PascalCase...")
        queue_data = QueueStateCreate(
            ServiceTypeId=service_id,  # PascalCase
            QueueLength=5,
            AverageWaitTime=20
        )

        print(f"Intentando crear con queue_crud.create()")
        print(f"   Datos: {queue_data.model_dump()}")

        # El CRUD necesita agregar LastUpdateAt
        queue_state = queue_crud.create(db_session, obj_in=queue_data)

        if queue_state:
            print(f"✅ QueueState creado exitosamente con CRUD")
            print(f"   ID: {queue_state.Id}")
            print(f"   ServiceTypeId: {queue_state.ServiceTypeId}")
            print(f"   QueueLength: {queue_state.QueueLength}")

            # Limpiar
            db_session.delete(queue_state)
            db_session.commit()
            print("✅ QueueState de prueba eliminado")
        else:
            print("❌ CRUD retornó None")

        return queue_state.Id if queue_state else None

    except Exception as e:
        print(f"❌ Error creando QueueState con CRUD: {e}")
        print(f"   Tipo de error: {type(e).__name__}")

        import traceback
        print("\nStack trace completo:")
        traceback.print_exc()

        db_session.rollback()
        raise


if __name__ == "__main__":
    # Ejecutar diagnóstico completo
    session = TestSessionLocal()
    try:
        test_full_diagnostic(session)
    finally:
        session.close()