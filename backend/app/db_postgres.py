"""
PostgreSQL Database Adapter
===========================
Production-ready database layer with connection pooling and async support.
Replaces DuckDB for better concurrent access in Docker environment.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Generator
from contextlib import contextmanager
from functools import wraps

# Check if we should use PostgreSQL
USE_POSTGRES = os.getenv('USE_POSTGRES', 'false').lower() == 'true'
DATABASE_URL = os.getenv('DATABASE_URL', '')

logger = logging.getLogger(__name__)

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2 import pool
        from psycopg2.extras import RealDictCursor, Json
        POSTGRES_AVAILABLE = True
    except ImportError:
        POSTGRES_AVAILABLE = False
        logger.warning("psycopg2 not installed, falling back to DuckDB")
        USE_POSTGRES = False
else:
    POSTGRES_AVAILABLE = False

# Connection pool (initialized lazily)
_connection_pool: Optional[Any] = None


def _get_pool():
    """Get or create connection pool."""
    global _connection_pool
    if _connection_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL environment variable not set")
        
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=DATABASE_URL
        )
        logger.info("PostgreSQL connection pool created")
    return _connection_pool


@contextmanager
def get_pg_connection():
    """Context manager for PostgreSQL connections with auto-return to pool."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"PostgreSQL error: {e}")
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def get_pg_cursor(dict_cursor=True):
    """Context manager for PostgreSQL cursor with auto-commit."""
    with get_pg_connection() as conn:
        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
        finally:
            cursor.close()


def close_pg_pool():
    """Close all connections in the pool."""
    global _connection_pool
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("PostgreSQL connection pool closed")


# ============================================
# CRUD Operations for Posts
# ============================================

def pg_insert_post(source: str, author: str, content: str, url: str,
                   created_at: str, sentiment_score: float, sentiment_label: str,
                   language: str = 'unknown', country: str = None,
                   relevance_score: float = 0.0, product: str = None) -> Optional[int]:
    """Insert a new post into PostgreSQL."""
    with get_pg_cursor() as cur:
        cur.execute("""
            INSERT INTO posts (source, author, content, url, created_at, 
                             sentiment_score, sentiment_label, language, country, 
                             relevance_score, product)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (source, author, content, url, created_at, sentiment_score,
              sentiment_label, language, country, relevance_score, product))
        result = cur.fetchone()
        return result['id'] if result else None


def pg_get_all_posts(limit: int = 1000, offset: int = 0,
                     source: str = None, sentiment: str = None,
                     language: str = None, search: str = None,
                     sort_by: str = 'created_at', sort_order: str = 'DESC') -> List[Dict]:
    """Get posts with filtering and pagination."""
    conditions = []
    params = []
    
    if source:
        conditions.append("source = %s")
        params.append(source)
    if sentiment:
        conditions.append("sentiment_label = %s")
        params.append(sentiment)
    if language:
        conditions.append("language = %s")
        params.append(language)
    if search:
        conditions.append("content ILIKE %s")
        params.append(f"%{search}%")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Validate sort parameters
    valid_sort_cols = ['created_at', 'sentiment_score', 'relevance_score', 'source']
    sort_col = sort_by if sort_by in valid_sort_cols else 'created_at'
    sort_dir = 'ASC' if sort_order.upper() == 'ASC' else 'DESC'
    
    query = f"""
        SELECT * FROM posts 
        WHERE {where_clause}
        ORDER BY {sort_col} {sort_dir}
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    
    with get_pg_cursor() as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def pg_get_post_by_id(post_id: int) -> Optional[Dict]:
    """Get a single post by ID."""
    with get_pg_cursor() as cur:
        cur.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def pg_get_post_count(source: str = None, sentiment: str = None,
                      language: str = None) -> int:
    """Get total count of posts with optional filtering."""
    conditions = []
    params = []
    
    if source:
        conditions.append("source = %s")
        params.append(source)
    if sentiment:
        conditions.append("sentiment_label = %s")
        params.append(sentiment)
    if language:
        conditions.append("language = %s")
        params.append(language)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    with get_pg_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) as count FROM posts WHERE {where_clause}", params)
        return cur.fetchone()['count']


