"""Pytest configuration and fixtures."""
import pytest
import duckdb
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import db


@pytest.fixture
def test_db(monkeypatch):
    """Create a temporary DuckDB database for testing."""
    # Create temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.duckdb')
    temp_file.close()
    db_path = Path(temp_file.name)
    
    try:
        # Temporarily override DB_FILE in db module
        monkeypatch.setattr(db, 'DB_FILE', db_path)
        
        # Initialize database using db.init_db()
        db.init_db()
        
        yield db_path
        
    finally:
        # Clean up temporary database
        if db_path.exists():
            os.unlink(str(db_path))


@pytest.fixture
def sample_post():
    """Sample post data for testing."""
    return {
        'source': 'TestSource',
        'author': 'test_user',
        'content': 'This is a test post about OVH cloud services.',
        'url': 'https://example.com/test-post',
        'created_at': '2026-01-20T10:00:00',
        'sentiment_score': 0.5,
        'sentiment_label': 'positive',
        'language': 'en',
        'relevance_score': 0.8
    }

