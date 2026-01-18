"""Mastodon scraper for OVH-related posts."""
from datetime import datetime
import requests
import asyncio
import logging
import time
import re
from typing import List, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Popular Mastodon instances
MASTODON_INSTANCES = [
    "https://mastodon.social",
    "https://mastodon.online",
    "https://mstdn.social",
    "https://mastodon.world",
]


class MastodonScraper(BaseScraper):
    """Async Mastodon scraper."""
    
    def __init__(self):
        super().__init__("Mastodon")
    
    async def scrape(self, query: str = "OVH", limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape Mastodon for posts about OVH."""
        start_time = asyncio.get_event_loop().time()
        self.logger.log_scraping_start(query, limit)
        
        all_posts = []
        seen_urls = set()
        
        for instance in MASTODON_INSTANCES:
            if len(all_posts) >= limit:
                break
            
            try:
                self.logger.log("info", f"Searching {instance} for: {query}", url=instance)
                
                # Strategy 1: Search by hashtag
                hashtag = query.lower().replace(' ', '')
                tag_url = f"{instance}/api/v1/timelines/tag/{hashtag}"
                
                try:
                    response = await self._fetch_get(tag_url, params={'limit': min(limit, 40)})
                    if response.status_code == 200:
                        data = response.json()
                        for status in data:
                            if len(all_posts) >= limit:
                                break
                            
                            try:
                                post_url = status.get('url', '')
                                if post_url in seen_urls:
                                    continue
                                seen_urls.add(post_url)
                                
                                content = status.get('content', '')
                                content = re.sub(r'<[^>]+>', '', content)
                                
                                account = status.get('account', {})
                                author = account.get('acct', 'unknown')
                                display_name = account.get('display_name', '')
                                if display_name:
                                    author = f"{display_name} (@{author})"
                                else:
                                    author = f"@{author}"
                                
                                created_at = status.get('created_at', datetime.now().isoformat())
                                
                                post = {
                                    'source': 'Mastodon',
                                    'author': author,
                                    'content': content[:500],
                                    'url': post_url,
                                    'created_at': created_at,
                                    'sentiment_score': 0.0,
                                    'sentiment_label': 'neutral',
                                }
                                all_posts.append(post)
                            except Exception as e:
                                self.logger.log("warning", f"Error parsing Mastodon status: {e}")
                                continue
                except Exception as e:
                    self.logger.log("debug", f"Tag search failed for {instance}: {e}")
                
                # Strategy 2: Search API
                if len(all_posts) < limit:
                    search_url = f"{instance}/api/v2/search"
                    search_params = {
                        'q': query,
                        'type': 'statuses',
                        'limit': min(limit - len(all_posts), 40)
                    }
                    
                    try:
                        response = await self._fetch_get(search_url, params=search_params)
                        if response.status_code == 200:
                            data = response.json()
                            statuses = data.get('statuses', [])
                            
                            for status in statuses:
                                if len(all_posts) >= limit:
                                    break
                                
                                try:
                                    post_url = status.get('url', '')
                                    if post_url in seen_urls:
                                        continue
                                    seen_urls.add(post_url)
                                    
                                    content = status.get('content', '')
                                    content = re.sub(r'<[^>]+>', '', content)
                                    
                                    account = status.get('account', {})
                                    author = account.get('acct', 'unknown')
                                    display_name = account.get('display_name', '')
                                    if display_name:
                                        author = f"{display_name} (@{author})"
                                    else:
                                        author = f"@{author}"
                                    
                                    created_at = status.get('created_at', datetime.now().isoformat())
                                    
                                    post = {
                                        'source': 'Mastodon',
                                        'author': author,
                                        'content': content[:500],
                                        'url': post_url,
                                        'created_at': created_at,
                                        'sentiment_score': 0.0,
                                        'sentiment_label': 'neutral',
                                    }
                                    all_posts.append(post)
                                except Exception as e:
                                    self.logger.log("warning", f"Error parsing Mastodon search result: {e}")
                                    continue
                    except Exception as e:
                        self.logger.log("debug", f"Search API failed for {instance}: {e}")
                
                if all_posts:
                    break
            
            except Exception as e:
                self.logger.log("debug", f"Error with Mastodon {instance}: {str(e)}")
                continue
            
            await asyncio.sleep(1)  # Delay between instances
        
        duration = asyncio.get_event_loop().time() - start_time
        if all_posts:
            self.logger.log_scraping_success(len(all_posts), duration)
            return all_posts[:limit]
        else:
            self.logger.log("warning", f"No posts found for query: {query}", duration=duration)
            return []


# Global scraper instance
_async_scraper = MastodonScraper()


async def scrape_mastodon_async(query: str = "OVH", limit: int = 50) -> List[Dict[str, Any]]:
    """Async entry point for Mastodon scraper."""
    return await _async_scraper.scrape(query, limit)


def scrape_mastodon(query: str = "OVH", limit: int = 50):
    """Synchronous wrapper for async scraper (for backward compatibility)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return _scrape_mastodon_sync(query, limit)
        else:
            return loop.run_until_complete(scrape_mastodon_async(query, limit))
    except RuntimeError:
        return asyncio.run(scrape_mastodon_async(query, limit))


def _scrape_mastodon_sync(query: str = "OVH", limit: int = 50):
    """Synchronous fallback implementation."""
    """Scrape Mastodon for posts about OVH.
    
    Uses Mastodon's public API to search for hashtags and posts.
    Tries multiple instances for better coverage.
    
    Returns list of dicts: source, author, content, url, created_at
    """
    all_posts = []
    seen_urls = set()
    
    for instance in MASTODON_INSTANCES:
        if len(all_posts) >= limit:
            break
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"[Mastodon] Searching {instance} for: {query}")
                
                # Create session with retry strategy
                session = requests.Session()
                retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
                adapter = HTTPAdapter(max_retries=retry)
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                
                headers = {
                    'User-Agent': 'OVH-Tracker-Bot/1.0 (Feedback Monitor)',
                    'Accept': 'application/json'
                }
                
                # Strategy 1: Search by hashtag
                # Mastodon API v1: GET /api/v1/timelines/tag/:hashtag
                hashtag = query.lower().replace(' ', '')
                tag_url = f"{instance}/api/v1/timelines/tag/{hashtag}"
                
                try:
                    response = session.get(tag_url, headers=headers, timeout=10, params={'limit': min(limit, 40)})
                    if response.status_code == 200:
                        data = response.json()
                        for status in data:
                            try:
                                post_url = status.get('url', '')
                                if post_url in seen_urls:
                                    continue
                                seen_urls.add(post_url)
                                
                                content = status.get('content', '')
                                # Remove HTML tags
                                import re
                                content = re.sub(r'<[^>]+>', '', content)
                                
                                account = status.get('account', {})
                                author = account.get('acct', 'unknown')
                                display_name = account.get('display_name', '')
                                if display_name:
                                    author = f"{display_name} (@{author})"
                                else:
                                    author = f"@{author}"
                                
                                created_at = status.get('created_at', datetime.now().isoformat())
                                
                                post = {
                                    'source': 'Mastodon',
                                    'author': author,
                                    'content': content[:500],
                                    'url': post_url,
                                    'created_at': created_at,
                                    'sentiment_score': 0.0,
                                    'sentiment_label': 'neutral',
                                }
                                all_posts.append(post)
                                logger.info(f"✓ Mastodon: {author} - {content[:50]}")
                                
                                if len(all_posts) >= limit:
                                    break
                                    
                            except Exception as e:
                                logger.debug(f"Error parsing Mastodon status: {e}")
                                continue
                except Exception as e:
                    logger.debug(f"Tag search failed for {instance}: {e}")
                
                # Strategy 2: Search API (if available)
                if len(all_posts) < limit:
                    search_url = f"{instance}/api/v2/search"
                    search_params = {
                        'q': query,
                        'type': 'statuses',
                        'limit': min(limit - len(all_posts), 40)
                    }
                    
                    try:
                        response = session.get(search_url, headers=headers, params=search_params, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            statuses = data.get('statuses', [])
                            
                            for status in statuses:
                                try:
                                    post_url = status.get('url', '')
                                    if post_url in seen_urls:
                                        continue
                                    seen_urls.add(post_url)
                                    
                                    content = status.get('content', '')
                                    import re
                                    content = re.sub(r'<[^>]+>', '', content)
                                    
                                    account = status.get('account', {})
                                    author = account.get('acct', 'unknown')
                                    display_name = account.get('display_name', '')
                                    if display_name:
                                        author = f"{display_name} (@{author})"
                                    else:
                                        author = f"@{author}"
                                    
                                    created_at = status.get('created_at', datetime.now().isoformat())
                                    
                                post = {
                                    'source': 'Mastodon',
                                    'author': author,
                                    'content': content[:500],
                                    'url': post_url,
                                    'created_at': created_at,
                                    'sentiment_score': 0.0,
                                    'sentiment_label': 'neutral',
                                }
                                    all_posts.append(post)
                                    logger.info(f"✓ Mastodon: {author} - {content[:50]}")
                                    
                                    if len(all_posts) >= limit:
                                        break
                                        
                                except Exception as e:
                                    logger.debug(f"Error parsing Mastodon search result: {e}")
                                    continue
                    except Exception as e:
                        logger.debug(f"Search API failed for {instance}: {e}")
                
                # If we got results from this instance, break retry loop
                if all_posts:
                    break
                    
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logger.debug(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Mastodon {instance} error: {e}. Retrying...")
                    time.sleep(wait_time)
                else:
                    logger.debug(f"Mastodon {instance} failed after {MAX_RETRIES} attempts")
                    continue
            except Exception as e:
                logger.debug(f"Error with Mastodon {instance}: {str(e)}")
                continue
        
        # Small delay between instances
        if len(all_posts) < limit:
            time.sleep(1)
    
    if not all_posts:
        logger.warning(f"[Mastodon] No posts found for query: {query}")
        return []
    
    logger.info(f"[Mastodon] Successfully scraped {len(all_posts)} posts")
    return all_posts[:limit]

