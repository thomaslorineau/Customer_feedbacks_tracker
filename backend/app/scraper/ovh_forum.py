"""OVH Community Forum scraper for customer feedback."""
from datetime import datetime
import requests
import logging
import time
import re
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .anti_bot_helpers import (
    get_realistic_headers, human_like_delay, 
    create_stealth_session, simulate_human_behavior
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# OVH Community Forum base URL (nouveau domaine)
OVH_FORUM_BASE = "https://community.ovhcloud.com/community"


def scrape_ovh_forum(query: str = "OVH", limit: int = 50, languages: list = None):
    """Scrape OVH Community Forum for customer feedback and discussions.
    
    Searches the OVH community forum for posts related to the query.
    Uses HTML scraping as the forum doesn't have a public API.
    
    Args:
        query: Search query
        limit: Maximum number of posts to scrape
        languages: List of language codes to scrape (e.g., ['en', 'fr']). 
                   Defaults to ['en', 'fr'] to scrape both English and French forums.
    
    Returns list of dicts: source, author, content, url, created_at
    """
    try:
        if languages is None:
            languages = ['en', 'fr']  # Par défaut, scraper les deux langues
        
        all_posts = []
        posts_per_language = max(limit // len(languages), 10) if languages else limit
        
        for language in languages:
            if len(all_posts) >= limit:
                break
            try:
                posts = _scrape_ovh_forum_single_language(query, posts_per_language, language)
                all_posts.extend(posts)
            except Exception as lang_error:
                logger.warning(f"[OVH Forum] Error scraping language {language}: {lang_error}")
                continue
        
        return all_posts[:limit]
    except Exception as e:
        logger.error(f"[OVH Forum] Error in scrape_ovh_forum: {e}", exc_info=True)
        return []  # Return empty list instead of crashing


def _scrape_ovh_forum_single_language(query: str = "OVH", limit: int = 50, language: str = "en"):
    """Scrape OVH Community Forum for a single language.
    
    Args:
        query: Search query
        limit: Maximum number of posts to scrape
        language: Language code ('en', 'fr', etc.)
    
    Returns list of dicts: source, author, content, url, created_at
    """
    try:
        import signal
        
        # Set a global timeout to prevent infinite loops (60 seconds max)
        start_time = time.time()
        MAX_TOTAL_TIME = 60
        
        for attempt in range(MAX_RETRIES):
            # Check if we've exceeded total time limit
            if time.time() - start_time > MAX_TOTAL_TIME:
                logger.warning(f"[OVH Forum] Exceeded maximum time limit ({MAX_TOTAL_TIME}s)")
                return []
            try:
                # OVH Forum - Try multiple strategies
                # Strategy 1: Try main forum page with language (more reliable than search)
                main_url = f"{OVH_FORUM_BASE}/{language}/"
                
                logger.info(f"[OVH Forum] Attempt {attempt + 1}/{MAX_RETRIES} - Searching for: {query} (language: {language})")
                
                # Create stealth session with realistic headers
                session = create_stealth_session()
                
                # Get realistic headers with referer
                headers = get_realistic_headers(referer=OVH_FORUM_BASE)
                
                # Simulate human behavior: visit main page first (but skip if same URL)
                # This is optional and can be disabled if causing issues
                # simulate_human_behavior(session, main_url)
                
                # Try main forum page first (more stable)
                soup = None
                response = None
                try:
                    response = session.get(main_url, headers=headers, timeout=10)  # Reduced timeout
                    response.raise_for_status()
                    # Small delay after first request
                    time.sleep(0.3)  # Reduced delay
                    # Parse HTML
                    soup = BeautifulSoup(response.content, 'html.parser')
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [403, 503]:
                        logger.warning(f"[OVH Forum] Server returned {e.response.status_code}")
                        # Browser automation is DISABLED - it blocks the asyncio event loop
                        logger.warning("[OVH Forum] Cannot scrape - server blocked request and browser automation is disabled")
                        return []
                    else:
                        raise
                except requests.exceptions.Timeout:
                    logger.warning(f"[OVH Forum] Timeout on attempt {attempt + 1}")
                    if attempt < MAX_RETRIES - 1:
                        continue
                    return []
                except Exception as e:
                    logger.error(f"[OVH Forum] Error fetching page: {e}")
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        time.sleep(wait_time)
                        continue
                    return []
                
                if not soup:
                    logger.warning("[OVH Forum] Failed to parse HTML")
                    if attempt < MAX_RETRIES - 1:
                        continue
                    return []
                
                posts = []
                
                # OVH Forum uses ServiceNow platform with URLs like:
                # ?id=community_question&sys_id=...
                # First try the ServiceNow pattern (current forum structure)
                topic_links = soup.find_all('a', href=re.compile(r'community_question.*sys_id=|id=community_question'))
                
                if not topic_links:
                    # Try broader sys_id pattern
                    topic_links = soup.find_all('a', href=re.compile(r'sys_id='))
                    # Filter to only question-like links
                    topic_links = [link for link in topic_links if 'question' in link.get('href', '').lower() or 'topic' in link.get('href', '').lower()]
                
                if not topic_links:
                    # Legacy patterns (old forum structure)
                    logger.info("[OVH Forum] No ServiceNow links found, trying legacy patterns...")
                    topic_links = soup.find_all('a', href=re.compile(r'/t/|/topic/|/post/|/discussion/'))
                
                if not topic_links:
                    # NOTE: Browser automation (Playwright) is DISABLED because it blocks the asyncio event loop
                    # and prevents the heartbeat from running, causing the progress bar to freeze.
                    # The OVH Forum uses JavaScript to load content, so we can't scrape it without a browser.
                    logger.warning("[OVH Forum] No posts found - forum requires JavaScript (browser automation disabled)")
                    return []
                
                seen_urls = set()
                
                # Limit the number of links to process to avoid infinite loops
                max_links_to_process = min(limit * 2, 30)  # Cap at 30 links max
                
                for link in topic_links[:max_links_to_process]:
                    try:
                        href = link.get('href', '')
                        if not href:
                            continue
                        
                        # Make absolute URL - handle ServiceNow format
                        if href.startswith('http'):
                            full_url = href
                        elif href.startswith('?'):
                            # ServiceNow query string format: ?id=community_question&sys_id=...
                            full_url = f"{OVH_FORUM_BASE}{href}"
                        elif href.startswith('/'):
                            # URL relative
                            if href.startswith('/community'):
                                full_url = f"https://community.ovhcloud.com{href}"
                            else:
                                full_url = f"https://community.ovhcloud.com{href}"
                        else:
                            # URL relative sans slash initial
                            full_url = f"{OVH_FORUM_BASE}/{href}"
                        
                        # Skip if already seen (normalize URL for comparison)
                        url_key = full_url.split('sys_id=')[-1] if 'sys_id=' in full_url else full_url
                        if url_key in seen_urls:
                            continue
                        seen_urls.add(url_key)
                        
                        # Extract title
                        title = link.get_text(strip=True)
                        # Clean up title (remove "Question :" prefix)
                        title = re.sub(r'^(Question\s*:\s*)', '', title)
                        if not title or len(title) < 5:
                            continue
                        
                        # For OVH forum, most posts are OVH-related by nature
                        # So we're less strict on query matching
                        
                        # Try to get post details (but skip if we already have enough posts)
                        if len(posts) >= limit:
                            break
                        
                        # Check timeout before making request
                        if time.time() - start_time > MAX_TOTAL_TIME:
                            logger.warning("[OVH Forum] Timeout reached, stopping")
                            break
                        
                        # First, try to extract metadata from the parent element (faster, no extra request)
                        author = 'OVH Community User'
                        created_at = datetime.now().isoformat()
                        content = title
                        
                        parent = link.find_parent(['div', 'li', 'article', 'tr'])
                        if parent:
                            # Look for author in ServiceNow format
                            author_elem = parent.find('a', href=re.compile(r'community_user_profile'))
                            if author_elem:
                                author = author_elem.get_text(strip=True)
                                author = re.sub(r'^Profil de\s*', '', author)
                            
                            # Look for date/time info
                            parent_text = parent.get_text()
                            date_match = re.search(r'(\d+)\s*(hour|heure|jour|day|week|semaine|month|mois|minute)', parent_text, re.I)
                            if date_match:
                                from datetime import timedelta
                                num = int(date_match.group(1))
                                unit = date_match.group(2).lower()
                                now = datetime.now()
                                if 'hour' in unit or 'heure' in unit:
                                    created_at = (now - timedelta(hours=num)).isoformat()
                                elif 'day' in unit or 'jour' in unit:
                                    created_at = (now - timedelta(days=num)).isoformat()
                                elif 'week' in unit or 'semaine' in unit:
                                    created_at = (now - timedelta(weeks=num)).isoformat()
                                elif 'month' in unit or 'mois' in unit:
                                    created_at = (now - timedelta(days=num*30)).isoformat()
                                elif 'minute' in unit:
                                    created_at = (now - timedelta(minutes=num)).isoformat()
                        
                        # Skip fetching individual pages to save time
                        # Just use the title as content for fast scraping
                        
                        post = {
                            'source': 'OVH Forum',
                            'author': author,
                            'content': title,
                            'url': full_url,
                            'created_at': created_at,
                            'sentiment_score': 0.0,
                            'sentiment_label': 'neutral',
                        }
                        posts.append(post)
                        logger.info(f"✓ OVH Forum: {author} - {title[:50]}")
                        
                        # Break early if we have enough posts
                        if len(posts) >= limit:
                            break
                        
                    except Exception as e:
                        logger.debug(f"Error processing forum link: {e}")
                        continue
                
                if not posts:
                    logger.warning(f"[OVH Forum] No posts found for query: {query}")
                    return []
                
                logger.info(f"[OVH Forum] Successfully scraped {len(posts)} posts")
                return posts[:limit]
            
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait_time = min(RETRY_DELAY * (2 ** attempt), 10)  # Cap at 10 seconds
                    logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] OVH Forum network error: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"OVH Forum scraper failed after {MAX_RETRIES} attempts: {e}")
                    return []
            
            except Exception as e:
                logger.error(f"Error scraping OVH Forum: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)  # Small delay before retry
                    continue
                return []
    
        # Should not reach here, but return empty if it does
        return []
    except Exception as e:
        logger.error(f"[OVH Forum] Critical error in _scrape_ovh_forum_single_language: {e}", exc_info=True)
        return []  # Return empty list instead of crashing


def _try_browser_automation(url: str) -> str:
    """Try to scrape using browser automation (Selenium/Playwright) as fallback.
    
    Args:
        url: URL to scrape
    
    Returns:
        HTML content or None if failed
    """
    try:
        from .selenium_helper import scrape_with_playwright, scrape_with_selenium, get_best_scraping_method
        
        method = get_best_scraping_method()
        logger.info(f"[OVH Forum] Trying {method} for browser automation...")
        
        if method == 'playwright':
            return scrape_with_playwright(url, wait_selector='body', timeout=8000)
        elif method == 'selenium':
            return scrape_with_selenium(url, wait_selector='body', timeout=8)
        else:
            logger.warning("[OVH Forum] No browser automation available. Install: pip install playwright")
            return None
    except Exception as e:
        logger.debug(f"Browser automation failed: {e}")
        return None

