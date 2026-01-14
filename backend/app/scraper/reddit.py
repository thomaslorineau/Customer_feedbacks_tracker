from datetime import datetime
import requests
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def scrape_reddit(query: str, limit: int = 50):
    """Scrape Reddit using RSS feeds.
    
    Reddit allows RSS feeds by appending .rss to search URLs:
    - Search: https://www.reddit.com/search.rss?q=ovh&sort=new
    - Subreddit: https://www.reddit.com/r/ovh.rss
    
    Returns list of dicts: source, author, content, url, created_at
    Raises exception if RSS is unavailable after retries.
    Implements retry logic with exponential backoff.
    """
    for attempt in range(MAX_RETRIES):
        try:
            import feedparser
            
            # Reddit RSS search endpoint - searches across all Reddit
            # Sort by new to get recent posts
            url = f"https://www.reddit.com/search.rss?q={query}&sort=new&limit={min(limit, 100)}"
            
            logger.info(f"[REDDIT] Fetching RSS feed: {url}")
            
            # Create a session with retry strategy and proper headers
            session = requests.Session()
            retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            # Set user agent - Reddit requires a proper user agent
            headers = {
                'User-Agent': 'OVH-Tracker-Bot/1.0 (Feedback Monitor)'
            }
            
            # Fetch the RSS feed with timeout
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse the RSS content
            feed = feedparser.parse(response.content)
            
            # Check if feed has entries
            if not feed.entries:
                logger.warning(f"[REDDIT] No results found for query: {query}")
                raise RuntimeError(f"Reddit RSS returned no results for: {query}")
            
            logger.info(f"[REDDIT] Found {len(feed.entries)} posts")
            
            posts = []
            for entry in feed.entries[:limit]:
                try:
                    # Extract post details
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '').strip()
                    author = entry.get('author', 'unknown').strip()
                    
                    # Get content/summary
                    content = entry.get('summary', title)[:500]
                    
                    # Parse date
                    published = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published:
                        created_at = datetime(*published[:6]).isoformat()
                    else:
                        created_at = datetime.now().isoformat()
                    
                    # Extract subreddit from category if available
                    subreddit = ''
                    if hasattr(entry, 'tags') and entry.tags:
                        subreddit = entry.tags[0].get('term', '')
                    
                    post = {
                        'source': 'Reddit',
                        'author': f"u/{author}" if author != 'unknown' else 'unknown',
                        'content': f"[r/{subreddit}] {title}\n{content}" if subreddit else f"{title}\n{content}",
                        'url': link,
                        'created_at': created_at,
                        'sentiment_score': 0.0,  # Will be analyzed in main.py
                        'sentiment_label': 'neutral',
                    }
                    posts.append(post)
                    logger.info(f"✓ Reddit: u/{author} in r/{subreddit} - {title[:50]}")
                    
                except Exception as e:
                    logger.warning(f"Could not parse Reddit entry: {e}")
                    continue
            
            if not posts:
                raise RuntimeError("No valid Reddit posts could be parsed")
            
            logger.info(f"[REDDIT] Successfully scraped {len(posts)} posts")
            return posts
        
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Reddit network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Reddit scraper failed after {MAX_RETRIES} attempts: {e}")
                raise RuntimeError(f"Could not fetch Reddit RSS after {MAX_RETRIES} attempts: {e}")
        
        except Exception as e:
            logger.error(f"Error scraping Reddit: {str(e)}")
            raise RuntimeError(f"Reddit scraping failed: {str(e)}")
    
    # All retries failed
    raise RuntimeError(f"Could not fetch Reddit posts after {MAX_RETRIES} attempts")


def scrape_reddit_subreddit(subreddit: str, limit: int = 50):
    """Scrape a specific subreddit using RSS.
    
    Args:
        subreddit: Name of the subreddit (without /r/)
        limit: Maximum number of posts to fetch
    
    Returns:
        List of post dictionaries
    """
    for attempt in range(MAX_RETRIES):
        try:
            import feedparser
            
            # Subreddit RSS endpoint
            url = f"https://www.reddit.com/r/{subreddit}.rss?limit={min(limit, 100)}"
            
            logger.info(f"[REDDIT] Fetching subreddit r/{subreddit}")
            
            session = requests.Session()
            retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            headers = {
                'User-Agent': 'OVH-Tracker-Bot/1.0 (Feedback Monitor)'
            }
            
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if not feed.entries:
                logger.warning(f"[REDDIT] No posts found in r/{subreddit}")
                raise RuntimeError(f"Subreddit r/{subreddit} returned no results")
            
            logger.info(f"[REDDIT] Found {len(feed.entries)} posts in r/{subreddit}")
            
            posts = []
            for entry in feed.entries[:limit]:
                try:
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '').strip()
                    author = entry.get('author', 'unknown').strip()
                    content = entry.get('summary', title)[:500]
                    
                    published = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published:
                        created_at = datetime(*published[:6]).isoformat()
                    else:
                        created_at = datetime.now().isoformat()
                    
                    post = {
                        'source': 'Reddit',
                        'author': f"u/{author}" if author != 'unknown' else 'unknown',
                        'content': f"[r/{subreddit}] {title}\n{content}",
                        'url': link,
                        'created_at': created_at,
                        'sentiment_score': 0.0,
                        'sentiment_label': 'neutral',
                    }
                    posts.append(post)
                    logger.info(f"✓ Reddit: u/{author} - {title[:50]}")
                    
                except Exception as e:
                    logger.warning(f"Could not parse Reddit entry: {e}")
                    continue
            
            if not posts:
                raise RuntimeError(f"No valid posts found in r/{subreddit}")
            
            logger.info(f"[REDDIT] Successfully scraped {len(posts)} posts from r/{subreddit}")
            return posts
        
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Reddit network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Reddit scraper failed after {MAX_RETRIES} attempts: {e}")
                raise RuntimeError(f"Could not fetch r/{subreddit} after {MAX_RETRIES} attempts: {e}")
        
        except Exception as e:
            logger.error(f"Error scraping r/{subreddit}: {str(e)}")
            raise RuntimeError(f"Reddit scraping failed: {str(e)}")
    
    raise RuntimeError(f"Could not fetch Reddit posts after {MAX_RETRIES} attempts")
