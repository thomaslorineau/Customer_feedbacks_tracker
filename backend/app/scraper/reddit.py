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
    """Scrape Reddit using JSON API with pagination, fallback to RSS if API fails.
    
    First tries Reddit JSON API which supports pagination via 'after' token.
    Falls back to RSS feed if API fails.
    
    Returns list of dicts: source, author, content, url, created_at
    """
    # Try API first (better pagination support)
    try:
        posts = _scrape_reddit_with_api(query, limit)
        if posts:
            logger.info(f"[REDDIT] Successfully scraped {len(posts)} posts using JSON API")
            return posts
    except Exception as e:
        logger.warning(f"[REDDIT] API scraping failed: {e}, falling back to RSS")
    
    # Fallback to RSS
    return _scrape_reddit_with_rss(query, limit)


def _scrape_reddit_with_api(query: str, limit: int) -> list:
    """Scrape Reddit using JSON API with pagination."""
    all_posts = []
    after = None  # Reddit pagination token
    page = 0
    
    headers = {
        'User-Agent': 'OVH-Tracker-Bot/1.0 (Feedback Monitor)'
    }
    
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    while len(all_posts) < limit:
        page += 1
        # Reddit JSON API endpoint
        url = "https://www.reddit.com/search.json"
        params = {
            'q': query,
            'sort': 'new',
            'limit': min(100, limit - len(all_posts)),  # Reddit API max is 100
        }
        
        if after:
            params['after'] = after
        
        logger.info(f"[REDDIT API] Fetching page {page} (after={after[:10] if after else 'None'}...)")
        
        try:
            response = session.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data or 'children' not in data['data']:
                logger.warning(f"[REDDIT API] Unexpected API response structure")
                break
            
            children = data['data']['children']
            if len(children) == 0:
                logger.info(f"[REDDIT API] No more results on page {page}")
                break
            
            for child in children:
                if len(all_posts) >= limit:
                    break
                
                post_data = child.get('data', {})
                try:
                    title = post_data.get('title', '').strip()
                    if not title:
                        continue
                    
                    # Get post content (selftext for text posts, or title for link posts)
                    selftext = post_data.get('selftext', '').strip()
                    content = f"{title}\n{selftext}" if selftext else title
                    
                    author = post_data.get('author', 'unknown')
                    subreddit = post_data.get('subreddit', '')
                    url_link = post_data.get('url', '')
                    permalink = post_data.get('permalink', '')
                    if permalink and not url_link.startswith('http'):
                        url_link = f"https://www.reddit.com{permalink}"
                    
                    # Parse created timestamp
                    created_utc = post_data.get('created_utc', 0)
                    if created_utc:
                        created_at = datetime.fromtimestamp(created_utc).isoformat()
                    else:
                        created_at = datetime.now().isoformat()
                    
                    post = {
                        'source': 'Reddit',
                        'author': f"u/{author}" if author != 'unknown' else 'unknown',
                        'content': f"[r/{subreddit}] {content}"[:500] if subreddit else content[:500],
                        'url': url_link,
                        'created_at': created_at,
                        'sentiment_score': 0.0,
                        'sentiment_label': 'neutral',
                    }
                    all_posts.append(post)
                    logger.debug(f"✓ Reddit: u/{author} in r/{subreddit} - {title[:50]}")
                except Exception as e:
                    logger.warning(f"Could not parse Reddit post: {e}")
                    continue
            
            # Get pagination token for next page
            after = data['data'].get('after')
            if not after:
                logger.info(f"[REDDIT API] No more pages (after token is None)")
                break
            
            # Small delay between pages to respect rate limits
            if len(all_posts) < limit:
                time.sleep(0.5)
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"[REDDIT API] Request error on page {page}: {e}")
            if page == 1:
                raise  # If first page fails, let fallback handle it
            break  # Return what we have
        except Exception as e:
            logger.warning(f"[REDDIT API] Error on page {page}: {e}")
            if page == 1:
                raise
            break
    
    return all_posts


def _scrape_reddit_with_rss(query: str, limit: int) -> list:
    """Fallback: Scrape Reddit using RSS feeds."""
    for attempt in range(MAX_RETRIES):
        try:
            import feedparser
            
            # Reddit RSS search endpoint - searches across all Reddit
            # Sort by new to get recent posts
            url = f"https://www.reddit.com/search.rss?q={query}&sort=new&limit={min(limit, 100)}"
            
            logger.info(f"[REDDIT RSS] Fetching RSS feed: {url}")
            
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
                logger.warning(f"[REDDIT RSS] No results found for query: {query}")
                logger.info(f"[REDDIT RSS] RSS feed parsed but empty. Status: {response.status_code}, URL: {url}")
                return []
            
            logger.info(f"[REDDIT RSS] Found {len(feed.entries)} posts")
            
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
                        'sentiment_score': 0.0,
                        'sentiment_label': 'neutral',
                    }
                    posts.append(post)
                    logger.info(f"✓ Reddit: u/{author} in r/{subreddit} - {title[:50]}")
                    
                except Exception as e:
                    logger.warning(f"Could not parse Reddit entry: {e}")
                    continue
            
            if not posts:
                logger.warning("[REDDIT RSS] No valid Reddit posts could be parsed from RSS feed")
                return []
            
            logger.info(f"[REDDIT RSS] Successfully scraped {len(posts)} posts")
            return posts
        
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Reddit RSS network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Reddit RSS scraper failed after {MAX_RETRIES} attempts: {e}")
                return []
        
        except Exception as e:
            logger.error(f"Error scraping Reddit RSS: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                continue
            return []
    
    logger.error(f"Reddit RSS scraper failed after {MAX_RETRIES} attempts")
    return []


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
                return []  # Return empty list instead of raising exception
            
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
                logger.warning(f"[REDDIT] No valid posts found in r/{subreddit}")
                return []
            
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
                return []  # Return empty list instead of raising exception
        
        except Exception as e:
            logger.error(f"Error scraping r/{subreddit}: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                continue
            return []  # Return empty list instead of raising exception
    
    logger.error(f"Reddit scraper failed after {MAX_RETRIES} attempts")
    return []
