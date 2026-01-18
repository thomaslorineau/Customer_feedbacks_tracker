import locale
from pathlib import Path
import os
import json
import datetime
import sys

# Fix encoding for Windows console (cp1252 can't handle emojis)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        # Python < 3.7 or reconfigure not available
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
import time
import threading
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
import httpx
from collections import defaultdict
from functools import wraps

logger = logging.getLogger(__name__)

from . import db
from .scraper import x_scraper, stackoverflow, news, github, reddit, trustpilot, ovh_forum, mastodon, g2_crowd
from .scraper import keyword_expander, linkedin
from .analysis import sentiment
from .analysis import country_detection
from .analysis import relevance_scorer
from .config import keywords_base

# Configuration du seuil de pertinence (peut être ajusté via variable d'environnement)
RELEVANCE_THRESHOLD = float(os.getenv('RELEVANCE_THRESHOLD', '0.3'))


def should_insert_post(post: dict) -> tuple:
    """
    Détermine si un post doit être inséré en base selon son score de pertinence.
    
    Special case: All Trustpilot posts from ovhcloud.com are considered relevant
    (no relevance filtering applied).
    
    Returns:
        (should_insert: bool, relevance_score: float)
    """
    # Special handling for Trustpilot: all posts from ovhcloud.com are relevant
    source = post.get('source', '').lower()
    url = post.get('url', '')
    
    if source == 'trustpilot' or 'trustpilot.com/review/ovhcloud.com' in url.lower():
        # All Trustpilot posts from ovhcloud.com are considered relevant
        return True, 1.0
    
    # For other sources, apply normal relevance filtering
    relevance_score = relevance_scorer.calculate_relevance_score(post)
    is_relevant = relevance_scorer.is_relevant(post, threshold=RELEVANCE_THRESHOLD)
    
    return is_relevant, relevance_score


# Configure locale for French support
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'fr_FR')
    except locale.Error:
        pass  # Locale not available, use system default


app = FastAPI(
    title="OVH Customer Feedbacks Tracker API",
    description="API for tracking and analyzing customer feedback from multiple sources (X/Twitter, Reddit, GitHub, Stack Overflow, Trustpilot, etc.)",
    version="1.0.1",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Mount static files for dashboard frontend
frontend_dashboard_path = Path(__file__).resolve().parents[2] / "frontend" / "dashboard"
frontend_path = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dashboard_path.exists():
    # Mount CSS and JS directories separately
    css_path = frontend_dashboard_path / "css"
    js_path = frontend_dashboard_path / "js"
    if css_path.exists():
        app.mount("/dashboard/css", StaticFiles(directory=str(css_path), html=False), name="dashboard-css")
    if js_path.exists():
        app.mount("/dashboard/js", StaticFiles(directory=str(js_path), html=False), name="dashboard-js")

# Mount assets (logos, images)
assets_path = frontend_path / "assets"
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path), html=False), name="assets")

# Mount shared CSS files
if (frontend_path / "css").exists():
    app.mount("/css", StaticFiles(directory=str(frontend_path / "css"), html=False), name="shared-css")

# Mount shared JS files
if (frontend_path / "js").exists():
    app.mount("/js", StaticFiles(directory=str(frontend_path / "js"), html=False), name="shared-js")

# Mount improvements static files (must be before /improvements route)
improvements_path = frontend_path / "improvements"
if improvements_path.exists():
    improvements_js_path = improvements_path / "js"
    if improvements_js_path.exists():
        app.mount("/improvements/js", StaticFiles(directory=str(improvements_js_path), html=False), name="improvements-js")

# Enable CORS for frontend - restrict to specific ports for security
import os
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8080,http://127.0.0.1:8000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Only add HSTS if using HTTPS in production
    if os.getenv("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Global exception handler to ensure JSON responses for all errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure all exceptions return JSON responses, especially for scraper endpoints."""
    import traceback
    error_type = type(exc).__name__
    error_msg = str(exc)
    
    # Skip handling for HTTPException and ValidationError (handled by specific handlers)
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        raise exc
    
    # Log the full traceback
    try:
        logger.error(f"Unhandled exception: {error_type}: {error_msg}", exc_info=True)
        traceback.print_exc()
    except Exception:
        # If logging fails, at least print to console
        print(f"ERROR: {error_type}: {error_msg}")
        traceback.print_exc()
    
    # Check if this is a scraper endpoint
    if request.url.path.startswith("/scrape/"):
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"{error_type}: {error_msg}",
                "error_type": error_type,
                "path": request.url.path
            }
        )
    
    # For other endpoints, return standard error
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {error_type}: {error_msg}",
            "error_type": error_type
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions and ensure JSON responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and ensure JSON responses."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


class ScrapeRequest(BaseModel):
    """Validated scrape request with input validation."""
    query: str = Field(default="OVH", min_length=1, max_length=100)
    limit: int = Field(default=50, ge=1, le=1000)


class ImprovementIdeaRequest(BaseModel):
    """Request model for generating improvement ideas."""
    posts: List[dict] = Field(..., description="List of posts to analyze")
    max_ideas: int = Field(default=5, ge=1, le=10, description="Maximum number of ideas to generate")


class ImprovementIdea(BaseModel):
    """Model for a single improvement idea."""
    title: str = Field(..., description="Short title for the idea")
    description: str = Field(..., description="Detailed description of the improvement idea")
    priority: str = Field(..., description="Priority level: high, medium, or low")
    related_posts_count: int = Field(..., description="Number of posts that support this idea")


class ImprovementIdeasResponse(BaseModel):
    """Response model for improvement ideas."""
    ideas: List[ImprovementIdea] = Field(..., description="List of generated improvement ideas")


class RecommendedActionRequest(BaseModel):
    """Request model for generating recommended actions."""
    posts: List[dict] = Field(..., description="List of posts to analyze")
    recent_posts: List[dict] = Field(default=[], description="Recent posts (last 48h)")
    stats: dict = Field(default={}, description="Statistics about posts")
    max_actions: int = Field(default=5, ge=1, le=10, description="Maximum number of actions to generate")


class RecommendedAction(BaseModel):
    """Model for a single recommended action."""
    icon: str = Field(..., description="Emoji icon for the action")
    text: str = Field(..., description="Action description")
    priority: str = Field(..., description="Priority level: high, medium, or low")


class RecommendedActionsResponse(BaseModel):
    """Response model for recommended actions."""
    actions: List[RecommendedAction] = Field(..., description="List of generated recommended actions")
    llm_available: bool = Field(default=True, description="Whether LLM was used to generate actions")


class PainPoint(BaseModel):
    """Model for a recurring pain point."""
    title: str = Field(..., description="Title of the pain point")
    description: str = Field(..., description="Brief description")
    icon: str = Field(..., description="Emoji icon")
    posts_count: int = Field(..., description="Number of posts mentioning this pain point")
    posts: List[dict] = Field(default=[], description="Sample posts related to this pain point")


class ProductOpportunity(BaseModel):
    """Model for product opportunity score."""
    product: str = Field(..., description="Product name")
    opportunity_score: int = Field(..., description="Opportunity score (0-100)")
    negative_posts: int = Field(..., description="Number of negative posts")
    total_posts: int = Field(..., description="Total posts for this product")
    color: str = Field(..., description="Color for visualization")


class PainPointsResponse(BaseModel):
    """Response model for recurring pain points."""
    pain_points: List[PainPoint] = Field(..., description="List of recurring pain points")
    total_pain_points: int = Field(..., description="Total number of pain points found")


class ProductDistributionResponse(BaseModel):
    """Response model for product distribution."""
    products: List[ProductOpportunity] = Field(..., description="List of products with opportunity scores")


class ScrapeResult(BaseModel):
    added: int


class KeywordsPayload(BaseModel):
    keywords: List[str]

    @validator('keywords')
    def check_keywords(cls, v):
        if not isinstance(v, list):
            raise ValueError('keywords must be a list')
        # Clean and validate individual keywords
        cleaned = []
        for item in v:
            s = str(item).strip()
            if not s:
                continue
            if len(s) > 200:
                raise ValueError('each keyword must be <= 200 chars')
            cleaned.append(s)
        if len(cleaned) > 10:
            raise ValueError('maximum 10 keywords allowed')
        return cleaned


# ===== SCHEDULER SETUP =====
scheduler = BackgroundScheduler()

