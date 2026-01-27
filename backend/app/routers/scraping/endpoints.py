"""Scraping endpoints for individual sources."""
from fastapi import APIRouter, Request, Query
from pydantic import BaseModel, Field, validator
from typing import List
import logging

from .base import log_scraping, process_and_save_items, get_query_with_base_keywords
from ...scraper import x_scraper, stackoverflow, github, reddit, trustpilot, ovh_forum, mastodon, g2_crowd, linkedin
from ...analysis import sentiment, country_detection
from ... import database as db

logger = logging.getLogger(__name__)

router = APIRouter()

# Response models
class ScrapeResult(BaseModel):
    """Response model for scraping operations."""
    posts: List[dict] = Field(
        default=[], 
        description="List of scraped posts with metadata (source, author, content, url, sentiment, etc.)"
    )
    total: int = Field(
        default=0, 
        description="Total number of posts scraped from the source",
        ge=0
    )
    added: int = Field(
        default=0, 
        description="Number of new posts successfully added to database (duplicates are excluded)",
        ge=0
    )
    errors: List[str] = Field(
        default=[], 
        description="List of error messages encountered during scraping or processing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "posts": [],
                "total": 25,
                "added": 20,
                "errors": []
            }
        }


class KeywordsPayload(BaseModel):
    """Payload for keyword-based scraping operations."""
    keywords: List[str] = Field(
        default_factory=list, 
        description="List of keywords to scrape. If empty, base keywords from settings will be used automatically. Maximum 50 keywords allowed.",
        max_items=50
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "keywords": ["OVH", "OVHCloud", "OVH hosting"]
            }
        }
    
    @validator('keywords')
    def check_keywords(cls, v):
        # Allow empty list - base keywords will be used automatically
        if v is None:
            return []
        if len(v) > 50:
            raise ValueError('Maximum 50 keywords allowed')
        # Clean and filter empty keywords
        cleaned = [k.strip() for k in v if k and k.strip()]
        # Return cleaned list (can be empty - base keywords will be used)
        return cleaned


