"""
CRUD operations module
"""

from .patient import patient
from .queue import queue_crud
from .user import user_crud
from .role import role_crud
from .station import station_crud
from .service_type import service_type_crud
from .ticket import ticket_crud

__all__ = [
    "patient",
    "user_crud",
    "role_crud",
    "station_crud",
    "service_type_crud",
    "ticket_crud",
    "queue_crud"
]