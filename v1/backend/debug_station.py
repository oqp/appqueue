#!/usr/bin/env python3
"""
Script CORREGIDO de diagnóstico completo para stations
Ejecutar directamente: python debug_stations_complete.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.station import Station
from sqlalchemy import text  # Importar text para SQL raw
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO)  # Reducir verbosidad
logger = logging.getLogger(__name__)


def check_stations_exist():
    """Verificar rápidamente si hay estaciones"""
    db = SessionLocal()
    try:
        # Usar text() para SQL raw
        result = db.execute(text("SELECT COUNT(*) FROM Stations"))
        count = result.scalar()
        print(f"✅ Hay {count} estaciones en la BD")
        return count
    except Exception as e:
        print(f"❌ Error verificando estaciones: {e}")
        return 0
    finally:
        db.close()


def simulate_list_endpoint():
    """Simular exactamente lo que hace el endpoint /stations/"""
    print("\n" + "=" * 60)
    print("SIMULACIÓN DEL ENDPOINT /stations/")
    print("=" * 60)

    db = SessionLocal()
    try:
        from app.crud.station import station_crud
        from app.schemas.station import StationResponse, StationListResponse

        # Parámetros del endpoint
        skip = 0
        limit = 20
        include_inactive = False
        include_stats = False

        print(f"\nParámetros:")
        print(f"  skip={skip}, limit={limit}")
        print(f"  include_inactive={include_inactive}, include_stats={include_stats}")

        print("\n--- Ejecutando flujo del endpoint ---")

        try:
            # PASO 1: Obtener estaciones
            print("\nPaso 1: Obtener estaciones...")

            if include_stats:
                # Con estadísticas
                if hasattr(station_crud, 'get_stations_with_stats'):
                    stations = station_crud.get_stations_with_stats(
                        db, include_inactive=include_inactive
                    )
                    print(f"✅ get_stations_with_stats retornó {len(stations)} estaciones")
                else:
                    print("⚠️ No existe get_stations_with_stats, usando get_multi")
                    stations = station_crud.get_multi(
                        db, skip=skip, limit=limit, active_only=not include_inactive
                    )
            else:
                # Sin estadísticas (caso normal)
                stations = station_crud.get_multi(
                    db, skip=skip, limit=limit, active_only=not include_inactive
                )
                print(f"✅ get_multi retornó {len(stations)} estaciones")

            # PASO 2: Contar total
            print("\nPaso 2: Contar total de estaciones...")

            if hasattr(station_crud, 'get_count'):
                total = station_crud.get_count(db, active_only=not include_inactive)
                print(f"✅ get_count retornó: {total}")
            else:
                # Fallback
                query = db.query(Station)
                if not include_inactive:
                    query = query.filter(Station.IsActive == True)
                total = query.count()
                print(f"✅ Query directo retornó: {total}")

            # PASO 3: Construir respuestas
            print("\nPaso 3: Convertir a StationResponse...")

            station_responses = []
            for i, station in enumerate(stations):
                try:
                    # Verificar qué método usar
                    if hasattr(StationResponse, 'from_attributes'):
                        response = StationResponse.from_attributes(station)
                        if i == 0:
                            print("   Usando from_attributes")
                    elif hasattr(StationResponse, 'from_orm'):
                        response = StationResponse.from_orm(station)
                        if i == 0:
                            print("   Usando from_orm")
                    else:
                        # Construcción manual
                        if i == 0:
                            print("   Usando construcción manual")
                        response = StationResponse(
                            Id=station.Id,
                            Name=station.Name,
                            Code=station.Code,
                            Description=station.Description,
                            ServiceTypeId=station.ServiceTypeId,
                            Location=station.Location,
                            Status=station.Status,
                            CurrentTicketId=str(station.CurrentTicketId) if station.CurrentTicketId else None,
                            IsActive=station.IsActive,
                            CreatedAt=station.CreatedAt,
                            UpdatedAt=station.UpdatedAt
                        )

                    station_responses.append(response)

                except Exception as e:
                    print(f"❌ Error convirtiendo estación {i + 1}: {e}")
                    print(f"   Tipo de error: {type(e).__name__}")

                    # Mostrar información de la estación problemática
                    print(f"   Station.Id: {station.Id} (tipo: {type(station.Id)})")
                    print(f"   Station.Name: {station.Name}")
                    print(
                        f"   Station.CurrentTicketId: {station.CurrentTicketId} (tipo: {type(station.CurrentTicketId)})")

                    # Intentar identificar el campo problemático
                    for field in ['Id', 'Name', 'Code', 'Description', 'ServiceTypeId',
                                  'Location', 'Status', 'CurrentTicketId', 'IsActive',
                                  'CreatedAt', 'UpdatedAt']:
                        try:
                            value = getattr(station, field)
                            print(f"   {field}: {value} (tipo: {type(value)})")
                        except Exception as field_error:
                            print(f"   {field}: ERROR - {field_error}")

                    raise

            print(f"✅ Convertidas {len(station_responses)} estaciones")

            # PASO 4: Crear StationListResponse
            print("\nPaso 4: Crear StationListResponse...")

            list_response = StationListResponse(
                Stations=station_responses,
                Total=total,
                Page=skip // limit + 1 if limit > 0 else 1,
                PageSize=limit,
                TotalPages=(total + limit - 1) // limit if limit > 0 else 1,
                HasNext=skip + limit < total,
                HasPrev=skip > 0
            )

            print("✅ StationListResponse creado exitosamente")
            print(f"\nResultado final:")
            print(f"  Total estaciones: {list_response.Total}")
            print(f"  Estaciones en página: {len(list_response.Stations)}")
            print(f"  Página: {list_response.Page}/{list_response.TotalPages}")

            # Mostrar algunas estaciones
            if list_response.Stations:
                print("\nPrimeras 3 estaciones:")
                for i, st in enumerate(list_response.Stations[:3]):
                    print(f"  {i + 1}. {st.Name} (Code: {st.Code}, Status: {st.Status})")

            return True

        except Exception as e:
            print(f"\n❌ ERROR EN EL FLUJO DEL ENDPOINT: {e}")
            print(f"Tipo de error: {type(e).__name__}")
            print("\n--- STACK TRACE ---")
            traceback.print_exc()
            print("--- FIN STACK TRACE ---")

            print("\n⚠️ ESTE ES EL ERROR EXACTO QUE ESTÁ OCURRIENDO EN TU ENDPOINT")
            return False

    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False
    finally:
        db.close()


def main():
    """Ejecutar diagnóstico completo"""
    print("\n" + "=" * 60)
    print("DIAGNÓSTICO COMPLETO DEL ENDPOINT /stations/")
    print("=" * 60)

    # Verificar si hay estaciones
    count = check_stations_exist()

    if count == 0:
        print("\n⚠️ No hay estaciones en la base de datos")
        print("Necesitas crear al menos una estación primero")
        print("\nPuedes crear una estación con:")
        print("POST /api/v1/stations/")
        print("Con el siguiente JSON:")
        print("""
{
  "Name": "Ventanilla 1",
  "Code": "V01",
  "Description": "Ventanilla de atención general",
  "Specialization": "general",
  "MaxConcurrentPatients": 1,
  "AverageServiceTimeMinutes": 15,
  "IsActive": true
}
        """)
        return

    # Simular el endpoint
    success = simulate_list_endpoint()

    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)

    if success:
        print("\n✅ LA SIMULACIÓN FUNCIONÓ CORRECTAMENTE")
        print("El endpoint debería funcionar. Posibles causas del error:")
        print("1. El servidor no se ha reiniciado después de cambios")
        print("2. Hay un problema de caché")
        print("3. El error está en otro lugar del código")
        print("\nIntenta:")
        print("- Reiniciar el servidor FastAPI")
        print("- Limpiar el caché de Python (__pycache__)")
        print("- Verificar los logs del servidor")
    else:
        print("\n❌ LA SIMULACIÓN FALLÓ")
        print("El error está identificado arriba")
        print("Necesitas corregir el problema antes de que el endpoint funcione")


if __name__ == "__main__":
    main()