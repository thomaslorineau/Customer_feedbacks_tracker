"""GitHub Issues scraper for OVH complaints."""
import httpx
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_HEADERS = {"Accept": "application/vnd.github.v3+json"}


def scrape_github_issues(query="OVH", limit=20):
    """
    Scrape GitHub issues for OVH domain customer complaints and feedback.
    Focuses on user experience issues and service feedback, not technical bugs.
    Returns a list of issue dictionaries ready for insertion.
    """
    try:
        # Build customer experience-focused queries
        domain_keywords = [
            "OVH domain",
            "OVH customer",
            "OVH support",
            "OVH renewal",
            "OVH experience",
        ]
        
        all_posts = []
        for keyword in domain_keywords:
            try:
                search_query = f"{keyword} is:issue"
                
                params = {
                    "q": search_query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": max(5, limit // len(domain_keywords)),
                }
                
                response = httpx.get(
                    f"{GITHUB_API_BASE}/search/issues",
                    params=params,
                    headers=GITHUB_HEADERS,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("items"):
                    logger.info(f"No GitHub issues found for: {keyword}")
                    continue
                
                for issue in data["items"]:
                    try:
                        # Extract relevant info
                        post = {
                            "source": "GitHub Issues",
                            "author": issue["user"]["login"],
                            "content": (issue["title"] + "\n" + (issue["body"] or ""))[:500],
                            "url": issue["html_url"],
                            "created_at": issue["created_at"],
                            "sentiment_score": 0.0,  # Will be analyzed in main.py
                            "sentiment_label": "neutral",
                        }
                        all_posts.append(post)
                        logger.info(f"✓ GitHub issue ({keyword}): {issue['title'][:50]}")
                    except Exception as e:
                        logger.warning(f"Could not parse GitHub issue: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Error searching for '{keyword}': {e}")
                continue
        
        if not all_posts:
            # Fallback: search with basic OVH term
            search_query = "OVH domain is:issue"
            params = {
                "q": search_query,
                "sort": "updated",
                "order": "desc",
                "per_page": limit,
            }
            
            response = httpx.get(
                f"{GITHUB_API_BASE}/search/issues",
                params=params,
                headers=GITHUB_HEADERS,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            for issue in data.get("items", [])[:limit]:
                try:
                    post = {
                        "source": "GitHub Issues",
                        "author": issue["user"]["login"],
                        "content": (issue["title"] + "\n" + (issue["body"] or ""))[:500],
                        "url": issue["html_url"],
                        "created_at": issue["created_at"],
                        "sentiment_score": 0.0,
                        "sentiment_label": "neutral",
                    }
                    all_posts.append(post)
                except Exception as e:
                    logger.warning(f"Could not parse GitHub issue: {e}")
                    continue
        
        posts = all_posts[:limit]
        if not posts:
            raise RuntimeError("No valid GitHub issues could be parsed")
        
        return posts
    
    except (httpx.ReadTimeout, httpx.ConnectError):
        raise RuntimeError("GitHub API timeout - service may be unavailable")
    except httpx.HTTPError as e:
        raise RuntimeError(f"GitHub API error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error scraping GitHub issues: {str(e)}")
