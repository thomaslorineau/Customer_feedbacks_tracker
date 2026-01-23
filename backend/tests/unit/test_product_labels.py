"""Unit tests for product label detection and update functions."""
import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import db


class TestDetectProductLabel:
    """Tests for detect_product_label function."""
    
    def test_detect_domain_product(self, test_db):
        """Test detection of Domain product."""
        content = "I'm having issues with my domain registration on OVH"
        product = db.detect_product_label(content, 'en')
        assert product == 'Domain'
    
    def test_detect_vps_product(self, test_db):
        """Test detection of VPS product."""
        content = "My VPS server is down and I can't access it"
        product = db.detect_product_label(content, 'en')
        assert product == 'VPS'
    
    def test_detect_hosting_product(self, test_db):
        """Test detection of Hosting product."""
        content = "My web hosting plan is not working properly"
        product = db.detect_product_label(content, 'en')
        assert product == 'Hosting'
    
    def test_detect_email_product(self, test_db):
        """Test detection of Email product."""
        content = "I can't send emails through my SMTP server"
        product = db.detect_product_label(content, 'en')
        assert product == 'Email'
    
    def test_detect_public_cloud_product(self, test_db):
        """Test detection of Public Cloud product."""
        content = "My OVHcloud public cloud instance is not responding"
        product = db.detect_product_label(content, 'en')
        assert product == 'Public Cloud'
    
    def test_detect_no_product(self, test_db):
        """Test that no product is detected for generic content."""
        content = "I have a general question about OVH services"
        product = db.detect_product_label(content, 'en')
        assert product is None
    
    def test_detect_product_priority(self, test_db):
        """Test that more specific products are detected first."""
        # Domain should be detected before general hosting
        content = "I need help with my domain DNS configuration on my hosting"
        product = db.detect_product_label(content, 'en')
        assert product == 'Domain'  # More specific pattern matches first


class TestUpdatePostProductLabel:
    """Tests for update_post_product_label function."""
    
    def test_update_product_label(self, test_db, sample_post):
        """Test updating product label for a post."""
        # Insert post
        post_id = db.insert_post(sample_post)
        assert post_id is not None
        
        # Update product label
        success = db.update_post_product_label(post_id, 'VPS')
        assert success is True
        
        # Verify update
        posts = db.get_posts(limit=1, offset=0)
        updated_post = next((p for p in posts if p['id'] == post_id), None)
        assert updated_post is not None
        assert updated_post.get('product') == 'VPS'
    
    def test_update_product_label_to_none(self, test_db, sample_post):
        """Test removing product label by setting it to None."""
        # Insert post
        post_id = db.insert_post(sample_post)
        assert post_id is not None
        
        # Set product label first
        db.update_post_product_label(post_id, 'VPS')
        
        # Remove product label
        success = db.update_post_product_label(post_id, None)
        assert success is True
        
        # Verify removal
        posts = db.get_posts(limit=1, offset=0)
        updated_post = next((p for p in posts if p['id'] == post_id), None)
        assert updated_post is not None
        assert updated_post.get('product') is None
    
    def test_update_product_label_nonexistent_post(self, test_db):
        """Test updating product label for non-existent post."""
        success = db.update_post_product_label(99999, 'VPS')
        assert success is False


class TestUpdateAllPostsProductLabels:
    """Tests for update_all_posts_product_labels function."""
    
    @pytest.mark.asyncio
    async def test_update_all_posts_product_labels(self, test_db, sample_post):
        """Test updating product labels for all posts."""
        # Insert multiple posts with different content
        posts_data = [
            {'content': 'I have a VPS server issue', 'url': 'https://example.com/1'},
            {'content': 'My domain is not working', 'url': 'https://example.com/2'},
            {'content': 'General question about OVH', 'url': 'https://example.com/3'},
        ]
        
        post_ids = []
        for post_data in posts_data:
            post = sample_post.copy()
            post.update(post_data)
            post['created_at'] = datetime.now().isoformat()
            post_id = db.insert_post(post)
            post_ids.append(post_id)
        
        # Update all product labels
        result = db.update_all_posts_product_labels(limit=10)
        
        assert result['success'] is True
        assert result['updated_count'] >= 3
        assert result['total_posts'] >= 3
        
        # Verify product labels were set
        posts = db.get_posts(limit=10, offset=0)
        vps_post = next((p for p in posts if 'VPS' in p.get('content', '')), None)
        domain_post = next((p for p in posts if 'domain' in p.get('content', '').lower()), None)
        
        if vps_post:
            assert vps_post.get('product') == 'VPS'
        if domain_post:
            assert domain_post.get('product') == 'Domain'
    
    @pytest.mark.asyncio
    async def test_update_all_posts_with_limit(self, test_db, sample_post):
        """Test updating product labels with a limit."""
        # Insert 5 posts with product-related content
        posts_content = [
            'I have a VPS server issue',
            'My domain is not working',
            'General question about OVH',
            'Email server problem',
            'Hosting issue'
        ]
        
        for i, content in enumerate(posts_content):
            post = sample_post.copy()
            post['url'] = f'https://example.com/post-{i}'
            post['content'] = content
            post['created_at'] = datetime.now().isoformat()
            db.insert_post(post)
        
        # Update only first 3 posts
        result = db.update_all_posts_product_labels(limit=3)
        
        assert result['success'] is True
        assert result['total_posts'] == 3
        # At least some posts should be updated (those with product-related content)
        assert result['updated_count'] >= 1

