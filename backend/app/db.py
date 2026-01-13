import sqlite3
from pathlib import Path

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
            sentiment_label TEXT
        )
    ''')
    conn.commit()
    conn.close()


def insert_post(post: dict):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        '''INSERT INTO posts (source, author, content, url, created_at, sentiment_score, sentiment_label)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (
            post.get('source'),
            post.get('author'),
            post.get('content'),
            post.get('url'),
            post.get('created_at'),
            post.get('sentiment_score'),
            post.get('sentiment_label'),
        ),
    )
    conn.commit()
    conn.close()


def get_posts(limit: int = 100):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, source, author, content, url, created_at, sentiment_score, sentiment_label FROM posts ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    keys = ['id', 'source', 'author', 'content', 'url', 'created_at', 'sentiment_score', 'sentiment_label']
    return [dict(zip(keys, row)) for row in rows]
