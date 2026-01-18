"""LinkedIn scraper for OVH-related posts (requires user's API credentials)."""
import httpx
import asyncio
from datetime import datetime
import logging
import time
from typing import Optional, List, Dict, Any
from httpx import Timeout
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


class LinkedInScraper(BaseScraper):
    """Async LinkedIn scraper."""
    
    def __init__(self):
        super().__init__("LinkedIn")
    
    async def scrape(self, query: str = "OVH", limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape LinkedIn for posts about OVH."""
        start_time = asyncio.get_event_loop().time()
        self.logger.log_scraping_start(query, limit)
        
        from ..config import config
        
        client_id = config.get_api_key("linkedin_client_id")
        client_secret = config.get_api_key("linkedin_client_secret")
        
        if not client_id or not client_secret:
            self.logger.log("info", "API credentials not configured. User can add them in Settings.")
            return []
        
        try:
            # 1. Obtain access token
            access_token = await self._get_access_token(client_id, client_secret)
            if not access_token:
                self.logger.log("warning", "Failed to obtain access token")
                return []
            
            # 2. Search for posts
            posts = await self._search_posts(access_token, query, limit)
            
            duration = asyncio.get_event_loop().time() - start_time
            if posts:
                self.logger.log_scraping_success(len(posts), duration)
            else:
                self.logger.log("warning", "No posts found", duration=duration)
            return posts
        
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            self.logger.log_scraping_error(e, duration)
            return []
    
    async def _get_access_token(self, client_id: str, client_secret: str) -> Optional[str]:
        """Obtain LinkedIn OAuth2 access token."""
        params = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        
        self.logger.log("info", "Requesting access token", url=LINKEDIN_TOKEN_URL)
        
        try:
            response = await self._fetch_post(
                LINKEDIN_TOKEN_URL,
                data=params,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                self.logger.log("warning", f"Token request failed: {response.status_code}")
                return None
            
            data = response.json()
            access_token = data.get("access_token")
            
            if access_token:
                self.logger.log("success", "Successfully obtained access token")
                return access_token
            else:
                self.logger.log("warning", f"No access token in response: {data}")
                return None
        
        except Exception as e:
            self.logger.log("error", f"Error obtaining token: {type(e).__name__}: {e}")
            return None
    
    async def _search_posts(self, access_token: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search LinkedIn posts using API v2."""
        posts = []
        
        search_url = f"{LINKEDIN_API_BASE}/search"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        params = {
            "keywords": query,
            "count": min(100, limit),
        }
        
        self.logger.log("info", f"Searching for: {query}", url=search_url)
        
        try:
            response = await self._fetch_get(search_url, headers=headers, params=params)
            
            if response.status_code == 401:
                self.logger.log("warning", "Authentication failed. Token may be expired or invalid.")
                return []
            elif response.status_code == 403:
                self.logger.log("warning", "Access forbidden. Check API permissions in LinkedIn Developer Portal.")
                return []
            elif response.status_code != 200:
                self.logger.log("warning", f"API error: {response.status_code}")
                return []
            
            data = response.json()
            elements = data.get("elements", [])
            
            for element in elements[:limit]:
                try:
                    content = ""
                    author = "Unknown"
                    url = ""
                    created_at = datetime.now().isoformat()
                    
                    if "text" in element:
                        content = element["text"]
                    elif "commentary" in element:
                        content = element["commentary"]
                    elif "summary" in element:
                        content = element["summary"]
                    
                    if "author" in element:
                        author_data = element["author"]
                        if isinstance(author_data, dict):
                            author = author_data.get("name", author_data.get("displayName", "Unknown"))
                        elif isinstance(author_data, str):
                            author = author_data
                    
                    if "url" in element:
                        url = element["url"]
                    elif "permalink" in element:
                        url = element["permalink"]
                    elif "webUrl" in element:
                        url = element["webUrl"]
                    
                    if "created" in element:
                        created_data = element["created"]
                        if isinstance(created_data, dict) and "time" in created_data:
                            created_at = created_data["time"]
                        elif isinstance(created_data, (int, float)):
                            created_at = datetime.fromtimestamp(created_data).isoformat()
                    
                    if not content:
                        continue
                    
                    post = {
                        "source": "LinkedIn",
                        "author": author,
                        "content": content[:500],
                        "url": url or f"https://www.linkedin.com/feed/",
                        "created_at": created_at,
                        "sentiment_score": 0.0,
                        "sentiment_label": "neutral",
                    }
                    posts.append(post)
                
                except Exception as e:
                    self.logger.log("warning", f"Could not parse LinkedIn post: {e}")
                    continue
            
            if not posts:
                self.logger.log("info", "No posts found via search API. LinkedIn API v2 has limited search capabilities.")
        
        except Exception as e:
            self.logger.log("error", f"Search failed: {type(e).__name__}: {e}")
        
        return posts


# Global scraper instance
_async_scraper = LinkedInScraper()


async def scrape_linkedin_async(query: str = "OVH", limit: int = 50) -> List[Dict[str, Any]]:
    """Async entry point for LinkedIn scraper."""
    return await _async_scraper.scrape(query, limit)


def scrape_linkedin(query: str = "OVH", limit: int = 50) -> List[dict]:
    """Synchronous wrapper for async scraper (for backward compatibility)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return _scrape_linkedin_sync(query, limit)
        else:
            return loop.run_until_complete(scrape_linkedin_async(query, limit))
    except RuntimeError:
        return asyncio.run(scrape_linkedin_async(query, limit))


def _scrape_linkedin_sync(query: str = "OVH", limit: int = 50) -> List[dict]:
    """
    Synchronous fallback implementation.
    
    Scrape LinkedIn for posts about OVH.
    
    REQUIRES: User must provide their own LinkedIn API credentials in .env:
    - LINKEDIN_CLIENT_ID
    - LINKEDIN_CLIENT_SECRET
    
    Returns list of dicts: source, author, content, url, created_at
    If credentials are not configured, returns empty list (no error).
    """
    from ..config import config
    
    client_id = config.get_api_key("linkedin_client_id")
    client_secret = config.get_api_key("linkedin_client_secret")
    
    if not client_id or not client_secret:
        logger.info("[LinkedIn] API credentials not configured. User can add them in Settings.")
        logger.info("[LinkedIn] Get credentials from: https://www.linkedin.com/developers/apps")
        return []  # Return empty if no credentials (not an error)
    
    try:
        # 1. Obtain access token
        access_token = _get_linkedin_access_token(client_id, client_secret)
        if not access_token:
            logger.warning("[LinkedIn] Failed to obtain access token")
            return []
        
        # 2. Search for posts
        posts = _search_linkedin_posts(access_token, query, limit)
        
        logger.info(f"[LinkedIn] Successfully scraped {len(posts)} posts")
        return posts
        
    except Exception as e:
        logger.error(f"[LinkedIn] Error scraping: {type(e).__name__}: {e}")
        return []


def _get_linkedin_access_token(client_id: str, client_secret: str) -> Optional[str]:
    """
    Obtain LinkedIn OAuth2 access token using client credentials flow.
    
    Note: LinkedIn API v2 requires specific permissions and may need
    additional setup in the LinkedIn Developer Portal.
    """
    try:
        params = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        
        logger.info("[LinkedIn] Requesting access token...")
        response = httpx.post(
            LINKEDIN_TOKEN_URL,
            params=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=Timeout(10.0, connect=5.0)
        )
        
        if response.status_code != 200:
            logger.warning(f"[LinkedIn] Token request failed: {response.status_code} - {response.text[:200]}")
            return None
        
        data = response.json()
        access_token = data.get("access_token")
        
        if access_token:
            logger.info("[LinkedIn] Successfully obtained access token")
            return access_token
        else:
            logger.warning(f"[LinkedIn] No access token in response: {data}")
            return None
        
    except httpx.HTTPStatusError as e:
        logger.error(f"[LinkedIn] HTTP error obtaining token: {e.response.status_code}")
        if e.response.status_code == 401:
            logger.error("[LinkedIn] Authentication failed. Check your CLIENT_ID and CLIENT_SECRET.")
        return None
    except Exception as e:
        logger.error(f"[LinkedIn] Error obtaining token: {type(e).__name__}: {e}")
        return None


def _search_linkedin_posts(access_token: str, query: str, limit: int) -> List[dict]:
    """
    Search LinkedIn posts using API v2.
    
    Note: LinkedIn API v2 has limited search capabilities for posts.
    This implementation uses available endpoints.
    """
    posts = []
    
    try:
        # LinkedIn API v2 search endpoint
        # Note: LinkedIn's search API for posts is limited and may require
        # specific permissions. This is a basic implementation.
        search_url = f"{LINKEDIN_API_BASE}/search"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        # LinkedIn search parameters
        # Note: Actual search capabilities depend on API permissions
        params = {
            "keywords": query,
            "count": min(100, limit),
        }
        
        logger.info(f"[LinkedIn] Searching for: {query}")
        
        response = httpx.get(
            search_url,
            headers=headers,
            params=params,
            timeout=Timeout(15.0, connect=5.0)
        )
        
        if response.status_code == 401:
            logger.warning("[LinkedIn] Authentication failed. Token may be expired or invalid.")
            return []
        elif response.status_code == 403:
            logger.warning("[LinkedIn] Access forbidden. Check API permissions in LinkedIn Developer Portal.")
            return []
        elif response.status_code != 200:
            logger.warning(f"[LinkedIn] API error: {response.status_code} - {response.text[:200]}")
            return []
        
        data = response.json()
        
        # Parse results based on LinkedIn API response structure
        # Note: Structure may vary depending on API version and permissions
        elements = data.get("elements", [])
        
        for element in elements[:limit]:
            try:
                # Extract post information
                # LinkedIn API structure varies, so we handle multiple formats
                content = ""
                author = "Unknown"
                url = ""
                created_at = datetime.now().isoformat()
                
                # Try to extract content from various possible fields
                if "text" in element:
                    content = element["text"]
                elif "commentary" in element:
                    content = element["commentary"]
                elif "summary" in element:
                    content = element["summary"]
                
                # Extract author
                if "author" in element:
                    author_data = element["author"]
                    if isinstance(author_data, dict):
                        author = author_data.get("name", author_data.get("displayName", "Unknown"))
                    elif isinstance(author_data, str):
                        author = author_data
                
                # Extract URL
                if "url" in element:
                    url = element["url"]
                elif "permalink" in element:
                    url = element["permalink"]
                elif "webUrl" in element:
                    url = element["webUrl"]
                
                # Extract date
                if "created" in element:
                    created_data = element["created"]
                    if isinstance(created_data, dict) and "time" in created_data:
                        created_at = created_data["time"]
                    elif isinstance(created_data, (int, float)):
                        created_at = datetime.fromtimestamp(created_data).isoformat()
                
                if not content:
                    continue  # Skip posts without content
                
                post = {
                    "source": "LinkedIn",
                    "author": author,
                    "content": content[:500],
                    "url": url or f"https://www.linkedin.com/feed/",
                    "created_at": created_at,
                    "sentiment_score": 0.0,
                    "sentiment_label": "neutral",
                }
                posts.append(post)
                logger.debug(f"✓ LinkedIn: {author} - {content[:50]}")
                
            except Exception as e:
                logger.warning(f"Could not parse LinkedIn post: {e}")
                continue
        
        # If no posts found via search API, try alternative approach
        # LinkedIn's API has limitations, so we log this for user awareness
        if not posts:
            logger.info("[LinkedIn] No posts found via search API. LinkedIn API v2 has limited search capabilities.")
            logger.info("[LinkedIn] Consider using LinkedIn's Marketing API or other endpoints for better results.")
        
    except httpx.HTTPStatusError as e:
        logger.error(f"[LinkedIn] HTTP error: {e.response.status_code}")
        if e.response.status_code == 401:
            logger.error("[LinkedIn] Authentication failed. Check your API credentials.")
        elif e.response.status_code == 403:
            logger.error("[LinkedIn] Access forbidden. Check API permissions in LinkedIn Developer Portal.")
    except Exception as e:
        logger.error(f"[LinkedIn] Search failed: {type(e).__name__}: {e}")
    
    return posts



