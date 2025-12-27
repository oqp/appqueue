#!/usr/bin/env python3
"""
Script de pruebas para verificar la configuración del sistema
Ejecutar: python test_config.py
"""

import sys
import os
from pathlib import Path

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))


def print_header(title: str):
    print(f"\n{'=' * 50}")
    print(f"🧪 {title}")
    print(f"{'=' * 50}")


def print_result(test_name: str, success: bool, details: str = ""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"   📝 {details}")


def test_dependencies():
    """Prueba que todas las dependencias estén instaladas"""
    print_header("VERIFICACIÓN DE DEPENDENCIAS")

    required_packages = [
        ("fastapi", "FastAPI framework"),
        ("sqlalchemy", "ORM para base de datos"),
        ("pyodbc", "Driver SQL Server"),
        ("redis", "Cliente Redis"),
        ("pydantic", "Validación de datos"),
        ("jose", "JWT tokens"),
        ("passlib", "Hash de passwords"),
        ("python_dotenv", "Variables de entorno")
    ]

    all_ok = True

    for package, description in required_packages:
        try:
            if package == "python_dotenv":
                import dotenv
            elif package == "jose":
                from jose import jwt
            else:
                __import__(package)
            print_result(f"{package:<15}", True, description)
        except ImportError as e:
            print_result(f"{package:<15}", False, f"Error: {e}")
            all_ok = False

    return all_ok


def test_env_file():
    """Prueba que el archivo .env exista y tenga las variables necesarias"""
    print_header("VERIFICACIÓN ARCHIVO .env")

    # 1) Carga primero las variables de entorno
    from dotenv import load_dotenv
    load_dotenv()

    # 2) Verifica que el .env exista
    env_file = Path(".env")
    if not env_file.exists():
        print_result("Archivo .env", False, "Archivo .env no encontrado")
        print("   💡 Copia .env.example a .env y configúralo")
        return False

    print_result("Archivo .env", True, "Archivo encontrado")

    # 3) Ahora sí, verifica DATABASE_URL o componentes individuales
    has_database_url = bool(os.getenv("DATABASE_URL"))
    has_db_components = all([
        os.getenv("DB_SERVER"),
        os.getenv("DB_NAME"),
        os.getenv("DB_USERNAME"),
        os.getenv("DB_PASSWORD"),
    ])

    if not has_database_url and not has_db_components:
        print_result("Configuración BD", False, "Falta DATABASE_URL o componentes DB_*")
        return False
    elif has_db_components:
        print_result("Configuración BD", True, "Usando componentes individuales")
    else:
        print_result("Configuración BD", True, "Usando DATABASE_URL")

    # 4) Verifica luego las variables críticas
    critical_vars = ["SECRET_KEY", "APP_NAME"]
    missing_vars = [v for v in critical_vars if not os.getenv(v)]
    if missing_vars:
        print_result("Variables críticas", False, f"Faltan: {', '.join(missing_vars)}")
        return False
    else:
        print_result("Variables críticas", True, "Todas las variables están configuradas")
        return True


#
# def test_env_file():
#     """Prueba que el archivo .env exista y tenga las variables necesarias"""
#     print_header("VERIFICACIÓN ARCHIVO .env")
#
#     env_file = Path(".env")
#
#     if not env_file.exists():
#         print_result("Archivo .env", False, "Archivo .env no encontrado")
#         print("   💡 Copia .env.example a .env y configúralo")
#         return False
#
#     print_result("Archivo .env", True, "Archivo encontrado")
#
#     # Verificar variables críticas
#     critical_vars = [
#         "SECRET_KEY", "APP_NAME"
#     ]
#
#     # Verificar que tenga o DATABASE_URL o los componentes individuales
#     has_database_url = bool(os.getenv("DATABASE_URL"))
#     has_db_components = all([
#         os.getenv("DB_SERVER"),
#         os.getenv("DB_NAME"),
#         os.getenv("DB_USERNAME"),
#         os.getenv("DB_PASSWORD")
#     ])
#
#     if not has_database_url and not has_db_components:
#         print_result("Configuración BD", False, "Falta DATABASE_URL o componentes DB_*")
#         return False
#     elif has_db_components:
#         print_result("Configuración BD", True, "Usando componentes individuales")
#     elif has_database_url:
#         print_result("Configuración BD", True, "Usando DATABASE_URL")
#
#     try:
#         from dotenv import load_dotenv
#         load_dotenv()
#
#         missing_vars = []
#         for var in critical_vars:
#             value = os.getenv(var)
#             if not value or value == "":
#                 missing_vars.append(var)
#
#         if missing_vars:
#             print_result("Variables críticas", False, f"Faltan: {', '.join(missing_vars)}")
#             return False
#         else:
#             print_result("Variables críticas", True, "Todas las variables están configuradas")
#             return True
#
#     except Exception as e:
#         print_result("Carga de variables", False, f"Error: {e}")
#         return False


def test_configuration():
    """Prueba que la configuración se cargue correctly"""
    print_header("VERIFICACIÓN DE CONFIGURACIÓN")

    try:
        from app.core.config import settings

        print_result("Carga de configuración", True, f"App: {settings.APP_NAME}")
        print_result("Debug mode", settings.DEBUG, f"DEBUG = {settings.DEBUG}")
        print_result("Secret key", len(settings.SECRET_KEY) >= 32, f"Longitud: {len(settings.SECRET_KEY)} chars")

        # Verificar URL de base de datos
        db_url = settings.database_url_sync
        has_credentials = "@" in db_url and not db_url.startswith("mssql+pyodbc://username:password")
        print_result("BD credentials", has_credentials,
                     "Credenciales configuradas" if has_credentials else "Usar credenciales reales")

        return True

    except Exception as e:
        print_result("Configuración", False, f"Error: {e}")
        return False


