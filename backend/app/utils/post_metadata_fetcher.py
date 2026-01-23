"""
Utility functions to fetch post metadata from URLs for re-checking answered status.
"""
import re
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


async def fetch_reddit_post_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata for a specific Reddit post from its URL.
    
    Args:
        url: Reddit post URL (e.g., https://www.reddit.com/r/ovh/comments/abc123/...)
    
    Returns:
        Dict with metadata (num_comments, etc.) or None if failed
    """
    try:
        # Extract post ID from Reddit URL
        # Format: https://www.reddit.com/r/SUBREDDIT/comments/POST_ID/TITLE/
        match = re.search(r'/r/\w+/comments/(\w+)', url)
        if not match:
            logger.warning(f"Could not extract Reddit post ID from URL: {url}")
            return None
        
        post_id = match.group(1)
        
        # Fetch post metadata from Reddit JSON API
        json_url = f"https://www.reddit.com/comments/{post_id}.json"
        headers = {
            'User-Agent': 'OVH-Tracker-Bot/1.0 (Feedback Monitor)'
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(json_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                post_data = data[0]['data']['children'][0]['data']
                return {
                    'source': 'reddit',
                    'num_comments': post_data.get('num_comments', 0),
                    'comments': post_data.get('num_comments', 0),
                    'url': url
                }
        
        return None
        
    except Exception as e:
        logger.debug(f"Error fetching Reddit metadata for {url}: {e}")
        return None


async def fetch_github_issue_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata for a specific GitHub issue from its URL.
    
    Args:
        url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
    
    Returns:
        Dict with metadata (comments, comments_count, etc.) or None if failed
    """
    try:
        # Extract owner, repo, and issue number from URL
        match = re.search(r'github\.com/([^/]+)/([^/]+)/issues/(\d+)', url)
        if not match:
            logger.warning(f"Could not extract GitHub issue info from URL: {url}")
            return None
        
        owner, repo, issue_num = match.groups()
        
        # Fetch issue metadata from GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # Add GitHub token if available
        import os
        github_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url, headers=headers)
            
            # Handle rate limiting
            if response.status_code == 403:
                logger.warning("GitHub API rate limit reached")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return {
                'source': 'github',
                'comments': data.get('comments', 0),
                'comments_count': data.get('comments', 0),
                'url': url
            }
        
    except Exception as e:
        logger.debug(f"Error fetching GitHub metadata for {url}: {e}")
        return None


async def fetch_stackoverflow_question_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata for a specific Stack Overflow question from its URL.
    
    Args:
        url: Stack Overflow question URL (e.g., https://stackoverflow.com/questions/123456/...)
    
    Returns:
        Dict with metadata (answer_count, is_answered, etc.) or None if failed
    """
    try:
        # Extract question ID from URL
        match = re.search(r'stackoverflow\.com/questions/(\d+)', url)
        if not match:
            logger.warning(f"Could not extract Stack Overflow question ID from URL: {url}")
            return None
        
        question_id = match.group(1)
        
        # Fetch question metadata from Stack Overflow API
        api_url = "https://api.stackexchange.com/2.3/questions/" + question_id
        params = {
            "site": "stackoverflow",
            "filter": "withbody"
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('items') and len(data['items']) > 0:
                item = data['items'][0]
                return {
                    'source': 'stackoverflow',
                    'is_answered': item.get('is_answered', False),
                    'answer_count': item.get('answer_count', 0),
                    'answers': item.get('answer_count', 0),
                    'url': url
                }
        
        return None
        
    except Exception as e:
        logger.debug(f"Error fetching Stack Overflow metadata for {url}: {e}")
        return None


async def fetch_trustpilot_review_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata for a specific Trustpilot review from its URL.
    
    Args:
        url: Trustpilot review URL
    
    Returns:
        Dict with metadata (has_company_reply, etc.) or None if failed
    """
    try:
        # Trustpilot doesn't have a public API, so we'd need to scrape HTML
        # For now, return None as this requires more complex HTML parsing
        # This could be implemented later with Selenium or similar
        
        logger.debug(f"Trustpilot metadata fetching not yet implemented for {url}")
        return None
        
    except Exception as e:
        logger.debug(f"Error fetching Trustpilot metadata for {url}: {e}")
        return None


async def fetch_post_metadata_from_url(url: str, source: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata for a post from its URL based on the source.
    
    Args:
        url: Post URL
        source: Source name (reddit, github, stackoverflow, etc.)
    
    Returns:
        Dict with metadata or None if failed
    """
    source_lower = source.lower()
    
    if 'reddit.com' in url.lower() or source_lower == 'reddit':
        return await fetch_reddit_post_metadata(url)
    elif 'github.com' in url.lower() or source_lower == 'github':
        return await fetch_github_issue_metadata(url)
    elif 'stackoverflow.com' in url.lower() or source_lower == 'stackoverflow' or source_lower == 'stack overflow':
        return await fetch_stackoverflow_question_metadata(url)
    elif 'trustpilot.com' in url.lower() or source_lower == 'trustpilot':
        return await fetch_trustpilot_review_metadata(url)
    else:
        logger.debug(f"Metadata fetching not implemented for source: {source}")
        return None