def pg_delete_post(post_id: int) -> bool:
    """Delete a post by ID."""
    with get_pg_cursor() as cur:
        cur.execute("DELETE FROM posts WHERE id = %s", (post_id,))
        return cur.rowcount > 0


def pg_url_exists(url: str) -> bool:
    """Check if a URL already exists in the database."""
    with get_pg_cursor() as cur:
        cur.execute("SELECT 1 FROM posts WHERE url = %s LIMIT 1", (url,))
        return cur.fetchone() is not None


def pg_delete_duplicate_posts() -> int:
    """Delete duplicate posts keeping the oldest."""
    with get_pg_cursor() as cur:
        cur.execute("""
            DELETE FROM posts 
            WHERE id NOT IN (
                SELECT MIN(id) FROM posts GROUP BY url
            )
        """)
        return cur.rowcount


# ============================================
# Statistics and Analytics
# ============================================

def pg_get_sentiment_stats() -> Dict[str, int]:
    """Get sentiment distribution statistics."""
    with get_pg_cursor() as cur:
        cur.execute("""
            SELECT sentiment_label, COUNT(*) as count 
            FROM posts 
            WHERE sentiment_label IS NOT NULL
            GROUP BY sentiment_label
        """)
        return {row['sentiment_label']: row['count'] for row in cur.fetchall()}


def pg_get_source_stats() -> Dict[str, int]:
    """Get posts count per source."""
    with get_pg_cursor() as cur:
        cur.execute("""
            SELECT source, COUNT(*) as count 
            FROM posts 
            GROUP BY source 
            ORDER BY count DESC
        """)
        return {row['source']: row['count'] for row in cur.fetchall()}


def pg_get_language_stats() -> Dict[str, int]:
    """Get posts count per language."""
    with get_pg_cursor() as cur:
        cur.execute("""
            SELECT language, COUNT(*) as count 
            FROM posts 
            GROUP BY language 
            ORDER BY count DESC
        """)
        return {row['language']: row['count'] for row in cur.fetchall()}


def pg_get_timeline_stats(days: int = 30) -> List[Dict]:
    """Get posts per day for timeline chart."""
    with get_pg_cursor() as cur:
        cur.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM posts
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (days,))
        return [{'date': str(row['date']), 'count': row['count']} 
                for row in cur.fetchall()]


# ============================================
# Saved Queries / Keywords
# ============================================

def pg_get_saved_queries() -> List[str]:
    """Get all saved search queries."""
    with get_pg_cursor() as cur:
        cur.execute("SELECT keyword FROM saved_queries ORDER BY created_at DESC")
        return [row['keyword'] for row in cur.fetchall()]


def pg_add_saved_query(keyword: str) -> bool:
    """Add a new saved query."""
    with get_pg_cursor() as cur:
        try:
            cur.execute("""
                INSERT INTO saved_queries (keyword, created_at) 
                VALUES (%s, %s)
                ON CONFLICT (keyword) DO NOTHING
            """, (keyword, datetime.now().isoformat()))
            return cur.rowcount > 0
        except Exception:
            return False


def pg_delete_saved_query(keyword: str) -> bool:
    """Delete a saved query."""
    with get_pg_cursor() as cur:
        cur.execute("DELETE FROM saved_queries WHERE keyword = %s", (keyword,))
        return cur.rowcount > 0


# ============================================
# Scraping Logs
# ============================================

def pg_add_scraping_log(source: str, level: str, message: str, 
                        details: Dict = None) -> int:
    """Add a scraping log entry."""
    with get_pg_cursor() as cur:
        cur.execute("""
            INSERT INTO scraping_logs (timestamp, source, level, message, details)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (datetime.now(), source, level, message, 
              Json(details) if details else None))
        return cur.fetchone()['id']


def pg_get_scraping_logs(limit: int = 100, source: str = None, 
                         level: str = None) -> List[Dict]:
    """Get scraping logs with filtering."""
    conditions = []
    params = []
    
    if source:
        conditions.append("source = %s")
        params.append(source)
    if level:
        conditions.append("level = %s")
        params.append(level)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    with get_pg_cursor() as cur:
        cur.execute(f"""
            SELECT * FROM scraping_logs 
            WHERE {where_clause}
            ORDER BY timestamp DESC 
            LIMIT %s
        """, params + [limit])
        return [dict(row) for row in cur.fetchall()]


# ============================================
# Job Queue Operations
# ============================================

def pg_enqueue_job(job_type: str, payload: Dict, priority: int = 0,
                   scheduled_for: datetime = None) -> str:
    """Add a job to the queue."""
    with get_pg_cursor() as cur:
        cur.execute("""
            INSERT INTO job_queue (job_type, payload, priority, scheduled_for)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (job_type, Json(payload), priority, 
              scheduled_for or datetime.now()))
        return str(cur.fetchone()['id'])