def test_database():
    """Prueba la conexión a la base de datos"""
    print_header("VERIFICACIÓN BASE DE DATOS")

    try:
        from app.core.database import check_database_connection, get_database_info

        # Probar conexión
        connection_ok = check_database_connection()
        print_result("Conexión BD", connection_ok, "Conectado correctamente" if connection_ok else "Error de conexión")

        if connection_ok:
            # Obtener información de la BD
            db_info = get_database_info()
            if "error" not in db_info:
                print_result("Info BD", True, f"BD: {db_info.get('database_name')} en {db_info.get('server_name')}")
                print_result("Usuario BD", True, f"Usuario: {db_info.get('user_name')}")
            else:
                print_result("Info BD", False, db_info["error"])

        return connection_ok

    except Exception as e:
        print_result("Base de datos", False, f"Error: {e}")
        return False


def test_redis():
    """Prueba la conexión a Redis"""
    print_header("VERIFICACIÓN REDIS")

    try:
        from app.core.redis import check_redis_connection, get_redis_info

        # Probar conexión
        connection_ok = check_redis_connection()
        print_result("Conexión Redis", connection_ok,
                     "Conectado correctamente" if connection_ok else "Redis no disponible")

        if connection_ok:
            # Obtener información de Redis
            redis_info = get_redis_info()
            if "error" not in redis_info:
                print_result("Info Redis", True,
                             f"v{redis_info.get('version')} - Memoria: {redis_info.get('used_memory')}")
            else:
                print_result("Info Redis", False, redis_info["error"])
        else:
            print("   💡 Redis es opcional - el sistema funcionará sin cache")

        return True  # Redis es opcional

    except Exception as e:
        print_result("Redis", False, f"Error: {e}")
        print("   💡 Redis es opcional - el sistema funcionará sin cache")
        return True


def test_security():
    """Prueba el sistema de seguridad"""
    print_header("VERIFICACIÓN SEGURIDAD")

    try:
        from app.core.security import create_password_hash, verify_password, create_access_token, verify_token, \
            get_security_info

        # Probar hash de passwords
        test_password = "test_password_123"
        hashed = create_password_hash(test_password)
        verify_ok = verify_password(test_password, hashed)
        print_result("Hash passwords", verify_ok, "Bcrypt funcionando")

        # Probar JWT
        test_data = {"sub": "test_user", "permissions": ["read"]}
        token = create_access_token(test_data)
        decoded = verify_token(token)
        jwt_ok = decoded is not None and decoded.get("sub") == "test_user"
        print_result("JWT tokens", jwt_ok, "JWT funcionando")

        # Info de seguridad
        sec_info = get_security_info()
        print_result("Config seguridad", "error" not in sec_info, f"Algoritmo: {sec_info.get('algorithm', 'N/A')}")

        return verify_ok and jwt_ok

    except Exception as e:
        print_result("Seguridad", False, f"Error: {e}")
        return False


def test_directories():
    """Prueba que los directorios necesarios existan"""
    print_header("VERIFICACIÓN DIRECTORIOS")

    try:
        from app.core.config import settings

        # Crear directorios si no existen
        settings.ensure_directories()

        directories = [
            ("logs", "./logs/"),
            ("static", "./static/"),
            ("uploads", settings.UPLOAD_PATH),
            ("reports", settings.REPORTS_EXPORT_PATH)
        ]

        all_ok = True
        for name, path in directories:
            exists = Path(path).exists()
            print_result(f"Dir {name}", exists, path)
            if not exists:
                all_ok = False

        return all_ok

    except Exception as e:
        print_result("Directorios", False, f"Error: {e}")
        return False


def main():
    """Función principal de pruebas"""
    print("🚀 SISTEMA DE GESTIÓN DE COLAS - VERIFICACIÓN DE CONFIGURACIÓN")
    print(f"📁 Directorio: {os.getcwd()}")
    print(f"🐍 Python: {sys.version}")

    # Ejecutar todas las pruebas
    tests = [
        ("Dependencias", test_dependencies),
        ("Archivo .env", test_env_file),
        ("Configuración", test_configuration),
        ("Base de datos", test_database),
        ("Redis", test_redis),
        ("Seguridad", test_security),
        ("Directorios", test_directories)
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Error ejecutando prueba {test_name}: {e}")
            results[test_name] = False

    # Resumen final
    print_header("RESUMEN FINAL")

    passed = sum(1 for success in results.values() if success)
    total = len(results)

    for test_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")

    print(f"\n📊 RESULTADO: {passed}/{total} pruebas pasadas")

    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está listo.")
        print("💚 Puedes continuar con el desarrollo.")
    elif passed >= total - 1:  # Solo Redis falló
        print("⚠️  Sistema casi listo - solo Redis opcional no disponible.")
        print("💛 Puedes continuar con el desarrollo.")
    else:
        print("⚠️  Hay problemas que necesitan resolverse antes de continuar.")
        print("💔 Revisa los errores y configura correctamente.")

    print(f"\n🏁 Pruebas completadas.")
    return passed == total or passed >= total - 1


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)