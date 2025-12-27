#!/usr/bin/env python3
"""
Prueba rápida de conexión a base de datos
Ejecutar: python quick_db_test.py
"""

import sys
from pathlib import Path

from sqlalchemy import text

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))


def test_basic_connection():
    """Prueba básica de conexión"""
    print("🧪 PRUEBA BÁSICA DE CONEXIÓN A SQL SERVER")
    print("=" * 50)

    try:
        # Cargar variables de entorno
        from dotenv import load_dotenv
        load_dotenv()

        # Probar configuración
        print("📋 1. Cargando configuración...")
        from app.core.config import settings
        print(f"   ✅ App: {settings.APP_NAME}")
        print(f"   ✅ BD: {settings.DB_NAME} en {settings.DB_SERVER}")

        # Probar creación de engine
        print("\n🔧 2. Creando engine de base de datos...")
        from sqlalchemy import create_engine

        # Configuración mínima para prueba
        test_config = {
            "echo": False,
            "pool_pre_ping": True,
        }

        engine = create_engine(settings.database_url_sync, **test_config)
        print("   ✅ Engine creado exitosamente")

        # Probar conexión
        print("\n🔗 3. Probando conexión...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test, GETDATE() as fecha, @@VERSION as version"))
            row = result.fetchone()
            print(f"   ✅ Conexión exitosa!")
            print(f"   📊 Test: {row[0]}")
            print(f"   📅 Fecha servidor: {row[1]}")
            print(f"   🖥️  Versión: {row[2].split('n')[0]}")

        # Probar BD específica
        print(f"\n📂 4. Verificando base de datos {settings.DB_NAME}...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT DB_NAME() as current_db, COUNT(*) as table_count FROM information_schema.tables WHERE table_type = 'BASE TABLE'"))
            row = result.fetchone()
            print(f"   ✅ BD actual: {row[0]}")
            print(f"   📋 Tablas encontradas: {row[1]}")

            if row[1] > 0:
                print("   💚 ¡Base de datos configurada correctamente!")
            else:
                print("   ⚠️  Base de datos vacía - necesita ejecutar script inicial")

        print(f"\n🎉 ¡PRUEBA EXITOSA! Conexión a SQL Server funcionando.")
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\n💡 Posibles soluciones:")
        print(f"   1. Verificar que SQL Server esté corriendo")
        print(f"   2. Verificar credenciales en .env")
        print(f"   3. Verificar que la BD AppQueueMunoz exista")
        print(f"   4. Verificar driver ODBC 17 para SQL Server")
        return False


def test_with_full_config():
    """Prueba con configuración completa"""
    print("\n" + "=" * 50)
    print("🧪 PRUEBA CON CONFIGURACIÓN COMPLETA")
    print("=" * 50)

    try:
        from app.core.database import check_database_connection, get_database_info

        print("📡 Probando con configuración completa...")

        # Probar conexión
        if check_database_connection():
            print("   ✅ Conexión verificada")

            # Obtener info
            db_info = get_database_info()
            if "error" not in db_info:
                print(f"   📊 Servidor: {db_info.get('server_name')}")
                print(f"   🗄️  Base de datos: {db_info.get('database_name')}")
                print(f"   👤 Usuario: {db_info.get('user_name')}")
                print(f"   🔗 Pool size: {db_info.get('connection_pool_size')}")

            print("\n💚 ¡CONFIGURACIÓN COMPLETA FUNCIONANDO!")
            return True
        else:
            print("   ❌ Error en configuración completa")
            return False

    except Exception as e:
        print(f"   ❌ Error en configuración completa: {e}")
        return False


if __name__ == "__main__":
    print("🚀 PRUEBA RÁPIDA DE BASE DE DATOS SQL SERVER")

    # Prueba básica
    basic_ok = test_basic_connection()

    if basic_ok:
        # Prueba completa
        full_ok = test_with_full_config()

        if full_ok:
            print(f"\n🎉 ¡TODO FUNCIONANDO! Puedes continuar con el desarrollo.")
            sys.exit(0)

    print(f"\n❌ Hay problemas que resolver antes de continuar.")
    sys.exit(1)