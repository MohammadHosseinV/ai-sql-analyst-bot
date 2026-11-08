"""
Core Package - Application Settings, Database Engines, and Dependency Injection.
"""

from app.core.config import get_settings, Settings
from app.core.database import (
    admin_engine,
    readonly_engine,
    AdminSessionLocal,
    ReadOnlySessionLocal,
    get_admin_db,
    get_readonly_db,
    check_database_health,
    Base,
)

__all__ = [
    "get_settings",
    "Settings",
    "admin_engine",
    "readonly_engine",
    "AdminSessionLocal",
    "ReadOnlySessionLocal",
    "get_admin_db",
    "get_readonly_db",
    "check_database_health",
    "Base",
]
