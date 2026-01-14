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
    # Create indexes for frequently queried columns
    c.execute('CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_posts_sentiment_label ON posts(sentiment_label)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_posts_language ON posts(language)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_posts_url ON posts(url)')
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
    """Insert a post into the database, skipping duplicates.
    
    Checks for duplicates by:
    1. URL (if available) - most reliable
    2. Content + Author + Source (if URL check doesn't find a match)
    
    Returns True if inserted, False if duplicate found.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    url = post.get('url', '').strip() if post.get('url') else ''
    content = post.get('content', '').strip() if post.get('content') else ''
    author = post.get('author', '').strip() if post.get('author') else ''
    source = post.get('source', '').strip() if post.get('source') else ''
    
    # Method 1: Check for duplicate URL (most reliable)
    if url:
        c.execute('SELECT id FROM posts WHERE url = ?', (url,))
        existing = c.fetchone()
        if existing:
            conn.close()
            logger.debug(f"[DB] Duplicate detected by URL: {url[:80]}... (existing ID: {existing[0]})")
            return False  # Duplicate URL found, skip insertion
    
    # Method 2: Check for duplicate by content + author + source
    # This catches duplicates where URL might be slightly different or missing
    if content and author and source:
        # Normalize content and author for comparison (lowercase, trimmed)
        c.execute('''
            SELECT id FROM posts 
            WHERE LOWER(TRIM(content)) = LOWER(TRIM(?))
            AND LOWER(TRIM(author)) = LOWER(TRIM(?))
            AND source = ?
            LIMIT 1
        ''', (content, author, source))
        existing = c.fetchone()
        if existing:
            conn.close()
            logger.debug(f"[DB] Duplicate detected by content+author+source: {source}/{author} (existing ID: {existing[0]})")
            return False  # Duplicate content+author+source found, skip insertion
    
    # No duplicate found, insert the post
    c.execute(
        '''INSERT INTO posts (source, author, content, url, created_at, sentiment_score, sentiment_label, language)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            source,
            author,
            content,
            url,
            post.get('created_at'),
            post.get('sentiment_score'),
            post.get('sentiment_label'),
            post.get('language', 'unknown'),
        ),
    )
    conn.commit()
    conn.close()
    return True  # Successfully inserted


def get_posts(limit: int = 100, offset: int = 0, language: str = None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if language and language != 'all':
        c.execute('SELECT id, source, author, content, url, created_at, sentiment_score, sentiment_label, language FROM posts WHERE language = ? ORDER BY id DESC LIMIT ? OFFSET ?', (language, limit, offset))
    else:
        c.execute('SELECT id, source, author, content, url, created_at, sentiment_score, sentiment_label, language FROM posts ORDER BY id DESC LIMIT ? OFFSET ?', (limit, offset))
    
    rows = c.fetchall()
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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # clear existing
    c.execute('DELETE FROM saved_queries')
    import datetime
    now = datetime.datetime.utcnow().isoformat()
    for kw in keywords:
        c.execute('INSERT OR IGNORE INTO saved_queries (keyword, created_at) VALUES (?, ?)', (kw, now))
    conn.commit()
    conn.close()


def get_saved_queries():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT keyword FROM saved_queries ORDER BY id ASC')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def delete_sample_posts():
    """Delete all posts that are identified as sample data.
    
    Sample posts are identified by:
    - URL containing '/sample'
    - URL containing 'example.com'
    - URL containing '/status/174' (sample Twitter URLs)
    - URL exactly equal to 'https://trustpilot.com/sample'
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Delete posts with sample URLs
    patterns = [
        "%/sample%",
        "%example.com%",
        "%/status/174%"
    ]
    
    deleted_count = 0
    for pattern in patterns:
        c.execute('DELETE FROM posts WHERE url LIKE ?', (pattern,))
        deleted_count += c.rowcount
    
    # Also delete exact match
    c.execute('DELETE FROM posts WHERE url = ?', ('https://trustpilot.com/sample',))
    deleted_count += c.rowcount
    
    conn.commit()
    conn.close()
    return deleted_count


