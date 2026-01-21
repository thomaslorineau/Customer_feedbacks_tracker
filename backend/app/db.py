from pathlib import Path
import json
import datetime
from typing import Optional, Tuple, List, Dict, Any, Union, Generator, Iterator
import logging
from contextlib import contextmanager
from threading import Lock

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

# Simple connection pool for DuckDB
_connection_pool: List[duckdb.DuckDBPyConnection] = []
_pool_lock = Lock()
_MAX_POOL_SIZE = 5


def get_db_connection() -> Tuple[Any, bool]:
    """
    Get DuckDB database connection.
    Returns: (connection, is_duckdb) where is_duckdb is always True
    
    Note: For better resource management, prefer using get_db() context manager.
    """
    if not DUCKDB_AVAILABLE:
        raise RuntimeError("DuckDB is not available. Please install it: pip install duckdb")
    
    try:
        # Try to get connection from pool
        with _pool_lock:
            if _connection_pool:
                conn = _connection_pool.pop()
                # Verify connection is still valid
                try:
                    conn.execute("SELECT 1")
                    return conn, True
                except Exception:
                    # Connection is invalid, create new one
                    pass
        
        # Create new connection
        conn = duckdb.connect(str(DB_FILE))
        return conn, True
    except Exception as e:
        error_str = str(e)
        # Check if it's a serialization/corruption error
        if "Serialization" in error_str or "corrupt" in error_str.lower() or "Failed to deserialize" in error_str:
            logger.warning(f"DuckDB corruption detected: {e}")
            logger.info("Attempting automatic database repair...")
            try:
                # Try to repair the database
                _repair_database()
                # Retry connection after repair
                conn = duckdb.connect(str(DB_FILE))
                logger.info("Database repaired successfully, connection restored")
                return conn, True
            except Exception as repair_error:
                logger.error(f"Database repair failed: {repair_error}")
                raise RuntimeError(f"Failed to connect to DuckDB database at {DB_FILE} and repair failed: {repair_error}")
        else:
            logger.error(f"DuckDB connection failed: {e}")
            raise RuntimeError(f"Failed to connect to DuckDB database at {DB_FILE}: {e}")


def _return_connection_to_pool(conn: Any) -> None:
    """Return a connection to the pool if there's space."""
    with _pool_lock:
        if len(_connection_pool) < _MAX_POOL_SIZE:
            try:
                # Verify connection is still valid
                conn.execute("SELECT 1")
                _connection_pool.append(conn)
            except Exception:
                # Connection is invalid, close it
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            # Pool is full, close the connection
            try:
                conn.close()
            except Exception:
                pass


@contextmanager
def get_db() -> Generator[Any, None, None]:
    """
    Context manager for database connections with automatic commit/rollback.
    
    Usage:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts")
            # Connection is automatically committed on success or rolled back on error
    """
    conn, _ = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _return_connection_to_pool(conn)


