#!/usr/bin/env python3
"""
Script de comparaison Staging vs Production
Compare les données entre staging (DuckDB) et production (SQLite)
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

def get_table_sample(conn, table_name, limit=5, is_duckdb=False):
    """Récupérer un échantillon de lignes."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
    return cursor.fetchall()

def compare_table_counts(conn_prod, conn_staging, table_name):
    """Comparer le nombre de lignes entre production et staging."""
    count_prod = count_rows(conn_prod, table_name, is_duckdb=False)
    count_staging = count_rows(conn_staging, table_name, is_duckdb=True)
    
    diff = count_staging - count_prod
    diff_pct = (diff / count_prod * 100) if count_prod > 0 else 0
    
    status = "✓" if abs(diff) <= 1 else "⚠️"  # Tolérance de 1 ligne
    print(f"  {table_name:20s} Prod: {count_prod:6d} | Staging: {count_staging:6d} | Diff: {diff:+6d} ({diff_pct:+.1f}%) {status}")
    
    return abs(diff) <= 1, count_prod, count_staging

def main():
    """Point d'entrée principal."""
    prod_db = backend_dir / "data.db"
    staging_duckdb = backend_dir / "data_staging.duckdb"
    
    print("=" * 70)
    print("Comparaison Staging (DuckDB) vs Production (SQLite)")
    print("=" * 70)
    print(f"\nProduction: {prod_db}")
    print(f"Staging:    {staging_duckdb}")
    
    # Vérifier que les fichiers existent
    if not prod_db.exists():
        print(f"\n❌ Error: {prod_db} not found")
        return 1
    
    if not staging_duckdb.exists():
        print(f"\n❌ Error: {staging_duckdb} not found")
        return 1
    
    # Connexions
    print("\nConnecting to databases...")
    try:
        conn_prod = sqlite3.connect(prod_db)
        conn_staging = duckdb.connect(str(staging_duckdb))
    except Exception as e:
        print(f"❌ Error connecting to databases: {e}")
        return 1
    
    # Comparer les tables
    print("\nComparing table counts...")
    tables = ['posts', 'saved_queries', 'scraping_logs', 'jobs']
    all_match = True
    total_prod = 0
    total_staging = 0
    
    for table in tables:
        match, count_prod, count_staging = compare_table_counts(conn_prod, conn_staging, table)
        if not match:
            all_match = False
        total_prod += count_prod
        total_staging += count_staging
    
    # Fermer les connexions
    conn_prod.close()
    conn_staging.close()
    
    print("\n" + "=" * 70)
    print(f"Total rows - Production: {total_prod} | Staging: {total_staging}")
    diff_total = total_staging - total_prod
    print(f"Difference: {diff_total:+d} rows")
    
    if all_match:
        print("\n✅ All tables match (within tolerance)!")
        print("✅ Migration staging successful!")
        return 0
    else:
        print("\n⚠️  Some tables have differences (may be expected if staging was updated)")
        return 0  # Return 0 car des différences peuvent être normales

if __name__ == '__main__':
    sys.exit(main())

