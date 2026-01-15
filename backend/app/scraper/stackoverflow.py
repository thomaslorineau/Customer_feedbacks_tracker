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
    Retries automatically on network errors.
    Returns a list of post dictionaries ready for insertion.
    """
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            params = {
                "site": "stackoverflow",
                "intitle": query,
                "sort": "creation",
                "order": "desc",
                "pagesize": limit,
                "filter": "withbody",  # Includes body content
            }
            
            response = httpx.get(
                f"{STACKOVERFLOW_API}/search/advanced",
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=Timeout(15.0, connect=5.0)
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("items"):
                raise RuntimeError(f"No Stack Overflow questions found for: {query}")
            
            posts = []
            for item in data["items"][:limit]:
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
                    posts.append(post)
                    logger.info(f"[OK] Stack Overflow: {post['author']} - {post['content'][:30]}")
                except Exception as e:
                    logger.warning(f"Could not parse SO question: {e}")
                    continue
            
            if not posts:
                raise RuntimeError("No valid Stack Overflow questions could be parsed")
            
            return posts
        
        except (httpx.TimeoutError, httpx.ConnectError, httpx.NetworkError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] Stack Overflow network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Stack Overflow scraper failed after {MAX_RETRIES} attempts: {e}")
        except httpx.HTTPError as e:
            last_error = e
            logger.error(f"Stack Overflow API error: {str(e)}")
            break
        except Exception as e:
            logger.error(f"Error scraping Stack Overflow: {str(e)}")
            last_error = e
            break
    
    # All retries failed
    raise RuntimeError(f"Could not fetch Stack Overflow questions after {MAX_RETRIES} attempts: {last_error}")
