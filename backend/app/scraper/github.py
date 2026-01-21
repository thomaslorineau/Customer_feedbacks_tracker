"""GitHub Issues and Discussions scraper for OVH complaints."""
import httpx
import asyncio
from datetime import datetime, timedelta
import logging
import time
from typing import List, Dict, Any
from httpx import Timeout
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class GitHubScraper(BaseScraper):
    """Async GitHub scraper."""
    
    def __init__(self):
        super().__init__("GitHub")
    
    async def scrape(self, query: str = "OVH", limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape GitHub issues AND discussions for OVH domain customer complaints."""
        import time
        start_time = time.time()  # Use time.time() instead of asyncio.get_event_loop().time()
        self.logger.log_scraping_start(query, limit)
        
        try:
            all_posts = []
            
            # 1. Search Issues
            issues = await self._search_issues(query, limit // 2)
            all_posts.extend(issues)
            
            # 2. Search Discussions
            discussions = await self._search_discussions(query, limit // 2)
            all_posts.extend(discussions)
            
            if all_posts:
                duration = time.time() - start_time
                self.logger.log_scraping_success(len(all_posts), duration)
                return all_posts[:limit]
            
            # Fallback to Google Search
            try:
                from .google_search_fallback import search_via_google
                self.logger.log("info", "Trying Google Search fallback")
                all_posts = await search_via_google("site:github.com", query, limit)
                if all_posts:
                    duration = time.time() - start_time
                    self.logger.log_scraping_success(len(all_posts), duration)
                    return all_posts[:limit]
            except Exception as e:
                self.logger.log("warning", f"Google Search fallback failed: {e}")
            
            # Fallback to RSS Detector
            try:
                from .rss_detector import detect_and_parse_feeds
                self.logger.log("info", "Trying RSS detector fallback")
                all_posts = await detect_and_parse_feeds("https://github.com", limit)
                if all_posts:
                    duration = time.time() - start_time
                    self.logger.log_scraping_success(len(all_posts), duration)
                    return all_posts[:limit]
            except Exception as e:
                self.logger.log("warning", f"RSS detector fallback failed: {e}")
            
            self.logger.log("warning", f"No GitHub issues or discussions found for: {query}")
            duration = time.time() - start_time
            return []
        
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_scraping_error(e, duration)
            return []
    
    async def _search_issues(self, query: str, limit: int) -> List[Dict[str, Any]]:
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
                    "page": page,
                }
                
                self.logger.log("info", f"Searching issues page {page}", details={'query': search_query})
                
                try:
                    response = await self._fetch_get(
                        f"{GITHUB_API_BASE}/search/issues",
                        headers=GITHUB_HEADERS,
                        params=params
                    )
                    
                    # Check for rate limiting
                    if response.status_code == 403:
                        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
                        self.logger.log("warning", f"Rate limit hit! Remaining: {rate_limit_remaining}")
                        if page == 1:
                            return []
                        break
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    items = data.get("items", [])
                    if len(items) == 0:
                        break
                    
                    total_count = data.get("total_count", 0)
                    if page == 1:
                        self.logger.log("info", f"API returned {total_count} total results, {len(items)} items in first page")
                    
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
                        except Exception as e:
                            self.logger.log("warning", f"Could not parse GitHub issue: {e}")
                            continue
                    
                    page += 1
                    if len(all_posts) < limit:
                        await asyncio.sleep(0.5)  # Respect rate limits
                
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 403:
                        self.logger.log("error", "Rate limit exceeded. Consider using a GitHub token.")
                    break
                except Exception as e:
                    self.logger.log("warning", f"Error searching GitHub issues: {type(e).__name__}: {e}")
                    break
            
            self.logger.log("success", f"Successfully parsed {len(all_posts)} issues from {page - 1} page(s)")
            return all_posts
        
        except Exception as e:
            self.logger.log("error", f"Error in _search_issues: {e}")
            return []
    
    async def _search_discussions(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search GitHub discussions using GitHub's search API with pagination."""
        try:
            all_posts = []
            page = 1
            per_page = min(100, limit)
            
            while len(all_posts) < limit:
                search_query = f"{query} is:discussion"
                params = {
                    "q": search_query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                }
                
                self.logger.log("info", f"Searching discussions page {page}", details={'query': search_query})
                
                try:
                    response = await self._fetch_get(
                        f"{GITHUB_API_BASE}/search/issues",  # Discussions are searchable via /search/issues
                        headers=GITHUB_HEADERS,
                        params=params
                    )
                    
                    if response.status_code == 403:
                        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
                        self.logger.log("warning", f"Rate limit hit! Remaining: {rate_limit_remaining}")
                        if page == 1:
                            return []
                        break
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    items = data.get("items", [])
                    if len(items) == 0:
                        break
                    
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
                        except Exception as e:
                            self.logger.log("warning", f"Could not parse GitHub discussion: {e}")
                            continue
                    
                    page += 1
                    if len(all_posts) < limit:
                        await asyncio.sleep(0.5)
                
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 403:
                        self.logger.log("error", "Rate limit exceeded. Consider using a GitHub token.")
                    break
                except Exception as e:
                    self.logger.log("warning", f"Error searching GitHub discussions: {type(e).__name__}: {e}")
                    break
            
            self.logger.log("success", f"Successfully parsed {len(all_posts)} discussions from {page - 1} page(s)")
            return all_posts
        
        except Exception as e:
            self.logger.log("error", f"Error in _search_discussions: {e}")
            return []


# Global scraper instance
_async_scraper = GitHubScraper()


async def scrape_github_issues_async(query: str = "OVH", limit: int = 20) -> List[Dict[str, Any]]:
    """Async entry point for GitHub scraper."""
    return await _async_scraper.scrape(query, limit)


def scrape_github_issues(query="OVH", limit=20):
    """
    Synchronous wrapper for async scraper (for backward compatibility).
    
    Scrape GitHub issues AND discussions for OVH domain customer complaints and feedback.
    Returns a list of issue/discussion dictionaries ready for insertion.
    """
    try:
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in a running loop, use sync fallback
            return _scrape_github_sync(query, limit)
        except RuntimeError:
            # No running loop, try to get or create one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    # Loop is closed, create new one
                    return asyncio.run(scrape_github_issues_async(query, limit))
                elif loop.is_running():
                    # Loop is running, use sync fallback
                    return _scrape_github_sync(query, limit)
                else:
                    # Loop exists but not running, use it
                    return loop.run_until_complete(scrape_github_issues_async(query, limit))
            except RuntimeError:
                # No event loop available, create new one
                return asyncio.run(scrape_github_issues_async(query, limit))
    except Exception as e:
        logger.warning(f"[GitHub] Error in sync wrapper: {e}, using sync fallback")
        return _scrape_github_sync(query, limit)


def _scrape_github_sync(query="OVH", limit=20):
    """Synchronous fallback implementation."""
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
