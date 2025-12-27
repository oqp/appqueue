"""
Script simple para crear las tablas en la base de datos de test
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

# Importar la configuración
from app.core.config import settings

# IMPORTANTE: Importar Base ANTES que los modelos
from app.core.database import Base

# IMPORTANTE: Importar TODOS los modelos para que se registren
from app.models.role import Role
from app.models.service_type import ServiceType
from app.models.patient import Patient
from app.models.station import Station
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message_template import MessageTemplate
from app.models.notification import NotificationLog
from app.models.activity_log import ActivityLog
from app.models.daily_metrics import DailyMetrics
from app.models.queue_state import QueueState

# Crear URL para base de datos de test
# DATABASE_URL = f"mssql+pyodbc://{}:%40requ1pa@{settings.db_server}/{settings.db_name}_test?driver={settings.db_driver}&TrustServerCertificate=yes"
DATABASE_URL=f"mssql+pyodbc://sa:%40requ1pa@192.168.3.91/QueueManagementSystem_test?driver=ODBC+Driver+17+for+SQL+Server"

# Crear engine
engine = create_engine(DATABASE_URL, echo=True)

# Crear todas las tablas
print("Creando tablas...")
Base.metadata.create_all(bind=engine)

# Verificar qué tablas se crearon
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """))
    tables = result.fetchall()
    print(f"\n✅ {len(tables)} tablas creadas:")
    for table in tables:
        print(f"  - {table[0]}")

engine.dispose()
print("\n✅ Listo para ejecutar tests")