"""
Script de prueba rápida para verificar que los endpoints de Queue funcionan
Ejecutar con: python test_queue_quick.py
"""

import requests
import json
from datetime import datetime
from colorama import init, Fore, Style
import sys

# Inicializar colorama
init()

# Configuración
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Colores
SUCCESS = Fore.GREEN + "✓" + Style.RESET_ALL
ERROR = Fore.RED + "✗" + Style.RESET_ALL
INFO = Fore.CYAN + "→" + Style.RESET_ALL
WARNING = Fore.YELLOW + "⚠" + Style.RESET_ALL


def print_header(title):
    """Imprime un header formateado"""
    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Style.RESET_ALL}")


def get_token():
    """Obtiene un token de autenticación"""
    print(f"\n{INFO} Obteniendo token de autenticación...")

    # Primero intentar con credenciales comunes
    credentials = [
        {"username": "admin", "password": "P0rotit@s"},
        {"username": "admin", "password": "admin123"},
        {"username": "test_user", "password": "test123"},
    ]

    for cred in credentials:
        try:
            # IMPORTANTE: Usar JSON en lugar de form-data
            response = requests.post(
                f"{BASE_URL}{API_PREFIX}/auth/login",
                json={  # Cambio crítico: json en lugar de data
                    "username": cred["username"],
                    "password": cred["password"],
                    "remember_me": False
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                user_info = data.get("user", {})
                print(f"{SUCCESS} Token obtenido con usuario: {cred['username']}")
                print(f"     Nombre: {user_info.get('FullName', 'N/A')}")
                print(f"     Rol: {user_info.get('role_name', 'N/A')}")
                return token

        except Exception as e:
            continue

    print(f"{WARNING} No se pudo obtener token automáticamente")
    print(f"{INFO} Ingresa las credenciales manualmente:")

    username = input("   Usuario: ")
    password = input("   Contraseña: ")

    try:
        # Usar JSON para login manual también
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={
                "username": username,
                "password": password,
                "remember_me": False
            },
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            user_info = data.get("user", {})
            print(f"{SUCCESS} Token obtenido")
            print(f"     Nombre: {user_info.get('FullName', 'N/A')}")
            print(f"     Rol: {user_info.get('role_name', 'N/A')}")
            return token
        else:
            print(f"{ERROR} Error de autenticación: {response.status_code}")
            if response.status_code == 422:
                print(f"     El servidor espera JSON, no form-data")
            try:
                error_detail = response.json()
                print(f"     Detalles: {error_detail}")
            except:
                pass
            return None

    except Exception as e:
        print(f"{ERROR} Error conectando al servidor: {e}")
        return None


def test_endpoint(method, endpoint, headers, data=None, params=None, name=None):
    """Prueba un endpoint y reporta el resultado"""

    display_name = name or f"{method} {endpoint}"

    try:
        if method == "GET":
            response = requests.get(
                f"{BASE_URL}{API_PREFIX}{endpoint}",
                headers=headers,
                params=params
            )
        elif method == "POST":
            response = requests.post(
                f"{BASE_URL}{API_PREFIX}{endpoint}",
                headers=headers,
                json=data
            )
        elif method == "PATCH":
            response = requests.patch(
                f"{BASE_URL}{API_PREFIX}{endpoint}",
                headers=headers,
                json=data
            )
        else:
            print(f"{ERROR} Método no soportado: {method}")
            return False

        if response.status_code in [200, 201]:
            print(f"{SUCCESS} {display_name}: OK ({response.status_code})")

            # Mostrar parte de la respuesta si es interesante
            try:
                resp_data = response.json()
                if isinstance(resp_data, dict):
                    # Para respuestas de objeto único
                    if 'Id' in resp_data:
                        print(f"     ID: {resp_data.get('Id')}")
                    if 'ServiceTypeId' in resp_data:
                        print(f"     ServiceTypeId: {resp_data.get('ServiceTypeId')}")
                    if 'QueueLength' in resp_data:
                        print(f"     QueueLength: {resp_data.get('QueueLength')}")
                elif isinstance(resp_data, list):
                    print(f"     Registros: {len(resp_data)}")
            except:
                pass

            return response

        elif response.status_code == 404:
            print(f"{WARNING} {display_name}: No encontrado (404)")
            return None

        elif response.status_code == 401:
            print(f"{ERROR} {display_name}: No autorizado (401)")
            return None

        elif response.status_code == 500:
            print(f"{ERROR} {display_name}: Error del servidor (500)")
            try:
                error_detail = response.json().get('detail', 'Sin detalles')
                print(f"     Error: {error_detail}")
            except:
                print(f"     Respuesta: {response.text[:200]}")
            return None

        else:
            print(f"{WARNING} {display_name}: Código {response.status_code}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"{ERROR} {display_name}: No se puede conectar al servidor")
        print(f"     Verifica que el servidor esté ejecutándose en {BASE_URL}")
        return None

    except Exception as e:
        print(f"{ERROR} {display_name}: Error - {e}")
        return None


def test_queue_endpoints(token):
    """Prueba todos los endpoints principales de Queue"""

    headers = {"Authorization": f"Bearer {token}"}

    print_header("PRUEBAS DE ENDPOINTS DE QUEUE")

    # Test 1: GET /queue-states (con paginación - aquí estaba el error)
    print(f"\n{INFO} Probando endpoint con paginación (donde estaba el error)...")

    response = test_endpoint(
        "GET",
        "/queue-states/",
        headers,
        params={"skip": 0, "limit": 10, "include_empty": True},
        name="GET /queue-states/ con paginación"
    )

    if response and response.status_code == 200:
        print(f"   {SUCCESS} ¡ORDER BY funcionando correctamente!")

    # Test 2: GET /queue-states/summary
    test_endpoint(
        "GET",
        "/queue-states/summary",
        headers,
        name="GET /queue-states/summary"
    )

    # Test 3: POST /queue-states/ (crear)
    print(f"\n{INFO} Probando crear QueueState...")

    # Primero necesitamos obtener un ServiceType válido
    service_response = test_endpoint(
        "GET",
        "/service-types/",
        headers,
        params={"limit": 1},
        name="GET /service-types/ (para obtener ID)"
    )

    if service_response and service_response.status_code == 200:
        services = service_response.json()
        if services and len(services) > 0:
            service_id = services[0].get('Id')

            create_data = {
                "ServiceTypeId": service_id,
                "QueueLength": 0,
                "AverageWaitTime": 15
            }

            create_response = test_endpoint(
                "POST",
                "/queue-states/",
                headers,
                data=create_data,
                name="POST /queue-states/ (crear)"
            )

            if create_response and create_response.status_code in [200, 201]:
                queue_data = create_response.json()
                queue_id = queue_data.get('Id')

                # Test 4: GET /queue-states/{id}
                if queue_id:
                    test_endpoint(
                        "GET",
                        f"/queue-states/{queue_id}",
                        headers,
                        name=f"GET /queue-states/{queue_id}"
                    )

                    # Test 5: PATCH /queue-states/{id}
                    update_data = {
                        "QueueLength": 5,
                        "AverageWaitTime": 20
                    }

                    test_endpoint(
                        "PATCH",
                        f"/queue-states/{queue_id}",
                        headers,
                        data=update_data,
                        name=f"PATCH /queue-states/{queue_id}"
                    )

                    # Test 6: POST /queue-states/advance
                    advance_data = {
                        "ServiceTypeId": service_id,
                        "MarkCompleted": False
                    }

                    test_endpoint(
                        "POST",
                        "/queue-states/advance",
                        headers,
                        data=advance_data,
                        name="POST /queue-states/advance"
                    )

                    # Test 7: POST /queue-states/reset
                    reset_data = {
                        "ServiceTypeId": service_id,
                        "Reason": "Test reset",
                        "CancelPendingTickets": False
                    }

                    test_endpoint(
                        "POST",
                        "/queue-states/reset",
                        headers,
                        data=reset_data,
                        name="POST /queue-states/reset"
                    )

    # Test 8: GET /queue-states/active/all (también corregido)
    print(f"\n{INFO} Probando endpoint active/all (también corregido)...")

    test_endpoint(
        "GET",
        "/queue-states/active/all",
        headers,
        params={"skip": 0, "limit": 10},
        name="GET /queue-states/active/all con paginación"
    )


def main():
    """Función principal"""

    print(f"\n{Fore.MAGENTA}╔{'═'*58}╗")
    print(f"║      PRUEBA RÁPIDA DE ENDPOINTS DE QUEUE               ║")
    print(f"╚{'═'*58}╝{Style.RESET_ALL}")

    # Verificar que el servidor esté corriendo
    print(f"\n{INFO} Verificando servidor en {BASE_URL}...")

    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code in [200, 404]:
            print(f"{SUCCESS} Servidor respondiendo")
        else:
            print(f"{WARNING} Servidor respondió con código {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"{ERROR} No se puede conectar al servidor")
        print(f"\n{INFO} Asegúrate de que el servidor esté ejecutándose:")
        print(f"     uvicorn app.main:app --reload")
        return 1
    except Exception as e:
        print(f"{ERROR} Error verificando servidor: {e}")
        return 1

    # Obtener token
    token = get_token()

    if not token:
        print(f"\n{ERROR} No se pudo obtener token de autenticación")
        print(f"{INFO} Verifica que exista un usuario en la base de datos")
        return 1

    # Ejecutar pruebas
    test_queue_endpoints(token)

    # Resumen
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"  PRUEBAS COMPLETADAS")
    print(f"{'='*60}{Style.RESET_ALL}")

    print(f"\n{SUCCESS} Si no hay errores 500, los cambios funcionaron correctamente")
    print(f"{INFO} Los warnings 404 son normales si no hay datos")

    return 0


if __name__ == "__main__":
    exit(main())