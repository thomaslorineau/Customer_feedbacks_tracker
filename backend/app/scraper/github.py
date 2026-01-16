"""GitHub Issues and Discussions scraper for OVH complaints."""
import httpx
from datetime import datetime, timedelta
import logging
import time
from httpx import Timeout

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def scrape_github_issues(query="OVH", limit=20):
    """
    Scrape GitHub issues AND discussions for OVH domain customer complaints and feedback.
    Returns a list of issue/discussion dictionaries ready for insertion.
    """
    all_posts = []
    
    try:
        # 1. Search Issues
        logger.info(f"[GitHub] Searching issues for: {query}")
        issues = _search_github_issues(query, limit // 2)
        all_posts.extend(issues)
        
        # 2. Search Discussions
        logger.info(f"[GitHub] Searching discussions for: {query}")
        discussions = _search_github_discussions(query, limit // 2)
        all_posts.extend(discussions)
        
        if not all_posts:
            logger.warning(f"No GitHub issues or discussions found for: {query}")
            return []
        
        logger.info(f"[GitHub] Found {len(all_posts)} items ({len(issues)} issues + {len(discussions)} discussions)")
        return all_posts[:limit]
    
    except Exception as e:
        logger.error(f"Error scraping GitHub: {str(e)}")
        return []


def _search_github_issues(query: str, limit: int) -> list:
    """Search GitHub issues with pagination."""
    try:
        all_posts = []
        page = 1
        per_page = min(100, limit)
        
        while len(all_posts) < limit:
            search_query = f"{query} is:issue"
            params = {
                "q": search_query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
                "page": page,  # Pagination parameter
            }
            
            logger.info(f"[GitHub Issues] Searching page {page} with query: {search_query}")
            response = httpx.get(
                f"{GITHUB_API_BASE}/search/issues",
                params=params,
                headers=GITHUB_HEADERS,
                timeout=Timeout(10.0, connect=5.0)
            )
            
            logger.info(f"[GitHub Issues] Response status: {response.status_code}")
            
            # Check for rate limiting
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
                logger.warning(f"[GitHub Issues] Rate limit hit! Remaining: {rate_limit_remaining}")
                logger.warning("[GitHub Issues] Consider using a GitHub token to increase rate limits")
                if page == 1:
                    return []  # No results at all
                break  # Return what we have so far
            
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            if len(items) == 0:
                logger.info(f"[GitHub Issues] No more results on page {page}")
                break  # No more results
            
            total_count = data.get("total_count", 0)
            if page == 1:
                logger.info(f"[GitHub Issues] API returned {total_count} total results, {len(items)} items in first page")
            
            for issue in items:
                if len(all_posts) >= limit:
                    break
                try:
                    post = {
                        "source": "GitHub",
                        "author": issue["user"]["login"],
                        "content": (issue["title"] + "\n" + (issue["body"] or ""))[:500],
                        "url": issue["html_url"],
                        "created_at": issue["created_at"],
                        "sentiment_score": 0.0,
                        "sentiment_label": "neutral",
                    }
                    all_posts.append(post)
                    logger.debug(f"✓ GitHub issue: {issue['title'][:50]}")
                except Exception as e:
                    logger.warning(f"Could not parse GitHub issue: {e}")
                    continue
            
            page += 1
            # Respect rate limits: 60 req/h without token, 5000 with token
            # Use 0.5s delay between pages to be safe
            if len(all_posts) < limit:
                time.sleep(0.5)
        
        logger.info(f"[GitHub Issues] Successfully parsed {len(all_posts)} issues from {page - 1} page(s)")
        return all_posts
    except httpx.HTTPStatusError as e:
        logger.error(f"[GitHub Issues] HTTP error: {e.response.status_code} - {e}")
        if e.response.status_code == 403:
            logger.error("[GitHub Issues] Rate limit exceeded. Consider using a GitHub token.")
        return []
    except Exception as e:
        logger.warning(f"Error searching GitHub issues: {type(e).__name__}: {e}")
        return []


def _search_github_discussions(query: str, limit: int) -> list:
    """Search GitHub discussions using GitHub's search API with pagination."""
    try:
        all_posts = []
        page = 1
        per_page = min(100, limit)
        
        while len(all_posts) < limit:
            # GitHub search supports discussions via is:discussion
            search_query = f"{query} is:discussion"
            params = {
                "q": search_query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
                "page": page,  # Pagination parameter
            }
            
            logger.info(f"[GitHub Discussions] Searching page {page} with query: {search_query}")
            response = httpx.get(
                f"{GITHUB_API_BASE}/search/issues",  # Yes, discussions are searchable via /search/issues
                params=params,
                headers=GITHUB_HEADERS,
                timeout=Timeout(10.0, connect=5.0)
            )
            
            logger.info(f"[GitHub Discussions] Response status: {response.status_code}")
            
            # Check for rate limiting
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
                logger.warning(f"[GitHub Discussions] Rate limit hit! Remaining: {rate_limit_remaining}")
                if page == 1:
                    return []  # No results at all
                break  # Return what we have so far
            
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            if len(items) == 0:
                logger.info(f"[GitHub Discussions] No more results on page {page}")
                break  # No more results
            
            total_count = data.get("total_count", 0)
            if page == 1:
                logger.info(f"[GitHub Discussions] API returned {total_count} total results, {len(items)} items in first page")
            
            for discussion in items:
                if len(all_posts) >= limit:
                    break
                try:
                    post = {
                        "source": "GitHub",
                        "author": discussion["user"]["login"],
                        "content": (discussion["title"] + "\n" + (discussion["body"] or ""))[:500],
                        "url": discussion["html_url"],
                        "created_at": discussion["created_at"],
                        "sentiment_score": 0.0,
                        "sentiment_label": "neutral",
                    }
                    all_posts.append(post)
                    logger.debug(f"✓ GitHub discussion: {discussion['title'][:50]}")
                except Exception as e:
                    logger.warning(f"Could not parse GitHub discussion: {e}")
                    continue
            
            page += 1
            # Respect rate limits: 60 req/h without token, 5000 with token
            # Use 0.5s delay between pages to be safe
            if len(all_posts) < limit:
                time.sleep(0.5)
        
        logger.info(f"[GitHub Discussions] Successfully parsed {len(all_posts)} discussions from {page - 1} page(s)")
        return all_posts
    except httpx.HTTPStatusError as e:
        logger.error(f"[GitHub Discussions] HTTP error: {e.response.status_code} - {e}")
        if e.response.status_code == 403:
            logger.error("[GitHub Discussions] Rate limit exceeded. Consider using a GitHub token.")
        return []
    except Exception as e:
        logger.warning(f"Error searching GitHub discussions: {type(e).__name__}: {e}")
        return []


def get_mock_github_issues(limit=20):
    """Return empty list - no mock data."""
    return []
