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

# OVH Community Forum base URL
OVH_FORUM_BASE = "https://community.ovh.com"


def scrape_ovh_forum(query: str = "OVH", limit: int = 50):
    """Scrape OVH Community Forum for customer feedback and discussions.
    
    Searches the OVH community forum for posts related to the query.
    Uses HTML scraping as the forum doesn't have a public API.
    
    Returns list of dicts: source, author, content, url, created_at
    """
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
            # Strategy 1: Try main forum page (more reliable than search)
            main_url = f"{OVH_FORUM_BASE}/"
            
            logger.info(f"[OVH Forum] Attempt {attempt + 1}/{MAX_RETRIES} - Searching for: {query}")
            
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
                    # Don't try browser automation on first attempt to avoid long waits
                    if attempt == MAX_RETRIES - 1:  # Only on last attempt
                        logger.info("[OVH Forum] Trying browser automation as last resort...")
                        html = _try_browser_automation(main_url)
                        if html:
                            soup = BeautifulSoup(html, 'html.parser')
                        else:
                            logger.warning("[OVH Forum] Browser automation also failed")
                            return []
                    else:
                        # Return empty on early attempts to avoid long waits
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
            
            # Try to find topic links or post elements
            # The structure may vary, so we'll try multiple selectors
            topic_links = soup.find_all('a', href=re.compile(r'/t/|/topic/|/post/'))
            
            if not topic_links:
                # Try alternative selectors on the same page
                logger.info("[OVH Forum] No topic links found, trying alternative selectors...")
                # Try different patterns
                topic_links = soup.find_all('a', href=re.compile(r'/t/|/topic/|/post/|/discussion/'))
                if not topic_links:
                    # Try any links that might be posts
                    topic_links = soup.find_all('a', href=True)
                    # Filter to likely post links
                    topic_links = [link for link in topic_links if any(pattern in link.get('href', '') for pattern in ['/t/', '/topic/', '/post/', '/discussion/'])]
                
                if not topic_links:
                    logger.warning("[OVH Forum] No posts found - forum structure may have changed")
                    return []
            
            seen_urls = set()
            
            # Limit the number of links to process to avoid infinite loops
            max_links_to_process = min(limit * 2, 20)  # Cap at 20 links max
            
            for link in topic_links[:max_links_to_process]:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # Make absolute URL
                    if href.startswith('/'):
                        full_url = f"{OVH_FORUM_BASE}{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # Skip if already seen
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    
                    # Extract title
                    title = link.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue
                    
                    # Check if query is relevant (basic check)
                    if query.lower() not in title.lower() and query.lower() not in full_url.lower():
                        continue
                    
                    # Try to get post details (but skip if we already have enough posts)
                    if len(posts) >= limit:
                        break
                    
                    # Check timeout before making request
                    if time.time() - start_time > MAX_TOTAL_TIME:
                        logger.warning("[OVH Forum] Timeout reached, stopping")
                        break
                    
                    try:
                        # Small delay between requests (minimal to avoid blocking)
                        time.sleep(0.1)  # Very small delay
                        
                        post_response = session.get(full_url, headers=headers, timeout=5)  # Reduced timeout
                        post_response.raise_for_status()
                        post_soup = BeautifulSoup(post_response.content, 'html.parser')
                        
                        # Extract content
                        content_elem = post_soup.find('div', class_=re.compile(r'post|content|body|message'))
                        if not content_elem:
                            content_elem = post_soup.find('article')
                        if not content_elem:
                            content_elem = post_soup.find('main')
                        
                        content = content_elem.get_text(strip=True)[:500] if content_elem else title
                        
                        # Extract author
                        author_elem = post_soup.find('a', class_=re.compile(r'author|user|username'))
                        if not author_elem:
                            author_elem = post_soup.find('span', class_=re.compile(r'author|user'))
                        author = author_elem.get_text(strip=True) if author_elem else 'Unknown'
                        
                        # Extract date
                        date_elem = post_soup.find('time')
                        if date_elem:
                            date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                            try:
                                created_at = datetime.fromisoformat(date_str.replace('Z', '+00:00')).isoformat()
                            except:
                                created_at = datetime.now().isoformat()
                        else:
                            created_at = datetime.now().isoformat()
                        
                    except Exception as e:
                        logger.debug(f"Could not fetch post details for {full_url}: {e}")
                        # Use basic info from link
                        content = title
                        author = 'Unknown'
                        created_at = datetime.now().isoformat()
                    
                    post = {
                        'source': 'OVH Forum',
                        'author': author,
                        'content': f"{title}\n{content}",
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
            return scrape_with_playwright(url, wait_selector='body', timeout=15000)
        elif method == 'selenium':
            return scrape_with_selenium(url, wait_selector='body', timeout=15)
        else:
            logger.warning("[OVH Forum] No browser automation available. Install: pip install playwright")
            return None
    except Exception as e:
        logger.debug(f"Browser automation failed: {e}")
        return None

