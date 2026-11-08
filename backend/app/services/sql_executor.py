"""
SQL Validation & Safe Execution Service
Implements application-level AST/Regex firewall, JSON type serialization,
and transaction rollback safeguards.
"""

import re
import logging
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID
from typing import List, Dict, Any, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import psycopg2

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class UnsafeSQLError(Exception):
    """Raised when query fails SQL Firewall safety and read-only checks."""
    pass


class DatabaseExecutionError(Exception):
    """Raised when database engine execution fails (syntax, schema, or runtime error)."""
    pass


# =============================================================================
# SQL EXECUTOR CLASS
# =============================================================================

class SQLExecutor:
    """
    Safely validates, sanitizes, and executes AI-generated SQL on read-only database connections.
    """

    # Forbidden DDL, DML, and security-sensitive PostgreSQL commands
    FORBIDDEN_PATTERN = re.compile(
        r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|REPLACE|EXEC|EXECUTE|COPY|PG_SLEEP)\b",
        re.IGNORECASE,
    )

    @classmethod
    def validate_read_only_sql(cls, sql: str) -> str:
        """
        Validates that the SQL statement is strictly a read-only SELECT or WITH statement.
        Rejects mutating operations, stacked queries, and destructive functions.
        """
        if not sql or not sql.strip():
            raise UnsafeSQLError("متن کوئری ارسالی خالی است.")

        clean = sql.strip()

        # Remove single-line comments (-- ...) and multi-line comments (/* ... */)
        clean = re.sub(r"--.*?$", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
        clean = clean.strip()

        # Ensure query starts with SELECT or WITH
        if not re.match(r"^(SELECT|WITH)\b", clean, re.IGNORECASE):
            raise UnsafeSQLError(
                "کوئری‌های ارسالی تنها باید با کلیدواژه‌های SELECT یا WITH آغاز شوند."
            )

        # Check for stacked queries (statements separated by internal semicolons)
        statements = [stmt.strip() for stmt in clean.split(";") if stmt.strip()]
        if len(statements) > 1:
            raise UnsafeSQLError("اجرای چند کوئری همزمان (Stacked Queries) مجاز نمی‌باشد.")

        # Match forbidden keywords
        forbidden_match = cls.FORBIDDEN_PATTERN.search(clean)
        if forbidden_match:
            keyword = forbidden_match.group(1).upper()
            raise UnsafeSQLError(
                f"شناسایی دستور غیرمجاز '{keyword}'. هوش مصنوعی تنها به عملیات خواندنی (SELECT) دسترسی دارد."
            )

        return clean

    @classmethod
    def serialize_value(cls, val: Any) -> Any:
        """
        Converts non-serializable PostgreSQL types (Decimal, datetime, UUID)
        into JSON-compatible native Python primitives.
        """
        if isinstance(val, Decimal):
            # Convert to float or int
            return float(val) if val % 1 else int(val)
        elif isinstance(val, (datetime, date)):
            return val.isoformat()
        elif isinstance(val, UUID):
            return str(val)
        return val

    @classmethod
    def execute_query(
        cls,
        db: Session,
        sql: str,
        max_rows: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Executes sanitized SQL query on the provided read-only session,
        returning serialized rows and total row count.
        """
        sanitized_sql = cls.validate_read_only_sql(sql)

        try:
            result = db.execute(text(sanitized_sql))
            keys = list(result.keys())
            raw_rows = result.fetchall()
            total_count = len(raw_rows)

            serialized_rows = []
            for row in raw_rows[:max_rows]:
                row_dict = {}
                for idx, col_name in enumerate(keys):
                    row_dict[col_name] = cls.serialize_value(row[idx])
                serialized_rows.append(row_dict)

            return serialized_rows, total_count

        except (SQLAlchemyError, psycopg2.Error) as exc:
            # Vital for PostgreSQL: rollback transaction so session state is cleanly cleared for retries
            try:
                db.rollback()
            except Exception as rb_exc:
                logger.error("Session rollback failed: %s", rb_exc)

            error_message = str(exc).strip()
            # Extract root cause if available
            if hasattr(exc, "orig") and exc.orig:
                error_message = str(exc.orig).strip()

            logger.warning("Database execution error: %s", error_message)
            raise DatabaseExecutionError(error_message) from exc
