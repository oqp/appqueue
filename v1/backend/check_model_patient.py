"""
Script para verificar los campos exactos del modelo Patient
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.patient import Patient
from sqlalchemy import inspect

print("=" * 60)
print("CAMPOS DEL MODELO PATIENT")
print("=" * 60)

# Verificar atributos de columna
print("\n1. Columnas SQLAlchemy del modelo:")
print("-" * 40)

# Usar inspector para obtener las columnas reales
try:
    mapper = inspect(Patient)
    for column in mapper.columns:
        print(f"   {column.name}: {column.type}")
except Exception as e:
    print(f"Error al inspeccionar: {e}")

# Verificar atributos directos
print("\n2. Atributos directos del modelo:")
print("-" * 40)

# Buscar campos relacionados con tiempo
time_fields = []
for attr in dir(Patient):
    if not attr.startswith('_'):
        attr_lower = attr.lower()
        if 'create' in attr_lower or 'update' in attr_lower or 'time' in attr_lower or 'date' in attr_lower:
            time_fields.append(attr)
            obj = getattr(Patient, attr)
            print(f"   {attr}: {type(obj)}")

# Verificar campos específicos
print("\n3. Verificación de campos específicos:")
print("-" * 40)

fields_to_check = [
    'CreatedAt',
    'created_at',
    'CreateDate',
    'UpdatedAt',
    'updated_at',
    'UpdateDate',
    'IsActive',
    'is_active',
    'Active'
]

for field in fields_to_check:
    if hasattr(Patient, field):
        print(f"   ✅ {field} existe")
    else:
        print(f"   ❌ {field} NO existe")

# Verificar herencia
print("\n4. Clases base del modelo:")
print("-" * 40)
for base in Patient.__bases__:
    print(f"   - {base.__name__}")

    # Verificar atributos de las clases base
    if hasattr(base, '__table__'):
        print(f"     Tabla: {base.__table__.name if hasattr(base.__table__, 'name') else 'N/A'}")

print("\n" + "=" * 60)