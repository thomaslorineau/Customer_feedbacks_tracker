"""Pytest configuration and fixtures."""
import pytest
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import database as db


@pytest.fixture
def test_db(monkeypatch):
    """Create a test PostgreSQL database connection for testing."""
    # Use test database URL from environment or default
    test_db_url = os.getenv('TEST_DATABASE_URL', 'postgresql://ocft_user:test_password@localhost:5432/ocft_tracker_test')
    
    # Override DATABASE_URL for tests
    monkeypatch.setenv('DATABASE_URL', test_db_url)
    monkeypatch.setenv('USE_POSTGRES', 'true')
    
    # Initialize database
    db.init_db()
    
    yield test_db_url
    
    # Cleanup: drop test data (optional, depends on test strategy)
    # For now, we'll let tests handle their own cleanup


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

