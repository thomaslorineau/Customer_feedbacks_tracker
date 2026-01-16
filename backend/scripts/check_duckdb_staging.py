#!/usr/bin/env python3
"""Vérifier que DuckDB est bien utilisé en staging"""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

os.environ['ENVIRONMENT'] = 'staging'
os.environ['USE_DUCKDB'] = 'true'

from app.config import config
from app.db import get_db_connection

print("=" * 70)
print("Vérification DuckDB Staging")
print("=" * 70)
print(f"\nENVIRONMENT: {config.ENVIRONMENT}")
print(f"USE_DUCKDB: {config.USE_DUCKDB}")
print(f"DB_PATH: {config.DB_PATH}")
print(f"Fichier existe: {config.DB_PATH.exists()}")

conn, is_duckdb = get_db_connection()
db_type = "DuckDB" if is_duckdb else "SQLite (fallback)"
print(f"\nType de connexion: {db_type}")

if is_duckdb:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM posts")
    count = cursor.fetchone()[0]
    print(f"Posts dans DuckDB: {count}")
    conn.close()
    print("\n✅ OUI - Vous êtes bien sur DuckDB en staging!")
else:
    print("\n⚠️  NON - Fallback vers SQLite (DuckDB non disponible)")
    conn.close()

print("=" * 70)



