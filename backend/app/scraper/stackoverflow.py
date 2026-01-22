"""Stack Overflow API scraper for OVH-related questions."""
import httpx
import asyncio
from datetime import datetime
import logging
import time
from typing import List, Dict, Any
from httpx import Timeout
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

STACKOVERFLOW_API = "https://api.stackexchange.com/2.3"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class StackOverflowScraper(BaseScraper):
    """Async Stack Overflow scraper."""
    
    def __init__(self):
        super().__init__("Stack Overflow")
    
    async def scrape(self, query: str = "OVH", limit: int = 30) -> List[Dict[str, Any]]:
        """Scrape Stack Overflow for questions about OVH."""
        try:
            loop = asyncio.get_running_loop()
            start_time = loop.time()
        except RuntimeError:
            import time
            start_time = time.time()
        self.logger.log_scraping_start(query, limit)
        
        try:
            all_posts = []
            page = 1
            max_pages = (limit // 30) + 1
            pagesize = min(30, limit)
            
            # Ensure query contains OVH-related terms for better relevance
            search_query = query
            query_lower = query.lower()
            if 'ovh' not in query_lower and 'ovhcloud' not in query_lower:
                # If base keywords don't include OVH, add it to ensure relevance
                search_query = f"OVH {query}"
            
            while len(all_posts) < limit and page <= max_pages:
                # Use 'q' parameter to search in both title AND body for better relevance
                # Stack Overflow API: 'q' searches in title and body, 'intitle' only searches in title
                params = {
                    "site": "stackoverflow",
                    "q": search_query,  # Search in title AND body for better relevance
                    "sort": "relevance",  # Sort by relevance instead of creation date
                    "order": "desc",
                    "pagesize": pagesize,
                    "page": page,
                    "filter": "withbody",
                }
                
                self.logger.log("info", f"Fetching page {page}", details={'query': search_query})
                
                try:
                    response = await self._fetch_get(
                        f"{STACKOVERFLOW_API}/search/advanced",
                        headers=DEFAULT_HEADERS,
                        params=params
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if not data.get("items"):
                        if page == 1:
                            self.logger.log("warning", f"No questions found for query: {query}")
                        break
                    
                    for item in data["items"]:
                        if len(all_posts) >= limit:
                            break
                        try:
                            post = {
                                "source": "Stack Overflow",
                                "author": item.get("owner", {}).get("display_name", "Anonymous"),
                                "content": (item.get("title", "") + "\n" + (item.get("body", "") or ""))[:500],
                                "url": item.get("link", ""),
                                "created_at": datetime.fromtimestamp(item.get("creation_date", 0)).isoformat() if item.get("creation_date") else datetime.now().isoformat(),
                                "sentiment_score": 0.0,
                                "sentiment_label": "neutral",
                            }
                            all_posts.append(post)
                        except Exception as e:
                            self.logger.log("warning", f"Could not parse SO question: {e}")
                            continue
                    
                    if not data.get("has_more", False):
                        break
                    
                    page += 1
                    if len(all_posts) < limit:
                        await asyncio.sleep(1)  # Respect rate limits
                
                except Exception as e:
                    self.logger.log("error", f"Error fetching page {page}: {e}")
                    break
            
            try:
                loop = asyncio.get_running_loop()
                duration = loop.time() - start_time
            except RuntimeError:
                import time
                duration = time.time() - start_time
            
            if all_posts:
                self.logger.log_scraping_success(len(all_posts), duration)
                return all_posts[:limit]
            
            # Fallback to Google Search
            try:
                from .google_search_fallback import search_via_google
                self.logger.log("info", "Trying Google Search fallback")
                all_posts = await search_via_google("site:stackoverflow.com", query, limit)
                if all_posts:
                    duration = loop.time() - start_time if 'loop' in locals() else time.time() - start_time
                    self.logger.log_scraping_success(len(all_posts), duration)
                    return all_posts[:limit]
            except Exception as e:
                self.logger.log("warning", f"Google Search fallback failed: {e}")
            
            # Fallback to RSS Detector
            try:
                from .rss_detector import detect_and_parse_feeds
                self.logger.log("info", "Trying RSS detector fallback")
                all_posts = await detect_and_parse_feeds("https://stackoverflow.com", limit)
                if all_posts:
                    duration = loop.time() - start_time if 'loop' in locals() else time.time() - start_time
                    self.logger.log_scraping_success(len(all_posts), duration)
                    return all_posts[:limit]
            except Exception as e:
                self.logger.log("warning", f"RSS detector fallback failed: {e}")
            
            self.logger.log("warning", "No valid questions could be parsed", duration=duration)
            return []
        
        except Exception as e:
            try:
                loop = asyncio.get_running_loop()
                duration = loop.time() - start_time
            except RuntimeError:
                import time
                duration = time.time() - start_time
            self.logger.log_scraping_error(e, duration)
            return []


# Global scraper instance
_async_scraper = StackOverflowScraper()


async def scrape_stackoverflow_async(query: str = "OVH", limit: int = 30) -> List[Dict[str, Any]]:
    """Async entry point for Stack Overflow scraper."""
    return await _async_scraper.scrape(query, limit)


def scrape_stackoverflow(query="OVH", limit=30):
    """Synchronous wrapper for async scraper (for backward compatibility)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return _scrape_stackoverflow_sync(query, limit)
        else:
            return loop.run_until_complete(scrape_stackoverflow_async(query, limit))
    except RuntimeError:
        return asyncio.run(scrape_stackoverflow_async(query, limit))


def _scrape_stackoverflow_sync(query="OVH", limit=30):
    """Synchronous fallback implementation."""
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            all_posts = []
            page = 1
            max_pages = (limit // 30) + 1
            pagesize = min(30, limit)
            
            while len(all_posts) < limit and page <= max_pages:
                params = {
                    "site": "stackoverflow",
                    "intitle": query,
                    "sort": "creation",
                    "order": "desc",
                    "pagesize": pagesize,
                    "page": page,
                    "filter": "withbody",
                }
                
                logger.info(f"[STACKOVERFLOW] Fetching page {page} for query: {query}")
                
                response = httpx.get(
                    f"{STACKOVERFLOW_API}/search/advanced",
                    params=params,
                    headers=DEFAULT_HEADERS,
                    timeout=Timeout(15.0, connect=5.0)
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("items"):
                    if page == 1:
                        logger.warning(f"[STACKOVERFLOW] No questions found for query: {query}")
                    break
                
                for item in data["items"]:
                    if len(all_posts) >= limit:
                        break
                    try:
                        post = {
                            "source": "Stack Overflow",
                            "author": item.get("owner", {}).get("display_name", "Anonymous"),
                            "content": (item.get("title", "") + "\n" + (item.get("body", "") or ""))[:500],
                            "url": item.get("link", ""),
                            "created_at": datetime.fromtimestamp(item.get("creation_date", 0)).isoformat() if item.get("creation_date") else datetime.now().isoformat(),
                            "sentiment_score": 0.0,
                            "sentiment_label": "neutral",
                        }
                        all_posts.append(post)
                    except Exception as e:
                        logger.warning(f"Could not parse SO question: {e}")
                        continue
                
                if not data.get("has_more", False):
                    break
                
                page += 1
                if len(all_posts) < limit:
                    time.sleep(1)
            
            if not all_posts:
                logger.warning("[STACKOVERFLOW] No valid questions could be parsed from API response")
                return []
            
            logger.info(f"[STACKOVERFLOW] Successfully scraped {len(all_posts)} questions from {page - 1} page(s)")
            return all_posts
        
        except (httpx.TimeoutError, httpx.ConnectError, httpx.NetworkError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Stack Overflow network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Stack Overflow scraper failed after {MAX_RETRIES} attempts: {e}")
                return []
        except Exception as e:
            logger.error(f"Error scraping Stack Overflow: {str(e)}")
            last_error = e
            return []
    
    logger.error(f"Stack Overflow scraper failed after {MAX_RETRIES} attempts: {last_error}")
    return []
