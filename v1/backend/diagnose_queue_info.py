#!/usr/bin/env python3
"""
Script de diagnóstico para el endpoint queue-info
NO ES UN TEST DE PYTEST - Ejecutar directamente con Python:
python diagnose_queue_info.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.patient import Patient
from app.models.ticket import Ticket
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def check_patient_exists(patient_id: str):
    """Verificar si el paciente existe en la BD"""
    print(f"\n{'=' * 60}")
    print(f"PRUEBA 1: Verificar si existe el paciente")
    print(f"{'=' * 60}")

    db = SessionLocal()
    try:
        # Buscar directamente en la BD
        print(f"\nBuscando paciente con ID: {patient_id}")

        # Método 1: Query directo
        patient = db.query(Patient).filter(Patient.Id == patient_id).first()

        if patient:
            print(f"✅ Paciente encontrado:")
            print(f"   - ID: {patient.Id}")
            print(f"   - Nombre: {patient.FullName}")
            print(f"   - Documento: {patient.DocumentNumber}")
            print(f"   - Activo: {patient.IsActive}")
            return True
        else:
            print(f"❌ Paciente NO encontrado con ID: {patient_id}")

            # Buscar si existe con otro ID similar
            print("\nBuscando pacientes con IDs similares...")
            all_patients = db.query(Patient).limit(5).all()
            if all_patients:
                print("Primeros 5 pacientes en la BD:")
                for p in all_patients:
                    print(f"   - ID: {p.Id} | Nombre: {p.FullName}")
            else:
                print("❌ No hay pacientes en la base de datos")

            return False

    except Exception as e:
        print(f"❌ Error al buscar paciente: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def check_patient_tickets(patient_id: str):
    """Verificar tickets del paciente"""
    print(f"\n{'=' * 60}")
    print(f"PRUEBA 2: Verificar tickets del paciente")
    print(f"{'=' * 60}")

    db = SessionLocal()
    try:
        # Buscar tickets del paciente
        print(f"\nBuscando tickets para paciente ID: {patient_id}")

        tickets = db.query(Ticket).filter(
            Ticket.PatientId == patient_id
        ).all()

        if tickets:
            print(f"✅ Se encontraron {len(tickets)} tickets:")
            for ticket in tickets[:5]:  # Mostrar máximo 5
                print(f"   - Número: {ticket.TicketNumber}")
                print(f"     Estado: {ticket.Status}")
                print(f"     Servicio ID: {ticket.ServiceTypeId}")
                print(
                    f"     Creado: {ticket.CreatedAt if hasattr(ticket, 'CreatedAt') else ticket.created_at if hasattr(ticket, 'created_at') else 'N/A'}")
        else:
            print(f"⚠️ No se encontraron tickets para este paciente")

        # Buscar tickets activos
        active_tickets = db.query(Ticket).filter(
            Ticket.PatientId == patient_id,
            Ticket.Status.in_(['Waiting', 'Called', 'InProgress'])
        ).all()

        print(f"\nTickets activos: {len(active_tickets)}")

        return True

    except Exception as e:
        print(f"❌ Error al buscar tickets: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def check_crud_method(patient_id: str):
    """Probar el método get del CRUD"""
    print(f"\n{'=' * 60}")
    print(f"PRUEBA 3: Verificar método CRUD get")
    print(f"{'=' * 60}")

    db = SessionLocal()
    try:
        from app.crud.patient import patient as crud_patient

        print(f"\nProbando crud_patient.get con ID: {patient_id}")

        # Verificar si el método get existe
        if not hasattr(crud_patient, 'get'):
            print(f"❌ El CRUD no tiene método 'get'")
            print("Métodos disponibles en crud_patient:")
            for method in dir(crud_patient):
                if not method.startswith('_'):
                    print(f"   - {method}")
            return False

        patient = crud_patient.get(db, patient_id)

        if patient:
            print(f"✅ CRUD get funcionó correctamente")
            print(f"   - Paciente: {patient.FullName}")
        else:
            print(f"❌ CRUD get retornó None")

            # Probar con variaciones del ID
            print("\nProbando con variaciones del ID...")

            # Mayúsculas
            patient_upper = crud_patient.get(db, patient_id.upper())
            if patient_upper:
                print(f"✅ Funcionó con ID en mayúsculas: {patient_id.upper()}")

            # Minúsculas
            patient_lower = crud_patient.get(db, patient_id.lower())
            if patient_lower:
                print(f"✅ Funcionó con ID en minúsculas: {patient_id.lower()}")

        return patient is not None

    except Exception as e:
        print(f"❌ Error en CRUD: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Ejecutar todas las pruebas"""
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO DEL ENDPOINT QUEUE-INFO")
    print("=" * 60)

    # ID del paciente a probar
    patient_id = "F6A8B334-141A-4418-826C-C4F37C0A1B70"

    print(f"\nPaciente ID a probar: {patient_id}")

    # Ejecutar pruebas
    results = {
        "Paciente existe": check_patient_exists(patient_id),
        "Tickets del paciente": check_patient_tickets(patient_id),
        "CRUD get funciona": check_crud_method(patient_id)
    }

    # Resumen
    print(f"\n{'=' * 60}")
    print("RESUMEN DE RESULTADOS")
    print("=" * 60)

    for test, passed in results.items():
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{test:.<40} {status}")

    if not results["Paciente existe"]:
        print("\n⚠️ PROBLEMA PRINCIPAL: El paciente no existe en la BD")
        print("Soluciones:")
        print("1. Verificar que el ID del paciente es correcto")
        print("2. Crear el paciente primero")
        print("3. Verificar la conexión a la BD correcta")
        print("\nPara obtener un ID válido, ejecuta esta consulta en SQL Server:")
        print("SELECT TOP 5 Id, FullName, DocumentNumber FROM Patients WHERE IsActive = 1")
    elif not results["CRUD get funciona"]:
        print("\n⚠️ PROBLEMA: El método CRUD get no funciona correctamente")
        print("Revisar la implementación del método get en crud/patient.py")


if __name__ == "__main__":
    main()