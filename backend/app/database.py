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

# Explicitly ensure recheck_posts_answered_status is available after import
# This is needed because the alias is defined at the end of db_postgres.py
try:
    from app.db_postgres import recheck_posts_answered_status
except ImportError:
    # If direct import fails, try to get it from the module
    import app.db_postgres as pg_module
    if hasattr(pg_module, 'recheck_posts_answered_status'):
        recheck_posts_answered_status = pg_module.recheck_posts_answered_status
    else:
        # Fallback: import the function directly
        from app.db_postgres import pg_recheck_posts_answered_status as recheck_posts_answered_status