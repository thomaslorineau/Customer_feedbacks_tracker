"""Unit tests for db.py module."""
import pytest
from datetime import datetime
from app import db


class TestInsertPost:
    """Tests for insert_post function."""
    
    def test_insert_post_success(self, test_db, sample_post):
        """Test successful post insertion."""
        post_id = db.insert_post(sample_post)
        assert post_id is not None
        assert isinstance(post_id, int)
        assert post_id > 0
    
    def test_insert_post_duplicate_url(self, test_db, sample_post):
        """Test that duplicate URLs are detected and not inserted."""
        # Insert first post
        post_id1 = db.insert_post(sample_post)
        assert post_id1 is not None
        
        # Try to insert duplicate (same URL)
        post_id2 = db.insert_post(sample_post)
        assert post_id2 is None  # Should return None for duplicate
    
    def test_insert_post_minimal_data(self, test_db):
        """Test insertion with minimal required fields."""
        minimal_post = {
            'source': 'TestSource',
            'content': 'Minimal test content'
        }
        post_id = db.insert_post(minimal_post)
        assert post_id is not None
    
    def test_insert_post_with_relevance_score(self, test_db, sample_post):
        """Test insertion with relevance score."""
        sample_post['relevance_score'] = 0.95
        post_id = db.insert_post(sample_post)
        assert post_id is not None
        
        # Verify relevance score was saved
        saved_post = db.get_post_by_id(post_id)
        assert saved_post is not None
        assert saved_post['relevance_score'] == 0.95


class TestGetPost:
    """Tests for get_post_by_id function."""
    
    def test_get_post_by_id_success(self, test_db, sample_post):
        """Test retrieving post by ID."""
        post_id = db.insert_post(sample_post)
        assert post_id is not None
        
        retrieved_post = db.get_post_by_id(post_id)
        assert retrieved_post is not None
        assert retrieved_post['id'] == post_id
        assert retrieved_post['source'] == sample_post['source']
        assert retrieved_post['content'] == sample_post['content']
        assert retrieved_post['url'] == sample_post['url']
    
    def test_get_post_by_id_not_found(self, test_db):
        """Test retrieving non-existent post."""
        retrieved_post = db.get_post_by_id(99999)
        assert retrieved_post is None


class TestGetPosts:
    """Tests for get_posts function."""
    
    def test_get_posts_default(self, test_db, sample_post):
        """Test getting posts with default parameters."""
        # Insert a few posts
        for i in range(3):
            post = sample_post.copy()
            post['url'] = f'https://example.com/post-{i}'
            post['created_at'] = datetime.now().isoformat()
            db.insert_post(post)
        
        posts = db.get_posts(limit=10)
        assert len(posts) == 3
    
    def test_get_posts_with_limit(self, test_db, sample_post):
        """Test getting posts with limit."""
        # Insert 5 posts
        for i in range(5):
            post = sample_post.copy()
            post['url'] = f'https://example.com/post-{i}'
            post['created_at'] = datetime.now().isoformat()
            db.insert_post(post)
        
        posts = db.get_posts(limit=3)
        assert len(posts) == 3
    
    def test_get_posts_with_offset(self, test_db, sample_post):
        """Test getting posts with offset."""
        # Insert 5 posts
        for i in range(5):
            post = sample_post.copy()
            post['url'] = f'https://example.com/post-{i}'
            post['created_at'] = datetime.now().isoformat()
            db.insert_post(post)
        
        # Get first 2
        posts1 = db.get_posts(limit=2, offset=0)
        assert len(posts1) == 2
        
        # Get next 2
        posts2 = db.get_posts(limit=2, offset=2)
        assert len(posts2) == 2
        
        # Verify different posts
        assert posts1[0]['id'] != posts2[0]['id']
    
    def test_get_posts_with_language_filter(self, test_db, sample_post):
        """Test getting posts filtered by language."""
        # Insert posts with different languages
        post_en = sample_post.copy()
        post_en['language'] = 'en'
        post_en['url'] = 'https://example.com/en'
        db.insert_post(post_en)
        
        post_fr = sample_post.copy()
        post_fr['language'] = 'fr'
        post_fr['url'] = 'https://example.com/fr'
        db.insert_post(post_fr)
        
        # Get only English posts
        posts_en = db.get_posts(language='en')
        assert len(posts_en) == 1
        assert posts_en[0]['language'] == 'en'


class TestDuplicateDetection:
    """Tests for duplicate post detection."""
    
    def test_duplicate_detection_by_url(self, test_db, sample_post):
        """Test that posts with same URL are detected as duplicates."""
        post_id1 = db.insert_post(sample_post)
        assert post_id1 is not None
        
        # Try to insert same post again
        post_id2 = db.insert_post(sample_post)
        assert post_id2 is None
    
    def test_different_posts_same_content(self, test_db, sample_post):
        """Test that posts with same content but different URLs are both inserted."""
        post1 = sample_post.copy()
        post1['url'] = 'https://example.com/post1'
        
        post2 = sample_post.copy()
        post2['url'] = 'https://example.com/post2'
        
        post_id1 = db.insert_post(post1)
        post_id2 = db.insert_post(post2)
        
        assert post_id1 is not None
        assert post_id2 is not None
        assert post_id1 != post_id2






