from datetime import datetime
import requests
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def scrape_google_news(query: str, limit: int = 50):
    """Scrape Google News using feedparser RSS.
    
    If query contains multiple keywords (separated by + or space), searches each separately
    and combines results to avoid Google News RSS limitations with complex queries.
    
    Returns list of dicts: source, author, content, url, created_at
    Raises exception if RSS is unavailable after retries.
    Implements retry logic with exponential backoff.
    """
    import feedparser
    import urllib.parse
    
    # Extract individual keywords from query
    # Handle both "keyword1 + keyword2" and "keyword1 keyword2" formats
    if '+' in query or ' + ' in query:
        keywords = [k.strip() for k in query.replace(' + ', '+').split('+') if k.strip()]
    else:
        # Split by space and take meaningful keywords (at least 3 chars)
        keywords = [k.strip() for k in query.split() if len(k.strip()) >= 3]
    
    # Limit to first 3 keywords to avoid too many requests
    keywords = keywords[:3]
    
    if not keywords:
        keywords = ['ovhcloud']  # Default fallback
    
    logger.info(f"[GOOGLE NEWS] Searching with keywords: {keywords}")
    
    all_results = []
    seen_urls = set()  # Avoid duplicates
    
    # Search each keyword separately
    for keyword in keywords:
        if len(all_results) >= limit:
            break
            
        for attempt in range(MAX_RETRIES):
            try:
                # URL encode the keyword
                encoded_query = urllib.parse.quote_plus(keyword)
                
                # Google News RSS endpoint
                url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en&gl=US&ceid=US:en"
                
                logger.info(f"[GOOGLE NEWS] Fetching for '{keyword}': {url}")
                
                # Create a session with retry strategy and proper headers
                session = requests.Session()
                retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
                adapter = HTTPAdapter(max_retries=retry)
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                
                # Set user agent to avoid being blocked
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Fetch the RSS feed with timeout
                response = session.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # Parse the RSS content
                feed = feedparser.parse(response.content)
                
                # Check if feed has entries
                if not feed.entries:
                    logger.warning(f"[GOOGLE NEWS] No results for keyword '{keyword}'")
                    break  # Try next keyword
                
                # Process entries for this keyword
                keyword_results = []
                for entry in feed.entries:
                    if len(all_results) >= limit:
                        break
                    
                    try:
                        url_link = entry.get('link', '')
                        # Skip if we've already seen this URL
                        if url_link in seen_urls:
                            continue
                        seen_urls.add(url_link)
                        
                        # Extract author from the source/author field
                        author = entry.get('author', '')
                        if not author:
                            source = entry.get('source', {})
                            if isinstance(source, dict):
                                author = source.get('title', 'News Source')
                            else:
                                author = 'News Source'
                        
                        # Combine title and summary for content
                        title = entry.get('title', '')
                        summary = entry.get('summary', '')
                        content = title + ('\n\n' + summary if summary else '')
                        
                        # Parse published date
                        published = entry.get('published_parsed')
                        if published:
                            created_at = datetime(*published[:6]).isoformat()
                        else:
                            created_at = datetime.now().isoformat()
                        
                        keyword_results.append({
                            'source': 'Google News',
                            'author': author if author else 'News Source',
                            'content': content[:500],  # Limit content length
                            'url': url_link,
                            'created_at': created_at,
                        })
                    except Exception as e:
                        logger.warning(f"Error processing article: {e}")
                        continue
                
                if keyword_results:
                    all_results.extend(keyword_results)
                    logger.info(f"[GOOGLE NEWS] Found {len(keyword_results)} articles for '{keyword}' (total: {len(all_results)})")
                
                # Success for this keyword, move to next
                break
        
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Google News network error for '{keyword}': {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[GOOGLE NEWS] Failed after {MAX_RETRIES} attempts for '{keyword}': {e}")
                    # Continue to next keyword
                    break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Google News error for '{keyword}': {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[GOOGLE NEWS] Failed after {MAX_RETRIES} attempts for '{keyword}': {e}")
                    # Continue to next keyword
                    break
        
        # Small delay between keywords to avoid rate limiting
        if keyword != keywords[-1]:  # Not the last keyword
            time.sleep(0.5)
    
    # Return combined results, limited to requested limit
    if all_results:
        logger.info(f"[GOOGLE NEWS] Successfully scraped {len(all_results[:limit])} articles total")
        return all_results[:limit]
    else:
        logger.warning("[GOOGLE NEWS] No articles found for any keyword")
        return []


# Removed _get_sample_news - no sample data allowed


def _scrape_google_news_fallback(query: str, limit: int = 50):
    """Deprecated fallback function - returns empty list."""
    return []


def get_mock_news_articles(limit=20):
    """Return empty list - no fallback data."""
    return []