@router.post(
    "/scrape/x", 
    response_model=ScrapeResult,
    summary="Scrape X/Twitter",
    description="""
    Scrape posts from X/Twitter (formerly Twitter) about OVH and related topics.
    
    **Features:**
    - Uses Nitter instances for public access (no API key required)
    - Automatic rotation across multiple Nitter instances for reliability
    - If no query is provided or query is "OVH", uses base keywords from settings
    - Performs sentiment analysis and relevance scoring on scraped posts
    - Automatically filters duplicates based on URL
    
    **Parameters:**
    - `query`: Search query (default: "OVH"). If "OVH" or empty, uses base keywords
    - `limit`: Maximum number of posts to scrape (default: 50, max recommended: 100)
    
    **Returns:**
    - Number of new posts added to database
    - Duplicate posts are automatically skipped
    """,
    tags=["Scraping"],
    responses={
        200: {
            "description": "Scraping completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "posts": [],
                        "total": 25,
                        "added": 20,
                        "errors": []
                    }
                }
            }
        },
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error during scraping"}
    }
)
async def scrape_x_endpoint(
    request: Request, 
    query: str = Query("OVH", description="Search query for X/Twitter. Use 'OVH' to trigger base keywords mode.", examples=["OVH VPS"]),
    limit: int = Query(100, description="Maximum number of posts to scrape", ge=1, le=200, examples=[100])
):
    """
    Scrape X/Twitter posts about OVH.
    
    If query is "OVH" or empty, automatically uses base keywords from settings.
    Posts are analyzed for sentiment and relevance before being saved to database.
    """
    source_name = "X/Twitter"
    items = []
    try:
        query_val = query if query and query != "OVH" else None
        log_scraping(source_name, "info", f"Starting scrape with query='{query_val}', limit={limit}")
        if query_val:
            items = x_scraper.scrape_x(query_val, limit=limit)
        else:
            items = x_scraper.scrape_x_multi_queries(limit=limit)
        
        if items is None:
            items = []
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping X/Twitter: {e}", exc_info=True)
        items = []
    
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    
    if skipped_duplicates > 0:
        log_scraping(source_name, "info", f"Skipped {skipped_duplicates} duplicate posts")
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@router.post(
    "/scrape/stackoverflow", 
    response_model=ScrapeResult,
    summary="Scrape Stack Overflow",
    description="""
    Scrape questions and discussions from Stack Overflow related to OVH products and services.
    
    **Features:**
    - Uses Stack Overflow API v2.3
    - Automatically combines query with base keywords from settings
    - Filters by relevance and tags
    - Performs sentiment analysis on question titles and bodies
    
    **Parameters:**
    - `query`: Search query (default: "OVH"). Automatically combined with base keywords
    - `limit`: Maximum number of questions to scrape (default: 50)
    
    **Example:**
    - Query "OVH" will search for: "OVH OR OVHCloud OR OVH VPS OR ..." (base keywords)
    """,
    tags=["Scraping"]
)
async def scrape_stackoverflow_endpoint(
    query: str = Query("OVH", description="Search query. Will be combined with base keywords.", examples=["OVH domain"]),
    limit: int = Query(50, description="Maximum number of questions to scrape", ge=1, le=100, examples=[50])
):
    """Scrape Stack Overflow questions about OVH."""
    source_name = "Stack Overflow"
    query = get_query_with_base_keywords(query, source_name)
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    items = []
    try:
        items = await stackoverflow.scrape_stackoverflow_async(query, limit=limit)
        if items is None:
            items = []
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Stack Overflow: {e}", exc_info=True)
        items = []
    
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@router.post(
    "/scrape/github", 
    response_model=ScrapeResult,
    summary="Scrape GitHub Issues",
    description="""
    Scrape GitHub issues and discussions mentioning OVH products or services.
    
    **Features:**
    - Uses GitHub API v3 (requires GITHUB_TOKEN in environment)
    - Searches across public repositories
    - Combines query with base keywords automatically
    - Analyzes issue titles, bodies, and comments
    
    **Requirements:**
    - `GITHUB_TOKEN` environment variable must be set for best results
    
    **Parameters:**
    - `query`: Search query (default: "OVH")
    - `limit`: Maximum number of issues to scrape (default: 50)
    """,
    tags=["Scraping"]
)
async def scrape_github_endpoint(
    request: Request, 
    query: str = Query("OVH", description="Search query for GitHub issues", examples=["OVH API"]),
    limit: int = Query(50, description="Maximum number of issues to scrape", ge=1, le=100, examples=[50])
):
    """Scrape GitHub issues mentioning OVH."""
    source_name = "GitHub"
    query = get_query_with_base_keywords(query, source_name)
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    items = []
    try:
        items = await github.scrape_github_issues_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping GitHub: {e}", exc_info=True)
        items = []
    
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@router.post(
    "/scrape/reddit", 
    response_model=ScrapeResult,
    summary="Scrape Reddit",
    description="""
    Scrape Reddit posts and discussions about OVH using RSS feeds and JSON API.
    
    **Features:**
    - Uses Reddit RSS feeds and JSON API (no authentication required)
    - Searches across multiple subreddits
    - Automatically combines query with base keywords
    - Respects Reddit rate limits
    
    **Parameters:**
    - `query`: Search query (default: "OVH")
    - `limit`: Maximum number of posts to scrape (default: 50)
    """,
    tags=["Scraping"]
)
async def scrape_reddit_endpoint(
    request: Request, 
    query: str = Query("OVH", description="Search query for Reddit", examples=["OVH hosting"]),
    limit: int = Query(50, description="Maximum number of posts to scrape", ge=1, le=100, examples=[50])
):
    """Scrape Reddit posts and discussions about OVH using RSS feeds."""
    source_name = "Reddit"
    query = get_query_with_base_keywords(query, source_name)
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    items = []
    try:
        items = await reddit.scrape_reddit_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Reddit: {e}", exc_info=True)
        items = []
    
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@router.post("/scrape/ovh-forum", response_model=ScrapeResult)
async def scrape_ovh_forum_endpoint(
    request: Request, 
    query: str = "OVH", 
    limit: int = 50,
    languages: str = None
):
    """Scrape OVH Community Forum for customer feedback and discussions.
    
    Args:
        query: Search query
        limit: Maximum number of posts to scrape
        languages: Comma-separated list of language codes (e.g., 'en,fr'). 
                   Defaults to scraping both English and French forums.
    """
    source_name = "OVH Forum"
    query = get_query_with_base_keywords(query, source_name)
    
    # Parse languages parameter
    language_list = None
    if languages:
        language_list = [lang.strip() for lang in languages.split(',') if lang.strip()]
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}, languages={language_list}")
    items = []
    try:
        items = ovh_forum.scrape_ovh_forum(query, limit=limit, languages=language_list)
        if items is None:
            items = []
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping OVH Forum: {e}", exc_info=True)
        items = []
    
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    
    if skipped_duplicates > 0:
        log_scraping(source_name, "info", f"Skipped {skipped_duplicates} duplicate posts")
    
    if errors > 0:
        log_scraping(source_name, "warning", f"Encountered {errors} errors during processing")
    return {'added': added}


