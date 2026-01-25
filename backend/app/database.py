"""
Database Selector Module
========================
Automatically selects PostgreSQL (Docker) or DuckDB (local dev) based on environment.

This module should be imported instead of db.py directly.
Usage: from app.database import *
"""
import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgresql://")

if USE_POSTGRES:
    # Production mode: Use PostgreSQL (Docker)
    logger.info("✅ [DB] Using PostgreSQL (Docker mode)")
    print("✅ [DB] Using PostgreSQL (Docker mode)")
    from app.db_postgres import *
    DB_TYPE = "postgresql"
else:
    # Development mode: Use DuckDB
    logger.info("✅ [DB] Using DuckDB (local dev mode)")
    print("✅ [DB] Using DuckDB (local dev mode)")
    from app.db import *
    DB_TYPE = "duckdb"
