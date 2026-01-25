"""
Database Module
===============
PostgreSQL database adapter - DuckDB has been removed.
Always uses PostgreSQL.

Usage: from app.database import *
"""
import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Set it to: postgresql://user:password@host:port/database"
    )

if not DATABASE_URL.startswith("postgresql://"):
    raise RuntimeError(
        f"DATABASE_URL must start with 'postgresql://'. Got: {DATABASE_URL[:20]}..."
    )

logger.info("[DB] Using PostgreSQL")
print("[DB] Using PostgreSQL")

from app.db_postgres import *
DB_TYPE = "postgresql"
