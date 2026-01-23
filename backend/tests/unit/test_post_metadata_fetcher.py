"""Unit tests for post_metadata_fetcher module."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils.post_metadata_fetcher import (
    fetch_reddit_post_metadata,
    fetch_github_issue_metadata,
    fetch_stackoverflow_question_metadata,
    fetch_post_metadata_from_url
)


class TestFetchRedditPostMetadata:
    """Tests for fetch_reddit_post_metadata function."""
    
    @pytest.mark.asyncio
    async def test_fetch_reddit_metadata_success(self):
        """Test successful Reddit metadata fetch."""
        url = "https://www.reddit.com/r/ovh/comments/abc123/test_post/"
        
        mock_response_data = [
            {
                'data': {
                    'children': [
                        {
                            'data': {
                                'num_comments': 5,
                                'id': 'abc123'
                            }
                        }
                    ]
                }
            }
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await fetch_reddit_post_metadata(url)
            
            assert result is not None
            assert result['source'] == 'reddit'
            assert result['num_comments'] == 5
            assert result['comments'] == 5
    
    @pytest.mark.asyncio
    async def test_fetch_reddit_metadata_invalid_url(self):
        """Test Reddit metadata fetch with invalid URL."""
        url = "https://example.com/not-reddit"
        result = await fetch_reddit_post_metadata(url)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_reddit_metadata_error(self):
        """Test Reddit metadata fetch with error."""
        url = "https://www.reddit.com/r/ovh/comments/abc123/test_post/"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Network error")
            
            result = await fetch_reddit_post_metadata(url)
            assert result is None


class TestFetchGitHubIssueMetadata:
    """Tests for fetch_github_issue_metadata function."""
    
    @pytest.mark.asyncio
    async def test_fetch_github_metadata_success(self):
        """Test successful GitHub issue metadata fetch."""
        url = "https://github.com/owner/repo/issues/123"
        
        mock_response_data = {
            'comments': 3,
            'number': 123,
            'state': 'open'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await fetch_github_issue_metadata(url)
            
            assert result is not None
            assert result['source'] == 'github'
            assert result['comments'] == 3
            assert result['comments_count'] == 3
    
    @pytest.mark.asyncio
    async def test_fetch_github_metadata_rate_limit(self):
        """Test GitHub metadata fetch with rate limit."""
        url = "https://github.com/owner/repo/issues/123"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await fetch_github_issue_metadata(url)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_github_metadata_invalid_url(self):
        """Test GitHub metadata fetch with invalid URL."""
        url = "https://example.com/not-github"
        result = await fetch_github_issue_metadata(url)
        assert result is None


class TestFetchStackOverflowQuestionMetadata:
    """Tests for fetch_stackoverflow_question_metadata function."""
    
    @pytest.mark.asyncio
    async def test_fetch_stackoverflow_metadata_success(self):
        """Test successful Stack Overflow question metadata fetch."""
        url = "https://stackoverflow.com/questions/123456/test-question"
        
        mock_response_data = {
            'items': [
                {
                    'is_answered': True,
                    'answer_count': 2,
                    'question_id': 123456
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await fetch_stackoverflow_question_metadata(url)
            
            assert result is not None
            assert result['source'] == 'stackoverflow'
            assert result['is_answered'] is True
            assert result['answer_count'] == 2
    
    @pytest.mark.asyncio
    async def test_fetch_stackoverflow_metadata_not_answered(self):
        """Test Stack Overflow metadata fetch for unanswered question."""
        url = "https://stackoverflow.com/questions/123456/test-question"
        
        mock_response_data = {
            'items': [
                {
                    'is_answered': False,
                    'answer_count': 0,
                    'question_id': 123456
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await fetch_stackoverflow_question_metadata(url)
            
            assert result is not None
            assert result['is_answered'] is False
            assert result['answer_count'] == 0
    
    @pytest.mark.asyncio
    async def test_fetch_stackoverflow_metadata_invalid_url(self):
        """Test Stack Overflow metadata fetch with invalid URL."""
        url = "https://example.com/not-stackoverflow"
        result = await fetch_stackoverflow_question_metadata(url)
        assert result is None


class TestFetchPostMetadataFromUrl:
    """Tests for fetch_post_metadata_from_url function."""
    
    @pytest.mark.asyncio
    async def test_fetch_reddit_via_router(self):
        """Test routing to Reddit fetcher."""
        url = "https://www.reddit.com/r/ovh/comments/abc123/test/"
        
        with patch('app.utils.post_metadata_fetcher.fetch_reddit_post_metadata') as mock_fetch:
            mock_fetch.return_value = {'source': 'reddit', 'num_comments': 5}
            result = await fetch_post_metadata_from_url(url, 'reddit')
            assert result is not None
            mock_fetch.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    async def test_fetch_github_via_router(self):
        """Test routing to GitHub fetcher."""
        url = "https://github.com/owner/repo/issues/123"
        
        with patch('app.utils.post_metadata_fetcher.fetch_github_issue_metadata') as mock_fetch:
            mock_fetch.return_value = {'source': 'github', 'comments': 3}
            result = await fetch_post_metadata_from_url(url, 'github')
            assert result is not None
            mock_fetch.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    async def test_fetch_stackoverflow_via_router(self):
        """Test routing to Stack Overflow fetcher."""
        url = "https://stackoverflow.com/questions/123456/test"
        
        with patch('app.utils.post_metadata_fetcher.fetch_stackoverflow_question_metadata') as mock_fetch:
            mock_fetch.return_value = {'source': 'stackoverflow', 'is_answered': True}
            result = await fetch_post_metadata_from_url(url, 'stackoverflow')
            assert result is not None
            mock_fetch.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    async def test_fetch_unknown_source(self):
        """Test routing with unknown source."""
        url = "https://example.com/post"
        result = await fetch_post_metadata_from_url(url, 'unknown')
        assert result is None

