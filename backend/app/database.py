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

# Explicitly ensure these functions are available
# Import the module to access functions that might not be captured by import *
import app.db_postgres as pg_module

# Ensure recheck_posts_answered_status is available
try:
    recheck_posts_answered_status = pg_module.recheck_posts_answered_status
except AttributeError:
    try:
        recheck_posts_answered_status = pg_module.pg_recheck_posts_answered_status
    except AttributeError:
        # Fallback: define wrapper
        def recheck_posts_answered_status(*args, **kwargs):
            return pg_module.pg_recheck_posts_answered_status(*args, **kwargs)

# CRITICAL: Ensure finalize_job is DEFINED DIRECTLY in this module
# This ensures it's always available regardless of import * behavior
try:
    # Try to get it from pg_module
    _finalize_func = pg_module.finalize_job
except AttributeError:
    try:
        _finalize_func = pg_module.pg_finalize_job
    except AttributeError:
        # Last resort: define it as a wrapper
        def _finalize_func(job_id: str, status: str, error_message: str = None) -> bool:
            """Finalize a job by updating its status."""
            return pg_module.pg_update_job_status(job_id, status, error_message)

# Ensure reset_all_answered_status is available
try:
    reset_all_answered_status = pg_module.pg_reset_all_answered_status
except AttributeError:
    def reset_all_answered_status() -> int:
        """Reset all posts to unanswered status."""
        return pg_module.pg_reset_all_answered_status()

# Define finalize_job directly in this module's namespace
def finalize_job(job_id: str, status: str, error_message: str = None) -> bool:
    """Finalize a job by updating its status to completed, failed, or cancelled."""
    return _finalize_func(job_id, status, error_message)

# Also ensure it's available via the module dict
import sys
current_module = sys.modules[__name__]
current_module.finalize_job = finalize_job
current_module.recheck_posts_answered_status = recheck_posts_answered_status