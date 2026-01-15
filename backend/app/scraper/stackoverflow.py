"""Stack Overflow API scraper for OVH-related questions."""
import httpx
from datetime import datetime
import logging
import time
from httpx import Timeout

logger = logging.getLogger(__name__)

STACKOVERFLOW_API = "https://api.stackexchange.com/2.3"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def scrape_stackoverflow(query="OVH", limit=30):
    """
    Scrape Stack Overflow for questions about OVH.
    Uses official Stack Exchange API - free and no authentication needed.
    Implements pagination to fetch multiple pages of results.
    Retries automatically on network errors.
    Returns a list of post dictionaries ready for insertion.
    """
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            all_posts = []
            page = 1
            max_pages = (limit // 30) + 1  # 30 items per page max
            pagesize = min(30, limit)  # Stack Exchange API max is 100, but we use 30 for better rate limit management
            
            while len(all_posts) < limit and page <= max_pages:
                params = {
                    "site": "stackoverflow",
                    "intitle": query,
                    "sort": "creation",
                    "order": "desc",
                    "pagesize": pagesize,
                    "page": page,  # Pagination parameter
                    "filter": "withbody",  # Includes body content
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
                        logger.info(f"[STACKOVERFLOW] API response: {data}")
                    break  # No more results
                
                for item in data["items"]:
                    if len(all_posts) >= limit:
                        break
                    try:
                        # Extract relevant info
                        post = {
                            "source": "Stack Overflow",
                            "author": item.get("owner", {}).get("display_name", "Anonymous"),
                            "content": (item.get("title", "") + "\n" + (item.get("body", "") or ""))[:500],
                            "url": item.get("link", ""),
                            "created_at": datetime.fromtimestamp(item.get("creation_date", 0)).isoformat() if item.get("creation_date") else datetime.now().isoformat(),
                            "sentiment_score": 0.0,  # Will be analyzed in main.py
                            "sentiment_label": "neutral",
                        }
                        all_posts.append(post)
                        logger.debug(f"[OK] Stack Overflow: {post['author']} - {post['content'][:30]}")
                    except Exception as e:
                        logger.warning(f"Could not parse SO question: {e}")
                        continue
                
                # Check if there are more pages
                if not data.get("has_more", False):
                    logger.info(f"[STACKOVERFLOW] No more pages available (has_more=False)")
                    break
                
                page += 1
                # Respect rate limits: 300 requests per day, so 1 second delay between pages
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
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Stack Overflow network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Stack Overflow scraper failed after {MAX_RETRIES} attempts: {e}")
                return []  # Return empty list instead of raising exception
        except httpx.HTTPError as e:
            last_error = e
            logger.error(f"Stack Overflow API error: {str(e)}")
            logger.error(f"Response status: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            return []  # Return empty list instead of raising exception
        except Exception as e:
            logger.error(f"Error scraping Stack Overflow: {str(e)}")
            last_error = e
            return []  # Return empty list instead of raising exception
    
    # All retries failed
    logger.error(f"Stack Overflow scraper failed after {MAX_RETRIES} attempts: {last_error}")
    return []
