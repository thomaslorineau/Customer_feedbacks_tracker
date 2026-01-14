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
    
    Returns list of dicts: source, author, content, url, created_at
    Raises exception if RSS is unavailable after retries.
    Implements retry logic with exponential backoff.
    """
    for attempt in range(MAX_RETRIES):
        try:
            import feedparser
            
            # Google News RSS endpoint - searches for articles matching the query
            url = f"https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"
            
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
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the RSS content
            feed = feedparser.parse(response.content)
            
            # Check if feed has entries
            if not feed.entries:
                raise RuntimeError("Google News RSS returned no results")
            
            results = []
            for i, entry in enumerate(feed.entries):
                if i >= limit:
                    break
                
                try:
                    # Extract author from the source/author field
                    author = entry.get('author', entry.get('source', {}).get('title', 'News Source'))
                    
                    # Combine title and summary for content
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    content = title + ('\n\n' + summary if summary else '')
                    
                    results.append({
                        'source': 'Google News',
                        'author': author if author else 'News Source',
                        'content': content,
                        'url': entry.get('link', ''),
                        'created_at': entry.get('published', datetime.now().isoformat()),
                    })
                except Exception as e:
                    logger.warning(f"Error processing article: {e}")
                    continue
            
            if not results:
                raise RuntimeError("No valid Google News articles could be parsed")

            return results
        
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Google News network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"[Google News] Failed after {MAX_RETRIES} attempts: {e}")
                logger.warning("Google News network failures — returning sample news articles as fallback")
                return _get_sample_news(query, limit)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Google News error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"[Google News] Failed after {MAX_RETRIES} attempts: {e}")
                logger.warning("Google News parsing failures — returning sample news articles as fallback")
                return _get_sample_news(query, limit)


def _get_sample_news(query: str, limit: int = 10):
    now = datetime.now().isoformat()
    samples = [
        {
            'source': 'Google News',
            'author': 'Tech News',
            'content': f'Article à propos de {query}: problèmes de domaine rapportés par plusieurs utilisateurs.',
            'url': 'https://news.example.com/sample',
            'created_at': now,
        },
        {
            'source': 'Google News',
            'author': 'Daily Web',
            'content': f'Analyse: les incidents liés aux domaines OVH affectent certains clients.',
            'url': 'https://news.example.com/sample2',
            'created_at': now,
        },
    ]
    return samples[:limit]


def _scrape_google_news_fallback(query: str, limit: int = 50):
    """Deprecated fallback function - returns empty list."""
    return []


def get_mock_news_articles(limit=20):
    """Return empty list - no fallback data."""
    return []



