import requests
from datetime import datetime
import logging
import httpx
from httpx import Timeout

logger = logging.getLogger(__name__)

def detect_language(text: str) -> str:
    """Detect language of text (simplified version for French/English)."""
    try:
        from textblob import TextBlob
        try:
            lang = TextBlob(text).detect_language()
            return lang if lang in ['fr', 'en'] else 'other'
        except:
            return 'unknown'
    except ImportError:
        # Simple heuristic if textblob not available
        french_words = ['le', 'la', 'de', 'et', 'qu', 'qui', 'est', 'pas', 'à', 'pour']
        english_words = ['the', 'and', 'is', 'to', 'of', 'in', 'a', 'that', 'it', 'you']
        
        text_lower = text.lower()
        fr_count = sum(1 for w in french_words if f' {w} ' in f' {text_lower} ')
        en_count = sum(1 for w in english_words if f' {w} ' in f' {text_lower} ')
        
        if fr_count > en_count:
            return 'fr'
        elif en_count > fr_count:
            return 'en'
        return 'unknown'

def scrape_x(query: str, limit: int = 50):
    """Scrape X (Twitter) using multiple strategies.
    
    Strategy priority:
    1. Twitter API v2 (if Bearer Token is configured)
    2. Nitter instances (fallback)
    
    Python 3.13 compatible - works around snscrape incompatibility.
    Returns list of dicts: source, author, content, url, created_at, language
    """
    results = []
    logger.info(f"[X SCRAPER] Searching for: {query}")
    
    # Strategy 1: Try Twitter API v2 if Bearer Token is available
    try:
        from ..config import config
        bearer_token = config.get_api_key("twitter_bearer")
        if bearer_token:
            logger.info("[X SCRAPER] Twitter Bearer Token found, using official API v2")
            results = _try_twitter_api_v2(query, limit, bearer_token)
            if results:
                logger.info(f"[X SCRAPER] Twitter API v2 returned {len(results)} tweets")
                return results
            else:
                logger.info("[X SCRAPER] Twitter API v2 returned no results, falling back to Nitter")
        else:
            logger.debug("[X SCRAPER] No Twitter Bearer Token configured, skipping API")
    except Exception as e:
        logger.debug(f"[X SCRAPER] Error checking for Twitter API token: {e}")
    
    # Strategy 2: Try Nitter instances (fallback)
    results = _try_nitter_scrape(query, limit)
    if results:
        return results
    
    # All methods failed - return empty list (no sample data)
    logger.warning("[X SCRAPER] All scraping methods failed, returning empty list")
    return []


def _try_nitter_scrape(query: str, limit: int) -> list:
    """Try scraping from public Nitter instances."""
    results = []  # Initialize results list
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.poast.org",
        "https://nitter.1d4.us",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    search_query = query.replace(' ', '%20')
    
    for nitter_url in nitter_instances:
        try:
            search_url = f"{nitter_url}/search?q={search_query}&f=tweets&since=&until=&near="
            logger.info(f"[X SCRAPER] Trying: {nitter_url}")
            
            response = requests.get(
                search_url,
                headers=headers,
                timeout=10,
                allow_redirects=True
            )
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            tweets = soup.find_all('article', class_='tweet')
            
            if tweets:
                logger.info(f"[X SCRAPER] Found {len(tweets)} tweets from {nitter_url}")
                for i, tweet in enumerate(tweets):
                    if i >= limit:
                        break
                    try:
                        author_elem = tweet.find('a', class_='username')
                        author = author_elem.text.strip() if author_elem else 'Unknown'
                        
                        content_elem = tweet.find('div', class_='tweet-text')
                        content = content_elem.text.strip() if content_elem else ''
                        
                        link_elem = tweet.find('a', class_='tweet-link')
                        url = f"{nitter_url}{link_elem['href']}" if link_elem and link_elem.get('href') else ''
                        
                        if content:
                            results.append({
                                'source': 'X/Twitter',
                                'author': author,
                                'content': content,
                                'url': url,
                                'created_at': datetime.now().isoformat(),
                                'language': detect_language(content),
                            })
                    except Exception as e:
                        logger.warning(f"[X SCRAPER] Error parsing tweet: {e}")
                        continue
                
                if results:
                    return results
        
        except Exception as e:
            logger.debug(f"[X SCRAPER] {nitter_url} failed: {str(e)[:100]}")
            continue
    
    return []


