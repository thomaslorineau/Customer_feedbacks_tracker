"""Stack Overflow API scraper for OVH-related questions."""
import httpx
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

STACKOVERFLOW_API = "https://api.stackexchange.com/2.3"


def scrape_stackoverflow(query="OVH", limit=30):
    """
    Scrape Stack Overflow for questions about OVH.
    Uses official Stack Exchange API - free and no authentication needed.
    Returns a list of post dictionaries ready for insertion.
    """
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
            timeout=10
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
                logger.info(f"✓ Stack Overflow: {post['author']} - {post['content'][:30]}")
            except Exception as e:
                logger.warning(f"Could not parse SO question: {e}")
                continue
        
        if not posts:
            raise RuntimeError("No valid Stack Overflow questions could be parsed")
        
        return posts
    
    except httpx.TimeoutError:
        raise RuntimeError("Stack Overflow API timeout - service may be unavailable")
    except httpx.HTTPError as e:
        raise RuntimeError(f"Stack Overflow API error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error scraping Stack Overflow: {str(e)}")
