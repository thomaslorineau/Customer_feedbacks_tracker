"""
Utility functions to fetch post metadata from URLs for re-checking answered status.
"""
import re
import logging
import httpx
import asyncio
import random
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# List of realistic User-Agents to rotate
REDDIT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]


def get_random_user_agent() -> str:
    """Get a random User-Agent from the list."""
    return random.choice(REDDIT_USER_AGENTS)


def get_random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> float:
    """Get a random delay between min and max seconds."""
    return random.uniform(min_seconds, max_seconds)


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
        
        # Use random User-Agent and headers to avoid detection
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'application/json',
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'fr-FR,fr;q=0.9', 'en-GB,en;q=0.9']),
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.reddit.com/',
            'Origin': 'https://www.reddit.com',
        }
        
        # Add random delay before request to avoid pattern detection (1.5-3.5 seconds)
        delay = get_random_delay(1.5, 3.5)
        await asyncio.sleep(delay)
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(json_url, headers=headers)
            
            # Handle 403 errors gracefully
            # Reddit blocks requests for several reasons:
            # 1. Rate limiting: Too many requests from same IP
            # 2. Missing/incorrect User-Agent: Reddit requires descriptive User-Agent
            # 3. Anti-bot detection: Reddit uses Cloudflare and other measures
            # 4. No API authentication: Using public endpoints without OAuth
            # 5. Suspicious patterns: Requests too fast or too regular
            if response.status_code == 403:
                logger.debug(f"Reddit API blocked request for {url} (403). Possible reasons: rate limiting, anti-bot measures, or missing authentication.")
                return None
            
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

