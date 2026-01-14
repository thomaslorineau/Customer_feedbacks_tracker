"""Hacker News scraper for technical discussions about OVH."""
import httpx
from datetime import datetime
import logging
import time
from httpx import Timeout

logger = logging.getLogger(__name__)

HACKERNEWS_API = "https://hn.algolia.com/api/v1"
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def scrape_hackernews(query="OVH", limit=20):
    """
    Scrape Hacker News for discussions about OVH.
    Uses official Algolia API - very fast and reliable.
    Returns a list of post dictionaries ready for insertion.
    Implements retry logic with exponential backoff.
    """
    for attempt in range(MAX_RETRIES):
        try:
            params = {
                "query": query,
                "hitsPerPage": limit,
            }
            
            response = httpx.get(
                f"{HACKERNEWS_API}/search",
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=Timeout(10.0, connect=5.0)
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("hits"):
                raise RuntimeError(f"No Hacker News discussions found for: {query}")
            
            posts = []
            for hit in data["hits"][:limit]:
                try:
                    # Extract relevant info
                    post = {
                        "source": "Hacker News",
                        "author": hit.get("author", "Anonymous"),
                        "content": (hit.get("title") or hit.get("comment_text") or "")[:500],
                        "url": hit.get("url", hit.get("story_url", f"https://news.ycombinator.com/item?id={hit['objectID']}")),
                        "created_at": datetime.fromtimestamp(hit.get("created_at_i", 0)).isoformat() if hit.get("created_at_i") else datetime.now().isoformat(),
                        "sentiment_score": 0.0,  # Will be analyzed in main.py
                        "sentiment_label": "neutral",
                    }
                    posts.append(post)
                    logger.info(f"[HN] {post['author']} - {post['content'][:30]}")
                except Exception as e:
                    logger.warning(f"Could not parse HN hit: {e}")
                    continue
            
            if not posts:
                raise RuntimeError("No valid Hacker News posts could be parsed")
            
            return posts
        
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.NetworkError) as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] HN network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"[HN] Failed after {MAX_RETRIES} attempts: {e}")
                raise RuntimeError(f"Hacker News scraping failed after {MAX_RETRIES} retry attempts")
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] HN error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"[HN] Failed after {MAX_RETRIES} attempts: {e}")
                raise RuntimeError(f"Hacker News scraping failed after {MAX_RETRIES} retry attempts")


def get_mock_hackernews_posts(limit=20):
    """Return empty list - no fallback data."""
    return []