def auto_scrape_job():
    """Scheduled job to scrape all sources automatically.

    Uses base keywords (fixed) + user keywords (saved queries) from the DB.
    Adds small sleeps to avoid hammering third-party endpoints (basic throttling).
    """
    print("🔄 Running scheduled scrape...")

    # Get user keywords (saved queries)
    user_keywords = db.get_saved_queries()
    
    # Combine base keywords (fixed) + user keywords
    all_keywords = keywords_base.get_all_keywords(user_keywords)
    
    if not all_keywords:
        # Fallback si vraiment rien
        all_keywords = keywords_base.get_all_base_keywords()
    
    queries = all_keywords

    # per-query limit for scheduled job
    per_query_limit = 20

    for qi, query in enumerate(queries):
        print(f"[AUTO SCRAPE] Query: {query}")

        # X/Twitter: use direct query
        try:
            items = x_scraper.scrape_x(query, limit=per_query_limit)

            added_count = 0
            duplicate_count = 0
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added_count += 1
                else:
                    duplicate_count += 1
            if duplicate_count > 0:
                print(f"✓ Added {added_count} posts from X/Twitter for '{query}' (skipped {duplicate_count} duplicates)")
            else:
                print(f"✓ Added {added_count} posts from X/Twitter for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping X (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # Stack Overflow
        try:
            items = stackoverflow.scrape_stackoverflow(query, limit=per_query_limit)
            added_count = 0
            duplicate_count = 0
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added_count += 1
                else:
                    duplicate_count += 1
            if duplicate_count > 0:
                print(f"✓ Added {added_count} posts from Stack Overflow for '{query}' (skipped {duplicate_count} duplicates)")
            else:
                print(f"✓ Added {added_count} posts from Stack Overflow for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping Stack Overflow (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # Reddit
        try:
            items = reddit.scrape_reddit(query, limit=per_query_limit)
            added_count = 0
            duplicate_count = 0
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added_count += 1
                else:
                    duplicate_count += 1
            if duplicate_count > 0:
                print(f"✓ Added {added_count} posts from Reddit for '{query}' (skipped {duplicate_count} duplicates)")
            else:
                print(f"✓ Added {added_count} posts from Reddit for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping Reddit (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # OVH Forum
        try:
            items = ovh_forum.scrape_ovh_forum(query, limit=per_query_limit)
            added_count = 0
            duplicate_count = 0
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added_count += 1
                else:
                    duplicate_count += 1
            if duplicate_count > 0:
                print(f"✓ Added {added_count} posts from OVH Forum for '{query}' (skipped {duplicate_count} duplicates)")
            else:
                print(f"✓ Added {added_count} posts from OVH Forum for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping OVH Forum (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # Mastodon
        try:
            items = mastodon.scrape_mastodon(query, limit=per_query_limit)
            added_count = 0
            duplicate_count = 0
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added_count += 1
                else:
                    duplicate_count += 1
            if duplicate_count > 0:
                print(f"✓ Added {added_count} posts from Mastodon for '{query}' (skipped {duplicate_count} duplicates)")
            else:
                print(f"✓ Added {added_count} posts from Mastodon for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping Mastodon (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # G2 Crowd
        try:
            items = g2_crowd.scrape_g2_crowd(query, limit=per_query_limit)
            added_count = 0
            duplicate_count = 0
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added_count += 1
                else:
                    duplicate_count += 1
            if duplicate_count > 0:
                print(f"✓ Added {added_count} reviews from G2 Crowd for '{query}' (skipped {duplicate_count} duplicates)")
            else:
                print(f"✓ Added {added_count} reviews from G2 Crowd for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping G2 Crowd (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # GitHub Issues
        try:
            items = github.scrape_github_issues(query, limit=per_query_limit)
            added_count = 0
            duplicate_count = 0
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added_count += 1
                else:
                    duplicate_count += 1
            if duplicate_count > 0:
                print(f"✓ Added {added_count} posts from GitHub Issues for '{query}' (skipped {duplicate_count} duplicates)")
            else:
                print(f"✓ Added {added_count} posts from GitHub Issues for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping GitHub Issues (non-fatal): {type(e).__name__}")

        # small pause between queries to avoid bursts
        time.sleep(1.0)


@app.on_event("startup")
def startup_event():
    db.init_db()
    
    # Automatically clean up sample/fake posts on startup
    try:
        deleted_count = db.delete_sample_posts()
        if deleted_count > 0:
            print(f"[CLEANUP] Removed {deleted_count} sample/fake posts from database")
    except Exception as e:
        print(f"[CLEANUP] Warning: Could not clean sample posts: {e}")
    
    # Automatically clean up non-OVH posts on startup
    try:
        deleted_count = db.delete_non_ovh_posts()
        if deleted_count > 0:
            print(f"[CLEANUP] Removed {deleted_count} non-OVH posts from database")
        else:
            print("[CLEANUP] All posts are OVH-related [OK]")
    except Exception as e:
        print(f"[CLEANUP] Warning: Could not clean non-OVH posts: {e}")
    
    # Start scheduler
    if not scheduler.running:
        scheduler.add_job(auto_scrape_job, 'interval', hours=3, id='auto_scrape')
        scheduler.start()
        print("[SCHEDULER] Started - will auto-scrape every 3 hours")


@app.on_event("shutdown")
def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
        print("[SCHEDULER] Stopped")


@app.post("/scrape/x", response_model=ScrapeResult)
async def scrape_x_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape X/Twitter. Accepts query via query param (or default behavior).

    For backward compatibility the endpoint returns the same `ScrapeResult`.
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
        import traceback
        traceback.print_exc()
        items = []

    added = 0
    skipped_duplicates = 0
    errors = 0
    try:
        for it in items:
            try:
                # Vérifier la pertinence avant traitement
                is_relevant, relevance_score = should_insert_post(it)
                if not is_relevant:
                    logger.debug(f"Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                    continue
                
                an = sentiment.analyze(it.get('content') or '')
                it['sentiment_score'] = an['score']
                it['sentiment_label'] = an['label']
                # Detect country
                country = country_detection.detect_country_from_post(it)
                inserted = db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': it.get('sentiment_score'),
                    'sentiment_label': it.get('sentiment_label'),
                    'language': it.get('language', 'unknown'),
                    'country': country,
                    'relevance_score': relevance_score,
                })
                if inserted:
                    added += 1
                else:
                    skipped_duplicates += 1
            except Exception as e:
                errors += 1
                logger.warning(f"Error processing X/Twitter item: {e}")
    except Exception as e:
        logger.error(f"Error processing X/Twitter items: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    
    if skipped_duplicates > 0:
        log_scraping(source_name, "info", f"Skipped {skipped_duplicates} duplicate posts")
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


# In-memory job store for background keyword scraping
JOBS = {}


# Security: Sanitize log messages to prevent leaking sensitive data
import re

def sanitize_log_message(message: str) -> str:
    """Remove sensitive data from log messages (API keys, tokens, etc.)."""
    if not message:
        return message
    
    # Mask API keys (OpenAI, Anthropic, GitHub, etc.)
    message = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***REDACTED***', message)
    message = re.sub(r'sk-ant-[a-zA-Z0-9-]{20,}', 'sk-ant-***REDACTED***', message)
    message = re.sub(r'ghp_[a-zA-Z0-9]{20,}', 'ghp_***REDACTED***', message)
    message = re.sub(r'github_pat_[a-zA-Z0-9_]{20,}', 'github_pat_***REDACTED***', message)
    
    # Mask tokens in URLs
    message = re.sub(r'(token|api_key|apikey|password|secret)=[a-zA-Z0-9_-]+', r'\1=***REDACTED***', message, flags=re.IGNORECASE)
    
    # Mask email addresses (optional - can be removed if needed for debugging)
    # message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***', message)
    
    return message


# Helper function to log scraping events
def log_scraping(source: str, level: str, message: str, details: dict = None):
    """Helper function to log scraping events to database and console."""
    try:
        # Sanitize message before logging
        sanitized_message = sanitize_log_message(message)
        try:
            db.add_scraping_log(source, level, sanitized_message, details)
        except Exception as e:
            # Don't fail the entire request if logging fails
            logger.warning(f"Failed to log scraping event: {e}")
        # Also print to console for immediate visibility
        level_emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "📝")
        print(f"{level_emoji} [{source}] {sanitized_message}")
    except Exception as e:
        # Fallback: just print to console if everything fails
        print(f"⚠️ [LOG ERROR] Failed to log: {e}")


async def _run_scrape_for_source_async(source: str, query: str, limit: int, use_keyword_expansion: bool = True):
    """
    Async version: Call the appropriate scraper and insert results into DB; return count added.
    
    Args:
        source: Source name (x, github, stackoverflow, etc.)
        query: Search query
        limit: Maximum number of posts to fetch
        use_keyword_expansion: Whether to expand keywords for better coverage
    
    Returns:
        Number of posts added to database. Returns 0 on any error to allow other tasks to continue.
    """
    try:
        # Async mapper - prefer async versions when available
        async_mapper = {
            'github': lambda q, l: github.scrape_github_issues_async(q, limit=l),
            'trustpilot': lambda q, l: trustpilot.scrape_trustpilot_reviews_async(q, limit=l),
            'stackoverflow': lambda q, l: stackoverflow.scrape_stackoverflow_async(q, limit=l),
            'reddit': lambda q, l: reddit.scrape_reddit_async(q, limit=l),
            'news': lambda q, l: news.scrape_google_news_async(q, limit=l),
            'mastodon': lambda q, l: mastodon.scrape_mastodon_async(q, limit=l),
            'linkedin': lambda q, l: linkedin.scrape_linkedin_async(q, limit=l),
        }
        
        # Sync mapper for scrapers not yet migrated (X, OVH Forum, G2 Crowd use Selenium/Playwright)
        sync_mapper = {
            'x': lambda q, l: x_scraper.scrape_x(q, limit=l),
            'ovh-forum': lambda q, l: ovh_forum.scrape_ovh_forum(q, limit=l),
            'g2-crowd': lambda q, l: g2_crowd.scrape_g2_crowd(q, limit=l),
        }
        
        # Try async first, fallback to sync
        async_func = async_mapper.get(source)
        sync_func = sync_mapper.get(source)
        
        if async_func is None and sync_func is None:
            return 0
        
        func = async_func if async_func else sync_func
        is_async = async_func is not None
        
        # Expand keywords if enabled
        queries_to_try = [query]
        if use_keyword_expansion:
            try:
                # Generate keyword variants (limit to avoid too many requests)
                expanded = keyword_expander.expand_keywords([query])
                # Limit to first 5 variants to avoid excessive requests
                # Prioritize original query + most relevant variants
                if len(expanded) > 1:
                    # Keep original first, then add up to 4 more variants
                    queries_to_try = [query] + expanded[1:5]
                    logger.info(f"[Keyword Expansion] Using {len(queries_to_try)} query variants for {source}: {queries_to_try[:3]}...")
            except Exception as e:
                logger.warning(f"[Keyword Expansion] Failed to expand keywords: {e}, using original query only")
                queries_to_try = [query]
        
        # Scrape with each query variant and combine results
        all_items = []
        seen_urls = set()  # Deduplicate by URL across queries
        
        for query_variant in queries_to_try:
            try:
                # Distribute limit across queries
                per_query_limit = max(limit // len(queries_to_try), 10)  # At least 10 per query
                
                # Call async or sync function
                if is_async:
                    items = await func(query_variant, per_query_limit)
                else:
                    # Run sync function in thread pool to avoid blocking event loop
                    items = await asyncio.to_thread(func, query_variant, per_query_limit)
                
                # Deduplicate by URL
                for item in items:
                    url = item.get('url', '')
                    if url and url not in seen_urls:
                        all_items.append(item)
                        seen_urls.add(url)
                    elif not url:
                        # If no URL, add anyway to avoid losing data
                        all_items.append(item)
                
                # If we have enough items, stop early
                if len(all_items) >= limit:
                    break
                    
            except Exception as e:
                try:
                    for job_id, info in JOBS.items():
                        if info.get('status') == 'running':
                            db.append_job_error(job_id, f"{source} (query: {query_variant}): {str(e)}")
                except Exception:
                    pass
                # Continue with next query variant
                continue
        
        # Limit to requested amount
        all_items = all_items[:limit]
        
        # Insert into database
        added = 0
        duplicates = 0
        filtered_by_relevance = 0
        for it in all_items:
            try:
                # Vérifier la pertinence avant traitement
                is_relevant, relevance_score = should_insert_post(it)
                if not is_relevant:
                    filtered_by_relevance += 1
                    logger.debug(f"[{source}] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                    continue
                
                an = sentiment.analyze(it.get('content') or '')
                # Detect country
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added += 1
                else:
                    duplicates += 1  # Duplicate detected and skipped
            except Exception:
                # ignore per-item failures
                continue
        
        if filtered_by_relevance > 0:
            logger.info(f"[{source}] Filtered {filtered_by_relevance} posts by relevance threshold")
        
        if duplicates > 0:
            print(f"  ⚠️ Skipped {duplicates} duplicate(s) from {source}")
        
        return added
    except Exception as e:
        # Catch any unhandled exceptions to prevent blocking other tasks
        error_msg = f"{source} (query: {query}): {str(e)}"
        logger.error(f"Error in _run_scrape_for_source_async: {error_msg}", exc_info=True)
        try:
            # Try to log error to job if available
            for job_id, info in JOBS.items():
                if info.get('status') == 'running':
                    db.append_job_error(job_id, error_msg)
        except Exception:
            pass
        # Return 0 to indicate failure but allow other tasks to continue
        return 0


def _run_scrape_for_source(source: str, query: str, limit: int, use_keyword_expansion: bool = True):
    """
    Synchronous wrapper for backward compatibility.
    Call the appropriate scraper and insert results into DB; return count added.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use run_until_complete in running loop, use sync version
            return _run_scrape_for_source_sync(source, query, limit, use_keyword_expansion)
        else:
            return loop.run_until_complete(_run_scrape_for_source_async(source, query, limit, use_keyword_expansion))
    except RuntimeError:
        return asyncio.run(_run_scrape_for_source_async(source, query, limit, use_keyword_expansion))


def _run_scrape_for_source_sync(source: str, query: str, limit: int, use_keyword_expansion: bool = True):
    """Synchronous fallback implementation."""
    mapper = {
        'x': lambda q, l: x_scraper.scrape_x(q, limit=l),
        'github': lambda q, l: github.scrape_github_issues(q, limit=l),
        'stackoverflow': lambda q, l: stackoverflow.scrape_stackoverflow(q, limit=l),
        'reddit': lambda q, l: reddit.scrape_reddit(q, limit=l),
        'news': lambda q, l: news.scrape_google_news(q, limit=l),
        'trustpilot': lambda q, l: trustpilot.scrape_trustpilot_reviews(q, limit=l),
    }
    func = mapper.get(source)
    if func is None:
        return 0
    
    # Expand keywords if enabled
    queries_to_try = [query]
    if use_keyword_expansion:
        try:
            expanded = keyword_expander.expand_keywords([query])
            if len(expanded) > 1:
                queries_to_try = [query] + expanded[1:5]
                logger.info(f"[Keyword Expansion] Using {len(queries_to_try)} query variants for {source}: {queries_to_try[:3]}...")
        except Exception as e:
            logger.warning(f"[Keyword Expansion] Failed to expand keywords: {e}, using original query only")
            queries_to_try = [query]
    
    # Scrape with each query variant and combine results
    all_items = []
    seen_urls = set()
    
    for query_variant in queries_to_try:
        try:
            per_query_limit = max(limit // len(queries_to_try), 10)
            items = func(query_variant, per_query_limit)
            
            for item in items:
                url = item.get('url', '')
                if url and url not in seen_urls:
                    all_items.append(item)
                    seen_urls.add(url)
                elif not url:
                    all_items.append(item)
            
            if len(all_items) >= limit:
                break
                
        except Exception as e:
            try:
                for job_id, info in JOBS.items():
                    if info.get('status') == 'running':
                        db.append_job_error(job_id, f"{source} (query: {query_variant}): {str(e)}")
            except Exception:
                pass
            continue
    
    all_items = all_items[:limit]
    
    # Insert into database
    added = 0
    duplicates = 0
    for it in all_items:
        try:
            an = sentiment.analyze(it.get('content') or '')
            country = country_detection.detect_country_from_post(it)
            if db.insert_post({
                'source': it.get('source'),
                'author': it.get('author'),
                'content': it.get('content'),
                'url': it.get('url'),
                'created_at': it.get('created_at'),
                'sentiment_score': an['score'],
                'sentiment_label': an['label'],
                'language': it.get('language', 'unknown'),
                'country': country,
            }):
                added += 1
            else:
                duplicates += 1
        except Exception:
            continue
    
    if duplicates > 0:
        print(f"  ⚠️ Skipped {duplicates} duplicate(s) from {source}")
    
    return added


async def _process_keyword_job_async(job_id: str, keywords: List[str], limit: int, concurrency: int, delay: float):
    """Async version of keyword job processing using asyncio.gather."""
    job = JOBS.get(job_id)
    if job is None:
        return
    job['status'] = 'running'
    # persist job
    try:
        db.create_job_record(job_id)
    except Exception:
        pass
    sources = ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
    total_tasks = len(keywords) * len(sources)
    job['progress'] = {'total': total_tasks, 'completed': 0}
    try:
        db.update_job_progress(job_id, total_tasks, 0)
    except Exception:
        pass

    try:
        # Create tasks for all scraping operations
        tasks = []
        for kw in keywords:
            if job.get('cancelled'):
                job['status'] = 'cancelled'
                return
            for s in sources:
                if job.get('cancelled'):
                    job['status'] = 'cancelled'
                    return
                # Create async task
                tasks.append(_run_scrape_for_source_async(s, kw, limit))
        
        # Process tasks with controlled concurrency using semaphore
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_with_semaphore(task):
            async with semaphore:
                if job.get('cancelled'):
                    return None
                try:
                    # Add timeout to prevent tasks from blocking indefinitely (5 minutes max per task)
                    result = await asyncio.wait_for(task, timeout=300.0)
                    return result
                except asyncio.TimeoutError:
                    error_msg = "Task timed out after 5 minutes"
                    if job.get('status') == 'running':
                        job['errors'].append(error_msg)
                        try:
                            db.append_job_error(job_id, error_msg)
                        except Exception:
                            pass
                    logger.warning(f"Task timed out for job {job_id}")
                    return None
                except Exception as e:
                    # Log error but continue with other tasks
                    error_msg = str(e)
                    if job.get('status') == 'running':
                        job['errors'].append(error_msg)
                        try:
                            db.append_job_error(job_id, error_msg)
                        except Exception:
                            pass
                    logger.warning(f"Task error for job {job_id}: {error_msg}")
                    return None
        
        # Execute tasks and process results as they complete (for real-time progress updates)
        # Create tasks explicitly for as_completed
        wrapped_tasks = [asyncio.create_task(process_with_semaphore(task)) for task in tasks]
        
        # Use as_completed to process results as they finish, updating progress in real-time
        for completed_task in asyncio.as_completed(wrapped_tasks):
            if job.get('cancelled'):
                job['status'] = 'cancelled'
                return
            
            try:
                result = await completed_task
                
                # Always increment progress counter, regardless of success or failure
                job['progress']['completed'] += 1
                try:
                    db.update_job_progress(job_id, total_tasks, job['progress']['completed'])
                except Exception:
                    pass
                
                if isinstance(result, Exception):
                    # Task raised an exception
                    error_msg = str(result)
                    if job.get('status') == 'running':
                        job['errors'].append(error_msg)
                        try:
                            db.append_job_error(job_id, error_msg)
                        except Exception:
                            pass
                    logger.warning(f"Task failed for job {job_id}: {error_msg}")
                elif result is None:
                    # Task returned None (likely failed but handled gracefully)
                    logger.debug(f"Task returned None for job {job_id}")
                else:
                    # Task succeeded
                    job['results'].append({'added': result})
                    try:
                        db.append_job_result(job_id, {'added': result})
                    except Exception:
                        pass
                
                # Gentle delay between processing results
                await asyncio.sleep(delay)
                
            except Exception as e:
                # Unexpected error while processing completed task
                error_msg = str(e)
                if job.get('status') == 'running':
                    job['errors'].append(error_msg)
                    try:
                        db.append_job_error(job_id, error_msg)
                    except Exception:
                        pass
                logger.error(f"Error processing completed task for job {job_id}: {error_msg}", exc_info=True)
                
                # Still count as completed even if there was an error
                job['progress']['completed'] += 1
                try:
                    db.update_job_progress(job_id, total_tasks, job['progress']['completed'])
                except Exception:
                    pass

        job['status'] = 'completed'
        try:
            db.finalize_job(job_id, 'completed')
        except Exception:
            pass
    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)
        try:
            db.append_job_error(job_id, str(e))
            db.finalize_job(job_id, 'failed', str(e))
        except Exception:
            pass


def _process_keyword_job(job_id: str, keywords: List[str], limit: int, concurrency: int, delay: float):
    """Synchronous wrapper that runs async job processing."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to use a different approach
            # Create a new thread with its own event loop
            import threading
            def run_async():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(_process_keyword_job_async(job_id, keywords, limit, concurrency, delay))
                finally:
                    new_loop.close()
            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()
            # Don't join - let it run in background
        else:
            loop.run_until_complete(_process_keyword_job_async(job_id, keywords, limit, concurrency, delay))
    except RuntimeError:
        asyncio.run(_process_keyword_job_async(job_id, keywords, limit, concurrency, delay))


async def _process_single_source_job_async(job_id: str, source: str, query: str, limit: int):
    """Process a single source scraping job with granular progress updates."""
    job = JOBS.get(job_id)
    if job is None:
        return
    
    job['status'] = 'running'
    
    # Use 100 steps for fine-grained progress: 5% init, 85% scraping (with heartbeat), 10% processing
    total_steps = 100
    init_steps = 5
    scraping_start = init_steps
    scraping_end = 90
    processing_start = scraping_end
    
    # Persist job
    try:
        db.create_job_record(job_id)
        db.update_job_progress(job_id, total_steps, 0)
    except Exception:
        pass
    
    job['progress'] = {'total': total_steps, 'completed': 0}
    
    # Heartbeat task to update progress during scraping
    heartbeat_running = True
    heartbeat_step = scraping_start
    
    async def progress_heartbeat():
        """Update progress gradually during scraping to show activity."""
        nonlocal heartbeat_step
        logger.info(f"[{source}] Starting heartbeat for job {job_id[:8]}... (step {heartbeat_step} -> {scraping_end})")
        while heartbeat_running and heartbeat_step < scraping_end:
            await asyncio.sleep(0.5)  # Update every 500ms
            if not heartbeat_running:
                logger.info(f"[{source}] Heartbeat stopped (heartbeat_running=False)")
                break
            # Increment progress gradually (max 1 step per heartbeat)
            if heartbeat_step < scraping_end - 1:
                heartbeat_step += 1
                # Update both in-memory job and DB
                job['progress']['completed'] = heartbeat_step
                try:
                    db.update_job_progress(job_id, total_steps, heartbeat_step)
                    logger.debug(f"[{source}] Heartbeat updated progress to {heartbeat_step}/{total_steps} ({heartbeat_step*100//total_steps}%)")
                except Exception as e:
                    logger.warning(f"[{source}] Failed to update job progress in DB: {e}")
            else:
                logger.info(f"[{source}] Heartbeat reached max step {scraping_end}")
                break
        logger.info(f"[{source}] Heartbeat finished at step {heartbeat_step}")
    
    try:
        # Check for cancellation
        if job.get('cancelled'):
            job['status'] = 'cancelled'
            db.finalize_job(job_id, 'cancelled', 'cancelled by user')
            return
        
        # Steps 1-5: Initialization (5%)
        for step in range(1, init_steps + 1):
            job['progress']['completed'] = step
            try:
                db.update_job_progress(job_id, total_steps, step)
            except Exception:
                pass
            await asyncio.sleep(0.1)  # Small delay for smooth progress
        
        # Use base keywords if query is empty
        if not query or query.strip() == "":
            base_keywords = keywords_base.get_all_base_keywords()
            if base_keywords:
                query = base_keywords[0] if len(base_keywords) == 1 else " ".join(base_keywords[:3])
                log_scraping(source, "info", f"Using base keywords: {query}")
        
        # Steps 6-90: Scraping (85% with heartbeat)
        job['progress']['completed'] = scraping_start
        try:
            db.update_job_progress(job_id, total_steps, scraping_start)
        except Exception:
            pass
        
        # Start heartbeat task BEFORE running scraper
        heartbeat_task = asyncio.create_task(progress_heartbeat())
        
        # Run the scraper (heartbeat will update progress during this)
        try:
            added = await _run_scrape_for_source_async(source, query, limit, use_keyword_expansion=False)
        finally:
            # Stop heartbeat after scraper completes
            heartbeat_running = False
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            # Set progress to scraping_end when scraper finishes
            job['progress']['completed'] = scraping_end
            try:
                db.update_job_progress(job_id, total_steps, scraping_end)
            except Exception:
                pass
        
        # Steps 91-95: Processing results (5%)
        for step in range(processing_start, processing_start + 5):
            job['progress']['completed'] = step
            try:
                db.update_job_progress(job_id, total_steps, step)
            except Exception:
                pass
            await asyncio.sleep(0.1)
        
        job['results'].append({'added': added, 'source': source})
        
        # Steps 96-99: Finalizing (4%)
        for step in range(processing_start + 5, total_steps):
            job['progress']['completed'] = step
            try:
                db.update_job_progress(job_id, total_steps, step)
            except Exception:
                pass
            await asyncio.sleep(0.05)
        
        # Step 100: Cleanup duplicates (final step)
        job['progress']['completed'] = total_steps - 1
        try:
            db.update_job_progress(job_id, total_steps, total_steps - 1)
        except Exception:
            pass
        
        # Cleanup duplicates after scraping
        try:
            deleted_duplicates = db.delete_duplicate_posts()
            if deleted_duplicates > 0:
                logger.info(f"[{source}] Cleaned up {deleted_duplicates} duplicate posts after scraping")
                job['results'].append({'duplicates_removed': deleted_duplicates})
        except Exception as e:
            logger.warning(f"[{source}] Failed to cleanup duplicates: {e}")
        
        # Final step: 100%
        job['progress']['completed'] = total_steps
        try:
            db.update_job_progress(job_id, total_steps, total_steps)
            db.append_job_result(job_id, {'added': added, 'source': source})
        except Exception:
            pass
        
        # Finalize job
        job['status'] = 'completed'
        db.finalize_job(job_id, 'completed')
        
    except Exception as e:
        heartbeat_running = False
        error_msg = str(e)
        job['status'] = 'failed'
        job['error'] = error_msg
        job['errors'].append(error_msg)
        try:
            db.append_job_error(job_id, error_msg)
            db.finalize_job(job_id, 'failed', error_msg)
        except Exception:
            pass
        logger.error(f"Error in single source job {job_id}: {error_msg}", exc_info=True)


def _process_single_source_job(job_id: str, source: str, query: str, limit: int):
    """Wrapper to run async job processing in a thread."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create new thread with new event loop
            import threading
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(_process_single_source_job_async(job_id, source, query, limit))
                finally:
                    new_loop.close()
            t = threading.Thread(target=run_in_new_loop, daemon=True)
            t.start()
        else:
            loop.run_until_complete(_process_single_source_job_async(job_id, source, query, limit))
    except RuntimeError:
        asyncio.run(_process_single_source_job_async(job_id, source, query, limit))


@app.post('/scrape/{source}/job')
async def start_single_source_job(
    source: str,
    query: str = "",
    limit: int = 50
):
    """Start a background job for a single scraper source.
    
    Args:
        source: Source name (x, github, stackoverflow, reddit, trustpilot, etc.)
        query: Search query (optional, uses base keywords if empty)
        limit: Maximum number of posts to fetch (default: 50)
    
    Returns:
        Job ID and source information
    """
    # Validate source
    valid_sources = ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}")
    
    # Create job
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'id': job_id,
        'status': 'pending',
        'progress': {'total': 1, 'completed': 0},
        'results': [],
        'errors': [],
        'cancelled': False,
        'error': None,
    }
    
    # Create DB record
    try:
        db.create_job_record(job_id)
        db.update_job_progress(job_id, 1, 0)
    except Exception:
        pass
    
    # Start background thread
    t = threading.Thread(target=_process_single_source_job, args=(job_id, source, query, limit), daemon=True)
    t.start()
    
    return {
        'job_id': job_id,
        'source': source,
        'query': query,
        'limit': limit,
        'total_tasks': 1
    }


@app.post('/scrape/keywords')
async def start_keyword_scrape(payload: KeywordsPayload, limit: int = 50, concurrency: int = 2, delay: float = 0.5):
    """Start a background job that scrapes multiple keywords across sources with throttling.

    Request body: JSON: { "keywords": ["a","b"] }. Returns job id.
    Les keywords utilisateur sont combinés avec les keywords de base (fixes).
    """
    user_keywords = payload.keywords or []
    
    # Combiner keywords de base (fixes) + keywords utilisateur
    all_keywords = keywords_base.get_all_keywords(user_keywords)
    
    if not all_keywords:
        raise HTTPException(status_code=400, detail='No keywords available (base + user)')

    # Calculate total tasks BEFORE creating job so frontend gets correct total immediately
    sources = ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
    total_tasks = len(all_keywords) * len(sources)

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'id': job_id,
        'status': 'pending',
        'progress': {'total': total_tasks, 'completed': 0},
        'results': [],
        'errors': [],
        'cancelled': False,
        'error': None,
    }

    # create DB record for job (best-effort)
    try:
        db.create_job_record(job_id)
        db.update_job_progress(job_id, total_tasks, 0)
    except Exception:
        pass

    # Start background thread (utiliser all_keywords au lieu de keywords)
    t = threading.Thread(target=_process_keyword_job, args=(job_id, all_keywords, limit, concurrency, delay), daemon=True)
    t.start()

    return {'job_id': job_id, 'total_keywords': len(all_keywords), 'base_keywords': len(keywords_base.get_all_base_keywords()), 'user_keywords': len(user_keywords)}


@app.get('/scrape/jobs')
async def get_all_jobs_endpoint(status: Optional[str] = None, limit: int = 100):
    """
    Get all scraping jobs with optional filters.
    
    Query parameters:
    - status: Filter by status (pending, running, completed, failed)
    - limit: Limit number of results (default: 100)
    """
    try:
        jobs = db.get_all_jobs(status=status, limit=limit)
        return {
            'jobs': jobs,
            'total': len(jobs)
        }
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/scrape/jobs/{job_id}')
async def get_job_status(job_id: str):
    # First check in-memory JOBS dict (faster, more up-to-date)
    job = JOBS.get(job_id)
    if job:
        # Also sync with DB to ensure we have the latest progress
        # The heartbeat updates DB, so we merge DB progress into in-memory job
        try:
            db_job = db.get_job_record(job_id)
            if db_job and db_job.get('progress'):
                # DB is source of truth for progress (updated by heartbeat)
                job['progress'] = db_job['progress']
                # Also sync status if different
                if db_job.get('status') and db_job['status'] != job.get('status'):
                    job['status'] = db_job['status']
        except Exception as e:
            # If DB read fails, just use in-memory job
            logger.debug(f"Could not sync job {job_id} with DB: {e}")
        return job
    # fall back to DB persisted job record
    try:
        rec = db.get_job_record(job_id)
        if rec:
            return rec
    except Exception:
        pass
    raise HTTPException(status_code=404, detail='Job not found')


@app.post('/scrape/jobs/{job_id}/cancel')
async def cancel_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        # try to mark persisted job as cancelled
        try:
            db.append_job_error(job_id, 'cancelled by user')
            db.finalize_job(job_id, 'cancelled', 'cancelled by user')
            return {'cancelled': True}
        except Exception:
            raise HTTPException(status_code=404, detail='Job not found')
    job['cancelled'] = True
    try:
        db.append_job_error(job_id, 'cancelled by user')
        db.finalize_job(job_id, 'cancelled', 'cancelled by user')
    except Exception:
        pass
    return {'cancelled': True}


@app.post('/scrape/jobs/cancel-all')
async def cancel_all_jobs():
    """
    Cancel all running jobs.
    """
    try:
        cancelled_count = 0
        
        # Cancel jobs in memory
        for job_id, job in list(JOBS.items()):
            if job.get('status') in ['running', 'pending']:
                job['cancelled'] = True
                job['status'] = 'cancelled'
                try:
                    db.append_job_error(job_id, 'cancelled by user (cancel-all)')
                    db.finalize_job(job_id, 'cancelled', 'cancelled by user (cancel-all)')
                except Exception:
                    pass
                cancelled_count += 1
        
        # Cancel jobs in database
        all_jobs = db.get_all_jobs(status='running')
        for job in all_jobs:
            try:
                db.append_job_error(job['id'], 'cancelled by user (cancel-all)')
                db.finalize_job(job['id'], 'cancelled', 'cancelled by user (cancel-all)')
                cancelled_count += 1
            except Exception:
                pass
        
        # Also check pending jobs
        pending_jobs = db.get_all_jobs(status='pending')
        for job in pending_jobs:
            try:
                db.append_job_error(job['id'], 'cancelled by user (cancel-all)')
                db.finalize_job(job['id'], 'cancelled', 'cancelled by user (cancel-all)')
                cancelled_count += 1
            except Exception:
                pass
        
        return {
            'cancelled': cancelled_count,
            'message': f'Successfully cancelled {cancelled_count} job(s)'
        }
    except Exception as e:
        logger.error(f"Error cancelling all jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        pass
    return {'cancelled': True}


@app.post("/scrape/stackoverflow", response_model=ScrapeResult)
async def scrape_stackoverflow_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Stack Overflow questions about OVH."""
    source_name = "Stack Overflow"
    
    # Use base keywords if query is empty or default
    if not query or query.strip() == "" or query == "OVH":
        base_keywords = keywords_base.get_all_base_keywords()
        if base_keywords:
            query = base_keywords[0] if len(base_keywords) == 1 else " ".join(base_keywords[:3])
            log_scraping(source_name, "info", f"Using base keywords: {query}")
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    items = []
    try:
        # Use async version
        items = await stackoverflow.scrape_stackoverflow_async(query, limit=limit)
        if items is None:
            items = []
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Stack Overflow: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        # Continue with empty items list instead of returning early
        items = []

    added = 0
    skipped_duplicates = 0
    errors = 0
    filtered_by_relevance = 0
    try:
        for it in items:
            try:
                # Vérifier la pertinence avant traitement
                is_relevant, relevance_score = should_insert_post(it)
                if not is_relevant:
                    filtered_by_relevance += 1
                    logger.debug(f"[Stack Overflow] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                    continue
                
                an = sentiment.analyze(it.get('content') or '')
                it['sentiment_score'] = an['score']
                it['sentiment_label'] = an['label']
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': it.get('sentiment_score'),
                    'sentiment_label': it.get('sentiment_label'),
                    'language': it.get('language', 'unknown'),
                }):
                    added += 1
                else:
                    skipped_duplicates += 1
            except Exception as e:
                errors += 1
                print(f"[STACKOVERFLOW SCRAPER] Error processing item: {e}")
                logger.warning(f"Error processing Stack Overflow item: {e}")
    except Exception as e:
        print(f"[STACKOVERFLOW SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@app.post("/scrape/github", response_model=ScrapeResult)
async def scrape_github_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape GitHub issues mentioning OVH."""
    source_name = "GitHub"
    
    # Use base keywords if query is empty or default
    if not query or query.strip() == "" or query == "OVH":
        base_keywords = keywords_base.get_all_base_keywords()
        if base_keywords:
            query = base_keywords[0] if len(base_keywords) == 1 else " ".join(base_keywords[:3])
            log_scraping(source_name, "info", f"Using base keywords: {query}")
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    try:
        # Use async version
        items = await github.scrape_github_issues_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping GitHub: {e}")
        import traceback
        traceback.print_exc()
        return {'added': 0}

    added = 0
    skipped_duplicates = 0
    errors = 0
    try:
        for it in items:
            try:
                an = sentiment.analyze(it.get('content') or '')
                it['sentiment_score'] = an['score']
                it['sentiment_label'] = an['label']
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': it.get('sentiment_score'),
                    'sentiment_label': it.get('sentiment_label'),
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added += 1
                else:
                    skipped_duplicates += 1
            except Exception as e:
                errors += 1
                print(f"[GITHUB SCRAPER] Error processing item: {e}")
                logger.warning(f"Error processing GitHub item: {e}")
    except Exception as e:
        print(f"[GITHUB SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@app.post("/scrape/reddit", response_model=ScrapeResult)
async def scrape_reddit_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Reddit posts and discussions about OVH using RSS feeds."""
    source_name = "Reddit"
    
    # Use base keywords if query is empty or default
    if not query or query.strip() == "" or query == "OVH":
        base_keywords = keywords_base.get_all_base_keywords()
        if base_keywords:
            query = base_keywords[0] if len(base_keywords) == 1 else " ".join(base_keywords[:3])
            log_scraping(source_name, "info", f"Using base keywords: {query}")
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    try:
        # Use async version
        items = await reddit.scrape_reddit_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Reddit: {e}")
        import traceback
        traceback.print_exc()
        return {'added': 0}

    added = 0
    skipped_duplicates = 0
    errors = 0
    filtered_by_relevance = 0
    try:
        for it in items:
            try:
                # Vérifier la pertinence avant traitement
                is_relevant, relevance_score = should_insert_post(it)
                if not is_relevant:
                    filtered_by_relevance += 1
                    logger.debug(f"[Reddit] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                    continue
                
                an = sentiment.analyze(it.get('content') or '')
                it['sentiment_score'] = an['score']
                it['sentiment_label'] = an['label']
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': it.get('sentiment_score'),
                    'sentiment_label': it.get('sentiment_label'),
                    'language': it.get('language', 'unknown'),
                }):
                    added += 1
                else:
                    skipped_duplicates += 1
            except Exception as e:
                errors += 1
                print(f"[REDDIT SCRAPER] Error processing item: {e}")
                logger.warning(f"Error processing Reddit item: {e}")
    except Exception as e:
        print(f"[REDDIT SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@app.post("/scrape/ovh-forum", response_model=ScrapeResult)
async def scrape_ovh_forum_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape OVH Community Forum for customer feedback and discussions."""
    try:
        items = ovh_forum.scrape_ovh_forum(query, limit=limit)
    except Exception as e:
        logger.error(f"Error scraping OVH Forum: {e}")
        return {'added': 0}
    
    added = 0
    skipped_duplicates = 0
    filtered_by_relevance = 0
    for it in items:
        try:
            # Vérifier la pertinence avant traitement
            is_relevant, relevance_score = should_insert_post(it)
            if not is_relevant:
                filtered_by_relevance += 1
                logger.debug(f"[OVH Forum] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                continue
            
            an = sentiment.analyze(it.get('content') or '')
            it['sentiment_score'] = an['score']
            it['sentiment_label'] = an['label']
            if db.insert_post({
                'source': it.get('source'),
                'author': it.get('author'),
                'content': it.get('content'),
                'url': it.get('url'),
                'created_at': it.get('created_at'),
                'sentiment_score': it.get('sentiment_score'),
                'sentiment_label': it.get('sentiment_label'),
                'language': it.get('language', 'unknown'),
            }):
                added += 1
            else:
                skipped_duplicates += 1
        except Exception as e:
            logger.warning(f"Error processing OVH Forum item: {e}")
    
    if filtered_by_relevance > 0:
        logger.info(f"[OVH Forum] Filtered {filtered_by_relevance} posts by relevance threshold")
    if skipped_duplicates > 0:
        logger.info(f"✓ Added {added} posts from OVH Forum (skipped {skipped_duplicates} duplicates)")
    return {'added': added}


@app.post("/scrape/mastodon", response_model=ScrapeResult)
async def scrape_mastodon_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Mastodon for posts about OVH using public API."""
    source_name = "Mastodon"
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    try:
        # Use async version
        items = await mastodon.scrape_mastodon_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Mastodon: {e}")
        return {'added': 0}
    
    added = 0
    skipped_duplicates = 0
    filtered_by_relevance = 0
    for it in items:
        try:
            # Vérifier la pertinence avant traitement
            is_relevant, relevance_score = should_insert_post(it)
            if not is_relevant:
                filtered_by_relevance += 1
                logger.debug(f"[Mastodon] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                continue
            
            an = sentiment.analyze(it.get('content') or '')
            it['sentiment_score'] = an['score']
            it['sentiment_label'] = an['label']
            if db.insert_post({
                'source': it.get('source'),
                'author': it.get('author'),
                'content': it.get('content'),
                'url': it.get('url'),
                'created_at': it.get('created_at'),
                'sentiment_score': it.get('sentiment_score'),
                'sentiment_label': it.get('sentiment_label'),
                'language': it.get('language', 'unknown'),
            }):
                added += 1
            else:
                skipped_duplicates += 1
        except Exception as e:
            logger.warning(f"Error processing Mastodon item: {e}")
    
    if filtered_by_relevance > 0:
        logger.info(f"[Mastodon] Filtered {filtered_by_relevance} posts by relevance threshold")
    if skipped_duplicates > 0:
        logger.info(f"✓ Added {added} posts from Mastodon (skipped {skipped_duplicates} duplicates)")
    return {'added': added}


@app.post("/scrape/linkedin", response_model=ScrapeResult)
async def scrape_linkedin_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape LinkedIn for posts about OVH (requires user's API credentials)."""
    source_name = "LinkedIn"
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    try:
        # Use async version
        items = await linkedin.scrape_linkedin_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping LinkedIn: {e}")
        import traceback
        traceback.print_exc()
        return {'added': 0}
    
    added = 0
    skipped_duplicates = 0
    errors = 0
    filtered_by_relevance = 0
    try:
        for it in items:
            try:
                # Vérifier la pertinence avant traitement
                is_relevant, relevance_score = should_insert_post(it)
                if not is_relevant:
                    filtered_by_relevance += 1
                    logger.debug(f"[LinkedIn] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                    continue
                
                an = sentiment.analyze(it.get('content') or '')
                it['sentiment_score'] = an['score']
                it['sentiment_label'] = an['label']
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': it.get('sentiment_score'),
                    'sentiment_label': it.get('sentiment_label'),
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added += 1
                else:
                    skipped_duplicates += 1
            except Exception as e:
                errors += 1
                logger.warning(f"Error processing LinkedIn item: {e}")
    except Exception as e:
        logger.error(f"Error processing LinkedIn posts: {e}")
        import traceback
        traceback.print_exc()
    
    log_scraping(source_name, "success" if added > 0 else "warning",
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@app.post("/scrape/g2-crowd", response_model=ScrapeResult)
async def scrape_g2_crowd_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape G2 Crowd for OVH product reviews."""
    source_name = "G2 Crowd"
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    try:
        items = g2_crowd.scrape_g2_crowd(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping G2 Crowd: {e}")
        import traceback
        traceback.print_exc()
        return {'added': 0}
    
    added = 0
    skipped_duplicates = 0
    errors = 0
    filtered_by_relevance = 0
    
    print(f"[G2 CROWD ENDPOINT] Processing {len(items)} items for database insertion...")
    for it in items:
        try:
            # Vérifier la pertinence avant traitement
            is_relevant, relevance_score = should_insert_post(it)
            if not is_relevant:
                filtered_by_relevance += 1
                logger.debug(f"[G2 Crowd] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                continue
            
            an = sentiment.analyze(it.get('content') or '')
            it['sentiment_score'] = an['score']
            it['sentiment_label'] = an['label']
            if db.insert_post({
                'source': it.get('source'),
                'author': it.get('author'),
                'content': it.get('content'),
                'url': it.get('url'),
                'created_at': it.get('created_at'),
                'sentiment_score': it.get('sentiment_score'),
                'sentiment_label': it.get('sentiment_label'),
                'language': it.get('language', 'unknown'),
            }):
                added += 1
            else:
                skipped_duplicates += 1
        except Exception as e:
            errors += 1
            print(f"[G2 CROWD ENDPOINT] Error processing item: {e}")
            logger.warning(f"Error processing G2 Crowd item: {e}")
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@app.post("/scrape/news", response_model=ScrapeResult)
async def scrape_news_endpoint(query: str = "OVH", limit: int = 50):
    source_name = "Google News"
    
    # Use base keywords if query is empty or default
    if not query or query.strip() == "" or query == "OVH":
        base_keywords = keywords_base.get_all_base_keywords()
        if base_keywords:
            # Use first base keyword as default, or combine them
            query = base_keywords[0] if len(base_keywords) == 1 else " ".join(base_keywords[:3])
            log_scraping(source_name, "info", f"Using base keywords: {query}")
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    try:
        # Use async version
        items = await news.scrape_google_news_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} items")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Google News: {e}")
        import traceback
        traceback.print_exc()
        return {'added': 0}

    added = 0
    skipped_duplicates = 0
    errors = 0
    filtered_by_relevance = 0
    try:
        for it in items:
            try:
                # Vérifier la pertinence avant traitement
                is_relevant, relevance_score = should_insert_post(it)
                if not is_relevant:
                    filtered_by_relevance += 1
                    logger.debug(f"[Google News] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                    continue
                
                an = sentiment.analyze(it.get('content') or '')
                it['sentiment_score'] = an['score']
                it['sentiment_label'] = an['label']
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': it.get('sentiment_score'),
                    'sentiment_label': it.get('sentiment_label'),
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added += 1
                else:
                    skipped_duplicates += 1
            except Exception as e:
                errors += 1
                print(f"[NEWS SCRAPER] Error processing item: {e}")
                logger.warning(f"Error processing News item: {e}")
    except Exception as e:
        print(f"[NEWS SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@app.post("/scrape/trustpilot", response_model=ScrapeResult)
async def scrape_trustpilot_endpoint(query: str = "OVH domain", limit: int = 50):
    """Scrape Trustpilot customer reviews about OVH."""
    source_name = "Trustpilot"
    
    # Use base keywords if query is empty or default
    if not query or query.strip() == "" or query == "OVH domain":
        base_keywords = keywords_base.get_all_base_keywords()
        if base_keywords:
            query = base_keywords[0] if len(base_keywords) == 1 else " ".join(base_keywords[:3])
            log_scraping(source_name, "info", f"Using base keywords: {query}")
    
    log_scraping(source_name, "info", f"Starting scrape with query='{query}', limit={limit}")
    try:
        # Use async version
        items = await trustpilot.scrape_trustpilot_reviews_async(query, limit=limit)
        log_scraping(source_name, "info", f"Scraper returned {len(items)} reviews")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        log_scraping(source_name, "error", f"Scraper error: {error_msg}")
        logger.error(f"Error scraping Trustpilot: {e}")
        import traceback
        traceback.print_exc()
        return {'added': 0}

    added = 0
    skipped_duplicates = 0
    errors = 0
    try:
        for it in items:
            try:
                # Skip sentiment analysis if already provided by scraper
                if not it.get('sentiment_score'):
                    an = sentiment.analyze(it.get('content') or '')
                    it['sentiment_score'] = an['score']
                    it['sentiment_label'] = an['label']
                
                country = country_detection.detect_country_from_post(it)
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': it.get('sentiment_score'),
                    'sentiment_label': it.get('sentiment_label'),
                    'language': it.get('language', 'unknown'),
                    'country': country,
                }):
                    added += 1
                else:
                    skipped_duplicates += 1
            except Exception as e:
                errors += 1
                print(f"[TRUSTPILOT SCRAPER] Error processing item: {e}")
                logger.warning(f"Error processing Trustpilot item: {e}")
    except Exception as e:
        print(f"[TRUSTPILOT SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    log_scraping(source_name, "success" if added > 0 else "warning", 
                f"Scraping completed: {added} added, {skipped_duplicates} duplicates, {errors} errors")
    return {'added': added}


@app.get('/settings/queries')
async def get_saved_queries():
    """Return saved keywords/queries from DB (user keywords only)."""
    return {'keywords': db.get_saved_queries()}


@app.post('/settings/queries')
async def post_saved_queries(payload: KeywordsPayload):
    """Save provided keywords list. Expects JSON: { "keywords": ["a","b"] } (user keywords only)."""
    db.save_queries(payload.keywords)
    return {'saved': len(payload.keywords)}


@app.get('/settings/base-keywords')
async def get_base_keywords():
    """Get base keywords by category (editable base keywords)."""
    try:
        keywords_by_category = db.get_base_keywords()
        return {
            'brands': keywords_by_category.get('brands', []),
            'products': keywords_by_category.get('products', []),
            'problems': keywords_by_category.get('problems', []),
            'leadership': keywords_by_category.get('leadership', [])
        }
    except Exception as e:
        logger.error(f"Error getting base keywords: {e}")
        # Fallback to defaults
        from .config.keywords_base import get_base_keywords_from_db
        return get_base_keywords_from_db()


class BaseKeywordsPayload(BaseModel):
    """Payload for updating base keywords."""
    brands: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list)
    leadership: List[str] = Field(default_factory=list)


@app.post('/settings/base-keywords')
async def update_base_keywords(payload: BaseKeywordsPayload):
    """Update base keywords by category."""
    try:
        keywords_by_category = {
            'brands': payload.brands,
            'products': payload.products,
            'problems': payload.problems,
            'leadership': payload.leadership
        }
        db.save_base_keywords(keywords_by_category)
        return {'success': True, 'keywords': keywords_by_category}
    except Exception as e:
        logger.error(f"Error updating base keywords: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update base keywords: {str(e)}")


@app.post('/admin/cleanup-hackernews-posts')
async def cleanup_hackernews_posts():
    """
    Delete all posts from Hacker News (replaced by Reddit).
    """
    try:
        deleted_count = db.delete_hackernews_posts()
        return {
            'deleted': deleted_count,
            'message': f'Successfully removed {deleted_count} Hacker News posts from database'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/admin/duplicates-stats')
async def get_duplicates_stats():
    """
    Get statistics about duplicate posts before deletion.
    Returns counts of duplicates by URL and by content+author+source.
    """
    try:
        conn, is_duckdb = db.get_db_connection()
        c = conn.cursor()
        
        # Count duplicates by URL
        if is_duckdb:
            url_duplicates_query = """
                SELECT url, COUNT(*) as count
                FROM posts
                WHERE url IS NOT NULL AND url != ''
                GROUP BY url
                HAVING COUNT(*) > 1
            """
        else:
            url_duplicates_query = """
                SELECT url, COUNT(*) as count
                FROM posts
                WHERE url IS NOT NULL AND url != ''
                GROUP BY url
                HAVING COUNT(*) > 1
            """
        
        c.execute(url_duplicates_query)
        url_duplicates = c.fetchall()
        url_duplicates_count = sum(count - 1 for _, count in url_duplicates)  # -1 to keep one
        
        # Count duplicates by content+author+source
        if is_duckdb:
            content_duplicates_query = """
                SELECT content, author, source, COUNT(*) as count
                FROM posts
                WHERE content IS NOT NULL AND content != ''
                GROUP BY content, author, source
                HAVING COUNT(*) > 1
            """
        else:
            content_duplicates_query = """
                SELECT content, author, source, COUNT(*) as count
                FROM posts
                WHERE content IS NOT NULL AND content != ''
                GROUP BY content, author, source
                HAVING COUNT(*) > 1
            """
        
        c.execute(content_duplicates_query)
        content_duplicates = c.fetchall()
        content_duplicates_count = sum(count - 1 for _, _, _, count in content_duplicates)  # -1 to keep one
        
        # Total unique duplicate groups
        total_duplicate_groups = len(url_duplicates) + len(content_duplicates)
        
        # Total posts that would be deleted
        total_to_delete = url_duplicates_count + content_duplicates_count
        
        conn.close()
        
        return {
            'duplicates_by_url': {
                'groups': len(url_duplicates),
                'posts_to_delete': url_duplicates_count
            },
            'duplicates_by_content': {
                'groups': len(content_duplicates),
                'posts_to_delete': content_duplicates_count
            },
            'total': {
                'duplicate_groups': total_duplicate_groups,
                'posts_to_delete': total_to_delete
            }
        }
    except Exception as e:
        logger.error(f"Error getting duplicates stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/admin/cleanup-duplicates')
async def cleanup_duplicates():
    """
    Delete duplicate posts from the database.
    Duplicates are identified by same URL or same content+author+source.
    Keeps the oldest post (lowest ID) and deletes the rest.
    """
    try:
        deleted_count = db.delete_duplicate_posts()
        return {
            'deleted': deleted_count,
            'message': f'Successfully removed {deleted_count} duplicate posts from database'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/admin/cleanup-non-ovh-posts')
async def cleanup_non_ovh_posts():
    """
    Delete all posts from the database that do NOT mention OVH or its brands.
    Keeps posts containing: ovh, ovhcloud, ovh cloud, kimsufi, soyoustart
    """
    try:
        deleted_count = db.delete_non_ovh_posts()
        return {
            'deleted': deleted_count,
            'message': f'Successfully removed {deleted_count} non-OVH posts from database'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@app.get("/api/posts-by-country")
async def get_posts_by_country():
    """Retourne la répartition des posts par pays."""
    # Récupérer tous les posts (ou un grand nombre)
    posts = db.get_posts(limit=10000, offset=0)
    
    country_counts = {}
    for post in posts:
        country = post.get('country')
        # Filter out invalid country codes (like 'EU' which is not a real country code)
        if country and country != 'EU' and len(country) == 2:
            country_counts[country] = country_counts.get(country, 0) + 1
    
    # Trier par nombre de posts décroissant
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "countries": dict(sorted_countries),
        "total": len(posts),
        "total_with_country": sum(country_counts.values()),
        "country_names": {code: country_detection.get_country_name(code) for code in country_counts.keys()}
    }


@app.get("/api/posts-by-source")
async def get_posts_by_source():
    """Retourne la répartition des posts par source."""
    # Récupérer tous les posts
    posts = db.get_posts(limit=10000, offset=0)
    
    source_counts = {}
    source_sentiment = {}  # Track sentiment per source
    
    for post in posts:
        source = post.get('source', 'Unknown')
        # Normalize GitHub sources: GitHub Issues and GitHub Discussions → GitHub
        if source == 'GitHub Issues' or source == 'GitHub Discussions':
            source = 'GitHub'
        sentiment = post.get('sentiment_label', 'neutral')
        
        if source not in source_counts:
            source_counts[source] = 0
            source_sentiment[source] = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        source_counts[source] += 1
        if sentiment in source_sentiment[source]:
            source_sentiment[source][sentiment] += 1
    
    # Trier par nombre de posts décroissant
    sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "sources": dict(sorted_sources),
        "total": len(posts),
        "sentiment_by_source": source_sentiment
    }


@app.get("/posts")
async def get_posts(limit: int = 20, offset: int = 0, language: str = None):
    """Get posts from database, excluding sample data."""
    posts = db.get_posts(limit=limit, offset=offset, language=language)
    # Filter out sample posts and add timestamp
    filtered = []
    for post in posts:
        url = post.get('url', '')
        is_sample = (
            '/sample' in url or
            'example.com' in url or
            '/status/174' in url or
            url == 'https://trustpilot.com/sample'
        )
        if not is_sample:
            # Add timestamp for date calculations
            try:
                created_at = post.get('created_at', '')
                if created_at:
                    dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    post['created_at_timestamp'] = dt.timestamp()
                else:
                    post['created_at_timestamp'] = 0
            except:
                post['created_at_timestamp'] = 0
            
            # Add default engagement metrics (can be enhanced later)
            post['views'] = post.get('views', 0)
            post['comments'] = post.get('comments', 0)
            post['reactions'] = post.get('reactions', 0)
            
            filtered.append(post)
    return filtered


async def generate_ideas_with_llm(posts: List[dict], max_ideas: int = 5) -> List[ImprovementIdea]:
    """
    Generate improvement ideas using LLM API.
    Supports OpenAI, Anthropic, or local LLM via environment variables.
    """
    # Prepare posts summary
    posts_summary = []
    for post in posts[:20]:  # Limit to 20 posts for context
        posts_summary.append({
            'content': post.get('content', '')[:500],  # Limit content length
            'sentiment': post.get('sentiment_label', 'neutral'),
            'source': post.get('source', 'Unknown')
        })
    
    # Create prompt
    prompt = f"""Analyze the following customer feedback posts about OVH products and generate {max_ideas} concrete product improvement ideas.

Posts to analyze:
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

For each idea, provide:
1. A clear, concise title (max 60 characters)
2. A detailed description explaining the improvement and why it's needed
3. Priority level (high/medium/low) based on impact and frequency
4. Count of related posts that support this idea

Format your response as a JSON array with this structure:
[
  {{
    "title": "Idea title",
    "description": "Detailed description...",
    "priority": "high|medium|low",
    "related_posts_count": 3
  }}
]

Focus on actionable improvements that address real customer pain points. Be specific and practical."""

    # Try to use LLM API (OpenAI, Anthropic, or local)
    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    
    if not api_key and llm_provider in ['openai', 'anthropic']:
        # Fallback: Generate ideas using rule-based approach
        return generate_ideas_fallback(posts, max_ideas)
    
    try:
        if llm_provider == 'openai' or (not os.getenv('LLM_PROVIDER') and api_key):
            # Use OpenAI API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                        'messages': [
                            {'role': 'system', 'content': 'You are a product improvement analyst. Generate actionable improvement ideas based on customer feedback.'},
                            {'role': 'user', 'content': prompt}
                        ],
                        'temperature': 0.7,
                        'max_tokens': 2000
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON from response
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    ideas_data = json.loads(json_match.group())
                    return [ImprovementIdea(**idea) for idea in ideas_data]
        
        elif llm_provider == 'anthropic':
            # Use Anthropic API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                        'max_tokens': 2000,
                        'messages': [
                            {'role': 'user', 'content': prompt}
                        ]
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['content'][0]['text']
                
                # Parse JSON from response
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    ideas_data = json.loads(json_match.group())
                    return [ImprovementIdea(**idea) for idea in ideas_data]
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.warning(f"LLM API authentication failed (401): Invalid or expired API key. Using fallback.")
        else:
            logger.warning(f"LLM API error ({e.response.status_code}): {e}. Using fallback.")
        # Fallback to rule-based generation
        return generate_ideas_fallback(posts, max_ideas)
    except Exception as e:
        logger.warning(f"LLM API error: {type(e).__name__}: {e}. Using fallback.")
        # Fallback to rule-based generation
        return generate_ideas_fallback(posts, max_ideas)
    
    # Fallback if no API configured
    return generate_ideas_fallback(posts, max_ideas)


def generate_ideas_fallback(posts: List[dict], max_ideas: int = 5) -> List[ImprovementIdea]:
    """Fallback rule-based idea generation when LLM is not available."""
    ideas = []
    
    # Analyze posts by theme
    themes = {
        'Performance': {'keywords': ['slow', 'lag', 'performance', 'speed', 'timeout'], 'posts': []},
        'Reliability': {'keywords': ['down', 'crash', 'error', 'bug', 'broken'], 'posts': []},
        'Support': {'keywords': ['support', 'help', 'ticket', 'response', 'wait'], 'posts': []},
        'Documentation': {'keywords': ['documentation', 'docs', 'guide', 'tutorial'], 'posts': []},
        'UI/UX': {'keywords': ['interface', 'ui', 'ux', 'confusing', 'unclear'], 'posts': []}
    }
    
    for post in posts:
        content_lower = post.get('content', '').lower()
        for theme, data in themes.items():
            if any(kw in content_lower for kw in data['keywords']):
                data['posts'].append(post)
    
    # Generate ideas from themes
    for theme, data in sorted(themes.items(), key=lambda x: len(x[1]['posts']), reverse=True)[:max_ideas]:
        if len(data['posts']) > 0:
            ideas.append(ImprovementIdea(
                title=f"Improve {theme}",
                description=f"Based on {len(data['posts'])} customer feedback posts, there are recurring issues related to {theme.lower()}. Consider reviewing and improving this aspect of the product.",
                priority='high' if len(data['posts']) >= 5 else 'medium' if len(data['posts']) >= 2 else 'low',
                related_posts_count=len(data['posts'])
            ))
    
    return ideas


@app.post("/generate-improvement-ideas", response_model=ImprovementIdeasResponse)
async def generate_improvement_ideas(request: ImprovementIdeaRequest):
    """Generate product improvement ideas based on customer feedback posts using LLM."""
    try:
        ideas = await generate_ideas_with_llm(request.posts, request.max_ideas)
        return ImprovementIdeasResponse(ideas=ideas)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ideas: {str(e)}")


def calculate_opportunity_score(product_posts: List[dict], all_posts: List[dict]) -> int:
    """
    Calculate opportunity score for a product based on:
    - Frequency of negative feedback (40%)
    - Recency of issues (30%)
    - Engagement level (views, comments, reactions) (30%)
    """
    if not product_posts:
        return 0
    
    negative_count = sum(1 for p in product_posts if p.get('sentiment_label') == 'negative')
    negative_ratio = negative_count / len(product_posts) if product_posts else 0
    
    # Recency: weight recent posts (last 30 days) more
    now = time.time()
    recent_negative = sum(1 for p in product_posts 
                         if p.get('sentiment_label') == 'negative' 
                         and (p.get('created_at_timestamp', 0) or 0) >= (now - 30 * 24 * 3600))
    recency_score = min(recent_negative / max(len(product_posts) * 0.3, 1), 1.0)
    
    # Engagement: average views, comments, reactions
    total_engagement = sum(
        (p.get('views', 0) or 0) + 
        (p.get('comments', 0) or 0) * 2 + 
        (p.get('reactions', 0) or 0) * 1.5
        for p in product_posts
    )
    avg_engagement = total_engagement / len(product_posts) if product_posts else 0
    engagement_score = min(avg_engagement / 1000, 1.0)  # Normalize to 0-1
    
    # Calculate final score (0-100)
    score = int((negative_ratio * 0.4 + recency_score * 0.3 + engagement_score * 0.3) * 100)
    return min(score, 100)


@app.get("/api/improvements-summary")
async def get_improvements_summary():
    """
    Generate a concise LLM summary of top improvement opportunities.
    Returns a single sentence summarizing the main improvement areas.
    """
    try:
        # Get top pain points
        pain_points_response = await get_pain_points(days=30, limit=5)
        pain_points = pain_points_response.pain_points if hasattr(pain_points_response, 'pain_points') else []
        
        if not pain_points:
            return {"summary": "No improvement opportunities identified at this time."}
        
        # Prepare summary for LLM
        pain_points_text = "\n".join([
            f"- {pp.title}: {pp.description} ({pp.posts_count} posts)"
            for pp in pain_points[:5]
        ])
        
        prompt = f"""Analyze the following improvement opportunities based on OVH customer feedback and generate ONE concise sentence (maximum 120 characters) that summarizes the main improvement ideas.

Identified opportunities:
{pain_points_text}

Generate a sentence in English that summarizes the top improvement ideas in a clear and actionable way. Generate ONLY the sentence, without JSON formatting or quotes."""
        
        # Try LLM API
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        
        if api_key:
            try:
                if llm_provider == 'openai' or (not os.getenv('LLM_PROVIDER') and api_key):
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(
                                'https://api.openai.com/v1/chat/completions',
                                headers={
                                    'Authorization': f'Bearer {api_key}',
                                    'Content-Type': 'application/json'
                                },
                                json={
                                    'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                                    'messages': [
                                        {'role': 'system', 'content': 'You are a product analyst. Generate concise and actionable summaries.'},
                                        {'role': 'user', 'content': prompt}
                                    ],
                                    'temperature': 0.7,
                                    'max_tokens': 150
                                }
                            )
                            response.raise_for_status()
                            result = response.json()
                            summary = result['choices'][0]['message']['content'].strip()
                            # Remove quotes if present
                            summary = summary.strip('"').strip("'")
                            return {"summary": summary}
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 401:
                            logger.warning(f"LLM API authentication failed (401): Invalid or expired API key. Using fallback summary.")
                        else:
                            logger.warning(f"LLM API error ({e.response.status_code}): {e}. Using fallback summary.")
                        return {"summary": "Analyzing improvement opportunities..."}
                    except Exception as e:
                        logger.warning(f"LLM API error: {type(e).__name__}: {e}. Using fallback summary.")
                        return {"summary": "Analyzing improvement opportunities..."}
                
                elif llm_provider == 'anthropic':
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            'https://api.anthropic.com/v1/messages',
                            headers={
                                'x-api-key': api_key,
                                'anthropic-version': '2023-06-01',
                                'Content-Type': 'application/json'
                            },
                            json={
                                'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                                'max_tokens': 150,
                                'messages': [
                                    {'role': 'user', 'content': prompt}
                                ]
                            }
                        )
                        response.raise_for_status()
                        result = response.json()
                        summary = result['content'][0]['text'].strip()
                        summary = summary.strip('"').strip("'")
                        return {"summary": summary}
            except Exception as e:
                logger.warning(f"LLM summary generation failed: {e}, using fallback")
        
        # Fallback: Generate simple summary
        top_3 = pain_points[:3]
        themes = [pp.title for pp in top_3]
        if len(themes) == 1:
            summary = f"Priority improvement: {themes[0]}"
        elif len(themes) == 2:
            summary = f"Priority improvements: {themes[0]} and {themes[1]}"
        else:
            summary = f"Top improvements: {', '.join(themes[:2])} and {themes[2] if len(themes) > 2 else 'others'}"
        
        return {"summary": summary}
        
    except Exception as e:
        logger.error(f"Error generating improvements summary: {e}")
        return {"summary": "Analyzing improvement opportunities..."}


@app.get("/api/pain-points", response_model=PainPointsResponse)
async def get_pain_points(days: int = 30, limit: int = 5):
    """
    Analyze recurring pain points from customer feedback over the last N days.
    Uses keyword clustering and frequency analysis.
    """
    # Get posts from last N days
    now = time.time()
    cutoff_time = now - (days * 24 * 3600)
    
    all_posts = db.get_posts(limit=10000, offset=0)
    
    # Add timestamps
    for post in all_posts:
        try:
            created_at = post.get('created_at', '')
            if created_at:
                dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                post['created_at_timestamp'] = dt.timestamp()
            else:
                post['created_at_timestamp'] = 0
        except:
            post['created_at_timestamp'] = 0
    
    recent_posts = [
        p for p in all_posts 
        if p.get('sentiment_label') == 'negative' 
        and (p.get('created_at_timestamp', 0) or 0) >= cutoff_time
    ]
    
    # Define pain point patterns
    pain_point_patterns = {
        'Refund Delays': {
            'keywords': ['refund', 'rembours', 'remboursement', 'pending refund', 'delayed refund'],
            'icon': '💸',
            'description': 'Late or pending refunds'
        },
        'Billing Clarity': {
            'keywords': ['billing', 'invoice', 'facture', 'charge', 'confusing', 'unclear'],
            'icon': '📄',
            'description': 'Confusing invoices & charges'
        },
        'HTTPS/SSL Renewal': {
            'keywords': ['ssl', 'https', 'certificate', 'renewal', 'expired', 'certificat'],
            'icon': '🔒',
            'description': 'SSL renewal reminders'
        },
        'Support Response Time': {
            'keywords': ['support', 'response', 'slow', 'unresponsive', 'waiting', 'ticket'],
            'icon': '⏱️',
            'description': 'Slow or unresponsive support'
        },
        'VPS Backups': {
            'keywords': ['backup', 'vps backup', 'backup error', 'backup fail', 'sauvegarde'],
            'icon': '💾',
            'description': 'Backup errors & failures'
        },
        'Domain Issues': {
            'keywords': ['domain', 'dns', 'nameserver', 'domaine', 'expired domain'],
            'icon': '🌐',
            'description': 'Domain registration and DNS issues'
        },
        'Email Problems': {
            'keywords': ['email', 'mail', 'mx record', 'smtp', 'imap', 'exchange'],
            'icon': '📧',
            'description': 'Email delivery and configuration issues'
        }
    }
    
    pain_points = []
    for title, pattern in pain_point_patterns.items():
        matching_posts = []
        keywords_lower = [k.lower() for k in pattern['keywords']]
        
        for post in recent_posts:
            content_lower = (post.get('content', '') or '').lower()
            if any(keyword in content_lower for keyword in keywords_lower):
                matching_posts.append(post)
        
        if matching_posts:
            pain_points.append(PainPoint(
                title=title,
                description=pattern['description'],
                icon=pattern['icon'],
                posts_count=len(matching_posts),
                posts=matching_posts[:5]  # Sample posts
            ))
    
    # Sort by posts count (most frequent first)
    pain_points.sort(key=lambda x: x.posts_count, reverse=True)
    
    return PainPointsResponse(
        pain_points=pain_points[:limit],
        total_pain_points=len(pain_points)
    )


@app.get("/api/product-analysis/{product_name}")
async def get_product_analysis(product_name: str):
    """
    Analyze posts for a specific product using LLM and generate a summary of issues (in English).
    """
    try:
        # Get all posts
        all_posts = db.get_posts(limit=10000, offset=0)
        
        # Filter posts for this product (using same detection logic as product-opportunities)
        product_posts = []
        for post in all_posts:
            content = (post.get('content', '') or '').lower()
            detected_product = None
            
            # Simple product detection (same as in get_product_opportunities)
            if any(kw in content for kw in ['billing', 'invoice', 'facture', 'charge']):
                detected_product = 'Billing'
            elif any(kw in content for kw in ['domain', 'dns', 'domaine', 'nameserver']):
                detected_product = 'Domain'
            elif any(kw in content for kw in ['vps', 'virtual private server']):
                detected_product = 'VPS'
            elif any(kw in content for kw in ['hosting', 'hébergement', 'web host']):
                detected_product = 'Hosting'
            elif any(kw in content for kw in ['api', 'sdk', 'integration']):
                detected_product = 'API'
            elif any(kw in content for kw in ['email', 'mail', 'exchange', 'mx']):
                detected_product = 'Email'
            elif any(kw in content for kw in ['cdn', 'content delivery']):
                detected_product = 'CDN'
            elif any(kw in content for kw in ['dedicated', 'dédié', 'server']):
                detected_product = 'Dedicated'
            elif any(kw in content for kw in ['cloud', 'public cloud', 'instance']):
                detected_product = 'Public Cloud'
            elif any(kw in content for kw in ['storage', 'object storage', 'swift']):
                detected_product = 'Storage'
            
            if detected_product and detected_product.lower() == product_name.lower():
                product_posts.append(post)
        
        if not product_posts:
            return {
                "product": product_name,
                "summary": f"No posts found for product '{product_name}'.",
                "posts_count": 0,
                "llm_available": False
            }
        
        # Focus on negative posts for analysis
        negative_posts = [p for p in product_posts if p.get('sentiment_label') == 'negative']
        posts_to_analyze = negative_posts[:30] if len(negative_posts) >= 30 else negative_posts
        
        if not posts_to_analyze:
            # If no negative posts, analyze all posts
            posts_to_analyze = product_posts[:30]
        
        # Prepare posts summary for LLM
        posts_summary = []
        for post in posts_to_analyze:
            posts_summary.append({
                'content': (post.get('content', '') or '')[:500],
                'sentiment': post.get('sentiment_label', 'neutral'),
                'source': post.get('source', 'Unknown'),
                'created_at': post.get('created_at', '')
            })
        
        # Create prompt for LLM analysis
        prompt = f"""Analyze the following customer feedback posts about OVH product "{product_name}" and generate a comprehensive summary of what is wrong (in English).

Posts to analyze ({len(posts_to_analyze)} posts, {len(negative_posts)} negative):
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

Generate a detailed summary in English that:
1. Identifies the main issues and problems customers are experiencing
2. Groups related issues together
3. Highlights the most critical problems
4. Provides context about frequency and severity
5. Is written in clear, professional English

Format your response as a JSON object with this structure:
{{
  "summary": "Detailed summary text in English (3-5 paragraphs) explaining what is wrong with this product based on customer feedback..."
}}

Focus on actionable insights and specific problems mentioned in the posts. Be comprehensive but concise."""
        
        # Try LLM API
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        
        logger.info(f"[Product Analysis] Starting analysis for {product_name}: {len(product_posts)} posts ({len(negative_posts)} negative). API key: {'present' if api_key else 'MISSING'}, Provider: {llm_provider}")
        
        if api_key:
            try:
                if llm_provider == 'openai' or (not os.getenv('LLM_PROVIDER') and api_key):
                    logger.info(f"[Product Analysis] Calling OpenAI API for {product_name}")
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            'https://api.openai.com/v1/chat/completions',
                            headers={
                                'Authorization': f'Bearer {api_key}',
                                'Content-Type': 'application/json'
                            },
                            json={
                                'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                                'messages': [
                                    {'role': 'system', 'content': 'You are a product analyst. Analyze customer feedback and identify problems in clear English.'},
                                    {'role': 'user', 'content': prompt}
                                ],
                                'temperature': 0.7,
                                'max_tokens': 1500
                            }
                        )
                        response.raise_for_status()
                        result = response.json()
                        content = result['choices'][0]['message']['content'].strip()
                        
                        # Parse JSON from response
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            try:
                                analysis_data = json.loads(json_match.group())
                                summary = analysis_data.get('summary', content)  # Fallback to full content if no summary key
                                logger.info(f"[Product Analysis] LLM analysis successful for {product_name}")
                                return {
                                    "product": product_name,
                                    "summary": summary,
                                    "posts_count": len(product_posts),
                                    "negative_posts_count": len(negative_posts),
                                    "llm_available": True
                                }
                            except json.JSONDecodeError as je:
                                logger.warning(f"[Product Analysis] Failed to parse JSON from LLM response: {je}. Using raw content.")
                                # Use raw content as summary if JSON parsing fails
                                return {
                                    "product": product_name,
                                    "summary": content,
                                    "posts_count": len(product_posts),
                                    "negative_posts_count": len(negative_posts),
                                    "llm_available": True
                                }
                        else:
                            logger.warning(f"[Product Analysis] No JSON found in LLM response. Using raw content.")
                            # Use raw content as summary if no JSON found
                            return {
                                "product": product_name,
                                "summary": content,
                                "posts_count": len(product_posts),
                                "negative_posts_count": len(negative_posts),
                                "llm_available": True
                            }
                
                elif llm_provider == 'anthropic':
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            'https://api.anthropic.com/v1/messages',
                            headers={
                                'x-api-key': api_key,
                                'anthropic-version': '2023-06-01',
                                'Content-Type': 'application/json'
                            },
                            json={
                                'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                                'max_tokens': 1500,
                                'messages': [
                                    {'role': 'user', 'content': prompt}
                                ]
                            }
                        )
                        response.raise_for_status()
                        result = response.json()
                        content = result['content'][0]['text'].strip()
                        
                        # Parse JSON from response
                        import re
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            try:
                                analysis_data = json.loads(json_match.group())
                                summary = analysis_data.get('summary', content)  # Fallback to full content if no summary key
                                logger.info(f"[Product Analysis] LLM analysis successful for {product_name}")
                                return {
                                    "product": product_name,
                                    "summary": summary,
                                    "posts_count": len(product_posts),
                                    "negative_posts_count": len(negative_posts),
                                    "llm_available": True
                                }
                            except json.JSONDecodeError as je:
                                logger.warning(f"[Product Analysis] Failed to parse JSON from LLM response: {je}. Using raw content.")
                                return {
                                    "product": product_name,
                                    "summary": content,
                                    "posts_count": len(product_posts),
                                    "negative_posts_count": len(negative_posts),
                                    "llm_available": True
                                }
                        else:
                            logger.warning(f"[Product Analysis] No JSON found in LLM response. Using raw content.")
                            return {
                                "product": product_name,
                                "summary": content,
                                "posts_count": len(product_posts),
                                "negative_posts_count": len(negative_posts),
                                "llm_available": True
                            }
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.error(f"[Product Analysis] LLM API authentication failed (401) for product {product_name}. Check API key.")
                    try:
                        error_detail = e.response.json()
                        logger.error(f"[Product Analysis] API error details: {error_detail}")
                    except:
                        pass
                else:
                    logger.error(f"[Product Analysis] LLM API error ({e.response.status_code}) for product {product_name}: {e}")
                    try:
                        error_detail = e.response.json()
                        logger.error(f"[Product Analysis] API error details: {error_detail}")
                    except:
                        pass
            except Exception as e:
                logger.error(f"[Product Analysis] LLM API error for product {product_name}: {type(e).__name__}: {e}", exc_info=True)
        else:
            logger.warning(f"[Product Analysis] No API key found. OPENAI_API_KEY={bool(os.getenv('OPENAI_API_KEY'))}, ANTHROPIC_API_KEY={bool(os.getenv('ANTHROPIC_API_KEY'))}")
        
        # Fallback: Generate simple summary
        logger.info(f"[Product Analysis] Using fallback analysis for {product_name}")
        negative_ratio = (len(negative_posts) / len(product_posts) * 100) if product_posts else 0
        fallback_summary = f"Analysis of {len(product_posts)} posts for {product_name}: {len(negative_posts)} negative posts ({negative_ratio:.1f}%). "
        if negative_posts:
            fallback_summary += "Common issues include customer complaints about service quality, technical problems, and support issues."
        else:
            fallback_summary += "No significant negative feedback detected."
        
        return {
            "product": product_name,
            "summary": fallback_summary,
            "posts_count": len(product_posts),
            "negative_posts_count": len(negative_posts),
            "llm_available": False
        }
        
    except Exception as e:
        logger.error(f"Error analyzing product {product_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze product: {str(e)}")


@app.get("/api/product-opportunities", response_model=ProductDistributionResponse)
async def get_product_opportunities():
    """
    Calculate opportunity scores for each OVH product based on negative feedback.
    """
    all_posts = db.get_posts(limit=10000, offset=0)
    
    # Add timestamps and default engagement metrics
    for post in all_posts:
        try:
            created_at = post.get('created_at', '')
            if created_at:
                dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                post['created_at_timestamp'] = dt.timestamp()
            else:
                post['created_at_timestamp'] = 0
        except:
            post['created_at_timestamp'] = 0
        post['views'] = post.get('views', 0)
        post['comments'] = post.get('comments', 0)
        post['reactions'] = post.get('reactions', 0)
    
    # Group posts by product
    product_posts = defaultdict(list)
    for post in all_posts:
        # Try to detect product from content
        content = post.get('content', '') or ''
        product = None
        
        # Simple product detection (can be improved)
        content_lower = content.lower()
        if any(kw in content_lower for kw in ['billing', 'invoice', 'facture', 'charge']):
            product = 'Billing'
        elif any(kw in content_lower for kw in ['domain', 'dns', 'domaine', 'nameserver']):
            product = 'Domain'
        elif any(kw in content_lower for kw in ['vps', 'virtual private server']):
            product = 'VPS'
        elif any(kw in content_lower for kw in ['hosting', 'hébergement', 'web host']):
            product = 'Hosting'
        elif any(kw in content_lower for kw in ['api', 'sdk', 'integration']):
            product = 'API'
        elif any(kw in content_lower for kw in ['email', 'mail', 'exchange', 'mx']):
            product = 'Email'
        elif any(kw in content_lower for kw in ['cdn', 'content delivery']):
            product = 'CDN'
        elif any(kw in content_lower for kw in ['dedicated', 'dédié', 'server']):
            product = 'Dedicated'
        elif any(kw in content_lower for kw in ['cloud', 'public cloud', 'instance']):
            product = 'Public Cloud'
        elif any(kw in content_lower for kw in ['storage', 'object storage', 'swift']):
            product = 'Storage'
        
        if product:
            product_posts[product].append(post)
    
    # Calculate opportunity scores
    products = []
    colors = ['#0099ff', '#34d399', '#60a5fa', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
    
    for idx, (product, posts) in enumerate(product_posts.items()):
        score = calculate_opportunity_score(posts, all_posts)
        negative_count = sum(1 for p in posts if p.get('sentiment_label') == 'negative')
        
        products.append(ProductOpportunity(
            product=product,
            opportunity_score=score,
            negative_posts=negative_count,
            total_posts=len(posts),
            color=colors[idx % len(colors)]
        ))
    
    # Sort by opportunity score (highest first)
    products.sort(key=lambda x: x.opportunity_score, reverse=True)
    
    return ProductDistributionResponse(products=products)


@app.get("/api/posts-for-improvement")
async def get_posts_for_improvement(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    language: Optional[str] = None,
    source: Optional[str] = None,
    sort_by: str = "opportunity_score"
):
    """
    Get posts ranked by priority score for improvement review.
    Priority score = sentiment * keyword_relevance * recency (0-100 scale).
    - sentiment: negative=1.0, neutral=0.5, positive=0.2
    - keyword_relevance: based on pain point keywords found (0.1-1.0)
    - recency: exponential decay (last 7 days=1.0, 30 days=0.7, 90 days=0.4, older=0.1)
    """
    all_posts = db.get_posts(limit=10000, offset=0)
    
    # Add timestamps and default engagement metrics
    for post in all_posts:
        try:
            created_at = post.get('created_at', '')
            if created_at:
                dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                post['created_at_timestamp'] = dt.timestamp()
            else:
                post['created_at_timestamp'] = 0
        except:
            post['created_at_timestamp'] = 0
        post['views'] = post.get('views', 0)
        post['comments'] = post.get('comments', 0)
        post['reactions'] = post.get('reactions', 0)
    
    # Filter posts
    filtered = all_posts
    
    if search:
        search_lower = search.lower()
        filtered = [p for p in filtered if search_lower in (p.get('content', '') or '').lower()]
    
    if language and language != 'all':
        filtered = [p for p in filtered if p.get('language') == language]
    
    if source and source != 'all':
        # Normalize GitHub sources: GitHub Issues and GitHub Discussions → GitHub
        filtered = [p for p in filtered if 
                   (p.get('source') == source) or 
                   (source == 'GitHub' and (p.get('source') == 'GitHub Issues' or p.get('source') == 'GitHub Discussions'))]
    
    # Calculate priority score for each post using: sentiment * keyword_relevance * recency
    now = time.time()
    posts_with_scores = []
    
    # Get pain point keywords for keyword relevance calculation
    pain_point_keywords = []
    pain_point_patterns = {
        'Refund Delays': ['refund', 'rembours', 'remboursement', 'pending refund', 'delayed refund'],
        'Billing Clarity': ['billing', 'invoice', 'facture', 'charge', 'confusing', 'unclear'],
        'HTTPS/SSL Renewal': ['ssl', 'https', 'certificate', 'renewal', 'expired', 'certificat'],
        'Support Response Time': ['support', 'response', 'slow', 'unresponsive', 'waiting', 'ticket'],
        'VPS Backups': ['backup', 'vps backup', 'backup error', 'backup fail', 'sauvegarde'],
        'Domain Issues': ['domain', 'dns', 'nameserver', 'domaine', 'expired domain'],
        'Email Problems': ['email', 'mail', 'mx record', 'smtp', 'imap', 'exchange']
    }
    for pattern in pain_point_patterns.values():
        pain_point_keywords.extend([k.lower() for k in pattern])
    
    for post in filtered:
        content_lower = (post.get('content', '') or '').lower()
        
        # 1. Sentiment score (0-1): negative = 1.0, neutral = 0.5, positive = 0.2
        sentiment_value = 0.0
        if post.get('sentiment_label') == 'negative':
            sentiment_value = 1.0
        elif post.get('sentiment_label') == 'neutral':
            sentiment_value = 0.5
        else:
            sentiment_value = 0.2
        
        # 2. Keyword relevance (0-1): based on pain point keywords found
        keyword_matches = sum(1 for keyword in pain_point_keywords if keyword in content_lower)
        # Normalize: 1+ matches = 1.0, 0 matches = 0.1 (minimum relevance)
        keyword_relevance = min(1.0, 0.1 + (keyword_matches * 0.3))
        
        # 3. Recency score (0-1): exponential decay based on days ago
        post_time = post.get('created_at_timestamp', 0) or 0
        days_ago = (now - post_time) / (24 * 3600)
        if days_ago <= 7:
            recency_value = 1.0
        elif days_ago <= 30:
            recency_value = 0.7
        elif days_ago <= 90:
            recency_value = 0.4
        else:
            recency_value = 0.1
        
        # Priority score = sentiment * keyword_relevance * recency (0-1, scaled to 0-100)
        priority_score = sentiment_value * keyword_relevance * recency_value
        priority_score_scaled = int(priority_score * 100)
        
        posts_with_scores.append({
            **post,
            'opportunity_score': priority_score_scaled,
            'priority_score': priority_score_scaled  # Alias for consistency
        })
    
    # Sort by opportunity score
    if sort_by == 'opportunity_score':
        posts_with_scores.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
    elif sort_by == 'recent':
        posts_with_scores.sort(key=lambda x: x.get('created_at_timestamp', 0) or 0, reverse=True)
    elif sort_by == 'engagement':
        posts_with_scores.sort(key=lambda x: 
            (x.get('views', 0) or 0) + (x.get('comments', 0) or 0) + (x.get('reactions', 0) or 0), 
            reverse=True)
    
    # Paginate
    paginated = posts_with_scores[offset:offset + limit]
    
    return {
        'posts': paginated,
        'total': len(posts_with_scores),
        'offset': offset,
        'limit': limit
    }


async def generate_recommended_actions_with_llm(
    posts: List[dict], 
    recent_posts: List[dict], 
    stats: dict,
    max_actions: int = 5
) -> List[RecommendedAction]:
    """
    Generate recommended actions using LLM API.
    Supports OpenAI, Anthropic, or local LLM via environment variables.
    """
    # Prepare posts summary (focus on recent negative posts)
    negative_posts = [p for p in recent_posts if p.get('sentiment_label') == 'negative']
    posts_summary = []
    for post in (negative_posts[:10] if negative_posts else posts[:15]):  # Limit to 10-15 posts
        posts_summary.append({
            'content': (post.get('content', '') or '')[:300],  # Limit content length
            'sentiment': post.get('sentiment_label', 'neutral'),
            'source': post.get('source', 'Unknown'),
            'created_at': post.get('created_at', '')
        })
    
    # Get filter context (including search term)
    active_filters = stats.get('active_filters', 'All posts')
    filtered_context = stats.get('filtered_context', False)
    search_term = stats.get('search_term', '')
    
    # Create comprehensive prompt with context
    prompt = f"""You are an OVHcloud customer support analyst. Analyze the following customer feedback posts and generate {max_actions} specific, actionable recommended actions.

CONTEXT:
- Active filters: {active_filters}
- Search term: "{search_term}" {'(user is specifically searching for this)' if search_term else '(no specific search term)'}
- Analysis is based on {'filtered posts' if filtered_context else 'all posts'} in the database
- Total posts analyzed: {stats.get('total', 0)} (Positive: {stats.get('positive', 0)}, Negative: {stats.get('negative', 0)}, Neutral: {stats.get('neutral', 0)})
- Recent posts (last 48h): {stats.get('recent_total', 0)} total, {stats.get('recent_negative', 0)} negative
- Spike detected: {stats.get('spike_detected', False)} {'⚠️ Significant increase in negative feedback!' if stats.get('spike_detected', False) else ''}
- Top product impacted: {stats.get('top_product', 'N/A')} ({stats.get('top_product_count', 0)} negative posts)
- Top issue keyword: "{stats.get('top_issue', 'N/A')}" (mentioned {stats.get('top_issue_count', 0)} times)

POSTS TO ANALYZE:
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

IMPORTANT: The recommendations must be SPECIFIC to the actual issues found in these posts. 
- If a search term is provided, prioritize recommendations related to that search term
- If a specific product is mentioned frequently, reference it
- If specific errors or problems appear, mention them
- If the analysis is filtered (e.g., by product, date, or source), acknowledge this context
- Base priorities on the actual data: high for urgent spikes or critical issues, medium for recurring problems, low for minor improvements

Generate {max_actions} recommended actions. Each action should:
1. Be SPECIFIC and ACTIONABLE (not generic like "improve support")
2. Reference actual issues, products, or patterns found in the posts
3. Include an appropriate emoji icon
4. Have a priority level (high/medium/low) based on:
   - High: Spike detected, critical issues, urgent problems
   - Medium: Recurring issues, moderate impact
   - Low: Minor improvements, nice-to-have features

Format your response as a JSON array with this structure:
[
  {{
    "icon": "🔍",
    "text": "Investigate: [specific issue/product] - [specific detail from posts]",
    "priority": "high"
  }},
  {{
    "icon": "📣",
    "text": "Check: [specific thing to verify] related to [product/issue]",
    "priority": "medium"
  }},
  {{
    "icon": "💬",
    "text": "Prepare: [specific response/macro/documentation] for [specific issue]",
    "priority": "medium"
  }}
]

Use appropriate emojis:
- 🔍 for investigate/research
- 📣 for check/announce/verify
- 💬 for communication/prepare responses
- ⚠️ for alerts/urgent issues
- 🔧 for technical fixes
- 📊 for analysis/reporting
- 🎯 for focus areas
- ⚡ for urgent actions

Be specific and reference actual content from the posts when possible."""

    # Try to use LLM API (OpenAI, Anthropic, or local)
    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    
    if not api_key and llm_provider in ['openai', 'anthropic']:
        # No API key available - return empty list (frontend will show a nice message)
        logger.info("[Recommended Actions] No LLM API key configured, returning empty list")
        return []
    
    try:
        if llm_provider == 'openai' or (not os.getenv('LLM_PROVIDER') and api_key):
            # Use OpenAI API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                        'messages': [
                            {'role': 'system', 'content': 'You are an OVHcloud customer support analyst. Generate specific, actionable recommended actions based on customer feedback.'},
                            {'role': 'user', 'content': prompt}
                        ],
                        'temperature': 0.7,
                        'max_tokens': 1500
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON from response
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    actions_data = json.loads(json_match.group())
                    return [RecommendedAction(**action) for action in actions_data]
        
        elif llm_provider == 'anthropic':
            # Use Anthropic API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                        'max_tokens': 1500,
                        'messages': [
                            {'role': 'user', 'content': prompt}
                        ],
                        'system': 'You are an OVHcloud customer support analyst. Generate specific, actionable recommended actions based on customer feedback.'
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['content'][0]['text']
                
                # Parse JSON from response
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    actions_data = json.loads(json_match.group())
                    return [RecommendedAction(**action) for action in actions_data]
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.warning(f"LLM API authentication failed (401): Invalid or expired API key. Using fallback.")
        else:
            logger.warning(f"LLM API error ({e.response.status_code}): {e}. Using fallback.")
        # Fallback to rule-based generation
        return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)
    except Exception as e:
        logger.warning(f"LLM API error: {type(e).__name__}: {e}. Using fallback.")
        # Fallback to rule-based generation
        return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)
    
    # Fallback if no API key or other error
    return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)


def generate_recommended_actions_fallback(
    posts: List[dict], 
    recent_posts: List[dict], 
    stats: dict,
    max_actions: int = 5
) -> List[RecommendedAction]:
    """
    Fallback rule-based recommended actions generator.
    Uses context-aware logic based on filtered posts and active filters.
    """
    actions = []
    active_filters = stats.get('active_filters', 'All posts')
    filtered_context = stats.get('filtered_context', False)
    
    # Build context-aware actions based on actual data
    recent_negative = stats.get('recent_negative', 0)
    total_negative = stats.get('negative', 0)
    top_product = stats.get('top_product', 'N/A')
    top_product_count = stats.get('top_product_count', 0)
    top_issue = stats.get('top_issue', 'N/A')
    top_issue_count = stats.get('top_issue_count', 0)
    
    # If spike detected, add urgent action
    if stats.get('spike_detected', False):
        context_note = f" (filtered: {active_filters})" if filtered_context else ""
        actions.append(RecommendedAction(
            icon='⚠️',
            text=f'Investigate: Spike in negative feedback - {recent_negative} posts in last 48h{context_note}',
            priority='high'
        ))
    
    # If top product identified with significant count, add product-specific action
    if top_product != 'N/A' and top_product_count > 0:
        context_note = f" (in {active_filters})" if filtered_context else ""
        actions.append(RecommendedAction(
            icon='🎁',
            text=f'Review: {top_product} issues - {top_product_count} negative posts{context_note}',
            priority='high' if stats.get('spike_detected', False) or top_product_count > 5 else 'medium'
        ))
    
    # If top issue identified with significant mentions, add issue-specific action
    if top_issue != 'N/A' and top_issue_count > 2:
        context_note = f" (filtered context)" if filtered_context else ""
        actions.append(RecommendedAction(
            icon='💬',
            text=f'Address: "{top_issue}" related complaints ({top_issue_count} mentions){context_note}',
            priority='medium'
        ))
    
    # Add context-aware generic actions
    if len(actions) < max_actions:
        if recent_negative > 0:
            actions.append(RecommendedAction(
                icon='📣',
                text=f'Check: Status page or ongoing incident ({recent_negative} recent negative posts)',
                priority='high' if recent_negative > 5 else 'medium'
            ))
        
        if total_negative > 10:
            actions.append(RecommendedAction(
                icon='💬',
                text='Prepare: Support macro / canned response for common issues',
                priority='medium'
            ))
        
        if filtered_context and len(actions) < max_actions:
            actions.append(RecommendedAction(
                icon='🔍',
                text=f'Note: Analysis filtered to {active_filters}',
                priority='low'
            ))
    
    # Limit to max_actions
    return actions[:max_actions]


@app.post("/api/recommended-actions", response_model=RecommendedActionsResponse)
async def get_recommended_actions(request: RecommendedActionRequest):
    """Generate recommended actions based on customer feedback posts using LLM."""
    try:
        # Check if LLM is available (check BEFORE calling the function)
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        # LLM is available if we have an API key OR if provider is not openai/anthropic (local LLM)
        llm_available = bool(api_key) or (llm_provider not in ['openai', 'anthropic'])
        
        logger.info(f"[Recommended Actions] LLM check: api_key={bool(api_key)}, provider={llm_provider}, llm_available={llm_available}")
        
        actions = await generate_recommended_actions_with_llm(
            request.posts, 
            request.recent_posts, 
            request.stats, 
            request.max_actions
        )
        
        # If we have API key but got empty actions, it might be an error - but still mark as available
        if llm_available and not actions:
            logger.warning(f"[Recommended Actions] LLM available but no actions generated. This might indicate an error or no relevant actions.")
        
        return RecommendedActionsResponse(actions=actions, llm_available=llm_available)
    except Exception as e:
        logger.error(f"Error generating recommended actions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate recommended actions: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend HTML file - redirects to dashboard by default."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/scraping", response_class=HTMLResponse)
@app.get("/scraping-configuration", response_class=HTMLResponse)
async def serve_frontend_scraping():
    """Serve the scraping & configuration page."""
    frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "index.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        raise HTTPException(status_code=404, detail="Scraping page not found")


@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/dashboard-analytics", response_class=HTMLResponse)
async def serve_frontend_dashboard():
    """Serve the dashboard analytics page."""
    frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "dashboard" / "index.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        raise HTTPException(status_code=404, detail="Dashboard page not found")


@app.get("/logs", response_class=HTMLResponse)
async def serve_logs_page():
    """Serve the scraping logs page."""
    frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "logs.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        # Create a simple logs page if it doesn't exist
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scraping Logs</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <h1>Scraping Logs</h1>
            <p>Logs page will be created here.</p>
        </body>
        </html>
        """


@app.get("/api/logs")
async def get_logs_api(source: Optional[str] = None, level: Optional[str] = None, limit: int = 1000, offset: int = 0):
    """Get scraping logs from the database."""
    logs = db.get_scraping_logs(source=source, level=level, limit=limit, offset=offset)
    return {"logs": logs, "count": len(logs)}


@app.delete("/api/logs")
async def clear_logs_api(source: Optional[str] = None, older_than_days: Optional[int] = None):
    """Clear scraping logs."""
    deleted = db.clear_scraping_logs(source=source, older_than_days=older_than_days)
    return {"deleted": deleted, "message": f"Deleted {deleted} log entries"}


@app.get("/improvements", response_class=HTMLResponse)
async def serve_improvements():
    """Serve the improvements opportunities HTML file."""
    frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "improvements" / "index.html"
    if frontend_path.exists():
        content = open(frontend_path, "r", encoding="utf-8").read()
        # Replace relative paths with absolute paths for static files
        content = content.replace('href="/dashboard/css/', 'href="/dashboard/css/')
        content = content.replace('src="/improvements/js/', 'src="/improvements/js/')
        return content
    else:
        raise HTTPException(status_code=404, detail="Improvements page not found")


@app.get("/settings", response_class=HTMLResponse)
async def serve_settings():
    """Serve the settings page."""
    frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "dashboard" / "settings.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        raise HTTPException(status_code=404, detail="Settings page not found")


# Additional static file mounts (duplicates removed, already mounted above)


class UIVersionPayload(BaseModel):
    version: str = Field(..., pattern="^(v1|v2)$")

class LLMConfigPayload(BaseModel):
    """Request model for LLM configuration."""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    llm_provider: Optional[str] = Field(None, pattern="^(openai|anthropic)$", description="LLM provider")

class LLMConfigResponse(BaseModel):
    """Response model for LLM configuration."""
    openai_api_key_set: bool = Field(..., description="Whether OpenAI API key is set")
    anthropic_api_key_set: bool = Field(..., description="Whether Anthropic API key is set")
    llm_provider: str = Field(..., description="Current LLM provider")
    status: str = Field(..., description="Configuration status")

def get_version():
    """
    Get application version with automatic MINOR and PATCH calculation.
    
    Format: MAJOR.MINOR.PATCH
    - MAJOR: Read from VERSION file (manual update for breaking changes)
    - MINOR: Count of Git tags matching vMAJOR.* pattern (e.g., v1.0, v1.1, etc.)
    - PATCH: Count of commits from git rev-list --count HEAD
    
    Returns:
        Version string in format "MAJOR.MINOR.PATCH" (e.g., "1.5.77")
    """
    import subprocess
    
    # Read MAJOR from VERSION file
    version_path = Path(__file__).resolve().parents[2] / "VERSION"
    try:
        if version_path.exists():
            with open(version_path, "r", encoding="utf-8") as f:
                major = f.read().strip()
                if not major:
                    major = "1"
        else:
            major = "1"
    except Exception:
        major = "1"
    
    # Calculate MINOR from Git tags (Option A - recommended)
    minor = "0"
    try:
        # Get all tags matching vMAJOR.* pattern
        result = subprocess.run(
            ["git", "tag", "-l", f"v{major}.*"],
            capture_output=True,
            text=True,
            cwd=version_path.parent,
            timeout=5
        )
        if result.returncode == 0:
            tags = [tag for tag in result.stdout.strip().split('\n') if tag]
            # Count unique MINOR versions (e.g., v1.0, v1.1, v1.2 -> 3)
            minor_versions = set()
            for tag in tags:
                # Extract MINOR from tag like v1.5.10 -> 5
                parts = tag.replace(f"v{major}.", "").split(".")
                if parts:
                    try:
                        minor_versions.add(int(parts[0]))
                    except ValueError:
                        pass
            # MINOR is the count of unique minor versions, or max + 1
            if minor_versions:
                minor = str(max(minor_versions) + 1)
            else:
                minor = "0"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug(f"Could not calculate MINOR from Git tags: {e}")
        minor = "0"
    
    # Calculate PATCH from commit count
    patch = "0"
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            cwd=version_path.parent,
            timeout=5
        )
        if result.returncode == 0:
            patch = result.stdout.strip()
            if not patch:
                patch = "0"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug(f"Could not calculate PATCH from Git commits: {e}")
        patch = "0"
    
    # Return format: MAJOR.MINOR.PATCH
    return f"{major}.{minor}.{patch}"

@app.get("/api/version")
async def get_app_version():
    """Get application version."""
    return {
        "version": get_version(),
        "build_date": datetime.datetime.now().isoformat()
    }

@app.get("/api/config")
async def get_config():
    """Get full configuration including API keys status, rate limiting, and environment."""
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    github_token = os.getenv('GITHUB_TOKEN')
    trustpilot_key = os.getenv('TRUSTPILOT_API_KEY')
    linkedin_client_id = os.getenv('LINKEDIN_CLIENT_ID')
    linkedin_client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
    twitter_bearer = os.getenv('TWITTER_BEARER_TOKEN')
    provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    environment = os.getenv('ENVIRONMENT', 'development')
    
    def mask_key(key):
        """Mask API key for display."""
        if not key:
            return None
        if len(key) <= 8:
            return '••••••••'
        return f"{key[:4]}••••{key[-4:]}"
    
    # For LinkedIn, check if both credentials are configured
    linkedin_configured = bool(linkedin_client_id and linkedin_client_secret)
    linkedin_masked = mask_key(linkedin_client_id) if linkedin_client_id else None
    linkedin_length = len(linkedin_client_id) if linkedin_client_id else 0
    
    return {
        "environment": environment,
        "llm_provider": provider,
        "api_keys": {
            "openai": {
                "configured": bool(openai_key),
                "masked": mask_key(openai_key),
                "length": len(openai_key) if openai_key else 0
            },
            "anthropic": {
                "configured": bool(anthropic_key),
                "masked": mask_key(anthropic_key),
                "length": len(anthropic_key) if anthropic_key else 0
            },
            "google": {
                "configured": bool(google_key),
                "masked": mask_key(google_key),
                "length": len(google_key) if google_key else 0
            },
            "github": {
                "configured": bool(github_token),
                "masked": mask_key(github_token),
                "length": len(github_token) if github_token else 0
            },
            "trustpilot": {
                "configured": bool(trustpilot_key),
                "masked": mask_key(trustpilot_key),
                "length": len(trustpilot_key) if trustpilot_key else 0
            },
            "linkedin": {
                "configured": linkedin_configured,
                "masked": linkedin_masked,
                "length": linkedin_length
            },
            "twitter": {
                "configured": bool(twitter_bearer),
                "masked": mask_key(twitter_bearer),
                "length": len(twitter_bearer) if twitter_bearer else 0
            }
        },
        "rate_limiting": {
            "requests_per_window": 100,
            "window_seconds": 60
        }
    }

@app.get("/api/llm-config", response_model=LLMConfigResponse)
async def get_llm_config():
    """Get current LLM configuration status (without exposing keys)."""
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    
    return LLMConfigResponse(
        openai_api_key_set=bool(openai_key),
        anthropic_api_key_set=bool(anthropic_key),
        llm_provider=provider,
        status="configured" if (openai_key or anthropic_key) else "not_configured"
    )

@app.post("/api/llm-config", response_model=LLMConfigResponse)
async def set_llm_config(payload: LLMConfigPayload):
    """Set LLM configuration (save to .env file)."""
    backend_path = Path(__file__).resolve().parents[1]
    env_path = backend_path / ".env"
    
    # Read existing .env if it exists
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    
    # Update with new values
    if payload.openai_api_key is not None:
        if payload.openai_api_key:
            env_vars['OPENAI_API_KEY'] = payload.openai_api_key
        elif 'OPENAI_API_KEY' in env_vars:
            del env_vars['OPENAI_API_KEY']
    
    if payload.anthropic_api_key is not None:
        if payload.anthropic_api_key:
            env_vars['ANTHROPIC_API_KEY'] = payload.anthropic_api_key
        elif 'ANTHROPIC_API_KEY' in env_vars:
            del env_vars['ANTHROPIC_API_KEY']
    
    if payload.llm_provider:
        env_vars['LLM_PROVIDER'] = payload.llm_provider
    
    # Write back to .env
    with open(env_path, "w", encoding="utf-8") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    # Update environment variables for current session
    if payload.openai_api_key:
        os.environ['OPENAI_API_KEY'] = payload.openai_api_key
    if payload.anthropic_api_key:
        os.environ['ANTHROPIC_API_KEY'] = payload.anthropic_api_key
    if payload.llm_provider:
        os.environ['LLM_PROVIDER'] = payload.llm_provider
    
    return LLMConfigResponse(
        openai_api_key_set=bool(env_vars.get('OPENAI_API_KEY')),
        anthropic_api_key_set=bool(env_vars.get('ANTHROPIC_API_KEY')),
        llm_provider=env_vars.get('LLM_PROVIDER', 'openai'),
        status="configured"
    )

@app.post("/api/config/set-key")
async def set_api_key(payload: dict):
    """Set a generic API key (for Google, GitHub, Trustpilot, LinkedIn, Twitter, etc.)."""
    provider = payload.get('provider')
    keys = payload.get('keys')  # For providers with multiple keys (e.g., LinkedIn)
    key = payload.get('key')  # For single key providers
    
    if not provider:
        raise HTTPException(status_code=400, detail="Provider is required")
    
    # Handle multiple keys (e.g., LinkedIn has CLIENT_ID and CLIENT_SECRET)
    if keys and isinstance(keys, dict):
        if not keys:
            raise HTTPException(status_code=400, detail="At least one key is required")
    elif key:
        keys = {provider: key}
    else:
        raise HTTPException(status_code=400, detail="Key(s) are required")
    
    backend_path = Path(__file__).resolve().parents[1]
    env_path = backend_path / ".env"
    
    # Read existing .env if it exists
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key_name, value = line.split("=", 1)
                    env_vars[key_name.strip()] = value.strip()
    
    # Update the keys
    for key_name, key_value in keys.items():
        env_vars[key_name] = key_value
        os.environ[key_name] = key_value
    
    # Write back to .env
    with open(env_path, "w", encoding="utf-8") as f:
        for key_name, value in env_vars.items():
            f.write(f"{key_name}={value}\n")
    
    return {"success": True, "message": f"{provider} API key(s) saved successfully"}

@app.post("/admin/set-ui-version")
async def set_ui_version(payload: UIVersionPayload):
    """Set the UI version (v1 or v2)."""
    version_str = payload.version
    if version_str not in ["v1", "v2"]:
        raise HTTPException(status_code=400, detail="Version must be 'v1' or 'v2'")
    
    app_config_path = Path(__file__).resolve().parents[2] / "backend" / ".app_config"
    
    # Read existing config
    config_lines = []
    if app_config_path.exists():
        with open(app_config_path, "r", encoding="utf-8") as f:
            config_lines = f.readlines()
    
    # Update or add UI_VERSION
    updated = False
    for i, line in enumerate(config_lines):
        if line.startswith("UI_VERSION="):
            config_lines[i] = f"UI_VERSION={version_str}\n"
            updated = True
            break
    
    if not updated:
        config_lines.append(f"UI_VERSION={version_str}\n")
    
    # Write back
    with open(app_config_path, "w", encoding="utf-8") as f:
        f.writelines(config_lines)
    
    # Update environment variable for current process
    os.environ['UI_VERSION'] = version_str
    
    return {"message": f"UI version set to {version_str}", "version": version_str}


@app.get("/admin/get-ui-version")
async def get_ui_version():
    """Get the current UI version."""
    app_config_path = Path(__file__).resolve().parents[2] / "backend" / ".app_config"
    ui_version = "v2"  # default to v2
    
    if app_config_path.exists():
        with open(app_config_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("UI_VERSION="):
                    ui_version = line.split("=", 1)[1].strip()
                    break
    
    return {"version": ui_version}


@app.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    """Upload OVHcloud logo file."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(('.svg', '.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only SVG, PNG, JPG, JPEG are allowed.")
    
    # Read file contents
    contents = await file.read()
    
    # Validate file size (max 5MB)
    if len(contents) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
    
    # Determine file extension
    file_ext = file.filename.split('.')[-1].lower()
    
    # Save to assets/logo directory
    assets_logo_path = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "logo"
    assets_logo_path.mkdir(parents=True, exist_ok=True)
    
    # If SVG or starts with SVG content, always save as .svg
    if file_ext == 'svg' or contents.startswith(b'<svg') or contents.startswith(b'<?xml'):
        logo_filename = "ovhcloud-logo.svg"
    else:
        logo_filename = f"ovhcloud-logo.{file_ext}"
    
    logo_path = assets_logo_path / logo_filename
    
    try:
        with open(logo_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"Logo uploaded successfully: {logo_filename}")
        return JSONResponse({
            "success": True,
            "message": f"Logo uploaded successfully as {logo_filename}",
            "filename": logo_filename,
            "path": f"/assets/logo/{logo_filename}"
        })
    except Exception as e:
        logger.error(f"Error saving logo: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save logo: {str(e)}")


@app.get("/api/logo-status")
async def get_logo_status():
    """Check if logo file exists."""
    assets_logo_path = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "logo"
    
    # Check for SVG first (preferred)
    svg_path = assets_logo_path / "ovhcloud-logo.svg"
    if svg_path.exists():
        file_size = svg_path.stat().st_size
        return {
            "exists": True,
            "filename": "ovhcloud-logo.svg",
            "path": "/assets/logo/ovhcloud-logo.svg",
            "size": file_size,
            "format": "svg"
        }
    
    # Check for other formats
    for ext in ['png', 'jpg', 'jpeg']:
        logo_path = assets_logo_path / f"ovhcloud-logo.{ext}"
        if logo_path.exists():
            file_size = logo_path.stat().st_size
            return {
                "exists": True,
                "filename": f"ovhcloud-logo.{ext}",
                "path": f"/assets/logo/ovhcloud-logo.{ext}",
                "size": file_size,
                "format": ext
            }
    
    return {
        "exists": False,
        "message": "No logo file found. Please upload one."
    }


# PowerPoint report generation now uses FormData with images
# No Pydantic model needed - we'll parse FormData directly


@app.post("/api/generate-powerpoint-report")
async def generate_powerpoint_report_endpoint(request: Request):
    """
    Generate a PowerPoint report with key charts, insights, and recommendations.
    Accepts FormData with chart images from the dashboard.
    """
    form = await request.form()
    
    # Parse filters from form data
    filters_str = form.get('filters', '{}')
    try:
        filters = json.loads(filters_str) if isinstance(filters_str, str) else filters_str
    except:
        filters = {}
    
    include_recommendations = form.get('include_recommendations', 'true').lower() == 'true'
    include_analysis = form.get('include_analysis', 'true').lower() == 'true'
    
    # Get chart images
    timeline_file = form.get('timeline_chart')
    source_file = form.get('source_chart')
    sentiment_file = form.get('sentiment_chart')
    
    timeline_chart = await timeline_file.read() if timeline_file else None
    source_chart = await source_file.read() if source_file else None
    sentiment_chart = await sentiment_file.read() if sentiment_file else None
    
    chart_images = {
        'timeline': timeline_chart,
        'source': source_chart,
        'sentiment': sentiment_chart
    }
    
    logger.info(f"[PowerPoint Report] Starting generation with filters: {filters}")
    
    try:
            from . import powerpoint_generator
            
            if not powerpoint_generator.PPTX_AVAILABLE:
                missing_deps = getattr(powerpoint_generator, 'MISSING_DEPENDENCIES', ['python-pptx', 'matplotlib', 'Pillow'])
                deps_str = ", ".join(missing_deps)
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"PowerPoint generation requires {deps_str}. "
                        f"Install with: pip install {' '.join(missing_deps)} "
                        f"or install all dependencies: pip install -r requirements.txt"
                    )
                )
            
            # Get filtered posts based on request filters
            all_posts = db.get_posts(limit=10000, offset=0)
            
            # Apply filters (similar to state filtering logic)
            filtered_posts = all_posts
            if filters.get('search'):
                search_lower = filters['search'].lower()
                filtered_posts = [p for p in filtered_posts if search_lower in (p.get('content', '') or '').lower()]
            
            if filters.get('sentiment') and filters['sentiment'] != 'all':
                filtered_posts = [p for p in filtered_posts if p.get('sentiment_label') == filters['sentiment']]
            
            if filters.get('language') and filters['language'] != 'all':
                filtered_posts = [p for p in filtered_posts if p.get('language') == filters['language']]
            
            if filters.get('source') and filters['source'] != 'all':
                source_filter = filters['source']
                # Normalize GitHub sources: GitHub Issues and GitHub Discussions → GitHub
                filtered_posts = [p for p in filtered_posts if 
                                 (p.get('source') == source_filter) or 
                                 (source_filter == 'GitHub' and (p.get('source') == 'GitHub Issues' or p.get('source') == 'GitHub Discussions'))]
            
            # Date filtering
            if filters.get('dateFrom'):
                filtered_posts = [p for p in filtered_posts if p.get('created_at', '') >= filters['dateFrom']]
            if filters.get('dateTo'):
                filtered_posts = [p for p in filtered_posts if p.get('created_at', '') <= filters['dateTo']]
            
            # Calculate stats
            stats = {
                'total': len(filtered_posts),
                'positive': len([p for p in filtered_posts if p.get('sentiment_label') == 'positive']),
                'negative': len([p for p in filtered_posts if p.get('sentiment_label') == 'negative']),
                'neutral': len([p for p in filtered_posts if p.get('sentiment_label') == 'neutral' or not p.get('sentiment_label')])
            }
            
            # Get recommended actions
            recommended_actions = []
            if include_recommendations:
                try:
                    # Get recent posts for recommendations
                    now = time.time()
                    recent_posts = []
                    for p in filtered_posts:
                        try:
                            created_at = p.get('created_at', '')
                            if created_at:
                                # Handle different date formats
                                try:
                                    dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                except:
                                    # Try parsing with strptime as fallback
                                    try:
                                        dt = datetime.datetime.strptime(created_at.split('T')[0], '%Y-%m-%d')
                                    except:
                                        continue
                                post_timestamp = dt.timestamp()
                                if post_timestamp >= (now - 48 * 3600):
                                    recent_posts.append(p)
                        except Exception as e:
                            logger.debug(f"Error parsing post date: {e}")
                            continue
                    
                    # Call recommended actions endpoint logic
                    actions_response = await get_recommended_actions(RecommendedActionRequest(
                        posts=filtered_posts[:30],
                        recent_posts=recent_posts[:20],
                        stats=stats,
                        max_actions=5
                    ))
                    recommended_actions = [{'icon': a.icon, 'text': a.text, 'priority': a.priority} for a in actions_response.actions]
                except Exception as e:
                    logger.warning(f"Failed to get recommended actions for report: {e}")
            
            # Generate LLM analysis if requested
            llm_analysis = None
            if include_analysis:
                try:
                    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
                    if api_key:
                        # Generate brief analysis
                        prompt = f"""Analyze the following customer feedback data and provide 2-3 key bullet points (one sentence each):
- Total posts: {stats['total']}
- Positive: {stats['positive']}, Negative: {stats['negative']}, Neutral: {stats['neutral']}
- Active filters: {filters}

Format as bullet points, professional and executive-friendly."""
                        
                        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
                        if llm_provider == 'openai' or (not os.getenv('LLM_PROVIDER') and api_key):
                            try:
                                async with httpx.AsyncClient(timeout=30.0) as client:
                                    response = await client.post(
                                        'https://api.openai.com/v1/chat/completions',
                                        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                                        json={
                                            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                                            'messages': [
                                                {'role': 'system', 'content': 'You are a business analyst. Provide concise, professional insights.'},
                                                {'role': 'user', 'content': prompt}
                                            ],
                                            'temperature': 0.7,
                                            'max_tokens': 200
                                        }
                                    )
                                    response.raise_for_status()
                                    result = response.json()
                                    llm_analysis = result['choices'][0]['message']['content'].strip()
                            except httpx.HTTPStatusError as e:
                                if e.response.status_code == 401:
                                    logger.warning(f"LLM API authentication failed (401) for PowerPoint report. Skipping LLM analysis.")
                                else:
                                    logger.warning(f"LLM API error ({e.response.status_code}) for PowerPoint report: {e}. Skipping LLM analysis.")
                                llm_analysis = None
                            except Exception as e:
                                logger.warning(f"Failed to generate LLM analysis for report: {type(e).__name__}: {e}")
                                llm_analysis = None
                        elif llm_provider == 'anthropic':
                            # Anthropic handling would go here if needed
                            pass
                except Exception as e:
                    logger.warning(f"Error generating LLM analysis: {type(e).__name__}: {e}")
                    llm_analysis = None
            
            # Generate PowerPoint with chart images
            pptx_bytes = powerpoint_generator.generate_powerpoint_report(
                posts=filtered_posts,
                filters=filters,
                recommended_actions=recommended_actions,
                stats=stats,
                llm_analysis=llm_analysis,
                chart_images=chart_images
            )
            
            # Return as file download
            filename = f"OVH_Feedback_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
            return Response(
                content=pptx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
            
    except Exception as e:
        logger.error(f"Error generating PowerPoint report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