@router.post("/scrape/mastodon", response_model=ScrapeResult)
async def scrape_mastodon_endpoint(request: Request, query: str = "OVH", limit: int = 50):
    """Scrape Mastodon for posts about OVH using public API."""
    source_name = "Mastodon"
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    items = []
    try:
        items = await mastodon.scrape_mastodon_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Mastodon: {e}", exc_info=True)
        items = []
    
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    
    if skipped_duplicates > 0:
        log_scraping(source_name, "info", f"Skipped {skipped_duplicates} duplicate posts")
    
    if errors > 0:
        log_scraping(source_name, "warning", f"Encountered {errors} errors during processing")
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@router.post("/scrape/linkedin", response_model=ScrapeResult)
async def scrape_linkedin_endpoint(request: Request, query: str = "OVH", limit: int = 50):
    """Scrape LinkedIn for posts about OVH (requires user's API credentials)."""
    source_name = "LinkedIn"
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    items = []
    try:
        items = await linkedin.scrape_linkedin_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping LinkedIn: {e}", exc_info=True)
        items = []
    
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    
    if skipped_duplicates > 0:
        log_scraping(source_name, "info", f"Skipped {skipped_duplicates} duplicate posts")
    
    if errors > 0:
        log_scraping(source_name, "warning", f"Encountered {errors} errors during processing")
    
    log_scraping(source_name, "success" if added > 0 else "warning",
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@router.post("/scrape/g2-crowd", response_model=ScrapeResult)
async def scrape_g2_crowd_endpoint(request: Request, query: str = "OVH", limit: int = 50):
    """Scrape G2 Crowd for OVH product reviews."""
    source_name = "G2 Crowd"
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    items = []
    try:
        items = g2_crowd.scrape_g2_crowd(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping G2 Crowd: {e}", exc_info=True)
        items = []
    
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    
    if skipped_duplicates > 0:
        log_scraping(source_name, "info", f"Skipped {skipped_duplicates} duplicate posts")
    
    if errors > 0:
        log_scraping(source_name, "warning", f"Encountered {errors} errors during processing")
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@router.post(
    "/scrape/trustpilot", 
    response_model=ScrapeResult,
    summary="Scrape Trustpilot Reviews",
    description="""
    Scrape customer reviews from Trustpilot about OVH services.
    
    **Features:**
    - Scrapes public Trustpilot reviews (no API key required, but TRUSTPILOT_API_KEY improves results)
    - Automatically detects country from review content
    - Performs sentiment analysis on review text
    - Extracts rating, date, and reviewer information
    
    **Parameters:**
    - `query`: Search query (default: "OVH domain")
    - `limit`: Maximum number of reviews to scrape (default: 50)
    
    **Note:**
    Trustpilot reviews are particularly valuable for understanding customer satisfaction.
    """,
    tags=["Scraping"]
)
async def scrape_trustpilot_endpoint(
    request: Request, 
    query: str = Query("OVH domain", description="Search query for Trustpilot reviews", examples=["OVH domain"]),
    limit: int = Query(200, description="Maximum number of reviews to scrape", ge=1, le=1000, examples=[200])
):
    """Scrape Trustpilot customer reviews about OVH."""
    source_name = "Trustpilot"
    query = get_query_with_base_keywords(query, source_name)
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    items = []
    try:
        items = await trustpilot.scrape_trustpilot_reviews_async(query, limit=limit)
        if items is None:
            items = []
        log_scraping(source_name, "info", f"Scraper returned {len(items)} reviews")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Trustpilot: {e}", exc_info=True)
        items = []
    
    # Use the same processing logic as other scrapers
    added, skipped_duplicates, errors = process_and_save_items(items, source_name)
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}

