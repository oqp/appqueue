#!/usr/bin/env python3
"""
Pruebas para los endpoints de gestión de colas
Ejecutar: python test_queue_endpoints.py
"""

import sys
import os
from pathlib import Path
import json
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar variables de entorno para pruebas
os.environ["TESTING"] = "1"

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueueEndpointTester:
    """
    Clase para probar los endpoints de Queue
    """

    def __init__(self):
        """Inicializa el tester"""
        self.base_url = "http://localhost:8000/api/v1"
        self.token = None
        self.session = None
        self.test_results = []

    async def setup(self):
        """Configura el entorno de pruebas"""
        try:
            import aiohttp
            self.session = aiohttp.ClientSession()

            # Intentar login para obtener token
            await self.login()

            return True
        except Exception as e:
            logger.error(f"Error en setup: {e}")
            return False

    async def teardown(self):
        """Limpia recursos"""
        if self.session:
            await self.session.close()

    async def login(self):
        """Realiza login para obtener token de autenticación"""
        try:
            # Usar credenciales de prueba
            login_data = {
                "username": "admin",
                "password": "admin123"
            }

            async with self.session.post(
                    f"{self.base_url}/auth/login",
                    json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get("access_token")
                    logger.info("✅ Login exitoso")
                    return True
                else:
                    logger.warning(f"⚠️ Login falló con status {response.status}")
                    # Continuar sin autenticación para pruebas públicas
                    return False

        except Exception as e:
            logger.warning(f"⚠️ No se pudo hacer login: {e}")
            return False

    def get_headers(self) -> Dict[str, str]:
        """Obtiene headers con autenticación si está disponible"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def test_endpoint(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict[str, Any]] = None,
            params: Optional[Dict[str, Any]] = None,
            expected_status: int = 200,
            test_name: Optional[str] = None
    ) -> bool:
        """
        Prueba un endpoint específico

        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Ruta del endpoint
            data: Datos para enviar en el body
            params: Parámetros query
            expected_status: Status HTTP esperado
            test_name: Nombre de la prueba

        Returns:
            bool: True si la prueba pasó
        """
        if not test_name:
            test_name = f"{method} {endpoint}"

        try:
            url = f"{self.base_url}{endpoint}"

            async with self.session.request(
                    method,
                    url,
                    headers=self.get_headers(),
                    json=data,
                    params=params
            ) as response:

                # Leer respuesta
                response_text = await response.text()

                # Verificar status
                if response.status == expected_status:
                    # Intentar parsear JSON si hay contenido
                    response_data = None
                    if response_text:
                        try:
                            response_data = json.loads(response_text)
                        except:
                            pass

                    logger.info(f"✅ {test_name}: Status {response.status}")

                    # Log de datos si están disponibles
                    if response_data:
                        logger.debug(f"   Respuesta: {json.dumps(response_data, indent=2)[:200]}...")

                    self.test_results.append({
                        "test": test_name,
                        "passed": True,
                        "status": response.status,
                        "data": response_data
                    })
                    return True

                else:
                    logger.error(f"❌ {test_name}: Status {response.status} (esperado {expected_status})")
                    logger.error(f"   Respuesta: {response_text[:500]}")

                    self.test_results.append({
                        "test": test_name,
                        "passed": False,
                        "status": response.status,
                        "expected": expected_status,
                        "error": response_text
                    })
                    return False

        except Exception as e:
            logger.error(f"❌ {test_name}: Error - {e}")
            self.test_results.append({
                "test": test_name,
                "passed": False,
                "error": str(e)
            })
            return False

    async def run_all_tests(self):
        """Ejecuta todas las pruebas de endpoints de Queue"""

        print("\n" + "=" * 60)
        print("🧪 PRUEBAS DE ENDPOINTS DE QUEUE")
        print("=" * 60)

        # ========================================
        # PRUEBAS DE VISTA GENERAL
        # ========================================

        print("\n📊 Probando Vista General...")

        await self.test_endpoint(
            "GET",
            "/queue/overview",
            test_name="Vista general de colas"
        )

        await self.test_endpoint(
            "GET",
            "/queue/service/1",
            test_name="Cola de servicio específico"
        )

        await self.test_endpoint(
            "GET",
            "/queue/service/1",
            params={"include_completed": True},
            test_name="Cola con tickets completados"
        )

        # ========================================
        # PRUEBAS DE ESTADÍSTICAS
        # ========================================

        print("\n📈 Probando Estadísticas...")

        await self.test_endpoint(
            "GET",
            "/queue/stats",
            test_name="Estadísticas generales"
        )

        await self.test_endpoint(
            "GET",
            "/queue/stats",
            params={"service_type_id": 1},
            test_name="Estadísticas por servicio"
        )

        await self.test_endpoint(
            "GET",
            "/queue/daily-summary",
            test_name="Resumen diario"
        )

        await self.test_endpoint(
            "GET",
            "/queue/daily-summary",
            params={"target_date": date.today().isoformat()},
            test_name="Resumen de fecha específica"
        )

        # ========================================
        # PRUEBAS DE MONITOREO
        # ========================================

        print("\n👁️ Probando Monitoreo...")

        await self.test_endpoint(
            "GET",
            "/queue/next-calls",
            test_name="Próximas llamadas estimadas"
        )

        await self.test_endpoint(
            "GET",
            "/queue/next-calls",
            params={"limit": 5},
            test_name="Próximas 5 llamadas"
        )

        await self.test_endpoint(
            "GET",
            "/queue/station/1/current",
            test_name="Ticket actual de estación"
        )

        # ========================================
        # PRUEBAS DE HEALTHCHECK
        # ========================================

        print("\n🏥 Probando Health Check...")

        await self.test_endpoint(
            "GET",
            "/queue/health",
            test_name="Health check del sistema"
        )

        # ========================================
        # PRUEBAS DE OPERACIONES (requieren auth)
        # ========================================

        if self.token:
            print("\n🎬 Probando Operaciones de Cola...")

            # Llamar siguiente paciente
            await self.test_endpoint(
                "POST",
                "/queue/call-next/1",
                test_name="Llamar siguiente paciente",
                expected_status=200  # o 404 si no hay pacientes
            )

            # Rebalancear colas
            await self.test_endpoint(
                "POST",
                "/queue/rebalance",
                test_name="Rebalancear colas"
            )
        else:
            print("\n⚠️ Saltando pruebas que requieren autenticación")

        # ========================================
        # RESUMEN DE RESULTADOS
        # ========================================

        print("\n" + "=" * 60)
        print("📊 RESUMEN DE PRUEBAS")
        print("=" * 60)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed

        print(f"\n✅ Pasadas: {passed}/{total}")
        print(f"❌ Fallidas: {failed}/{total}")

        if failed > 0:
            print("\n⚠️ Pruebas fallidas:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}")
                    if "error" in result:
                        print(f"    Error: {result['error'][:100]}...")

        # Retornar éxito si todas pasaron
        return failed == 0


async def test_with_database():
    """
    Prueba los endpoints con datos reales de la base de datos
    """
    print("\n" + "=" * 60)
    print("🗄️ PRUEBAS CON BASE DE DATOS")
    print("=" * 60)

    try:
        # Importar dependencias
        from app.core.database import SessionLocal, check_database_connection
        from app.crud.ticket import ticket_crud
        from app.crud.patient import patient as patient_crud
        from app.services.queue_service import queue_service

        # Verificar conexión
        if not check_database_connection():
            print("❌ No se pudo conectar a la base de datos")
            return False

        print("✅ Conexión a base de datos establecida")

        # Crear sesión
        db = SessionLocal()

        try:
            # Probar el servicio directamente
            print("\n📊 Probando Queue Service directamente...")

            # Test 1: Obtener estadísticas
            stats = await queue_service.get_queue_stats(db)
            print(f"✅ Estadísticas obtenidas: {stats.total_tickets} tickets totales")

            # Test 2: Obtener próximas llamadas
            next_calls = await queue_service.get_estimated_next_calls(db, limit=5)
            print(f"✅ Próximas llamadas: {len(next_calls)} estimadas")

            # Test 3: Obtener cola por servicio
            service_id = 1  # Asumiendo que existe el servicio 1
            queue = await queue_service.get_queue_by_service(db, service_id)
            print(f"✅ Cola del servicio {service_id}: {len(queue)} tickets")

            return True

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error en pruebas con base de datos: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """
    Función principal de pruebas
    """
    print("🚀 INICIANDO PRUEBAS DE ENDPOINTS DE QUEUE")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Verificar que el servidor esté corriendo
    print("\n🔍 Verificando servidor...")

    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api") as response:
                if response.status == 200:
                    print("✅ Servidor FastAPI está corriendo")
                else:
                    print(f"⚠️ Servidor respondió con status {response.status}")
    except Exception as e:
        print(f"❌ No se pudo conectar al servidor: {e}")
        print("💡 Asegúrate de que el servidor esté corriendo con: uvicorn app.main:app --reload")
        return False

    # Ejecutar pruebas de endpoints
    tester = QueueEndpointTester()

    if await tester.setup():
        success = await tester.run_all_tests()
        await tester.teardown()

        # Pruebas adicionales con base de datos
        if success:
            await test_with_database()

        return success
    else:
        print("❌ No se pudo configurar el entorno de pruebas")
        return False


if __name__ == "__main__":
    # Verificar dependencias
    try:
        import aiohttp
    except ImportError:
        print("❌ Necesitas instalar aiohttp: pip install aiohttp")
        sys.exit(1)

    # Ejecutar pruebas
    success = asyncio.run(main())

    if success:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        sys.exit(0)
    else:
        print("\n❌ Algunas pruebas fallaron")
        sys.exit(1)