import sqlite3
from pathlib import Path
import json
import datetime

DB_FILE = Path(__file__).resolve().parents[1] / "data.db"


def init_db():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            author TEXT,
            content TEXT,
            url TEXT,
            created_at TEXT,
            sentiment_score REAL,
            sentiment_label TEXT,
            language TEXT DEFAULT 'unknown'
        )
    ''')
    
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
    
    # Saved search queries / keywords
    c.execute('''
        CREATE TABLE IF NOT EXISTS saved_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE,
            created_at TEXT
        )
    ''')
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
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # SECURITY: Use parameterized query to prevent SQL injection
        c.execute(
            '''INSERT INTO posts (source, author, content, url, created_at, sentiment_score, sentiment_label, language)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                str(post.get('source'))[:100],  # Limit length
                str(post.get('author', 'unknown'))[:100],
                str(post.get('content', ''))[:10000],  # Limit content length
                str(post.get('url', ''))[:500],
                post.get('created_at'),
                float(post.get('sentiment_score', 0.0)) if post.get('sentiment_score') else 0.0,
                str(post.get('sentiment_label', 'neutral'))[:20],
                str(post.get('language', 'unknown'))[:20],
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
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # SECURITY: Always use parameterized queries
        if language and language != 'all':
            c.execute(
                'SELECT id, source, author, content, url, created_at, sentiment_score, sentiment_label, language '
                'FROM posts WHERE language = ? ORDER BY id DESC LIMIT ? OFFSET ?',
                (language, limit, offset)
            )
        else:
            c.execute(
                'SELECT id, source, author, content, url, created_at, sentiment_score, sentiment_label, language '
                'FROM posts ORDER BY id DESC LIMIT ? OFFSET ?',
                (limit, offset)
            )
        
        rows = c.fetchall()
    finally:
        conn.close()
    
    keys = ['id', 'source', 'author', 'content', 'url', 'created_at', 'sentiment_score', 'sentiment_label', 'language']
    return [dict(zip(keys, row)) for row in rows]


def create_job_record(job_id: str):
    conn = sqlite3.connect(DB_FILE)
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
    # insert job
    c.execute('INSERT OR REPLACE INTO jobs (job_id, status, progress_total, progress_completed, results, errors, cancelled, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
              (job_id, 'pending', 0, 0, json.dumps([]), json.dumps([]), 0, None, now, now))
    conn.commit()
    conn.close()


def update_job_progress(job_id: str, total: int, completed: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute('UPDATE jobs SET progress_total = ?, progress_completed = ?, updated_at = ? WHERE job_id = ?', (total, completed, now, job_id))
    conn.commit()
    conn.close()


def append_job_result(job_id: str, result: dict):
    conn = sqlite3.connect(DB_FILE)
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
    conn = sqlite3.connect(DB_FILE)
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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute('UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE job_id = ?', (status, error, now, job_id))
    conn.commit()
    conn.close()


def get_job_record(job_id: str):
    conn = sqlite3.connect(DB_FILE)
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
    
    conn = sqlite3.connect(DB_FILE)
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
            # SECURITY: Use parameterized query
            c.execute('INSERT OR IGNORE INTO saved_queries (keyword, created_at) VALUES (?, ?)', (kw, now))
        
        conn.commit()
    finally:
        conn.close()


def get_saved_queries():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT keyword FROM saved_queries ORDER BY id ASC')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]
