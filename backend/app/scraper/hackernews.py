"""Hacker News scraper for technical discussions about OVH."""
import httpx
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

HACKERNEWS_API = "https://hn.algolia.com/api/v1"


def scrape_hackernews(query="OVH", limit=20):
    """
    Scrape Hacker News for discussions about OVH.
    Uses official Algolia API - very fast and reliable.
    Returns a list of post dictionaries ready for insertion.
    """
    try:
        params = {
            "query": query,
            "hitsPerPage": limit,
        }
        
        response = httpx.get(
            f"{HACKERNEWS_API}/search",
            params=params,
            timeout=10
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
                logger.info(f"✓ Hacker News: {post['author']} - {post['content'][:30]}")
            except Exception as e:
                logger.warning(f"Could not parse HN hit: {e}")
                continue
        
        if not posts:
            raise RuntimeError("No valid Hacker News posts could be parsed")
        
        return posts
    
    except (httpx.ReadTimeout, httpx.ConnectError):
        raise RuntimeError("Hacker News API timeout - service may be unavailable")
    except httpx.HTTPError as e:
        raise RuntimeError(f"Hacker News API error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error scraping Hacker News: {str(e)}")