def _repair_database() -> None:
    """Internal function to repair corrupted DuckDB database."""
    import shutil
    from datetime import datetime
    
    db_path = Path(DB_FILE)
    backup_path = db_path.with_suffix('.duckdb.backup')
    
    logger.info(f"🔍 Repairing database: {DB_FILE}")
    
    # Create backup before repair
    if db_path.exists():
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}.duckdb"
            shutil.copy2(db_path, backup_path)
            logger.info(f"📦 Backup created: {backup_path}")
        except Exception as e:
            logger.warning(f"⚠️  Could not create backup: {e}")
    
    # Try to restore from automatic backups
    backups_dir = db_path.parent / "backups"
    if backups_dir.exists():
        # Determine prefix based on filename
        if "staging" in str(db_path):
            prefix = "staging_"
        else:
            prefix = "production_"
        
        # Find latest backup
        try:
            backup_files = sorted(
                backups_dir.glob(f"{prefix}*.duckdb"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if backup_files:
                latest_backup = backup_files[0]
                logger.info(f"📦 Found backup: {latest_backup.name}")
                try:
                    # Verify backup has data
                    conn_backup = duckdb.connect(str(latest_backup), read_only=True)
                    c_backup = conn_backup.cursor()
                    c_backup.execute("SELECT COUNT(*) FROM posts")
                    backup_post_count = c_backup.fetchone()[0]
                    conn_backup.close()
                    
                    if backup_post_count > 0:
                        logger.info(f"✅ Backup contains {backup_post_count} posts")
                        logger.info("🔄 Restoring from backup...")
                        shutil.copy2(latest_backup, db_path)
                        logger.info(f"✅ Database restored from: {latest_backup.name}")
                        return
                except Exception as backup_error:
                    logger.warning(f"⚠️  Could not restore from backup: {backup_error}")
        except Exception as e:
            logger.warning(f"⚠️  Error searching backups: {e}")
    
    # If no backup or restore failed, delete corrupted file and recreate
    try:
        if db_path.exists():
            logger.info(f"🗑️  Removing corrupted file...")
            db_path.unlink()
        
        logger.info(f"✨ Creating new database...")
        # The init_db() function will be called after this to recreate tables
    except Exception as e:
        logger.error(f"❌ Error during repair: {e}")
        raise


def init_db() -> None:
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
    
    # Email notifications tables
    c.execute("CREATE SEQUENCE IF NOT EXISTS email_notifications_id_seq START 1")
    c.execute('''
        CREATE TABLE IF NOT EXISTS email_notifications (
            id BIGINT PRIMARY KEY DEFAULT nextval('email_notifications_id_seq'),
            trigger_id BIGINT,
            post_ids TEXT NOT NULL,  -- JSON array des IDs de posts inclus dans l'email
            recipient_emails TEXT NOT NULL,  -- JSON array des emails destinataires
            sent_at TEXT,
            status TEXT,  -- 'sent', 'failed', 'pending'
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute("CREATE SEQUENCE IF NOT EXISTS notification_triggers_id_seq START 1")
    c.execute('''
        CREATE TABLE IF NOT EXISTS notification_triggers (
            id BIGINT PRIMARY KEY DEFAULT nextval('notification_triggers_id_seq'),
            name TEXT NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            conditions TEXT NOT NULL,  -- JSON: {"sentiment": "negative", "relevance_score_min": 0.5, "sources": ["Trustpilot", "Reddit"]}
            emails TEXT NOT NULL,  -- JSON array: ["email1@example.com", "email2@example.com"]
            cooldown_minutes INTEGER DEFAULT 60,  -- Éviter spam si plusieurs posts similaires
            max_posts_per_email INTEGER DEFAULT 10,  -- Nombre max de posts par email
            last_notification_sent_at TEXT,  -- Timestamp de la dernière notification envoyée (pour cooldown)
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Index for email notifications
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_email_notifications_trigger 
        ON email_notifications(trigger_id)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_email_notifications_created 
        ON email_notifications(created_at DESC)
    ''')
    
    # Initialize auth tables
    init_auth_tables(conn, c)
    
    # Create default admin user if no users exist
    # Note: User creation is deferred to avoid bcrypt issues at startup
    # Users should be created via /api/auth/register endpoint
    
    conn.commit()
    conn.close()


def init_auth_tables(conn: Any, c: Any) -> None:
    """Initialize authentication tables (users and sessions)."""
    # Users table
    c.execute("CREATE SEQUENCE IF NOT EXISTS users_id_seq START 1")
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY DEFAULT nextval('users_id_seq'),
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sessions table (for refresh token tracking, optional)
    c.execute("CREATE SEQUENCE IF NOT EXISTS sessions_id_seq START 1")
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id BIGINT PRIMARY KEY DEFAULT nextval('sessions_id_seq'),
            user_id BIGINT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Note: DuckDB doesn't support FOREIGN KEY constraints in the same way as SQLite
    # We'll handle referential integrity in application code
    
    # Indexes for auth tables
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_users_username 
        ON users(username)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
        ON sessions(user_id)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_sessions_refresh_token 
        ON sessions(refresh_token)
    ''')


def insert_post(post: Dict[str, Any]) -> Optional[int]:
    """Insert post with validation and proper error handling.
    
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
    
    with get_db() as conn:
        c = conn.cursor()
        
        try:
            # Check for duplicate URL first (most reliable)
            url = str(post.get('url', ''))[:500]
            if url:
                c.execute("SELECT id FROM posts WHERE url = ?", (url,))
                existing = c.fetchone()
                if existing:
                    logger.debug(f"Duplicate detected by URL: {url[:100]}")
                    return None  # Duplicate detected
            
            # Check for duplicate by normalized content + author + source
            # Normalize content: lowercase, remove extra whitespace, remove punctuation
            content = str(post.get('content', ''))[:10000]
            author = str(post.get('author', 'unknown'))[:100]
            source = str(post.get('source'))[:100]
            
            # Normalize content for comparison (remove HTML, extra spaces, lowercase)
            normalized_content = _normalize_content_for_comparison(content)
            
            # Improved duplicate detection: check normalized content more thoroughly
            if normalized_content and len(normalized_content) > 30:
                # Use longer normalized key for better detection (300 chars instead of 200)
                normalized_key = normalized_content[:300]
                
                # First check: same normalized content + same author + same source (strictest)
                c.execute('''
                    SELECT id, content FROM posts 
                    WHERE source = ? 
                    AND author = ?
                    AND LENGTH(content) > 30
                    LIMIT 50
                ''', (source, author))
                existing_posts = c.fetchall()
                
                for existing_id, existing_content in existing_posts:
                    existing_normalized = _normalize_content_for_comparison(str(existing_content))
                    if len(existing_normalized) > 30 and existing_normalized[:300] == normalized_key:
                        logger.debug(f"Duplicate detected by normalized content+author+source: {normalized_key[:50]}")
                        return None  # Duplicate detected
                
                # Second check: same normalized content + same source (catches author variations)
                # Only check if content is substantial (more than 100 chars)
                if len(normalized_content) > 100:
                    normalized_key_long = normalized_content[:300]
                    c.execute('''
                        SELECT id, content FROM posts 
                        WHERE source = ?
                        AND LENGTH(content) > 100
                        LIMIT 100
                    ''', (source,))
                    existing_posts = c.fetchall()
                    
                    for existing_id, existing_content in existing_posts:
                        existing_normalized = _normalize_content_for_comparison(str(existing_content))
                        if len(existing_normalized) > 100:
                            # Check if normalized content matches (first 300 chars)
                            if existing_normalized[:300] == normalized_key_long:
                                # Additional check: if content is very similar (90% match on first 500 chars)
                                if len(existing_normalized) >= 500 and len(normalized_content) >= 500:
                                    # Calculate similarity on first 500 chars
                                    similarity = sum(1 for a, b in zip(existing_normalized[:500], normalized_content[:500]) if a == b) / 500.0
                                    if similarity > 0.90:
                                        logger.debug(f"Duplicate detected by normalized content similarity ({similarity:.2%}): {normalized_key[:50]}")
                                        return None
                                elif existing_normalized[:300] == normalized_key_long:
                                    logger.debug(f"Duplicate detected by normalized content hash: {normalized_key[:100]}")
                                    return None  # Duplicate detected
            
            # SECURITY: Use parameterized query to prevent SQL injection
            # DuckDB: use nextval for auto-increment and RETURNING clause to get the ID
            c.execute('''
                INSERT INTO posts (id, source, author, content, url, created_at, sentiment_score, sentiment_label, language, relevance_score)
                VALUES (nextval('posts_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            ''', (
                str(post.get('source'))[:100],  # Limit length
                str(post.get('author', 'unknown'))[:100],
                str(post.get('content', ''))[:10000],  # Limit content length
                url,
                post.get('created_at'),
                float(post.get('sentiment_score', 0.0)) if post.get('sentiment_score') else 0.0,
                str(post.get('sentiment_label', 'neutral'))[:20],
                str(post.get('language', 'unknown'))[:20],
                float(post.get('relevance_score', 0.0)) if post.get('relevance_score') is not None else 0.0,
            ))
            result = c.fetchone()
            post_id = result[0] if result else None
            
            # Trigger notification check in background (non-blocking)
            try:
                from ..notifications import notification_manager
                notification_manager.check_and_send_notifications(post_id)
            except Exception as e:
                logger.warning(f"Failed to trigger notification check for post {post_id}: {e}")
                # Don't fail the insertion if notification check fails
            
            return post_id
        except Exception as e:
            logger.error(f"Error inserting post: {e}")
            raise  # Context manager will handle rollback


def get_post_by_id(post_id: int) -> Optional[Dict[str, Any]]:
    """Get a single post by ID."""
    with get_db() as conn:
        c = conn.cursor()
        
        c.execute('''
            SELECT id, source, author, content, url, created_at, 
                   sentiment_score, sentiment_label, language, country, relevance_score
            FROM posts WHERE id = ?
        ''', (post_id,))
        
        row = c.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'source': row[1],
            'author': row[2],
            'content': row[3],
            'url': row[4],
            'created_at': row[5],
            'sentiment_score': row[6],
            'sentiment_label': row[7],
            'language': row[8],
            'country': row[9],
            'relevance_score': row[10] if len(row) > 10 else 0.0
        }


def get_recent_posts(hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent posts from the last N hours."""
    with get_db() as conn:
        c = conn.cursor()
        
        # Calculate cutoff time
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        c.execute('''
            SELECT id, source, author, content, url, created_at, 
                   sentiment_score, sentiment_label, language, country, relevance_score
            FROM posts 
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (cutoff, limit))
        
        posts = []
        for row in c.fetchall():
            posts.append({
                'id': row[0],
                'source': row[1],
                'author': row[2],
                'content': row[3],
                'url': row[4],
                'created_at': row[5],
                'sentiment_score': row[6],
                'sentiment_label': row[7],
                'language': row[8],
                'country': row[9],
                'relevance_score': row[10] if len(row) > 10 else 0.0
            })
        
        return posts


def get_active_notification_triggers() -> List[Dict[str, Any]]:
    """Get all active notification triggers."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, name, enabled, conditions, emails, cooldown_minutes, 
                   max_posts_per_email, last_notification_sent_at, created_at, updated_at
            FROM notification_triggers
            WHERE enabled = TRUE
            ORDER BY created_at DESC
        ''')
        
        triggers = []
        for row in c.fetchall():
            triggers.append({
                'id': row[0],
                'name': row[1],
                'enabled': bool(row[2]),
                'conditions': row[3],
                'emails': row[4],
                'cooldown_minutes': row[5],
                'max_posts_per_email': row[6],
                'last_notification_sent_at': row[7],
                'created_at': row[8],
                'updated_at': row[9]
            })
        
        return triggers
    finally:
        conn.close()


def update_trigger_last_notification_time(trigger_id: int) -> None:
    """Update the last notification sent time for a trigger."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        from datetime import datetime
        now = datetime.now().isoformat()
        
        c.execute('''
            UPDATE notification_triggers
            SET last_notification_sent_at = ?, updated_at = ?
            WHERE id = ?
        ''', (now, now, trigger_id))
        
        conn.commit()
    finally:
        conn.close()


def log_email_notification(
    trigger_id: int,
    post_ids: List[int],
    recipient_emails: List[str],
    status: str,
    error_message: Optional[str] = None
) -> None:
    """Log an email notification attempt."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        import json
        from datetime import datetime
        
        post_ids_json = json.dumps(post_ids)
        emails_json = json.dumps(recipient_emails)
        sent_at = datetime.now().isoformat() if status == 'sent' else None
        
        c.execute('''
            INSERT INTO email_notifications 
            (trigger_id, post_ids, recipient_emails, sent_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (trigger_id, post_ids_json, emails_json, sent_at, status, error_message))
        
        conn.commit()
    finally:
        conn.close()


def create_notification_trigger(
    name: str,
    conditions: Dict[str, Any],
    emails: List[str],
    cooldown_minutes: int = 60,
    max_posts_per_email: int = 10,
    enabled: bool = True
) -> int:
    """Create a new notification trigger."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        import json
        from datetime import datetime
        
        conditions_json = json.dumps(conditions)
        emails_json = json.dumps(emails)
        now = datetime.now().isoformat()
        
        c.execute('''
            INSERT INTO notification_triggers 
            (name, enabled, conditions, emails, cooldown_minutes, max_posts_per_email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        ''', (name, enabled, conditions_json, emails_json, cooldown_minutes, max_posts_per_email, now, now))
        
        trigger_id = c.fetchone()[0]
        conn.commit()
        return trigger_id
    finally:
        conn.close()


def get_notification_trigger(trigger_id: int) -> Optional[Dict[str, Any]]:
    """Get a notification trigger by ID."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, name, enabled, conditions, emails, cooldown_minutes, 
                   max_posts_per_email, last_notification_sent_at, created_at, updated_at
            FROM notification_triggers
            WHERE id = ?
        ''', (trigger_id,))
        
        row = c.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'name': row[1],
            'enabled': bool(row[2]),
            'conditions': row[3],
            'emails': row[4],
            'cooldown_minutes': row[5],
            'max_posts_per_email': row[6],
            'last_notification_sent_at': row[7],
            'created_at': row[8],
            'updated_at': row[9]
        }
    finally:
        conn.close()


def get_all_notification_triggers() -> List[Dict[str, Any]]:
    """Get all notification triggers (active and inactive)."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, name, enabled, conditions, emails, cooldown_minutes, 
                   max_posts_per_email, last_notification_sent_at, created_at, updated_at
            FROM notification_triggers
            ORDER BY created_at DESC
        ''')
        
        triggers = []
        for row in c.fetchall():
            triggers.append({
                'id': row[0],
                'name': row[1],
                'enabled': bool(row[2]),
                'conditions': row[3],
                'emails': row[4],
                'cooldown_minutes': row[5],
                'max_posts_per_email': row[6],
                'last_notification_sent_at': row[7],
                'created_at': row[8],
                'updated_at': row[9]
            })
        
        return triggers
    finally:
        conn.close()


def update_notification_trigger(
    trigger_id: int,
    name: Optional[str] = None,
    conditions: Optional[Dict[str, Any]] = None,
    emails: Optional[List[str]] = None,
    cooldown_minutes: Optional[int] = None,
    max_posts_per_email: Optional[int] = None,
    enabled: Optional[bool] = None
) -> bool:
    """Update a notification trigger."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        import json
        from datetime import datetime
        
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if conditions is not None:
            updates.append("conditions = ?")
            params.append(json.dumps(conditions))
        
        if emails is not None:
            updates.append("emails = ?")
            params.append(json.dumps(emails))
        
        if cooldown_minutes is not None:
            updates.append("cooldown_minutes = ?")
            params.append(cooldown_minutes)
        
        if max_posts_per_email is not None:
            updates.append("max_posts_per_email = ?")
            params.append(max_posts_per_email)
        
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(enabled)
        
        if not updates:
            return False
        
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(trigger_id)
        
        query = f"UPDATE notification_triggers SET {', '.join(updates)} WHERE id = ?"
        c.execute(query, params)
        conn.commit()
        
        return c.rowcount > 0
    finally:
        conn.close()


def delete_notification_trigger(trigger_id: int) -> bool:
    """Delete a notification trigger."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM notification_triggers WHERE id = ?", (trigger_id,))
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()


def get_email_notifications(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get email notification history."""
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, trigger_id, post_ids, recipient_emails, sent_at, status, error_message, created_at
            FROM email_notifications
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        notifications = []
        for row in c.fetchall():
            notifications.append({
                'id': row[0],
                'trigger_id': row[1],
                'post_ids': row[2],
                'recipient_emails': row[3],
                'sent_at': row[4],
                'status': row[5],
                'error_message': row[6],
                'created_at': row[7]
            })
        
        return notifications
    finally:
        conn.close()


def get_posts(limit: int = 100, offset: int = 0, language: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch posts with parameterized queries to prevent SQL injection."""
    # SECURITY: Validate input types to prevent injection
    if not isinstance(limit, int) or not isinstance(offset, int):
        raise ValueError("limit and offset must be integers")
    if language and not isinstance(language, str):
        raise ValueError("language must be a string")
    
    with get_db() as conn:
        c = conn.cursor()
        
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
    
    keys = ['id', 'source', 'author', 'content', 'url', 'created_at', 'sentiment_score', 'sentiment_label', 'language', 'relevance_score']
    return [dict(zip(keys, row)) for row in rows]


def create_job_record(job_id: str) -> None:
    with get_db() as conn:
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


def update_job_progress(job_id: str, total: int, completed: int) -> None:
    with get_db() as conn:
        c = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        c.execute('UPDATE jobs SET progress_total = ?, progress_completed = ?, updated_at = ? WHERE job_id = ?', (total, completed, now, job_id))


def append_job_result(job_id: str, result: Dict[str, Any]) -> None:
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


def append_job_error(job_id: str, error_msg: str) -> None:
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


def finalize_job(job_id: str, status: str, error: Optional[str] = None) -> None:
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute('UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE job_id = ?', (status, error, now, job_id))
    conn.commit()
    conn.close()


def get_job_record(job_id: str) -> Optional[Dict[str, Any]]:
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


def get_all_jobs(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get all jobs from the database with optional filtering.
    
    Args:
        status: Optional status filter (e.g., 'running', 'completed', 'failed', 'pending')
        limit: Limit on number of results (default: 100)
    
    Returns:
        List of job records
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        query = 'SELECT job_id, status, progress_total, progress_completed, results, errors, cancelled, error, created_at, updated_at FROM jobs'
        params = []
        
        if status:
            query += ' WHERE status = ?'
            params.append(status)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        c.execute(query, params)
        rows = c.fetchall()
        
        jobs = []
        for row in rows:
            jobs.append({
                'id': row[0],
                'status': row[1],
                'progress': {'total': row[2], 'completed': row[3]},
                'results': json.loads(row[4] or '[]'),
                'errors': json.loads(row[5] or '[]'),
                'cancelled': bool(row[6]),
                'error': row[7],
                'created_at': row[8],
                'updated_at': row[9],
            })
        
        return jobs
    finally:
        conn.close()


def save_queries(keywords: List[str]) -> None:
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


def get_base_keywords() -> Dict[str, List[str]]:
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


def save_base_keywords(keywords_by_category: Dict[str, List[str]]) -> None:
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


def get_saved_queries() -> List[str]:
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT keyword FROM saved_queries ORDER BY id ASC')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


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


def delete_duplicate_posts() -> int:
    """
    Delete duplicate posts from the database.
    Duplicates are identified by:
    1. Same URL (most reliable)
    2. Same normalized content + author + source
    
    Keeps the oldest post (lowest ID) and deletes the rest.
    
    Returns:
        Number of posts deleted
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        deleted_count = 0
        
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
        deleted_count += deleted_by_url
        
        # Get all posts to check for content duplicates
        c.execute('''
            SELECT id, content, author, source
            FROM posts
            ORDER BY id
        ''')
        all_posts = c.fetchall()
        
        # Group posts by normalized content + author + source
        seen_normalized = {}
        duplicates_to_delete = []
        
        for post_id, content, author, source in all_posts:
            if not content:
                continue
                
            normalized = _normalize_content_for_comparison(str(content))
            if len(normalized) < 20:  # Skip very short content
                continue
            
            # Key: normalized content (first 300 chars) + author + source (improved)
            key = (normalized[:300], str(author or 'unknown')[:100], str(source or '')[:100])
            
            if key in seen_normalized:
                # This is a duplicate, mark for deletion
                duplicates_to_delete.append(post_id)
            else:
                # First occurrence, keep it
                seen_normalized[key] = post_id
        
        # Delete duplicates
        if duplicates_to_delete:
            placeholders = ','.join(['?'] * len(duplicates_to_delete))
            c.execute(f'''
                DELETE FROM posts
                WHERE id IN ({placeholders})
            ''', duplicates_to_delete)
            deleted_by_content = c.rowcount
            deleted_count += deleted_by_content
        
        conn.commit()
    finally:
        conn.close()
    
    return deleted_count


def delete_non_ovh_posts() -> int:
    """
    Delete all posts from the database that do NOT mention OVH or its brands.
    Keeps posts containing: ovh, ovhcloud, ovh cloud, kimsufi, soyoustart
    Also deletes posts from excluded domains (fool.com, 3m.com, etc.)
    
    Uses optimized SQL queries first, then relevance scorer for edge cases.
    
    Returns:
        Number of posts deleted
    """
    from .analysis import relevance_scorer
    
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        deleted_count = 0
        
        # First, delete posts from excluded domains (fast SQL query)
        excluded_domains = ['fool.com', 'motleyfool.com', '3m.com']
        for domain in excluded_domains:
            c.execute('''
                DELETE FROM posts
                WHERE LOWER(url) LIKE ?
            ''', (f'%{domain}%',))
            deleted_count += c.rowcount
        
        # Delete posts that don't contain OVH-related keywords in content or URL
        # (optimized SQL query for most cases)
        c.execute('''
            DELETE FROM posts
            WHERE LOWER(content) NOT LIKE '%ovh%'
            AND LOWER(content) NOT LIKE '%ovhcloud%'
            AND LOWER(content) NOT LIKE '%ovh cloud%'
            AND LOWER(content) NOT LIKE '%kimsufi%'
            AND LOWER(content) NOT LIKE '%soyoustart%'
            AND LOWER(author) NOT LIKE '%ovh%'
            AND (url IS NULL OR (
                LOWER(url) NOT LIKE '%ovh%' 
                AND LOWER(url) NOT LIKE '%kimsufi%' 
                AND LOWER(url) NOT LIKE '%soyoustart%'
                AND LOWER(url) NOT LIKE '%ovhcloud%'
            ))
        ''')
        deleted_count += c.rowcount
        
        # For posts that mention OVH but might be false positives,
        # check a sample with relevance scorer (limit to avoid timeout)
        c.execute('''
            SELECT id, source, author, content, url, created_at, 
                   sentiment_score, sentiment_label, language, country, relevance_score
            FROM posts
            WHERE (LOWER(content) LIKE '%ovh%' OR LOWER(url) LIKE '%ovh%')
            AND relevance_score < 0.3
            LIMIT 1000
        ''')
        suspicious_posts = c.fetchall()
        
        false_positive_ids = []
        for row in suspicious_posts:
            post = {
                'id': row[0],
                'source': row[1],
                'author': row[2],
                'content': row[3],
                'url': row[4],
                'created_at': row[5],
                'sentiment_score': row[6],
                'sentiment_label': row[7],
                'language': row[8],
                'country': row[9],
                'relevance_score': row[10] if len(row) > 10 else 0.0
            }
            
            # Check if post is actually relevant
            if not relevance_scorer.is_relevant(post, threshold=0.3):
                false_positive_ids.append(row[0])
        
        # Delete false positives
        if false_positive_ids:
            placeholders = ','.join(['?'] * len(false_positive_ids))
            c.execute(f'''
                DELETE FROM posts
                WHERE id IN ({placeholders})
            ''', false_positive_ids)
            deleted_count += c.rowcount
        
        conn.commit()
    finally:
        conn.close()
    
    return deleted_count


def delete_sample_posts() -> int:
    """
    Delete sample/fake posts used for testing.
    Identifies sample posts by checking for test keywords in content or author.
    
    Returns:
        Number of posts deleted
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


def delete_hackernews_posts() -> int:
    """
    Delete all posts from Hacker News source.
    
    Returns:
        Number of posts deleted
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

def add_scraping_log(
    source: str, 
    level: str, 
    message: str, 
    details: Optional[Union[str, Dict[str, Any]]] = None
) -> None:
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


def get_scraping_logs(
    source: Optional[str] = None, 
    level: Optional[str] = None, 
    limit: int = 1000, 
    offset: int = 0
) -> List[Dict[str, Any]]:
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
            try:
                log = {
                    'id': row[0],
                    'timestamp': row[1],
                    'source': row[2] if row[2] else '',
                    'level': row[3] if row[3] else 'info',
                    'message': row[4] if row[4] else '',
                    'details': row[5] if len(row) > 5 and row[5] else None
                }
                # Try to parse details as JSON if it exists
                if log['details']:
                    try:
                        if isinstance(log['details'], str):
                            log['details'] = json.loads(log['details'])
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass  # Keep as string if not valid JSON
                logs.append(log)
            except Exception as e:
                logger.warning(f"Error processing log row: {e}, row: {row}")
                continue
        
        return logs
    except Exception as e:
        logger.error(f"Error in get_scraping_logs: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def clear_scraping_logs(
    source: Optional[str] = None, 
    older_than_days: Optional[int] = None
) -> int:
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


# ===== AUTHENTICATION FUNCTIONS =====

def create_user(username: str, password_hash: str, email: Optional[str] = None, is_admin: bool = False) -> Optional[int]:
    """
    Create a new user in the database.
    
    Args:
        username: Unique username
        password_hash: Hashed password (bcrypt)
        email: Optional email address
        is_admin: Whether user has admin privileges
    
    Returns:
        User ID if successful, None if username already exists
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        now = datetime.datetime.utcnow().isoformat()
        c.execute('''
            INSERT INTO users (id, username, email, password_hash, is_admin, created_at, updated_at)
            VALUES (nextval('users_id_seq'), ?, ?, ?, ?, ?, ?)
            RETURNING id
        ''', (username, email, password_hash, is_admin, now, now))
        
        result = c.fetchone()
        user_id = result[0] if result else None
        conn.commit()
        return user_id
    except Exception as e:
        logger.error(f"Error creating user {username}: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Get user by username.
    
    Args:
        username: Username to lookup
    
    Returns:
        User dict with id, username, email, password_hash, is_admin, is_active, or None
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, username, email, password_hash, is_admin, is_active, created_at, updated_at
            FROM users WHERE username = ?
        ''', (username,))
        
        row = c.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'username': row[1],
            'email': row[2],
            'password_hash': row[3],
            'is_admin': bool(row[4]),
            'is_active': bool(row[5]),
            'created_at': row[6],
            'updated_at': row[7]
        }
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user by ID.
    
    Args:
        user_id: User ID to lookup
    
    Returns:
        User dict or None
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, username, email, password_hash, is_admin, is_active, created_at, updated_at
            FROM users WHERE id = ?
        ''', (user_id,))
        
        row = c.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'username': row[1],
            'email': row[2],
            'password_hash': row[3],
            'is_admin': bool(row[4]),
            'is_active': bool(row[5]),
            'created_at': row[6],
            'updated_at': row[7]
        }
    finally:
        conn.close()


def save_session(user_id: int, refresh_token: str, expires_at: str) -> bool:
    """
    Save a refresh token session.
    
    Args:
        user_id: User ID
        refresh_token: Refresh token string
        expires_at: Expiration timestamp (ISO format)
    
    Returns:
        True if successful, False otherwise
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO sessions (id, user_id, refresh_token, expires_at)
            VALUES (nextval('sessions_id_seq'), ?, ?, ?)
        ''', (user_id, refresh_token, expires_at))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving session: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_session_by_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Get session by refresh token.
    
    Args:
        refresh_token: Refresh token string
    
    Returns:
        Session dict with user_id, expires_at, or None
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT id, user_id, refresh_token, expires_at, created_at
            FROM sessions WHERE refresh_token = ?
        ''', (refresh_token,))
        
        row = c.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'user_id': row[1],
            'refresh_token': row[2],
            'expires_at': row[3],
            'created_at': row[4]
        }
    finally:
        conn.close()


def delete_session(refresh_token: str) -> bool:
    """
    Delete a session by refresh token.
    
    Args:
        refresh_token: Refresh token to delete
    
    Returns:
        True if deleted, False otherwise
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM sessions WHERE refresh_token = ?', (refresh_token,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_expired_sessions() -> int:
    """
    Delete expired sessions.
    
    Returns:
        Number of sessions deleted
    """
    conn, is_duckdb = get_db_connection()
    c = conn.cursor()
    
    try:
        now = datetime.datetime.utcnow().isoformat()
        c.execute('DELETE FROM sessions WHERE expires_at < ?', (now,))
        deleted_count = c.rowcount
        conn.commit()
        return deleted_count
    except Exception as e:
        logger.error(f"Error deleting expired sessions: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()
