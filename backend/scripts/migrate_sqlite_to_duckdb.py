#!/usr/bin/env python3
"""
Script de migration SQLite → DuckDB
Migre toutes les données d'une base SQLite vers DuckDB
"""

import sys
from pathlib import Path
import sqlite3
import duckdb

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

def get_table_columns(conn, table_name, is_duckdb=False):
    """Récupérer les colonnes d'une table."""
    cursor = conn.cursor()
    if is_duckdb:
        cursor.execute(f"DESCRIBE {table_name}")
        return [row[0] for row in cursor.fetchall()]
    else:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

def migrate_table(conn_sqlite, conn_duckdb, table_name):
    """Migrer une table de SQLite vers DuckDB."""
    print(f"  Migrating table: {table_name}...", end=" ")
    
    # Lire depuis SQLite
    cursor_sqlite = conn_sqlite.cursor()
    cursor_sqlite.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor_sqlite.fetchone()[0]
    
    if count == 0:
        print(f"0 rows (empty)")
        return 0
    
    # Récupérer les colonnes
    columns = get_table_columns(conn_sqlite, table_name, is_duckdb=False)
    columns_str = ", ".join(columns)
    
    # Lire toutes les données
    cursor_sqlite.execute(f"SELECT * FROM {table_name}")
    rows = cursor_sqlite.fetchall()
    
    # Insérer dans DuckDB
    cursor_duckdb = conn_duckdb.cursor()
    placeholders = ", ".join(["?" for _ in columns])
    
    try:
        cursor_duckdb.executemany(
            f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})",
            rows
        )
        conn_duckdb.commit()
        print(f"{len(rows)} rows ✓")
        return len(rows)
    except Exception as e:
        print(f"ERROR: {e}")
        return 0

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
    print(f"Migration SQLite → DuckDB ({env})")
    print("=" * 70)
    print(f"\nSQLite source: {sqlite_db}")
    print(f"DuckDB target: {duckdb_file}")
    
    # Vérifier que SQLite existe
    if not sqlite_db.exists():
        print(f"\n❌ Error: {sqlite_db} not found")
        return 1
    
    # Supprimer DuckDB si existe
    if duckdb_file.exists():
        print(f"\n⚠️  Warning: {duckdb_file} already exists, removing...")
        duckdb_file.unlink()
    
    # Connexions
    print("\nConnecting to databases...")
    try:
        conn_sqlite = sqlite3.connect(sqlite_db)
        conn_duckdb = duckdb.connect(str(duckdb_file))
    except Exception as e:
        print(f"❌ Error connecting to databases: {e}")
        return 1
    
    # Créer le schéma dans DuckDB (manuellement)
    print("\nCreating schema in DuckDB...")
    try:
        cursor_duckdb = conn_duckdb.cursor()
        
        # Table posts
        cursor_duckdb.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id BIGSERIAL PRIMARY KEY,
                source TEXT,
                author TEXT,
                content TEXT,
                url TEXT,
                created_at TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                language TEXT DEFAULT 'unknown',
                country TEXT
            )
        ''')
        
        # Indexes for posts
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source)')
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_posts_sentiment ON posts(sentiment_label)')
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC)')
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_posts_language ON posts(language)')
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_posts_source_date ON posts(source, created_at DESC)')
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_posts_url ON posts(url)')
        
        # Table saved_queries
        cursor_duckdb.execute('''
            CREATE TABLE IF NOT EXISTS saved_queries (
                id BIGSERIAL PRIMARY KEY,
                keyword TEXT UNIQUE,
                created_at TEXT
            )
        ''')
        
        # Table scraping_logs
        cursor_duckdb.execute('''
            CREATE TABLE IF NOT EXISTS scraping_logs (
                id BIGSERIAL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT,
                level TEXT,
                message TEXT,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Indexes for logs
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON scraping_logs(timestamp DESC)')
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_logs_source ON scraping_logs(source)')
        cursor_duckdb.execute('CREATE INDEX IF NOT EXISTS idx_logs_level ON scraping_logs(level)')
        
        # Table jobs
        cursor_duckdb.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                progress_total INTEGER,
                progress_completed INTEGER,
                results TEXT,
                errors TEXT,
                cancelled INTEGER DEFAULT 0,
                error TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn_duckdb.commit()
        print("  Schema created ✓")
    except Exception as e:
        print(f"  ❌ Error creating schema: {e}")
        import traceback
        traceback.print_exc()
        conn_sqlite.close()
        conn_duckdb.close()
        return 1
    
    # Migrer les tables
    print("\nMigrating data...")
    tables = ['posts', 'saved_queries', 'scraping_logs', 'jobs']
    total_rows = 0
    
    for table in tables:
        try:
            rows = migrate_table(conn_sqlite, conn_duckdb, table)
            total_rows += rows
        except Exception as e:
            print(f"  ❌ Error migrating {table}: {e}")
    
    # Fermer les connexions
    conn_sqlite.close()
    conn_duckdb.close()
    
    print("\n" + "=" * 70)
    print(f"✅ Migration complete: {total_rows} rows migrated")
    print(f"   DuckDB file: {duckdb_file}")
    print("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

