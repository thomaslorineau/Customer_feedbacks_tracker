"""Trustpilot scraper for real customer reviews and complaints about OVH."""
import httpx
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

TRUSTPILOT_API = "https://api.trustpilot.com/v1"


def scrape_trustpilot_reviews(query="OVH", limit=20):
    """
    Scrape Trustpilot reviews for OVH customer feedback.
    Trustpilot is a major customer review platform with real user feedback.
    Returns a list of review dictionaries ready for insertion.
    """
    try:
        # Trustpilot API endpoint for searching reviews
        # Note: Trustpilot has rate limiting, using their public search
        params = {
            "q": query,
            "businessUnitId": "349d5a8279cb5700019b1b97",  # OVH's business unit ID on Trustpilot
            "pageSize": limit,
            "sort": "recency"
        }
        
        response = httpx.get(
            f"{TRUSTPILOT_API}/reviews/search",
            params=params,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        data = response.json()
        
        reviews = []
        for review in data.get("reviews", [])[:limit]:
            try:
                # Extract review content
                review_text = review.get("text", "")[:500]
                rating = review.get("rating", 0)
                
                # Map rating to sentiment label
                if rating >= 4:
                    sentiment_label = "positive"
                elif rating >= 3:
                    sentiment_label = "neutral"
                else:
                    sentiment_label = "negative"
                
                # Convert rating to sentiment score (-1 to 1)
                sentiment_score = (rating - 3) / 2  # 1-5 scale becomes -1 to 1
                
                post = {
                    "source": "Trustpilot",
                    "author": review.get("consumer", {}).get("displayName", "Anonymous"),
                    "content": review_text,
                    "url": review.get("links", {}).get("self", {}).get("href", "https://trustpilot.com"),
                    "created_at": review.get("createdAt", datetime.now().isoformat()),
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                }
                reviews.append(post)
                logger.info(f"✓ Trustpilot: {post['author']} ({rating}⭐) - {review_text[:40]}")
            except Exception as e:
                logger.warning(f"Could not parse Trustpilot review: {e}")
                continue
        
        if not reviews:
            raise RuntimeError(f"No Trustpilot reviews found for: {query}")
        
        return reviews
    
    except httpx.ReadTimeout:
        raise RuntimeError("Trustpilot API timeout - service may be unavailable")
    except httpx.HTTPError as e:
        raise RuntimeError(f"Trustpilot API error: {e}")
    except Exception as e:
        logger.error(f"Trustpilot scraper error: {e}")
        raise RuntimeError(f"Could not fetch Trustpilot reviews: {e}")


def scrape_trustpilot_mock(limit=20):
    """
    Return mock Trustpilot reviews as fallback.
    These represent typical customer feedback patterns.
    """
    mock_reviews = [
        {
            "source": "Trustpilot",
            "author": "Jean Martin",
            "content": "Domain renewal costs are way too high. Competitor offers same services at 30% less price. Very disappointed.",
            "url": "https://trustpilot.com/review/ovh.com",
            "created_at": datetime.now().isoformat(),
            "sentiment_score": -0.8,
            "sentiment_label": "negative",
        },
        {
            "source": "Trustpilot",
            "author": "Marie Dubois",
            "content": "Customer support response time is terrible. Waited 2 days for domain transfer issue. Not acceptable.",
            "url": "https://trustpilot.com/review/ovh.com",
            "created_at": datetime.now().isoformat(),
            "sentiment_score": -0.7,
            "sentiment_label": "negative",
        },
        {
            "source": "Trustpilot",
            "author": "Pierre Blanc",
            "content": "The control panel interface is outdated and confusing. Hard to find domain management features.",
            "url": "https://trustpilot.com/review/ovh.com",
            "created_at": datetime.now().isoformat(),
            "sentiment_score": -0.6,
            "sentiment_label": "negative",
        },
        {
            "source": "Trustpilot",
            "author": "Sophie Laurent",
            "content": "Automatic renewal without clear warning. Charged suddenly for domain renewal at premium price.",
            "url": "https://trustpilot.com/review/ovh.com",
            "created_at": datetime.now().isoformat(),
            "sentiment_score": -0.9,
            "sentiment_label": "negative",
        },
        {
            "source": "Trustpilot",
            "author": "Thomas Lefevre",
            "content": "Domain transfer process is unnecessarily complicated. Took hours to figure out the steps.",
            "url": "https://trustpilot.com/review/ovh.com",
            "created_at": datetime.now().isoformat(),
            "sentiment_score": -0.7,
            "sentiment_label": "negative",
        },
    ]
    
    return mock_reviews[:limit]
