#!/usr/bin/env python3
"""
Script de debug actualizado para el endpoint queue-info
Ejecutar: python debug_queue_endpoint_updated.py
"""

import sys
from pathlib import Path
from datetime import datetime, date

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))


def test_service_method():
    """Prueba directa del método del servicio queue_service"""
    print("\n" + "=" * 60)
    print("PRUEBA 1: MÉTODO DEL SERVICIO")
    print("=" * 60)

    try:
        # Importar dependencias necesarias
        from app.core.database import SessionLocal
        from app.services.queue_service import queue_service
        from app.crud.patient import patient as patient_crud

        # Crear sesión de BD
        db = SessionLocal()

        try:
            print("\n1. Obteniendo primer paciente de prueba...")
            # Obtener cualquier paciente existente
            from app.models.patient import Patient
            first_patient = db.query(Patient).first()

            if not first_patient:
                print("❌ No hay pacientes en la base de datos")
                print("💡 Crea primero algunos pacientes de prueba")
                return False

            patient_id = str(first_patient.Id)
            print(f"✅ Paciente encontrado: {first_patient.FullName} (ID: {patient_id})")

            print("\n2. Llamando al método get_patient_queue_stats...")
            # Llamar al método directamente
            result = queue_service.get_patient_queue_stats(db, patient_id)

            print("✅ Método ejecutado exitosamente")
            print(f"\nResultado del servicio:")
            print(f"  - Tiene ticket activo: {result.get('has_active_ticket', False)}")

            if result.get('has_active_ticket'):
                ticket_info = result.get('ticket', {})
                print(f"  - Número de ticket: {ticket_info.get('number')}")
                print(f"  - Estado: {ticket_info.get('status')}")

                position_info = result.get('position', {})
                print(f"  - Posición en cola: {position_info.get('current')}")
                print(f"  - Personas adelante: {position_info.get('ahead_count')}")
                print(f"  - Tiempo estimado: {position_info.get('estimated_wait_time')} minutos")
            else:
                print(f"  - Mensaje: {result.get('message', 'Sin ticket activo')}")

            return True

        finally:
            db.close()

    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("💡 Verifica que todos los módulos estén correctamente instalados")
        return False

    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_queue_overview():
    """Prueba el endpoint de vista general de colas"""
    print("\n" + "=" * 60)
    print("PRUEBA 2: VISTA GENERAL DE COLAS")
    print("=" * 60)

    try:
        from app.core.database import SessionLocal
        from app.services.queue_service import queue_service
        from app.models.service_type import ServiceType
        from app.schemas.ticket import TicketStatus

        db = SessionLocal()

        try:
            print("\n1. Obteniendo servicios activos...")
            services = db.query(ServiceType).filter(ServiceType.IsActive == True).all()
            print(f"✅ Encontrados {len(services)} servicios activos")

            for service in services[:3]:  # Solo mostrar primeros 3
                print(f"\n2. Analizando servicio: {service.Name} (ID: {service.Id})")

                # Obtener cola del servicio
                tickets = queue_service.get_queue_by_service(
                    db,
                    service.Id,
                    include_completed=False
                )

                # El método es async, necesitamos ejecutarlo correctamente
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                tickets = loop.run_until_complete(
                    queue_service.get_queue_by_service(db, service.Id, False)
                )

                waiting = len([t for t in tickets if t.Status == TicketStatus.WAITING.value])
                in_progress = len([t for t in tickets if t.Status in [
                    TicketStatus.CALLED.value,
                    TicketStatus.IN_PROGRESS.value
                ]])

                print(f"   - En espera: {waiting}")
                print(f"   - En progreso: {in_progress}")
                print(f"   - Total en cola: {len(tickets)}")

            print("\n✅ Vista general funcionando correctamente")
            return True

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_queue_stats():
    """Prueba las estadísticas de cola"""
    print("\n" + "=" * 60)
    print("PRUEBA 3: ESTADÍSTICAS DE COLA")
    print("=" * 60)

    try:
        from app.core.database import SessionLocal
        from app.services.queue_service import queue_service
        import asyncio

        db = SessionLocal()

        try:
            print("\n1. Obteniendo estadísticas generales...")

            # Ejecutar método async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            stats = loop.run_until_complete(
                queue_service.get_queue_stats(db)
            )

            print("✅ Estadísticas obtenidas:")
            print(f"   - Total tickets hoy: {stats.total_tickets}")
            print(f"   - En espera: {stats.waiting_tickets}")
            print(f"   - Llamados: {stats.called_tickets}")
            print(f"   - En progreso: {stats.in_progress_tickets}")
            print(f"   - Completados: {stats.completed_tickets}")
            print(f"   - Cancelados: {stats.cancelled_tickets}")
            print(f"   - No show: {stats.no_show_tickets}")
            print(f"   - Tiempo promedio espera: {stats.average_wait_time:.1f} min")
            print(f"   - Tiempo promedio servicio: {stats.average_service_time:.1f} min")

            return True

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_estimated_calls():
    """Prueba las llamadas estimadas"""
    print("\n" + "=" * 60)
    print("PRUEBA 4: PRÓXIMAS LLAMADAS ESTIMADAS")
    print("=" * 60)

    try:
        from app.core.database import SessionLocal
        from app.services.queue_service import queue_service
        import asyncio

        db = SessionLocal()

        try:
            print("\n1. Obteniendo próximas llamadas estimadas...")

            # Ejecutar método async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            next_calls = loop.run_until_complete(
                queue_service.get_estimated_next_calls(db, limit=5)
            )

            if next_calls:
                print(f"✅ Próximas {len(next_calls)} llamadas:")
                for i, call in enumerate(next_calls, 1):
                    print(f"\n   {i}. Ticket: {call['ticket_number']}")
                    print(f"      Servicio: {call['service_name']}")
                    print(f"      Tiempo estimado: {call['estimated_time']} min")
                    print(f"      Hora estimada: {call['estimated_call']}")
            else:
                print("ℹ️ No hay tickets en espera")

            return True

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_connection():
    """Prueba la conexión a la base de datos"""
    print("\n" + "=" * 60)
    print("PRUEBA 0: CONEXIÓN A BASE DE DATOS")
    print("=" * 60)

    try:
        from app.core.database import check_database_connection, get_database_info

        print("\n1. Verificando conexión...")
        if check_database_connection():
            print("✅ Conexión exitosa")

            print("\n2. Información de la BD:")
            info = get_database_info()
            if "error" not in info:
                print(f"   - Servidor: {info.get('server_name')}")
                print(f"   - Base de datos: {info.get('database_name')}")
                print(f"   - Usuario: {info.get('user_name')}")
                return True
            else:
                print(f"❌ Error obteniendo info: {info['error']}")
                return False
        else:
            print("❌ No se pudo conectar a la base de datos")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Ejecutar todas las pruebas de debug"""
    print("\n" + "🔍 " * 30)
    print("DEBUG DEL SISTEMA DE COLAS - VERSIÓN ACTUALIZADA")
    print("🔍 " * 30)

    # Verificar primero la conexión a BD
    if not test_database_connection():
        print("\n❌ Sin conexión a BD, no se pueden ejecutar las demás pruebas")
        return

    # Ejecutar pruebas
    results = {
        "Método get_patient_queue_stats": test_service_method(),
        "Vista general de colas": test_queue_overview(),
        "Estadísticas de cola": test_queue_stats(),
        "Próximas llamadas": test_estimated_calls()
    }

    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{test_name:.<45} {status}")

    # Análisis de problemas
    total_passed = sum(1 for passed in results.values() if passed)
    total_tests = len(results)

    print(f"\n📈 Resultado: {total_passed}/{total_tests} pruebas pasadas")

    if total_passed == total_tests:
        print("\n🎉 ¡TODO FUNCIONANDO CORRECTAMENTE!")
        print("El sistema de colas está listo para usar")
    else:
        print("\n⚠️ Hay problemas que resolver:")

        if not results["Método get_patient_queue_stats"]:
            print("\n1. Problema con get_patient_queue_stats:")
            print("   - Verifica que el método esté correctamente implementado")
            print("   - Revisa que use los nombres correctos de columnas (CreatedAt, etc)")

        if not results["Vista general de colas"]:
            print("\n2. Problema con vista general:")
            print("   - Verifica que existan tipos de servicio en la BD")
            print("   - Revisa el método get_queue_by_service")

        if not results["Estadísticas de cola"]:
            print("\n3. Problema con estadísticas:")
            print("   - Verifica que existan tickets en la BD")
            print("   - Revisa el método get_queue_stats")

        if not results["Próximas llamadas"]:
            print("\n4. Problema con llamadas estimadas:")
            print("   - Verifica que existan tickets en estado 'Waiting'")
            print("   - Revisa el método get_estimated_next_calls")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback

        traceback.print_exc()