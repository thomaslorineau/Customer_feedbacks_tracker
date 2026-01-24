"""
DuckDB to PostgreSQL Migration Script
=====================================
Migrates all data from DuckDB to PostgreSQL.
Run once during initial Docker deployment.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('migration')

# Check for required libraries
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    logger.error("DuckDB not installed: pip install duckdb")

try:
    import psycopg2
    from psycopg2.extras import execute_batch
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.error("psycopg2 not installed: pip install psycopg2-binary")


def get_duckdb_connection(db_path: str):
    """Connect to DuckDB database."""
    if not DUCKDB_AVAILABLE:
        raise ImportError("DuckDB not installed")
    return duckdb.connect(db_path, read_only=True)


def get_postgres_connection(database_url: str):
    """Connect to PostgreSQL database."""
    if not POSTGRES_AVAILABLE:
        raise ImportError("psycopg2 not installed")
    return psycopg2.connect(database_url)


def migrate_posts(duck_conn, pg_conn):
    """Migrate posts table."""
    logger.info("Migrating posts...")
    
    # Get posts from DuckDB
    duck_cur = duck_conn.cursor()
    duck_cur.execute("""
        SELECT id, source, author, content, url, created_at,
               sentiment_score, sentiment_label, language, country,
               relevance_score, is_answered, answered_at, answered_by,
               answer_detection_method, product
        FROM posts
        ORDER BY id
    """)
    posts = duck_cur.fetchall()
    
    if not posts:
        logger.info("No posts to migrate")
        return 0
    
    logger.info(f"Found {len(posts)} posts to migrate")
    
    # Insert into PostgreSQL
    pg_cur = pg_conn.cursor()
    
    insert_query = """
        INSERT INTO posts (id, source, author, content, url, created_at,
                          sentiment_score, sentiment_label, language, country,
                          relevance_score, is_answered, answered_at, answered_by,
                          answer_detection_method, product)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """
    
    # Batch insert for performance
    batch_size = 500
    migrated = 0
    
    for i in range(0, len(posts), batch_size):
        batch = posts[i:i + batch_size]
        execute_batch(pg_cur, insert_query, batch, page_size=batch_size)
        pg_conn.commit()
        migrated += len(batch)
        logger.info(f"  Migrated {migrated}/{len(posts)} posts...")
    
    # Update sequence to avoid ID conflicts
    pg_cur.execute("""
        SELECT setval('posts_id_seq', COALESCE((SELECT MAX(id) FROM posts), 0) + 1, false)
    """)
    pg_conn.commit()
    
    logger.info(f"✓ Migrated {migrated} posts")
    return migrated


def migrate_saved_queries(duck_conn, pg_conn):
    """Migrate saved_queries table."""
    logger.info("Migrating saved queries...")
    
    duck_cur = duck_conn.cursor()
    try:
        duck_cur.execute("SELECT id, keyword, created_at FROM saved_queries ORDER BY id")
        queries = duck_cur.fetchall()
    except Exception:
        logger.warning("saved_queries table not found, skipping")
        return 0
    
    if not queries:
        logger.info("No saved queries to migrate")
        return 0
    
    pg_cur = pg_conn.cursor()
    
    insert_query = """
        INSERT INTO saved_queries (id, keyword, created_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (keyword) DO NOTHING
    """
    
    execute_batch(pg_cur, insert_query, queries)
    pg_conn.commit()
    
    # Update sequence
    pg_cur.execute("""
        SELECT setval('saved_queries_id_seq', 
                     COALESCE((SELECT MAX(id) FROM saved_queries), 0) + 1, false)
    """)
    pg_conn.commit()
    
    logger.info(f"✓ Migrated {len(queries)} saved queries")
    return len(queries)


def migrate_base_keywords(duck_conn, pg_conn):
    """Migrate base_keywords table."""
    logger.info("Migrating base keywords...")
    
    duck_cur = duck_conn.cursor()
    try:
        duck_cur.execute("SELECT id, category, keyword, created_at FROM base_keywords ORDER BY id")
        keywords = duck_cur.fetchall()
    except Exception:
        logger.warning("base_keywords table not found, skipping")
        return 0
    
    if not keywords:
        logger.info("No base keywords to migrate")
        return 0
    
    pg_cur = pg_conn.cursor()
    
    insert_query = """
        INSERT INTO base_keywords (id, category, keyword, created_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (category, keyword) DO NOTHING
    """
    
    execute_batch(pg_cur, insert_query, keywords)
    pg_conn.commit()
    
    # Update sequence
    pg_cur.execute("""
        SELECT setval('base_keywords_id_seq', 
                     COALESCE((SELECT MAX(id) FROM base_keywords), 0) + 1, false)
    """)
    pg_conn.commit()
    
    logger.info(f"✓ Migrated {len(keywords)} base keywords")
    return len(keywords)


def migrate_scraping_logs(duck_conn, pg_conn, limit: int = 10000):
    """Migrate recent scraping logs."""
    logger.info(f"Migrating scraping logs (last {limit})...")
    
    duck_cur = duck_conn.cursor()
    try:
        duck_cur.execute(f"""
            SELECT id, timestamp, source, level, message, details, created_at 
            FROM scraping_logs 
            ORDER BY timestamp DESC 
            LIMIT {limit}
        """)
        logs = duck_cur.fetchall()
    except Exception:
        logger.warning("scraping_logs table not found, skipping")
        return 0
    
    if not logs:
        logger.info("No logs to migrate")
        return 0
    
    pg_cur = pg_conn.cursor()
    
    insert_query = """
        INSERT INTO scraping_logs (id, timestamp, source, level, message, details, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    
    # Convert details to JSONB-compatible format
    processed_logs = []
    for log in logs:
        log_list = list(log)
        # Details field (index 5) - ensure it's a valid JSON string or None
        if log_list[5]:
            import json
            try:
                if isinstance(log_list[5], str):
                    json.loads(log_list[5])  # Validate
                else:
                    log_list[5] = json.dumps(log_list[5])
            except (json.JSONDecodeError, TypeError):
                log_list[5] = None
        processed_logs.append(tuple(log_list))
    
    batch_size = 500
    for i in range(0, len(processed_logs), batch_size):
        batch = processed_logs[i:i + batch_size]
        execute_batch(pg_cur, insert_query, batch, page_size=batch_size)
        pg_conn.commit()
    
    # Update sequence
    pg_cur.execute("""
        SELECT setval('scraping_logs_id_seq', 
                     COALESCE((SELECT MAX(id) FROM scraping_logs), 0) + 1, false)
    """)
    pg_conn.commit()
    
    logger.info(f"✓ Migrated {len(logs)} logs")
    return len(logs)


def verify_migration(duck_conn, pg_conn):
    """Verify migration was successful."""
    logger.info("Verifying migration...")
    
    duck_cur = duck_conn.cursor()
    pg_cur = pg_conn.cursor()
    
    tables = ['posts', 'saved_queries', 'base_keywords']
    all_ok = True
    
    for table in tables:
        try:
            duck_cur.execute(f"SELECT COUNT(*) FROM {table}")
            duck_count = duck_cur.fetchone()[0]
        except Exception:
            duck_count = 0
        
        pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
        pg_count = pg_cur.fetchone()[0]
        
        status = "✓" if pg_count >= duck_count else "✗"
        logger.info(f"  {table}: DuckDB={duck_count}, PostgreSQL={pg_count} {status}")
        
        if pg_count < duck_count:
            all_ok = False
    
    return all_ok


def run_migration(duckdb_path: str, postgres_url: str):
    """Run full migration."""
    logger.info("=" * 60)
    logger.info("DuckDB to PostgreSQL Migration")
    logger.info(f"Source: {duckdb_path}")
    logger.info(f"Target: {postgres_url.split('@')[1] if '@' in postgres_url else 'PostgreSQL'}")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    # Connect to databases
    logger.info("Connecting to databases...")
    duck_conn = get_duckdb_connection(duckdb_path)
    pg_conn = get_postgres_connection(postgres_url)
    
    try:
        # Run migrations
        stats = {
            'posts': migrate_posts(duck_conn, pg_conn),
            'saved_queries': migrate_saved_queries(duck_conn, pg_conn),
            'base_keywords': migrate_base_keywords(duck_conn, pg_conn),
            'scraping_logs': migrate_scraping_logs(duck_conn, pg_conn),
        }
        
        # Verify
        success = verify_migration(duck_conn, pg_conn)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("Migration Summary:")
        for table, count in stats.items():
            logger.info(f"  {table}: {count} records")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Status: {'SUCCESS' if success else 'PARTIAL'}")
        logger.info("=" * 60)
        
        return success
        
    finally:
        duck_conn.close()
        pg_conn.close()


def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate DuckDB to PostgreSQL')
    parser.add_argument(
        '--duckdb', '-d',
        default='data.duckdb',
        help='Path to DuckDB database file'
    )
    parser.add_argument(
        '--postgres', '-p',
        default=os.getenv('DATABASE_URL', 'postgresql://vibe_user:vibe_secure_password_2026@localhost:5432/vibe_tracker'),
        help='PostgreSQL connection URL'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without actually migrating'
    )
    
    args = parser.parse_args()
    
    # Resolve DuckDB path
    duckdb_path = Path(args.duckdb)
    if not duckdb_path.is_absolute():
        # Try relative to backend directory
        backend_dir = Path(__file__).resolve().parents[1]
        duckdb_path = backend_dir / args.duckdb
    
    if not duckdb_path.exists():
        logger.error(f"DuckDB file not found: {duckdb_path}")
        sys.exit(1)
    
    if args.dry_run:
        logger.info("DRY RUN - No changes will be made")
        duck_conn = get_duckdb_connection(str(duckdb_path))
        duck_cur = duck_conn.cursor()
        
        for table in ['posts', 'saved_queries', 'base_keywords', 'scraping_logs']:
            try:
                duck_cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = duck_cur.fetchone()[0]
                logger.info(f"  Would migrate {count} records from {table}")
            except Exception:
                logger.info(f"  Table {table} not found")
        
        duck_conn.close()
        return
    
    # Run migration
    success = run_migration(str(duckdb_path), args.postgres)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
