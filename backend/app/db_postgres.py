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
        logger.error("psycopg2 not installed. PostgreSQL is required.")
        raise ImportError("psycopg2-binary is required. Install with: pip install psycopg2-binary")
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
    """Insert a new post into PostgreSQL (low-level function)."""
    with get_pg_cursor() as cur:
        cur.execute("""
            INSERT INTO posts (source, author, content, url, created_at, 
                             sentiment_score, sentiment_label, language, country, 
                             relevance_score, product)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
        """, (source, author, content, url, created_at, sentiment_score,
              sentiment_label, language, country, relevance_score, product))
        result = cur.fetchone()
        return result['id'] if result else None


def _normalize_content_for_comparison(content: str) -> str:
    """
    Normalize content for duplicate comparison.
    Removes HTML tags, extra whitespace, and normalizes case.
    """
    if not content:
        return ""
    
    import re
    # Remove HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    # Normalize whitespace
    content = ' '.join(content.split())
    # Lowercase
    content = content.lower()
    # Remove punctuation for better matching
    content = re.sub(r'[^\w\s]', '', content)
    # Limit length for comparison
    return content[:500]


def detect_product_label(content: str, language: str = 'unknown') -> Optional[str]:
    """
    Détecte le produit OVH mentionné dans le contenu d'un post.
    Basé sur la logique de détection du frontend.
    
    Args:
        content: Contenu du post
        language: Langue du post (pour filtrage)
    
    Returns:
        Nom du produit détecté ou None
    """
    if not content:
        return None
    
    import re
    content_lower = content.lower()
    
    # Product patterns with priority order (more specific first)
    product_patterns = [
        # Web & Hosting
        {'key': 'domain', 'pattern': re.compile(r'\b(domain|domaine|dns|zone|registrar|nameserver|\.ovh|\.com|\.net|\.org)\b', re.I), 'label': 'Domain'},
        {'key': 'wordpress', 'pattern': re.compile(r'\b(wordpress|wp\s*host|wp\s*config)\b', re.I), 'label': 'WordPress'},
        {'key': 'email', 'pattern': re.compile(r'\b(email|exchange|mail|mx\s*record|zimbra|smtp|imap|pop3|mailbox)\b', re.I), 'label': 'Email'},
        {'key': 'web-hosting', 'pattern': re.compile(r'\b(web\s*host|hosting|hébergement|mutualisé|shared\s*host|web\s*server)\b', re.I), 'label': 'Hosting'},
        
        # Cloud & Servers
        {'key': 'vps', 'pattern': re.compile(r'\b(vps|virtual\s*private\s*server|kimsufi)\b', re.I), 'label': 'VPS'},
        {'key': 'dedicated', 'pattern': re.compile(r'\b(dedicated|dédié|bare\s*metal|server\s*dedicated|serveur\s*dédié)\b', re.I), 'label': 'Dedicated Server'},
        {'key': 'public-cloud', 'pattern': re.compile(r'\b(public\s*cloud|openstack|instance|compute|ovhcloud|ovh\s*cloud)\b', re.I), 'label': 'Public Cloud'},
        {'key': 'private-cloud', 'pattern': re.compile(r'\b(private\s*cloud|vmware|vsphere)\b', re.I), 'label': 'Private Cloud'},
        {'key': 'kubernetes', 'pattern': re.compile(r'\b(kubernetes|k8s|managed\s*k8s|container|pod|deployment)\b', re.I), 'label': 'Managed Kubernetes'},
        
        # Storage & Backup
        {'key': 'object-storage', 'pattern': re.compile(r'\b(object\s*storage|swift|s3|storage|cloud\s*storage|object\s*store)\b', re.I), 'label': 'Storage'},
        {'key': 'backup', 'pattern': re.compile(r'\b(backup|veeam|archive|snapshot|restore)\b', re.I), 'label': 'Backup'},
        
        # Network & CDN
        {'key': 'cdn', 'pattern': re.compile(r'\b(cdn|content\s*delivery|cache)\b', re.I), 'label': 'CDN'},
        {'key': 'load-balancer', 'pattern': re.compile(r'\b(load\s*balancer|iplb|lb|balancing)\b', re.I), 'label': 'Load Balancer'},
        {'key': 'ddos', 'pattern': re.compile(r'\b(ddos|anti-ddos|protection|mitigation)\b', re.I), 'label': 'DDoS Protection'},
        {'key': 'network', 'pattern': re.compile(r'\b(network|vrack|vlan|ip\s*address|subnet)\b', re.I), 'label': 'Network'},
        
        # Support & Billing (lower priority)
        {'key': 'billing', 'pattern': re.compile(r'\b(billing|facture|invoice|payment|paiement|refund|rembours|subscription)\b', re.I), 'label': 'Billing'},
        {'key': 'manager', 'pattern': re.compile(r'\b(manager|control\s*panel|espace\s*client|ovh\s*manager|panel)\b', re.I), 'label': 'Manager'},
        {'key': 'api', 'pattern': re.compile(r'\b(api|sdk|integration|rest\s*api|webhook)\b', re.I), 'label': 'API'},
        {'key': 'support', 'pattern': re.compile(r'\b(support|ticket|assistance|help|service\s*client|customer\s*service)\b', re.I), 'label': 'Support'},
    ]
    
    # Check patterns in priority order
    for pattern_info in product_patterns:
        if pattern_info['pattern'].search(content_lower):
            return pattern_info['label']
    
    return None


