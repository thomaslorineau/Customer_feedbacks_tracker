"""G2 Crowd scraper for OVH product reviews."""
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

G2_BASE_URL = "https://www.g2.com"


def scrape_g2_crowd(query: str = "OVH", limit: int = 50):
    """Scrape G2 Crowd for OVH product reviews.
    
    G2 Crowd is a B2B software review platform.
    Searches for OVH products and extracts reviews.
    
    Returns list of dicts: source, author, content, url, created_at
    """
    # Set a global timeout to prevent infinite loops (45 seconds max)
    start_time = time.time()
    MAX_TOTAL_TIME = 45
    
    for attempt in range(MAX_RETRIES):
        # Check if we've exceeded total time limit
        if time.time() - start_time > MAX_TOTAL_TIME:
            logger.warning(f"[G2 Crowd] Exceeded maximum time limit ({MAX_TOTAL_TIME}s)")
            return []
        try:
            # G2 search URL
            search_url = f"{G2_BASE_URL}/products/ovhcloud/reviews"
            
            # Alternative: search page
            # search_url = f"{G2_BASE_URL}/search?query={query}"
            
            logger.info(f"[G2 Crowd] Searching for: {query}")
            
            # Create stealth session with realistic headers
            session = create_stealth_session()
            
            # Get realistic headers with referer
            headers = get_realistic_headers(referer=G2_BASE_URL)
            
            # Simulate human behavior: visit main page first (but skip if same URL)
            # This is optional and can be disabled if causing issues
            # simulate_human_behavior(session, search_url)
            
            # Try direct reviews page first
            try:
                logger.info(f"[G2 Crowd] Fetching URL: {search_url}")
                response = session.get(search_url, headers=headers, timeout=15)
                logger.info(f"[G2 Crowd] Response status: {response.status_code}")
                logger.info(f"[G2 Crowd] Response size: {len(response.content)} bytes")
                response.raise_for_status()
                # Small delay after request (reduced to avoid long waits)
                time.sleep(0.5)
            except requests.exceptions.HTTPError as e:
                logger.error(f"[G2 Crowd] HTTP Error: {e.response.status_code} - {e}")
                if e.response.status_code == 403:
                    logger.warning(f"[G2 Crowd] Server returned 403 Forbidden - trying browser automation...")
                    # Try with browser automation as fallback
                    html = _try_browser_automation(search_url)
                    if html:
                        logger.info(f"[G2 Crowd] Browser automation succeeded, HTML size: {len(html)} bytes")
                        soup = BeautifulSoup(html, 'html.parser')
                    else:
                        logger.warning("[G2 Crowd] Browser automation also failed")
                        logger.info("[G2 Crowd] Solutions:")
                        logger.info("  1. Use G2 API (requires API key)")
                        logger.info("  2. Install Playwright: pip install playwright && playwright install")
                        logger.info("  3. Use residential proxies")
                        logger.info("  4. Manual data collection")
                        return []
                else:
                    raise
            except Exception as e:
                logger.error(f"[G2 Crowd] Error fetching page: {type(e).__name__}: {e}")
                raise
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            logger.info(f"[G2 Crowd] HTML parsed successfully")
            
            posts = []
            
            # G2 reviews are typically in specific containers
            # Look for review elements (structure may vary)
            logger.info("[G2 Crowd] Searching for review elements with class 'review|rating|feedback|comment'...")
            review_elements = soup.find_all(['div', 'article', 'section'], 
                                          class_=re.compile(r'review|rating|feedback|comment', re.I))
            logger.info(f"[G2 Crowd] Found {len(review_elements)} elements with review/rating/feedback/comment classes")
            
            if not review_elements:
                # Try alternative selectors
                logger.info("[G2 Crowd] Trying alternative selector: data-testid='review'...")
                review_elements = soup.find_all('div', {'data-testid': re.compile(r'review', re.I)})
                logger.info(f"[G2 Crowd] Found {len(review_elements)} elements with data-testid='review'")
            
            if not review_elements:
                # Try finding review cards
                logger.info("[G2 Crowd] Trying alternative selector: class='card|item|entry'...")
                review_elements = soup.find_all('div', class_=re.compile(r'card|item|entry', re.I))
                logger.info(f"[G2 Crowd] Found {len(review_elements)} elements with card/item/entry classes")
            
            if not review_elements:
                # Debug: Save HTML structure for analysis
                logger.warning("[G2 Crowd] No review elements found with any selector")
                logger.info("[G2 Crowd] Debug: Checking page structure...")
                # Try to find any divs with text content
                all_divs = soup.find_all('div', limit=50)
                logger.info(f"[G2 Crowd] Total divs on page: {len(soup.find_all('div'))}")
                logger.info(f"[G2 Crowd] Sample div classes (first 10): {[d.get('class', []) for d in all_divs[:10]]}")
                # Check for common G2 patterns
                if soup.find('body'):
                    body_text = soup.find('body').get_text()[:200]
                    logger.info(f"[G2 Crowd] Body text preview: {body_text}...")
            
            seen_urls = set()
            
            # Limit the number of reviews to process to avoid long waits
            max_reviews_to_process = min(limit * 2, 15)  # Cap at 15 reviews max
            
            logger.info(f"[G2 Crowd] Processing up to {max_reviews_to_process} review elements...")
            processed_count = 0
            skipped_no_content = 0
            skipped_short = 0
            
            for review_elem in review_elements[:max_reviews_to_process]:
                processed_count += 1
                try:
                    # Extract review content
                    content_elem = review_elem.find(['p', 'div', 'span'], 
                                                   class_=re.compile(r'content|text|body|description|review-text', re.I))
                    if not content_elem:
                        content_elem = review_elem.find('p')
                    
                    if not content_elem:
                        skipped_no_content += 1
                        logger.debug(f"[G2 Crowd] Review element {processed_count}: No content element found")
                        continue
                    
                    content = content_elem.get_text(strip=True)
                    if len(content) < 20:  # Skip very short reviews
                        skipped_short += 1
                        logger.debug(f"[G2 Crowd] Review element {processed_count}: Content too short ({len(content)} chars)")
                        continue
                    
                    logger.info(f"[G2 Crowd] Review element {processed_count}: Found content ({len(content)} chars)")
                    
                    # Extract author
                    author_elem = review_elem.find(['a', 'span', 'div'], 
                                                  class_=re.compile(r'author|user|name|reviewer', re.I))
                    if not author_elem:
                        author_elem = review_elem.find('strong')
                    author = author_elem.get_text(strip=True) if author_elem else 'Anonymous'
                    
                    # Extract rating (if available)
                    rating_elem = review_elem.find(['span', 'div'], class_=re.compile(r'rating|star|score', re.I))
                    rating = ''
                    if rating_elem:
                        rating_text = rating_elem.get_text(strip=True)
                        rating_match = re.search(r'(\d+\.?\d*)\s*(?:out of|/|stars?)', rating_text, re.I)
                        if rating_match:
                            rating = f"Rating: {rating_match.group(1)}/5"
                    
                    # Extract date
                    date_elem = review_elem.find('time')
                    if not date_elem:
                        date_elem = review_elem.find(['span', 'div'], class_=re.compile(r'date|time|published', re.I))
                    
                    created_at = datetime.now().isoformat()
                    if date_elem:
                        date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                        try:
                            # Try to parse various date formats
                            if 'ago' in date_str.lower():
                                # Relative date like "2 days ago"
                                created_at = datetime.now().isoformat()
                            else:
                                created_at = datetime.fromisoformat(date_str.replace('Z', '+00:00')).isoformat()
                        except:
                            pass
                    
                    # Extract URL
                    link_elem = review_elem.find('a', href=True)
                    if link_elem:
                        href = link_elem.get('href')
                        if href.startswith('/'):
                            post_url = f"{G2_BASE_URL}{href}"
                        elif href.startswith('http'):
                            post_url = href
                        else:
                            post_url = f"{G2_BASE_URL}/products/ovhcloud/reviews"
                    else:
                        post_url = f"{G2_BASE_URL}/products/ovhcloud/reviews"
                    
                    if post_url in seen_urls:
                        continue
                    seen_urls.add(post_url)
                    
                    # Build content with rating if available
                    full_content = f"{content}"
                    if rating:
                        full_content = f"{rating}\n{full_content}"
                    
                    post = {
                        'source': 'G2 Crowd',
                        'author': author,
                        'content': full_content[:500],
                        'url': post_url,
                        'created_at': created_at,
                        'sentiment_score': 0.0,
                        'sentiment_label': 'neutral',
                    }
                    posts.append(post)
                    logger.info(f"✓ G2 Crowd: {author} - {content[:50]}")
                    
                    # Break early if we have enough posts
                    if len(posts) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"[G2 Crowd] Error processing review element {processed_count}: {type(e).__name__}: {e}")
                    continue
            
            logger.info(f"[G2 Crowd] Processing summary: {processed_count} processed, {skipped_no_content} skipped (no content), {skipped_short} skipped (too short), {len(posts)} posts extracted")
            
            # If no reviews found, try search page
            if not posts:
                logger.info("[G2 Crowd] No reviews found on product page, trying search...")
                search_url = f"{G2_BASE_URL}/search"
                params = {'query': query}
                try:
                    response = session.get(search_url, params=params, headers=headers, timeout=15)
                    logger.info(f"[G2 Crowd] Search page response: {response.status_code}")
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        logger.info(f"[G2 Crowd] Search page HTML size: {len(response.content)} bytes")
                        # Similar parsing logic for search results
                        # (implementation similar to above)
                except Exception as e:
                    logger.warning(f"[G2 Crowd] Error fetching search page: {e}")
            
            if not posts:
                logger.warning(f"[G2 Crowd] No reviews found for query: {query}")
                logger.info(f"[G2 Crowd] Debug info: URL={search_url}, Status={response.status_code if 'response' in locals() else 'N/A'}, Elements found={len(review_elements) if 'review_elements' in locals() else 0}")
                return []
            
            logger.info(f"[G2 Crowd] Successfully scraped {len(posts)} reviews")
            return posts[:limit]
        
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] G2 Crowd network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"G2 Crowd scraper failed after {MAX_RETRIES} attempts: {e}")
                return []
        
        except Exception as e:
            logger.error(f"Error scraping G2 Crowd: {str(e)}")
            return []
    
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
        logger.info(f"[G2 Crowd] Trying {method} for browser automation...")
        
        if method == 'playwright':
            return scrape_with_playwright(url, wait_selector='body', timeout=20000)
        elif method == 'selenium':
            return scrape_with_selenium(url, wait_selector='body', timeout=20)
        else:
            logger.warning("[G2 Crowd] No browser automation available. Install: pip install playwright")
            return None
    except Exception as e:
        logger.debug(f"Browser automation failed: {e}")
        return None

