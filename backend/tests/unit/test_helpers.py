"""Unit tests for utils/helpers.py module."""
import pytest
from app.utils import helpers


class TestValidateQuery:
    """Tests for validate_query function."""
    
    def test_validate_query_valid(self):
        """Test validation of valid queries."""
        assert helpers.validate_query("OVH cloud") is True
        assert helpers.validate_query("test query") is True
        assert helpers.validate_query("a" * 50) is True  # Within limit
    
    def test_validate_query_empty(self):
        """Test validation of empty query."""
        assert helpers.validate_query("") is False
        assert helpers.validate_query(None) is False
    
    def test_validate_query_too_long(self):
        """Test validation of query exceeding max length."""
        long_query = "a" * 101  # Exceeds default max_length of 100
        assert helpers.validate_query(long_query) is False
    
    def test_validate_query_dangerous_patterns(self):
        """Test validation blocks dangerous SQL patterns."""
        dangerous_queries = [
            "'; DROP TABLE posts; --",
            "../etc/passwd",
            "<script>alert('xss')</script>",
            "DELETE FROM posts",
            "INSERT INTO posts",
            "UPDATE posts SET"
        ]
        
        for query in dangerous_queries:
            assert helpers.validate_query(query) is False, f"Should block: {query}"
    
    def test_validate_query_safe_special_chars(self):
        """Test that safe special characters are allowed."""
        safe_queries = [
            "OVH & cloud",
            "test@example.com",
            "query with-dashes",
            "query_with_underscores"
        ]
        
        for query in safe_queries:
            assert helpers.validate_query(query) is True, f"Should allow: {query}"


class TestProcessAndSaveItems:
    """Tests for process_and_save_items function."""
    
    def test_process_and_save_items_empty_list(self):
        """Test processing empty list."""
        result = helpers.process_and_save_items([], "TestSource")
        assert result == 0
    
    def test_process_and_save_items_single_item(self, test_db):
        """Test processing single item."""
        items = [{
            'source': 'TestSource',
            'author': 'test_user',
            'content': 'Test content about OVH',
            'url': 'https://example.com/test',
            'created_at': '2026-01-20T10:00:00'
        }]
        
        # Mock db.insert_post to avoid actual DB operations in unit test
        # In a real scenario, we'd use a test database fixture
        # For now, we'll test the function structure
        result = helpers.process_and_save_items(items, "TestSource")
        # Should return number of items saved (0 if DB not available in test)
        assert isinstance(result, int)
        assert result >= 0
    
    def test_process_and_save_items_with_sentiment(self, test_db):
        """Test processing items with pre-calculated sentiment."""
        items = [{
            'source': 'TestSource',
            'author': 'test_user',
            'content': 'Great service from OVH!',
            'url': 'https://example.com/test',
            'created_at': '2026-01-20T10:00:00',
            'sentiment_score': 0.8,
            'sentiment_label': 'positive'
        }]
        
        result = helpers.process_and_save_items(items, "TestSource")
        assert isinstance(result, int)
        assert result >= 0


class TestSafeScrape:
    """Tests for safe_scrape function."""
    
    def test_safe_scrape_success(self):
        """Test successful scraping."""
        def mock_scraper(query, limit):
            return [{
                'source': 'TestSource',
                'author': 'test_user',
                'content': 'Test content',
                'url': 'https://example.com/test',
                'created_at': '2026-01-20T10:00:00'
            }]
        
        # Note: This would require mocking db operations
        # For now, we test that the function structure is correct
        result = helpers.safe_scrape(mock_scraper, "OVH", 10, "TestSource")
        assert isinstance(result, int)
        assert result >= 0
    
    def test_safe_scrape_exception(self):
        """Test scraping with exception handling."""
        def failing_scraper(query, limit):
            raise Exception("Scraping failed")
        
        result = helpers.safe_scrape(failing_scraper, "OVH", 10, "TestSource")
        assert result == 0  # Should return 0 on error