def insert_post(post: Dict[str, Any]) -> Optional[int]:
    """
    Insert post with validation and proper error handling.
    Compatible with DuckDB interface (takes dict).
    
    Returns:
        int: ID of the inserted post, or None if insertion failed (duplicate)
    """
    
    # SECURITY: Validate post data before insertion
    if not isinstance(post, dict):
        raise ValueError("post must be a dictionary")
    
    # SECURITY: Validate required fields exist
    required_fields = ['source', 'content']
    for field in required_fields:
        if field not in post:
            raise ValueError(f"Missing required field: {field}")
    
    try:
        # Check for duplicate URL first (most reliable)
        url = str(post.get('url', ''))[:500]
        if url:
            with get_pg_cursor() as cur:
                cur.execute("SELECT id FROM posts WHERE url = %s LIMIT 1", (url,))
                existing = cur.fetchone()
                if existing:
                    logger.debug(f"Duplicate detected by URL: {url[:100]}")
                    return None  # Duplicate detected
        
        # Check for duplicate by normalized content + author + source
        content = str(post.get('content', ''))[:10000]
        author = str(post.get('author', 'unknown'))[:100]
        source = str(post.get('source'))[:100]
        
        # Normalize content for comparison
        normalized_content = _normalize_content_for_comparison(content)
        
        # Improved duplicate detection: check normalized content more thoroughly
        if normalized_content and len(normalized_content) > 30:
            normalized_key = normalized_content[:300]
            
            with get_pg_cursor() as cur:
                # First check: same normalized content + same author + same source (strictest)
                cur.execute("""
                    SELECT id, content FROM posts 
                    WHERE source = %s 
                    AND author = %s
                    AND LENGTH(content) > 30
                    LIMIT 50
                """, (source, author))
                existing_posts = cur.fetchall()
                
                for existing_id, existing_content in existing_posts:
                    existing_normalized = _normalize_content_for_comparison(str(existing_content))
                    if len(existing_normalized) > 30 and existing_normalized[:300] == normalized_key:
                        logger.debug(f"Duplicate detected by normalized content+author+source: {normalized_key[:50]}")
                        return None  # Duplicate detected
                
                # Second check: same normalized content + same source (catches author variations)
                if len(normalized_content) > 100:
                    normalized_key_long = normalized_content[:300]
                    cur.execute("""
                        SELECT id, content FROM posts 
                        WHERE source = %s
                        AND LENGTH(content) > 100
                        LIMIT 100
                    """, (source,))
                    existing_posts = cur.fetchall()
                    
                    for existing_id, existing_content in existing_posts:
                        existing_normalized = _normalize_content_for_comparison(str(existing_content))
                        if len(existing_normalized) > 100:
                            if existing_normalized[:300] == normalized_key_long:
                                # Additional check: if content is very similar (90% match on first 500 chars)
                                if len(existing_normalized) >= 500 and len(normalized_content) >= 500:
                                    similarity = sum(1 for a, b in zip(existing_normalized[:500], normalized_content[:500]) if a == b) / 500.0
                                    if similarity > 0.90:
                                        logger.debug(f"Duplicate detected by normalized content similarity ({similarity:.2%}): {normalized_key[:50]}")
                                        return None
                                elif existing_normalized[:300] == normalized_key_long:
                                    logger.debug(f"Duplicate detected by normalized content hash: {normalized_key[:100]}")
                                    return None  # Duplicate detected
        
        # Detect product label if not provided
        product_label = post.get('product')
        if not product_label:
            product_label = detect_product_label(str(post.get('content', '')), str(post.get('language', 'unknown')))
        
        # Insert the post
        post_id = pg_insert_post(
            source=str(post.get('source'))[:100],
            author=str(post.get('author', 'unknown'))[:100],
            content=str(post.get('content', ''))[:10000],
            url=url,
            created_at=post.get('created_at'),
            sentiment_score=float(post.get('sentiment_score', 0.0)) if post.get('sentiment_score') else 0.0,
            sentiment_label=str(post.get('sentiment_label', 'neutral'))[:20],
            language=str(post.get('language', 'unknown'))[:20],
            country=post.get('country'),
            relevance_score=float(post.get('relevance_score', 0.0)) if post.get('relevance_score') is not None else 0.0,
            product=product_label
        )
        
        # Trigger notification check in background (non-blocking)
        if post_id:
            try:
                from ..notifications import notification_manager
                notification_manager.check_and_send_notifications(post_id)
            except Exception as e:
                logger.warning(f"Failed to trigger notification check for post {post_id}: {e}")
        
        return post_id
        
    except Exception as e:
        logger.error(f"Error inserting post: {e}", exc_info=True)
        raise


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


