#!/usr/bin/env python3
"""
Script de vérification de la migration DuckDB
Compare les données SQLite et DuckDB pour vérifier l'intégrité
"""

import sys
from pathlib import Path
import sqlite3
import duckdb

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

def count_rows(conn, table_name, is_duckdb=False):
    """Compter les lignes d'une table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]

def compare_table_counts(conn_sqlite, conn_duckdb, table_name):
    """Comparer le nombre de lignes entre SQLite et DuckDB."""
    count_sqlite = count_rows(conn_sqlite, table_name, is_duckdb=False)
    count_duckdb = count_rows(conn_duckdb, table_name, is_duckdb=True)
    
    status = "✓" if count_sqlite == count_duckdb else "❌"
    print(f"  {table_name:20s} SQLite: {count_sqlite:6d} | DuckDB: {count_duckdb:6d} {status}")
    
    return count_sqlite == count_duckdb, count_sqlite, count_duckdb

def main():
    """Point d'entrée principal."""
    import os
    
    # Déterminer les chemins selon l'environnement
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "staging":
        sqlite_db = backend_dir / "data_staging.db"
        duckdb_file = backend_dir / "data_staging.duckdb"
    else:
        sqlite_db = backend_dir / "data.db"
        duckdb_file = backend_dir / "data.duckdb"
    
    print("=" * 70)
    print(f"Vérification Migration SQLite → DuckDB ({env})")
    print("=" * 70)
    print(f"\nSQLite: {sqlite_db}")
    print(f"DuckDB: {duckdb_file}")
    
    # Vérifier que les fichiers existent
    if not sqlite_db.exists():
        print(f"\n❌ Error: {sqlite_db} not found")
        return 1
    
    if not duckdb_file.exists():
        print(f"\n❌ Error: {duckdb_file} not found")
        return 1
    
    # Connexions
    print("\nConnecting to databases...")
    try:
        conn_sqlite = sqlite3.connect(sqlite_db)
        conn_duckdb = duckdb.connect(str(duckdb_file))
    except Exception as e:
        print(f"❌ Error connecting to databases: {e}")
        return 1
    
    # Comparer les tables
    print("\nComparing table counts...")
    tables = ['posts', 'saved_queries', 'scraping_logs', 'jobs']
    all_match = True
    total_sqlite = 0
    total_duckdb = 0
    
    for table in tables:
        match, count_sqlite, count_duckdb = compare_table_counts(conn_sqlite, conn_duckdb, table)
        if not match:
            all_match = False
        total_sqlite += count_sqlite
        total_duckdb += count_duckdb
    
    # Fermer les connexions
    conn_sqlite.close()
    conn_duckdb.close()
    
    print("\n" + "=" * 70)
    print(f"Total rows - SQLite: {total_sqlite} | DuckDB: {total_duckdb}")
    
    if all_match:
        print("✅ All tables match!")
        return 0
    else:
        print("❌ Some tables don't match!")
        return 1

if __name__ == '__main__':
    sys.exit(main())