def delete_hackernews_posts():
    """Delete all posts from Hacker News source.
    
    Returns the number of posts deleted.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Count first
    c.execute('SELECT COUNT(*) FROM posts WHERE source = ?', ('Hacker News',))
    count = c.fetchone()[0]
    
    # Delete Hacker News posts
    c.execute('DELETE FROM posts WHERE source = ?', ('Hacker News',))
    conn.commit()
    conn.close()
    
    return count


def delete_duplicate_posts():
    """Delete duplicate posts from the database.
    
    Duplicates are identified by:
    1. Same URL (most reliable) - keeps the post with lowest ID
    2. Same content + same author + same source (for cases where URL might vary slightly)
    
    Keeps the post with the lowest ID (oldest) and deletes the rest.
    
    Returns the number of duplicate posts deleted.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    deleted_count = 0
    
    # Method 1: Delete duplicates by URL (keep the one with lowest ID)
    # Find all URLs that appear more than once
    c.execute('''
        SELECT url, COUNT(*) as count
        FROM posts
        WHERE url IS NOT NULL AND url != ''
        GROUP BY url
        HAVING count > 1
    ''')
    duplicate_urls = c.fetchall()
    
    for url_tuple in duplicate_urls:
        url = url_tuple[0]
        # Get all IDs for this URL, keep the minimum
        c.execute('SELECT id FROM posts WHERE url = ? ORDER BY id ASC', (url,))
        ids = [row[0] for row in c.fetchall()]
        if len(ids) > 1:
            # Keep the first (lowest ID), delete the rest
            ids_to_delete = ids[1:]
            placeholders = ','.join(['?'] * len(ids_to_delete))
            c.execute(f'DELETE FROM posts WHERE id IN ({placeholders})', ids_to_delete)
            deleted_count += c.rowcount
    
    # Method 2: Delete duplicates by content + author + source
    # This catches duplicates where URL might be slightly different or missing
    c.execute('''
        SELECT LOWER(TRIM(content)), LOWER(TRIM(author)), source, COUNT(*) as count
        FROM posts
        WHERE content IS NOT NULL AND content != '' AND content != 'null'
        GROUP BY LOWER(TRIM(content)), LOWER(TRIM(author)), source
        HAVING count > 1
    ''')
    duplicate_content = c.fetchall()
    
    for content_tuple in duplicate_content:
        content_lower = content_tuple[0]
        author_lower = content_tuple[1]
        source = content_tuple[2]
        # Get all IDs for this combination, keep the minimum
        c.execute('''
            SELECT id FROM posts
            WHERE LOWER(TRIM(content)) = ? 
            AND LOWER(TRIM(author)) = ? 
            AND source = ?
            ORDER BY id ASC
        ''', (content_lower, author_lower, source))
        ids = [row[0] for row in c.fetchall()]
        if len(ids) > 1:
            # Keep the first (lowest ID), delete the rest
            ids_to_delete = ids[1:]
            placeholders = ','.join(['?'] * len(ids_to_delete))
            c.execute(f'DELETE FROM posts WHERE id IN ({placeholders})', ids_to_delete)
            deleted_count += c.rowcount
    
    conn.commit()
    conn.close()
    
    return deleted_count


def delete_non_ovh_posts():
    """Delete all posts that don't mention OVH or related terms.
    
    Keeps posts that contain (case-insensitive):
    - ovh
    - ovhcloud
    - ovh cloud
    - kimsufi (OVH brand)
    - soyoustart (OVH brand)
    
    Searches in: content, url, and author fields.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get all posts
    c.execute('SELECT id, content, url, author FROM posts')
    all_posts = c.fetchall()
    
    # OVH-related keywords to search for
    ovh_keywords = [
        'ovh',
        'ovhcloud',
        'ovh cloud',
        'kimsufi',  # OVH budget brand
        'soyoustart',  # OVH mid-range brand
    ]
    
    deleted_count = 0
    posts_to_delete = []
    
    for post_id, content, url, author in all_posts:
        # Combine all searchable text
        searchable_text = f"{content or ''} {url or ''} {author or ''}".lower()
        
        # Check if any OVH keyword is present
        is_ovh_related = any(keyword.lower() in searchable_text for keyword in ovh_keywords)
        
        if not is_ovh_related:
            posts_to_delete.append(post_id)
    
    # Delete non-OVH posts
    if posts_to_delete:
        placeholders = ','.join('?' * len(posts_to_delete))
        c.execute(f'DELETE FROM posts WHERE id IN ({placeholders})', posts_to_delete)
        deleted_count = c.rowcount
    
    conn.commit()
    conn.close()
    return deleted_count
