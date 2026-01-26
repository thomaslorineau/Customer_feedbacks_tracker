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

# Explicitly ensure recheck_posts_answered_status is available
# Import it directly to ensure it's in the module namespace
import app.db_postgres as pg_module
if hasattr(pg_module, 'recheck_posts_answered_status'):
    recheck_posts_answered_status = pg_module.recheck_posts_answered_status
elif hasattr(pg_module, 'pg_recheck_posts_answered_status'):
    # Fallback: use the pg_ prefixed version if alias doesn't exist
    recheck_posts_answered_status = pg_module.pg_recheck_posts_answered_status