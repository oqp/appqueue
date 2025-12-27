"""
Script de depuración para verificar la integración con modelo PascalCase
Ejecutar con: python debug_patient.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.patient import Patient
from app.schemas.patient import PatientCreate
from app.core.database import SessionLocal
from sqlalchemy import inspect
from datetime import date

def check_patient_model():
    """Verificar el modelo Patient"""
    print("=" * 60)
    print("VERIFICANDO MODELO PATIENT")
    print("=" * 60)

    # Verificar atributos de la clase Patient
    print("\n1. Atributos del modelo Patient:")
    patient_attrs = []
    for attr in dir(Patient):
        if not attr.startswith('_'):
            patient_attrs.append(attr)
            if len(patient_attrs) <= 20:  # Mostrar solo los primeros 20
                print(f"   - {attr}")

    if len(patient_attrs) > 20:
        print(f"   ... y {len(patient_attrs) - 20} más")

    # Verificar columnas específicas que necesitamos
    print("\n2. Verificando campos críticos:")

    # DocumentNumber (PascalCase)
    if hasattr(Patient, 'DocumentNumber'):
        print("   ✅ Patient.DocumentNumber existe")
    else:
        print("   ❌ Patient.DocumentNumber NO existe")

    # FullName
    if hasattr(Patient, 'FullName'):
        print("   ✅ Patient.FullName existe")
    else:
        print("   ❌ Patient.FullName NO existe")

    # Id (GUID)
    if hasattr(Patient, 'Id'):
        print("   ✅ Patient.Id existe")
    else:
        print("   ❌ Patient.Id NO existe")

    # IsActive
    if hasattr(Patient, 'IsActive'):
        print("   ✅ Patient.IsActive existe")
    else:
        print("   ❌ Patient.IsActive NO existe")

    # Verificar si usa snake_case (modelo antiguo)
    print("\n3. Verificando convención de nombres:")
    if hasattr(Patient, 'document_number'):
        print("   ⚠️  Modelo usa snake_case (document_number)")
    elif hasattr(Patient, 'DocumentNumber'):
        print("   ✅ Modelo usa PascalCase (DocumentNumber)")
    else:
        print("   ❌ No se encontró campo de documento")

    return hasattr(Patient, 'DocumentNumber')

def check_patient_schema():
    """Verificar el schema PatientCreate"""
    print("\n" + "=" * 60)
    print("VERIFICANDO SCHEMA PATIENTCREATE")
    print("=" * 60)

    # Crear un PatientCreate de prueba
    try:
        test_data = {
            "document_type": "DNI",
            "document_number": "12345678",
            "first_name": "Test",
            "last_name": "User",
            "birth_date": date(1990, 1, 1),
            "gender": "M"
        }

        patient_create = PatientCreate(**test_data)
        print("\n✅ PatientCreate creado exitosamente")
        print(f"   document_number: {patient_create.document_number}")
        print(f"   first_name: {patient_create.first_name}")
        print(f"   last_name: {patient_create.last_name}")

        return True
    except Exception as e:
        print(f"\n❌ Error al crear PatientCreate: {e}")
        return False

def test_database_query():
    """Probar una consulta real a la base de datos con PascalCase"""
    print("\n" + "=" * 60)
    print("PROBANDO CONSULTA A BASE DE DATOS")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Probar consulta con DocumentNumber (PascalCase)
        print("\n1. Probando consulta por DocumentNumber (PascalCase)...")

        result = db.query(Patient).filter(
            Patient.DocumentNumber == "12345678"
        ).first()

        if result:
            print(f"   ✅ Encontrado: {result.DocumentNumber}")
            print(f"      FullName: {result.FullName}")
            print(f"      Id: {result.Id}")
        else:
            print("   ✅ Consulta ejecutada correctamente (no hay resultados)")

        # Probar consulta por IsActive
        print("\n2. Probando consulta por IsActive...")
        count = db.query(Patient).filter(
            Patient.IsActive == True
        ).count()
        print(f"   ✅ Pacientes activos: {count}")

        return True

    except AttributeError as e:
        print(f"   ❌ Error de atributo: {e}")
        print("   El modelo no tiene los campos esperados en PascalCase")
        return False
    except Exception as e:
        print(f"   ❌ Error en consulta: {e}")
        print(f"   Tipo de error: {type(e)}")
        return False
    finally:
        db.close()

def test_crud_import():
    """Verificar que el CRUD esté importando correctamente"""
    print("\n" + "=" * 60)
    print("VERIFICANDO IMPORTS DEL CRUD")
    print("=" * 60)

    try:
        from app.crud.patient import patient as crud_patient
        print("\n✅ CRUD importado correctamente")
        print(f"   Tipo: {type(crud_patient)}")

        # Verificar métodos del CRUD
        print("\n   Métodos disponibles:")
        crud_methods = []
        for method in dir(crud_patient):
            if not method.startswith('_'):
                crud_methods.append(method)
                if len(crud_methods) <= 10:
                    print(f"      - {method}")

        if len(crud_methods) > 10:
            print(f"      ... y {len(crud_methods) - 10} más")

        # Verificar que get_by_document existe
        if hasattr(crud_patient, 'get_by_document'):
            print("\n   ✅ crud_patient.get_by_document existe")
        else:
            print("\n   ❌ crud_patient.get_by_document NO existe")

        return True
    except Exception as e:
        print(f"\n❌ Error al importar CRUD: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_import():
    """Verificar que el Service esté importando correctamente"""
    print("\n" + "=" * 60)
    print("VERIFICANDO IMPORTS DEL SERVICE")
    print("=" * 60)

    try:
        from app.services.patient_service import patient_service
        print("\n✅ Service importado correctamente")
        print(f"   Tipo: {type(patient_service)}")

        # Verificar que get_or_create_by_document existe
        if hasattr(patient_service, 'get_or_create_by_document'):
            print("   ✅ patient_service.get_or_create_by_document existe")
        else:
            print("   ❌ patient_service.get_or_create_by_document NO existe")

        return True
    except Exception as e:
        print(f"\n❌ Error al importar Service: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_crud_functionality():
    """Probar funcionalidad real del CRUD con PascalCase"""
    print("\n" + "=" * 60)
    print("PROBANDO FUNCIONALIDAD DEL CRUD")
    print("=" * 60)

    db = SessionLocal()
    try:
        from app.crud.patient import patient as crud_patient

        # Test get_by_document
        print("\n1. Probando crud_patient.get_by_document()...")
        test_doc = "29636795"
        result = crud_patient.get_by_document(db, test_doc)

        if result:
            print(f"   ✅ Paciente encontrado:")
            print(f"      DocumentNumber: {result.DocumentNumber}")
            print(f"      FullName: {result.FullName}")
        else:
            print(f"   ✅ No se encontró paciente con documento {test_doc} (esperado)")

        # Test get_multi
        print("\n2. Probando crud_patient.get_multi()...")
        patients = crud_patient.get_multi(db, skip=0, limit=5)
        print(f"   ✅ Obtenidos {len(patients)} pacientes")

        if patients:
            first = patients[0]
            print(f"      Ejemplo - DocumentNumber: {first.DocumentNumber}, FullName: {first.FullName}")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def check_database_tables():
    """Verificar las tablas en la base de datos"""
    print("\n" + "=" * 60)
    print("VERIFICANDO TABLAS EN BASE DE DATOS")
    print("=" * 60)

    try:
        from app.core.database import engine
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"\n📊 Tablas encontradas: {len(tables)}")
        for table in tables[:10]:  # Mostrar máximo 10 tablas
            print(f"   - {table}")

        if len(tables) > 10:
            print(f"   ... y {len(tables) - 10} más")

        # Verificar tabla Patients (con P mayúscula)
        if 'Patients' in tables:
            print("\n✅ Tabla 'Patients' existe")
            columns = inspector.get_columns('Patients')
            print("   Columnas:")
            for col in columns[:10]:  # Mostrar máximo 10 columnas
                print(f"      - {col['name']}: {col['type']}")

            if len(columns) > 10:
                print(f"      ... y {len(columns) - 10} más")

            # Verificar columnas críticas
            column_names = [col['name'] for col in columns]
            if 'DocumentNumber' in column_names:
                print("\n   ✅ Columna 'DocumentNumber' existe")
            else:
                print("\n   ❌ Columna 'DocumentNumber' NO existe")

        elif 'patients' in tables:
            print("\n⚠️  Tabla 'patients' (minúscula) existe - verificar convención")
        else:
            print("\n❌ Tabla 'Patients' NO existe")

        return True

    except Exception as e:
        print(f"❌ Error al verificar BD: {e}")
        return False

def main():
    """Ejecutar todas las verificaciones"""
    print("\n🔍 DIAGNÓSTICO DEL SISTEMA - MODELO PASCALCASE")
    print("-" * 60)

    results = {
        "Modelo Patient": check_patient_model(),
        "Schema PatientCreate": check_patient_schema(),
        "Query a BD": test_database_query(),
        "Import CRUD": test_crud_import(),
        "Import Service": test_service_import(),
        "Funcionalidad CRUD": test_crud_functionality(),
        "Tablas BD": check_database_tables()
    }

    print("\n" + "=" * 60)
    print("RESUMEN DE RESULTADOS")
    print("=" * 60)

    for test, passed in results.items():
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{test:.<30} {status}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests pasaron")

    if all(results.values()):
        print("\n✅ TODOS LOS TESTS PASARON - El sistema está listo")
        print("   Puedes probar: GET /api/v1/patients/document/29636795")
    else:
        print("\n❌ HAY PROBLEMAS - Revisa los tests que fallaron arriba")

        # Dar recomendaciones específicas
        if not results["Modelo Patient"]:
            print("\n⚠️  El modelo no tiene los campos PascalCase esperados")
            print("   Verifica que Patient tenga: DocumentNumber, FullName, Id, IsActive")

        if not results["Query a BD"]:
            print("\n⚠️  Las consultas a BD fallan")
            print("   Posible causa: El modelo no coincide con la estructura de la BD")

    # Información adicional
    print("\n" + "=" * 60)
    print("INFORMACIÓN DEL SISTEMA")
    print("=" * 60)

    import sqlalchemy
    print(f"SQLAlchemy version: {sqlalchemy.__version__}")

    try:
        from app.core.database import engine
        print(f"Database: {engine.url.database}")
        print(f"Driver: {engine.url.drivername}")
    except:
        print("No se pudo obtener información de la BD")

if __name__ == "__main__":
    main()