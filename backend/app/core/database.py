"""
Core Database Module - Dual Engine Management & Dependency Injection
Provides distinct connection pools for administrative tasks and read-only AI SQL execution.
"""

import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# =============================================================================
# DUAL SQLALCHEMY 2.0 ENGINES
# =============================================================================

# 1. Administrative Engine: For schema inspection, migrations, and system health checks
admin_engine = create_engine(
    settings.ADMIN_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

# 2. Read-Only AI Engine: Exclusively for AI SQL Agent with hard engine-level safety constraints
readonly_engine = create_engine(
    settings.READONLY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "options": "-c default_transaction_read_only=on -c statement_timeout=10000 -c timezone=Asia/Tehran"
    },
    echo=False,
)

# Session factories
AdminSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=admin_engine,
)

ReadOnlySessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=readonly_engine,
)

Base = declarative_base()


# =============================================================================
# FASTAPI DEPENDENCY INJECTION GENERATORS
# =============================================================================

def get_admin_db() -> Generator[Session, None, None]:
    """
    Dependency injection generator yielding an administrative database session.
    Guarantees session cleanup in all scenarios to prevent connection pool exhaustion.
    """
    db = AdminSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_readonly_db() -> Generator[Session, None, None]:
    """
    Dependency injection generator yielding a read-only database session for LLM execution.
    Guarantees rollback of any open transaction and proper session closure.
    """
    db = ReadOnlySessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


# =============================================================================
# HEALTH CHECK UTILITY
# =============================================================================

def check_database_health() -> dict:
    """
    Performs quick connectivity tests on both database connection pools.
    Returns status map indicating whether engines are actively communicating with PostgreSQL.
    """
    health = {
        "admin_connected": False,
        "readonly_connected": False,
    }

    # Test Admin Engine
    try:
        with admin_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            health["admin_connected"] = True
    except Exception as e:
        logger.error("Admin database health check failed: %s", e)

    # Test Read-Only Engine
    try:
        with readonly_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            health["readonly_connected"] = True
    except Exception as e:
        logger.error("Readonly database health check failed: %s", e)

    return health