def pg_get_pending_jobs(job_type: str = None, limit: int = 10) -> List[Dict]:
    """Get pending jobs from queue."""
    conditions = ["status = 'pending'", "scheduled_for <= NOW()"]
    params = []
    
    if job_type:
        conditions.append("job_type = %s")
        params.append(job_type)
    
    where_clause = " AND ".join(conditions)
    
    with get_pg_cursor() as cur:
        cur.execute(f"""
            SELECT * FROM job_queue 
            WHERE {where_clause}
            ORDER BY priority DESC, created_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, params + [limit])
        return [dict(row) for row in cur.fetchall()]


def pg_update_job_status(job_id: str, status: str, 
                         error_message: str = None) -> bool:
    """Update job status."""
    with get_pg_cursor() as cur:
        if status == 'running':
            cur.execute("""
                UPDATE job_queue 
                SET status = %s, started_at = NOW(), attempts = attempts + 1
                WHERE id = %s
            """, (status, job_id))
        elif status in ('completed', 'failed'):
            cur.execute("""
                UPDATE job_queue 
                SET status = %s, completed_at = NOW(), error_message = %s
                WHERE id = %s
            """, (status, error_message, job_id))
        else:
            cur.execute("""
                UPDATE job_queue SET status = %s WHERE id = %s
            """, (status, job_id))
        return cur.rowcount > 0


def pg_save_job_result(job_id: str, job_type: str, status: str,
                       result: Dict, duration: float) -> str:
    """Save job result for history."""
    with get_pg_cursor() as cur:
        cur.execute("""
            INSERT INTO job_results (job_id, job_type, status, result, duration_seconds)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (job_id, job_type, status, Json(result), duration))
        return str(cur.fetchone()['id'])


# ============================================
# Base Keywords
# ============================================

def pg_get_base_keywords() -> Dict[str, List[str]]:
    """Get all base keywords grouped by category."""
    with get_pg_cursor() as cur:
        cur.execute("""
            SELECT category, keyword FROM base_keywords 
            ORDER BY category, keyword
        """)
        result = {}
        for row in cur.fetchall():
            cat = row['category']
            if cat not in result:
                result[cat] = []
            result[cat].append(row['keyword'])
        return result


def pg_add_base_keyword(category: str, keyword: str) -> bool:
    """Add a base keyword."""
    with get_pg_cursor() as cur:
        try:
            cur.execute("""
                INSERT INTO base_keywords (category, keyword)
                VALUES (%s, %s)
                ON CONFLICT (category, keyword) DO NOTHING
            """, (category, keyword))
            return cur.rowcount > 0
        except Exception:
            return False


def pg_delete_base_keyword(category: str, keyword: str) -> bool:
    """Delete a base keyword."""
    with get_pg_cursor() as cur:
        cur.execute("""
            DELETE FROM base_keywords 
            WHERE category = %s AND keyword = %s
        """, (category, keyword))
        return cur.rowcount > 0


# ============================================
# Health Check
# ============================================

def pg_health_check() -> Dict[str, Any]:
    """Check PostgreSQL connection health."""
    try:
        with get_pg_cursor() as cur:
            cur.execute("SELECT 1 as ok, NOW() as server_time")
            row = cur.fetchone()
            return {
                'status': 'healthy',
                'database': 'postgresql',
                'server_time': str(row['server_time']),
                'pool_size': _connection_pool.maxconn if _connection_pool else 0
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'database': 'postgresql',
            'error': str(e)
        }
