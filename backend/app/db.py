from pathlib import Path
import json
import datetime
from typing import Optional, Tuple
import logging

# Import DuckDB
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    raise ImportError("DuckDB is required but not installed. Run: pip install duckdb")

# Import config for database path
try:
    from .config import config
    DB_FILE = getattr(config, 'DB_PATH', None)
    if DB_FILE is None:
        DB_FILE = Path(__file__).resolve().parents[1] / "data.duckdb"
except ImportError:
    DB_FILE = Path(__file__).resolve().parents[1] / "data.duckdb"

logger = logging.getLogger(__name__)


def get_db_connection():
    """
    Get DuckDB database connection.
    Returns: (connection, is_duckdb) where is_duckdb is always True
    """
    if not DUCKDB_AVAILABLE:
        raise RuntimeError("DuckDB is not available. Please install it: pip install duckdb")
    
    try:
        # Connect to DuckDB file directly
        conn = duckdb.connect(str(DB_FILE))
        return conn, True
    except Exception as e:
        logger.error(f"DuckDB connection failed: {e}")
        raise RuntimeError(f"Failed to connect to DuckDB database at {DB_FILE}: {e}")


def init_db():
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    # DuckDB: Create sequence first, then use BIGINT with DEFAULT nextval
    c.execute("CREATE SEQUENCE IF NOT EXISTS posts_id_seq START 1")
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id BIGINT PRIMARY KEY DEFAULT nextval('posts_id_seq'),
            source TEXT,
            author TEXT,
            content TEXT,
            url TEXT,
            created_at TEXT,
            sentiment_score REAL,
            sentiment_label TEXT,
            language TEXT DEFAULT 'unknown',
            country TEXT,
            relevance_score REAL DEFAULT 0.0
        )
    ''')
    
    # Add relevance_score column if it doesn't exist (migration for existing databases)
    try:
        c.execute("ALTER TABLE posts ADD COLUMN relevance_score REAL DEFAULT 0.0")
    except Exception:
        pass  # Column already exists
    
    # Add indexes for faster queries (Performance optimization)
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_source 
        ON posts(source)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_sentiment 
        ON posts(sentiment_label)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_created 
        ON posts(created_at DESC)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_language 
        ON posts(language)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_source_date 
        ON posts(source, created_at DESC)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_url 
        ON posts(url)
    ''')
    
    # Saved search queries / keywords
    c.execute("CREATE SEQUENCE IF NOT EXISTS saved_queries_id_seq START 1")
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_queries (
            id BIGINT PRIMARY KEY DEFAULT nextval('saved_queries_id_seq'),
            keyword TEXT UNIQUE,
            created_at TEXT
        )
    ''')
    
    # Scraping logs table for persistent logging
    c.execute("CREATE SEQUENCE IF NOT EXISTS scraping_logs_id_seq START 1")
    c.execute('''
        CREATE TABLE IF NOT EXISTS scraping_logs (
            id BIGINT PRIMARY KEY DEFAULT nextval('scraping_logs_id_seq'),
            timestamp TEXT NOT NULL,
            source TEXT,
            level TEXT,
            message TEXT,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Index for faster queries on logs
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
        ON scraping_logs(timestamp DESC)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_logs_source 
        ON scraping_logs(source)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_logs_level 
        ON scraping_logs(level)
    ''')
    
    # Base keywords table (editable base keywords)
    c.execute("CREATE SEQUENCE IF NOT EXISTS base_keywords_id_seq START 1")
    c.execute('''
        CREATE TABLE IF NOT EXISTS base_keywords (
            id BIGINT PRIMARY KEY DEFAULT nextval('base_keywords_id_seq'),
            category TEXT NOT NULL,
            keyword TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, keyword)
        )
    ''')
    
    # Initialize base keywords if table is empty
    c.execute("SELECT COUNT(*) FROM base_keywords")
    count = c.fetchone()[0]
    if count == 0:
        from .config.keywords_base import (
            DEFAULT_BRAND_KEYWORDS, DEFAULT_PRODUCT_KEYWORDS,
            DEFAULT_PROBLEM_KEYWORDS, DEFAULT_LEADERSHIP_KEYWORDS
        )
        
        # Insert default keywords
        for keyword in DEFAULT_BRAND_KEYWORDS:
            try:
                c.execute(
                    "INSERT INTO base_keywords (category, keyword) VALUES (?, ?)",
                    ('brands', keyword)
                )
            except Exception:
                pass  # Ignore duplicates
        
        for keyword in DEFAULT_PRODUCT_KEYWORDS:
            try:
                c.execute(
                    "INSERT INTO base_keywords (category, keyword) VALUES (?, ?)",
                    ('products', keyword)
                )
            except Exception:
                pass
        
        for keyword in DEFAULT_PROBLEM_KEYWORDS:
            try:
                c.execute(
                    "INSERT INTO base_keywords (category, keyword) VALUES (?, ?)",
                    ('problems', keyword)
                )
            except Exception:
                pass
        
        for keyword in DEFAULT_LEADERSHIP_KEYWORDS:
            try:
                c.execute(
                    "INSERT INTO base_keywords (category, keyword) VALUES (?, ?)",
                    ('leadership', keyword)
                )
            except Exception:
                pass
    
    conn.commit()
    conn.close()


def insert_post(post: dict):
    """Insert post with validation and proper error handling."""
    # SECURITY: Validate post data before insertion
    if not isinstance(post, dict):
        raise ValueError("post must be a dictionary")
    
    # SECURITY: Validate required fields exist
    required_fields = ['source', 'content']
    for field in required_fields:
        if field not in post:
            raise ValueError(f"Missing required field: {field}")
    
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        # SECURITY: Use parameterized query to prevent SQL injection
        # DuckDB: use nextval for auto-increment
        c.execute(
            '''INSERT INTO posts (id, source, author, content, url, created_at, sentiment_score, sentiment_label, language, relevance_score)
               VALUES (nextval('posts_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                str(post.get('source'))[:100],  # Limit length
                str(post.get('author', 'unknown'))[:100],
                str(post.get('content', ''))[:10000],  # Limit content length
                str(post.get('url', ''))[:500],
                post.get('created_at'),
                float(post.get('sentiment_score', 0.0)) if post.get('sentiment_score') else 0.0,
                str(post.get('sentiment_label', 'neutral'))[:20],
                str(post.get('language', 'unknown'))[:20],
                float(post.get('relevance_score', 0.0)) if post.get('relevance_score') is not None else 0.0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_posts(limit: int = 100, offset: int = 0, language: str = None):
    """Fetch posts with parameterized queries to prevent SQL injection."""
    # SECURITY: Validate input types to prevent injection
    if not isinstance(limit, int) or not isinstance(offset, int):
        raise ValueError("limit and offset must be integers")
    if language and not isinstance(language, str):
        raise ValueError("language must be a string")
    
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        # SECURITY: Always use parameterized queries
        if language and language != 'all':
            c.execute(
                'SELECT id, source, author, content, url, created_at, sentiment_score, sentiment_label, language, relevance_score '
                'FROM posts WHERE language = ? ORDER BY id DESC LIMIT ? OFFSET ?',
                (language, limit, offset)
            )
        else:
            c.execute(
                'SELECT id, source, author, content, url, created_at, sentiment_score, sentiment_label, language, relevance_score '
                'FROM posts ORDER BY id DESC LIMIT ? OFFSET ?',
                (limit, offset)
            )
        
        rows = c.fetchall()
    finally:
        conn.close()
    
    keys = ['id', 'source', 'author', 'content', 'url', 'created_at', 'sentiment_score', 'sentiment_label', 'language', 'relevance_score']
    return [dict(zip(keys, row)) for row in rows]


def create_job_record(job_id: str):
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    
    # ensure jobs table
    c.execute('''
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
    
    # insert job - use ON CONFLICT for DuckDB
    c.execute('''
        INSERT INTO jobs (job_id, status, progress_total, progress_completed, results, errors, cancelled, error, created_at, updated_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (job_id) DO UPDATE SET
            status = EXCLUDED.status,
            progress_total = EXCLUDED.progress_total,
            progress_completed = EXCLUDED.progress_completed,
            results = EXCLUDED.results,
            errors = EXCLUDED.errors,
            cancelled = EXCLUDED.cancelled,
            error = EXCLUDED.error,
            updated_at = EXCLUDED.updated_at
    ''', (job_id, 'pending', 0, 0, json.dumps([]), json.dumps([]), 0, None, now, now))
    
    conn.commit()
    conn.close()


def update_job_progress(job_id: str, total: int, completed: int):
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute('UPDATE jobs SET progress_total = ?, progress_completed = ?, updated_at = ? WHERE job_id = ?', (total, completed, now, job_id))
    conn.commit()
    conn.close()


def append_job_result(job_id: str, result: dict):
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT results FROM jobs WHERE job_id = ?', (job_id,))
    row = c.fetchone()
    results = json.loads(row[0]) if row and row[0] else []
    results.append(result)
    now = datetime.datetime.utcnow().isoformat()
    c.execute('UPDATE jobs SET results = ?, updated_at = ? WHERE job_id = ?', (json.dumps(results), now, job_id))
    conn.commit()
    conn.close()


def append_job_error(job_id: str, error_msg: str):
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT errors FROM jobs WHERE job_id = ?', (job_id,))
    row = c.fetchone()
    errors = json.loads(row[0]) if row and row[0] else []
    errors.append(error_msg)
    now = datetime.datetime.utcnow().isoformat()
    c.execute('UPDATE jobs SET errors = ?, updated_at = ? WHERE job_id = ?', (json.dumps(errors), now, job_id))
    conn.commit()
    conn.close()


def finalize_job(job_id: str, status: str, error: str = None):
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute('UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE job_id = ?', (status, error, now, job_id))
    conn.commit()
    conn.close()


def get_job_record(job_id: str):
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT job_id, status, progress_total, progress_completed, results, errors, cancelled, error, created_at, updated_at FROM jobs WHERE job_id = ?', (job_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0],
        'status': row[1],
        'progress': {'total': row[2], 'completed': row[3]},
        'results': json.loads(row[4] or '[]'),
        'errors': json.loads(row[5] or '[]'),
        'cancelled': bool(row[6]),
        'error': row[7],
        'created_at': row[8],
        'updated_at': row[9],
    }


def save_queries(keywords: list):
    """Replace saved queries with provided list (order preserved)."""
    # SECURITY: Validate input
    if not isinstance(keywords, list):
        raise ValueError("keywords must be a list")
    if len(keywords) > 100:
        raise ValueError("Too many keywords (max 100)")
    
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        # clear existing
        c.execute('DELETE FROM saved_queries')
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        
        for kw in keywords:
            # SECURITY: Validate and sanitize each keyword
            if not isinstance(kw, str):
                continue
            kw = str(kw).strip()[:100]  # Limit length
            if not kw:
                continue
            # SECURITY: Use parameterized query with sequence for ID
            c.execute('''
                INSERT INTO saved_queries (id, keyword, created_at) VALUES (nextval('saved_queries_id_seq'), ?, ?)
                ON CONFLICT (keyword) DO NOTHING
            ''', (kw, now))
        
        conn.commit()
    finally:
        conn.close()


def get_base_keywords():
    """Récupère les keywords de base par catégorie depuis la DB."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('SELECT category, keyword FROM base_keywords ORDER BY category, id')
        rows = c.fetchall()
        
        result = {
            'brands': [],
            'products': [],
            'problems': [],
            'leadership': []
        }
        
        for category, keyword in rows:
            if category in result:
                result[category].append(keyword)
        
        return result
    finally:
        conn.close()


def save_base_keywords(keywords_by_category: dict):
    """Sauvegarde les keywords de base dans la DB."""
    if not isinstance(keywords_by_category, dict):
        raise ValueError("keywords_by_category must be a dictionary")
    
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        # Vider la table
        c.execute('DELETE FROM base_keywords')
        
        # Insérer les nouveaux keywords
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        
        for category, keywords in keywords_by_category.items():
            if category not in ['brands', 'products', 'problems', 'leadership']:
                continue
            
            if not isinstance(keywords, list):
                continue
            
            for keyword in keywords:
                if not isinstance(keyword, str):
                    continue
                keyword = keyword.strip()[:100]  # Limit length
                if not keyword:
                    continue
                
                try:
                    c.execute(
                        "INSERT INTO base_keywords (category, keyword, created_at) VALUES (?, ?, ?)",
                        (category, keyword, now)
                    )
                except Exception:
                    pass  # Ignore duplicates
        
        conn.commit()
    finally:
        conn.close()


def get_saved_queries():
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT keyword FROM saved_queries ORDER BY id ASC')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def delete_duplicate_posts():
    """
    Delete duplicate posts from the database.
    Duplicates are identified by same URL or same content+author+source.
    Keeps the oldest post (lowest ID) and deletes the rest.
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        # First, delete duplicates by URL (keep the one with lowest ID)
        c.execute('''
            DELETE FROM posts
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM posts
                WHERE url IS NOT NULL AND url != ''
                GROUP BY url
            )
            AND url IS NOT NULL AND url != ''
        ''')
        deleted_by_url = c.rowcount
        
        # Then, delete duplicates by content+author+source (keep the one with lowest ID)
        c.execute('''
            DELETE FROM posts
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM posts
                GROUP BY content, author, source
            )
        ''')
        deleted_by_content = c.rowcount
        
        conn.commit()
        total_deleted = deleted_by_url + deleted_by_content
    finally:
        conn.close()
    
    return total_deleted


def delete_non_ovh_posts():
    """
    Delete all posts from the database that do NOT mention OVH or its brands.
    Keeps posts containing: ovh, ovhcloud, ovh cloud, kimsufi, soyoustart
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        # Check if posts table has country column
        c.execute("DESCRIBE posts")
        columns = [row[0] for row in c.fetchall()]
        has_country = 'country' in columns
        
        # Delete posts that don't contain OVH-related keywords
        # Case-insensitive search for: ovh, ovhcloud, ovh cloud, kimsufi, soyoustart
        query = '''
            DELETE FROM posts
            WHERE LOWER(content) NOT LIKE '%ovh%'
            AND LOWER(content) NOT LIKE '%ovhcloud%'
            AND LOWER(content) NOT LIKE '%ovh cloud%'
            AND LOWER(content) NOT LIKE '%kimsufi%'
            AND LOWER(content) NOT LIKE '%soyoustart%'
            AND LOWER(author) NOT LIKE '%ovh%'
            AND (url IS NULL OR (LOWER(url) NOT LIKE '%ovh%' AND LOWER(url) NOT LIKE '%kimsufi%' AND LOWER(url) NOT LIKE '%soyoustart%'))
        '''
        
        c.execute(query)
        deleted_count = c.rowcount
        conn.commit()
    finally:
        conn.close()
    
    return deleted_count


def delete_sample_posts():
    """
    Delete sample/fake posts used for testing.
    Identifies sample posts by checking for test keywords in content or author.
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            DELETE FROM posts
            WHERE LOWER(content) LIKE '%test%'
            OR LOWER(content) LIKE '%sample%'
            OR LOWER(content) LIKE '%example%'
            OR LOWER(author) LIKE '%test%'
            OR LOWER(author) LIKE '%sample%'
            OR source = 'test'
        ''')
        deleted_count = c.rowcount
        conn.commit()
    finally:
        conn.close()
    
    return deleted_count


def delete_hackernews_posts():
    """
    Delete all posts from Hacker News source.
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM posts WHERE source = ?', ('hackernews',))
        deleted_count = c.rowcount
        conn.commit()
    finally:
        conn.close()
    
    return deleted_count


# ===== SCRAPING LOGS FUNCTIONS =====

def add_scraping_log(source: str, level: str, message: str, details: str = None):
    """Add a log entry to the scraping_logs table.
    
    Args:
        source: Source of the log (e.g., 'X/Twitter', 'GitHub', 'Reddit')
        level: Log level ('info', 'warning', 'error', 'success')
        message: Log message
        details: Optional additional details (JSON string or dict)
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        timestamp = datetime.datetime.now().isoformat()
        
        # Convert details to JSON string if it's a dict
        if details is not None and isinstance(details, dict):
            details = json.dumps(details)
        elif details is None:
            details = None
        else:
            details = str(details)
        
        c.execute(
            '''INSERT INTO scraping_logs (id, timestamp, source, level, message, details)
               VALUES (nextval('scraping_logs_id_seq'), ?, ?, ?, ?, ?)''',
            (timestamp, source, level, message, details)
        )
        conn.commit()
    finally:
        conn.close()


def get_scraping_logs(source: str = None, level: str = None, limit: int = 1000, offset: int = 0):
    """Get scraping logs from the database.
    
    Args:
        source: Filter by source (optional)
        level: Filter by level (optional)
        limit: Maximum number of logs to return
        offset: Offset for pagination
    
    Returns:
        List of log dictionaries
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        query = "SELECT id, timestamp, source, level, message, details FROM scraping_logs WHERE 1=1"
        params = []
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        if level:
            query += " AND level = ?"
            params.append(level)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        c.execute(query, params)
        rows = c.fetchall()
        
        logs = []
        for row in rows:
            log = {
                'id': row[0],
                'timestamp': row[1],
                'source': row[2],
                'level': row[3],
                'message': row[4],
                'details': row[5]
            }
            # Try to parse details as JSON if it exists
            if log['details']:
                try:
                    log['details'] = json.loads(log['details'])
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string if not valid JSON
            logs.append(log)
        
        return logs
    finally:
        conn.close()


def clear_scraping_logs(source: str = None, older_than_days: int = None):
    """Clear scraping logs from the database.
    
    Args:
        source: Clear logs for specific source only (optional)
        older_than_days: Clear logs older than N days (optional)
    
    Returns:
        Number of logs deleted
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        if older_than_days:
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=older_than_days)).isoformat()
            if source:
                c.execute('DELETE FROM scraping_logs WHERE source = ? AND timestamp < ?', (source, cutoff_date))
            else:
                c.execute('DELETE FROM scraping_logs WHERE timestamp < ?', (cutoff_date,))
        elif source:
            c.execute('DELETE FROM scraping_logs WHERE source = ?', (source,))
        else:
            c.execute('DELETE FROM scraping_logs')
        
        deleted_count = c.rowcount
        conn.commit()
        return deleted_count
    finally:
        conn.close()