def _try_twitter_api_v2(query: str, limit: int, bearer_token: str) -> list:
    """
    Search Twitter using official API v2 with Bearer Token.
    
    Implements pagination to fetch multiple pages of results.
    Respects rate limits: 300 requests per 15 minutes.
    """
    import httpx
    import time
    
    all_tweets = []
    next_token = None
    page = 0
    
    try:
        while len(all_tweets) < limit:
            page += 1
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'User-Agent': 'OVH-Tracker-Bot/1.0'
            }
            
            # Twitter API v2 search endpoint
            search_url = "https://api.twitter.com/2/tweets/search/recent"
            params = {
                'query': f"{query} -is:retweet lang:fr OR lang:en",  # Exclude retweets, French or English
                'max_results': min(100, limit - len(all_tweets)),  # Max 100 per request
                'tweet.fields': 'created_at,author_id,public_metrics,lang',
                'expansions': 'author_id',
                'user.fields': 'username,name',
            }
            
            if next_token:
                params['next_token'] = next_token
            
            logger.info(f"[X SCRAPER API] Fetching page {page} (query: {query})")
            
            response = httpx.get(
                search_url,
                headers=headers,
                params=params,
                timeout=Timeout(15.0, connect=5.0)
            )
            
            if response.status_code == 401:
                logger.warning("[X SCRAPER API] Authentication failed. Check your Bearer Token.")
                return []
            elif response.status_code == 403:
                logger.warning("[X SCRAPER API] Access forbidden. Check API permissions.")
                return []
            elif response.status_code == 429:
                logger.warning("[X SCRAPER API] Rate limit exceeded. Waiting before retry...")
                time.sleep(60)  # Wait 1 minute for rate limit
                continue
            elif response.status_code != 200:
                logger.warning(f"[X SCRAPER API] API error: {response.status_code} - {response.text[:200]}")
                if page == 1:
                    return []  # If first page fails, return empty
                break  # Return what we have
            
            data = response.json()
            
            # Parse tweets
            tweets = data.get('data', [])
            if not tweets:
                logger.info(f"[X SCRAPER API] No more tweets on page {page}")
                break
            
            # Get user information from includes
            users = {}
            if 'includes' in data and 'users' in data['includes']:
                for user in data['includes']['users']:
                    users[user['id']] = user
            
            for tweet in tweets:
                if len(all_tweets) >= limit:
                    break
                
                try:
                    author_id = tweet.get('author_id', '')
                    author_info = users.get(author_id, {})
                    author = author_info.get('username', 'unknown')
                    if not author or author == 'unknown':
                        author = author_info.get('name', 'Unknown')
                    
                    content = tweet.get('text', '')
                    if not content:
                        continue
                    
                    created_at = tweet.get('created_at', datetime.now().isoformat())
                    tweet_id = tweet.get('id', '')
                    url = f"https://twitter.com/{author}/status/{tweet_id}" if tweet_id else ''
                    
                    lang = tweet.get('lang', 'unknown')
                    
                    all_tweets.append({
                        'source': 'X/Twitter',
                        'author': f"@{author}" if not author.startswith('@') else author,
                        'content': content,
                        'url': url,
                        'created_at': created_at,
                        'language': lang if lang in ['fr', 'en'] else detect_language(content),
                    })
                    logger.debug(f"✓ Twitter API: @{author} - {content[:50]}")
                except Exception as e:
                    logger.warning(f"Could not parse Twitter tweet: {e}")
                    continue
            
            # Get pagination token
            meta = data.get('meta', {})
            next_token = meta.get('next_token')
            if not next_token:
                logger.info(f"[X SCRAPER API] No more pages (next_token is None)")
                break
            
            # Respect rate limits: 300 requests per 15 minutes
            # Use 1 second delay between pages to be safe
            if len(all_tweets) < limit:
                time.sleep(1)
        
        logger.info(f"[X SCRAPER API] Successfully fetched {len(all_tweets)} tweets from {page} page(s)")
        return all_tweets
        
    except httpx.HTTPStatusError as e:
        logger.error(f"[X SCRAPER API] HTTP error: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"[X SCRAPER API] Error: {type(e).__name__}: {e}")
        return []


def _try_twitter_search(query: str, limit: int) -> list:
    """Deprecated: Use _try_twitter_api_v2 instead if Bearer Token is available."""
    # This function is kept for backward compatibility but is no longer used
    # The new implementation uses _try_twitter_api_v2 directly
    return []


# Removed _get_sample_ovh_complaints - no sample data allowed


def scrape_x_multi_queries(limit: int = 50):
    """Scrape X for customer feedback about OVH domain/TLD services using Nitter.
    
    Uses public Nitter instances (open-source Twitter alternative).
    Compatible with Python 3.13+
    
    Returns combined results from complaint-focused searches:
    - OVH domain tld complaint
    - OVH renew domain expensive
    - OVH registrar bad support
    - OVH domain expensive
    - problems OVH domain registration
    """
    
    queries = [
        "OVH domain TLD complaint",
        "OVH renew domain expensive",
        "OVH registrar bad support",
        "OVH domain expensive",
        "problems OVH domain registration",
    ]
    
    all_results = []
    seen_urls = set()
    
    for query_term in queries:
        try:
            logger.info(f"[X SCRAPER] Searching for: {query_term}")
            results = scrape_x(query_term, limit=limit // len(queries))
            
            # Avoid duplicates by URL
            for post in results:
                url = post.get('url')
                if url and url not in seen_urls:
                    all_results.append(post)
                    seen_urls.add(url)
                elif not url:
                    # If no URL, add anyway to avoid losing data
                    all_results.append(post)
        
        except Exception as e:
            logger.error(f"[X SCRAPER] Error scraping '{query_term}': {e}")
            continue
    
    logger.info(f"[X SCRAPER] Total posts scraped: {len(all_results)}")
    return all_results