# ============================================
# init_db - Create PostgreSQL schema
# ============================================

def init_db() -> None:
    """Initialize PostgreSQL database schema."""
    logger.info("Initializing PostgreSQL database schema...")
    
    with get_pg_cursor(dict_cursor=False) as cur:
        # Posts table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                source TEXT,
                author TEXT,
                content TEXT,
                url TEXT UNIQUE,
                created_at TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                language TEXT DEFAULT 'unknown',
                country TEXT,
                relevance_score REAL DEFAULT 0.0,
                is_answered INTEGER DEFAULT 0,
                answered_at TEXT,
                answered_by TEXT,
                answer_detection_method TEXT,
                product TEXT
            )
        ''')
        
        # Indexes for posts
        cur.execute('CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_posts_sentiment ON posts(sentiment_label)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_posts_language ON posts(language)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_posts_product ON posts(product)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_posts_is_answered ON posts(is_answered)')
        
        # Saved queries table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS saved_queries (
                id SERIAL PRIMARY KEY,
                keyword TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Scraping logs table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS scraping_logs (
                id SERIAL PRIMARY KEY,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                level TEXT,
                message TEXT,
                posts_scraped INTEGER DEFAULT 0,
                posts_inserted INTEGER DEFAULT 0,
                error TEXT
            )
        ''')
        
        # Jobs table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                payload JSONB,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                progress INTEGER DEFAULT 0,
                result JSONB,
                error TEXT,
                worker_id TEXT
            )
        ''')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)')
        
        # Job results table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS job_results (
                id SERIAL PRIMARY KEY,
                job_id TEXT,
                job_type TEXT,
                status TEXT,
                result JSONB,
                duration_seconds REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Base keywords table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS base_keywords (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,
                keyword TEXT NOT NULL,
                UNIQUE(category, keyword)
            )
        ''')
        
        # Email notifications table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS email_notifications (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                name TEXT,
                trigger_conditions JSONB,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Improvements table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS improvements (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'proposed',
                priority TEXT DEFAULT 'medium',
                source TEXT,
                source_post_ids TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                jira_key TEXT,
                jira_url TEXT,
                votes INTEGER DEFAULT 0
            )
        ''')
        
        # Users table for auth
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
    logger.info("PostgreSQL database schema initialized successfully")


# ============================================
# Compatibility Aliases (match db.py interface)
# ============================================

# Connection
def get_db_connection():
    """Compatibility: returns (connection, True) for PostgreSQL."""
    pool = _get_pool()
    conn = pool.getconn()
    return conn, False  # False = not DuckDB

# Posts
# insert_post is already defined above with full duplicate detection logic
get_posts = pg_get_all_posts
get_post_by_id = pg_get_post_by_id
delete_post = pg_delete_post
url_exists = pg_url_exists
delete_duplicate_posts = pg_delete_duplicate_posts

# Stats
get_sentiment_stats = pg_get_sentiment_stats
get_source_stats = pg_get_source_stats
get_language_stats = pg_get_language_stats
get_timeline_stats = pg_get_timeline_stats

# Saved queries
get_saved_queries = pg_get_saved_queries
save_queries = pg_add_saved_query
delete_saved_query = pg_delete_saved_query

# Scraping logs
add_scraping_log = pg_add_scraping_log
get_scraping_logs = pg_get_scraping_logs

# Jobs
create_job_record = pg_enqueue_job
def get_job_record(job_id: str) -> Optional[Dict]:
    """Get a job by ID."""
    with get_pg_cursor() as cur:
        cur.execute("SELECT * FROM job_queue WHERE id = %s", (job_id,))
        row = cur.fetchone()
        return dict(row) if row else None

update_job_progress = pg_update_job_status
get_all_jobs = pg_get_pending_jobs

# Base keywords  
get_base_keywords = pg_get_base_keywords
add_base_keyword = pg_add_base_keyword
delete_base_keyword = pg_delete_base_keyword

# Health
health_check = pg_health_check