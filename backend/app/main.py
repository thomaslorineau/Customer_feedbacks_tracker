import locale
from pathlib import Path
import os
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from apscheduler.schedulers.background import BackgroundScheduler
import httpx

from . import db
from .scraper import x_scraper, stackoverflow, news, github, reddit, trustpilot, ovh_forum, mastodon, g2_crowd
from .analysis import sentiment

# Configure locale for French support
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'fr_FR')
    except locale.Error:
        pass  # Locale not available, use system default


app = FastAPI(title="ovh-complaints-tracker")

# Mount static files for v2 frontend (mount subdirectories to avoid conflict with /v2 route)
frontend_v2_path = Path(__file__).resolve().parents[2] / "frontend" / "v2"
if frontend_v2_path.exists():
    # Mount CSS and JS directories separately
    css_path = frontend_v2_path / "css"
    js_path = frontend_v2_path / "js"
    if css_path.exists():
        app.mount("/v2/css", StaticFiles(directory=str(css_path), html=False), name="v2-css")
    if js_path.exists():
        app.mount("/v2/js", StaticFiles(directory=str(js_path), html=False), name="v2-js")

# Enable CORS for frontend - restrict to specific ports for security
import os
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
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

    Uses saved queries (if any) from the DB. Adds small sleeps to avoid
    hammering third-party endpoints (basic throttling).
    """
    print("🔄 Running scheduled scrape...")

    saved = db.get_saved_queries()
    if saved and len(saved) > 0:
        queries = saved
    else:
        queries = ["OVH domain", "OVH complaint", "OVH support"]

    # per-query limit for scheduled job
    per_query_limit = 20

    for qi, query in enumerate(queries):
        print(f"[AUTO SCRAPE] Query: {query}")

        # X/Twitter: use direct query when we have saved keywords
        try:
            if saved and len(saved) > 0:
                items = x_scraper.scrape_x(query, limit=per_query_limit)
            else:
                items = x_scraper.scrape_x_multi_queries(limit=per_query_limit)

            added_count = 0
            duplicate_count = 0
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
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
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
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
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
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
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
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
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
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
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
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
                if db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
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
            print("[CLEANUP] All posts are OVH-related ✓")
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
    try:
        query_val = query if query and query != "OVH" else None
        print(f"[X SCRAPER] Starting with query={query_val}, limit={limit}")
        if query_val:
            items = x_scraper.scrape_x(query_val, limit=limit)
        else:
            items = x_scraper.scrape_x_multi_queries(limit=limit)

        print(f"[X SCRAPER] Got {len(items)} items")
    except Exception as e:
        print(f"[X SCRAPER ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return ScrapeResult(added=0)

    added = 0
    skipped_duplicates = 0
    try:
        for it in items:
            an = sentiment.analyze(it.get('content') or '')
            it['sentiment_score'] = an['score']
            it['sentiment_label'] = an['label']
            inserted = db.insert_post({
                'source': it.get('source'),
                'author': it.get('author'),
                'content': it.get('content'),
                'url': it.get('url'),
                'created_at': it.get('created_at'),
                'sentiment_score': it.get('sentiment_score'),
                'sentiment_label': it.get('sentiment_label'),
                'language': it.get('language', 'unknown'),
            })
            if inserted:
                added += 1
            else:
                skipped_duplicates += 1
    except Exception as e:
        print(f"[X SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    if skipped_duplicates > 0:
        print(f"[X SCRAPER] Skipped {skipped_duplicates} duplicate posts")

    return ScrapeResult(added=added)


# In-memory job store for background keyword scraping
JOBS = {}


def _run_scrape_for_source(source: str, query: str, limit: int):
    """Call the appropriate scraper and insert results into DB; return count added."""
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
    try:
        items = func(query, limit)
    except Exception as e:
        try:
            for job_id, info in JOBS.items():
                if info.get('status') == 'running':
                    db.append_job_error(job_id, f"{source}: {str(e)}")
        except Exception:
            pass
        return 0
    added = 0
    duplicates = 0
    for it in items:
        try:
            an = sentiment.analyze(it.get('content') or '')
            if db.insert_post({
                'source': it.get('source'),
                'author': it.get('author'),
                'content': it.get('content'),
                'url': it.get('url'),
                'created_at': it.get('created_at'),
                'sentiment_score': an['score'],
                'sentiment_label': an['label'],
                'language': it.get('language', 'unknown'),
            }):
                added += 1
            else:
                duplicates += 1  # Duplicate detected and skipped
        except Exception:
            # ignore per-item failures
            continue
    
    if duplicates > 0:
        print(f"  ⚠️ Skipped {duplicates} duplicate(s) from {source}")
    
    return added


def _process_keyword_job(job_id: str, keywords: List[str], limit: int, concurrency: int, delay: float):
    job = JOBS.get(job_id)
    if job is None:
        return
    job['status'] = 'running'
    # persist job
    try:
        db.create_job_record(job_id)
    except Exception:
        pass
    sources = ['x', 'github', 'stackoverflow', 'hackernews', 'news', 'trustpilot']
    total_tasks = len(keywords) * len(sources)
    job['progress'] = {'total': total_tasks, 'completed': 0}
    try:
        db.update_job_progress(job_id, total_tasks, 0)
    except Exception:
        pass

    try:
        # Use a ThreadPoolExecutor to control concurrency across requests
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            futures = []
            for kw in keywords:
                if job.get('cancelled'):
                    job['status'] = 'cancelled'
                    return
                for s in sources:
                    if job.get('cancelled'):
                        job['status'] = 'cancelled'
                        return
                    # submit scraping task
                    futures.append(executor.submit(_run_scrape_for_source, s, kw, limit))

            # iterate completions and update progress
            for fut in as_completed(futures):
                if job.get('cancelled'):
                    job['status'] = 'cancelled'
                    return
                try:
                    added = fut.result()
                    job['results'].append({'added': added})
                    try:
                        db.append_job_result(job_id, {'added': added})
                    except Exception:
                        pass
                except Exception as e:
                    job['errors'].append(str(e))
                    try:
                        db.append_job_error(job_id, str(e))
                    except Exception:
                        pass
                job['progress']['completed'] += 1
                try:
                    db.update_job_progress(job_id, total_tasks, job['progress']['completed'])
                except Exception:
                    pass
                # gentle delay between finishing tasks
                time.sleep(delay)

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


@app.post('/scrape/keywords')
async def start_keyword_scrape(payload: KeywordsPayload, limit: int = 50, concurrency: int = 2, delay: float = 0.5):
    """Start a background job that scrapes multiple keywords across sources with throttling.

    Request body: JSON: { "keywords": ["a","b"] }. Returns job id.
    """
    keywords = payload.keywords
    if not keywords or len(keywords) == 0:
        raise HTTPException(status_code=400, detail='Provide list of keywords')

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'id': job_id,
        'status': 'pending',
        'progress': {'total': 0, 'completed': 0},
        'results': [],
        'errors': [],
        'cancelled': False,
        'error': None,
    }

    # create DB record for job (best-effort)
    try:
        db.create_job_record(job_id)
    except Exception:
        pass

    # Start background thread
    t = threading.Thread(target=_process_keyword_job, args=(job_id, keywords, limit, concurrency, delay), daemon=True)
    t.start()

    return {'job_id': job_id}


@app.get('/scrape/jobs/{job_id}')
async def get_job_status(job_id: str):
    job = JOBS.get(job_id)
    if job:
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


@app.post("/scrape/stackoverflow", response_model=ScrapeResult)
async def scrape_stackoverflow_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Stack Overflow questions about OVH."""
    items = stackoverflow.scrape_stackoverflow(query, limit=limit)

    added = 0
    for it in items:
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
    return {'added': added}


@app.post("/scrape/github", response_model=ScrapeResult)
async def scrape_github_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape GitHub issues mentioning OVH."""
    items = github.scrape_github_issues(query, limit=limit)

    added = 0
    for it in items:
        an = sentiment.analyze(it.get('content') or '')
        it['sentiment_score'] = an['score']
        it['sentiment_label'] = an['label']
        db.insert_post({
            'source': it.get('source'),
            'author': it.get('author'),
            'content': it.get('content'),
            'url': it.get('url'),
            'created_at': it.get('created_at'),
            'sentiment_score': it.get('sentiment_score'),
            'sentiment_label': it.get('sentiment_label'),
            'language': it.get('language', 'unknown'),
        })
        added += 1
    return {'added': added}


@app.post("/scrape/reddit", response_model=ScrapeResult)
async def scrape_reddit_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Reddit posts and discussions about OVH using RSS feeds."""
    # Reddit scraper using RSS
    items = reddit.scrape_reddit(query, limit=limit)

    added = 0
    for it in items:
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
    
    # Return success even if no items were added
    return {'added': added}


@app.post("/scrape/ovh-forum", response_model=ScrapeResult)
async def scrape_ovh_forum_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape OVH Community Forum for customer feedback and discussions."""
    try:
        items = ovh_forum.scrape_ovh_forum(query, limit=limit)
    except Exception as e:
        logger.error(f"Error scraping OVH Forum: {e}")
        return ScrapeResult(added=0)
    
    added = 0
    skipped_duplicates = 0
    for it in items:
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
    
    if skipped_duplicates > 0:
        logger.info(f"✓ Added {added} posts from OVH Forum (skipped {skipped_duplicates} duplicates)")
    return {'added': added}


@app.post("/scrape/mastodon", response_model=ScrapeResult)
async def scrape_mastodon_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Mastodon for posts about OVH using public API."""
    try:
        items = mastodon.scrape_mastodon(query, limit=limit)
    except Exception as e:
        logger.error(f"Error scraping Mastodon: {e}")
        return ScrapeResult(added=0)
    
    added = 0
    skipped_duplicates = 0
    for it in items:
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
    
    if skipped_duplicates > 0:
        logger.info(f"✓ Added {added} posts from Mastodon (skipped {skipped_duplicates} duplicates)")
    return {'added': added}


@app.post("/scrape/g2-crowd", response_model=ScrapeResult)
async def scrape_g2_crowd_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape G2 Crowd for OVH product reviews."""
    try:
        items = g2_crowd.scrape_g2_crowd(query, limit=limit)
    except Exception as e:
        logger.error(f"Error scraping G2 Crowd: {e}")
        return ScrapeResult(added=0)
    
    added = 0
    skipped_duplicates = 0
    for it in items:
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
    
    if skipped_duplicates > 0:
        logger.info(f"✓ Added {added} reviews from G2 Crowd (skipped {skipped_duplicates} duplicates)")
    return {'added': added}


@app.post("/scrape/news", response_model=ScrapeResult)
async def scrape_news_endpoint(query: str, limit: int = 50):
    print(f"[NEWS SCRAPER] Starting with query={query}, limit={limit}")
    items = news.scrape_google_news(query, limit=limit)
    print(f"[NEWS SCRAPER] Got {len(items)} items")

    added = 0
    try:
        for it in items:
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
    except Exception as e:
        print(f"[NEWS SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return ScrapeResult(added=added)


@app.post("/scrape/trustpilot", response_model=ScrapeResult)
async def scrape_trustpilot_endpoint(query: str = "OVH domain", limit: int = 50):
    """Scrape Trustpilot customer reviews about OVH."""
    print(f"[TRUSTPILOT SCRAPER] Starting with query={query}, limit={limit}")
    items = trustpilot.scrape_trustpilot_reviews(query, limit=limit)
    print(f"[TRUSTPILOT SCRAPER] Got {len(items)} reviews")

    added = 0
    try:
        for it in items:
            # Skip sentiment analysis if already provided by scraper
            if not it.get('sentiment_score'):
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
    except Exception as e:
        print(f"[TRUSTPILOT SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return ScrapeResult(added=added)


@app.get('/settings/queries')
async def get_saved_queries():
    """Return saved keywords/queries from DB."""
    return {'keywords': db.get_saved_queries()}


@app.post('/settings/queries')
async def post_saved_queries(payload: KeywordsPayload):
    """Save provided keywords list. Expects JSON: { "keywords": ["a","b"] }"""
    db.save_queries(payload.keywords)
    return {'saved': len(payload.keywords)}


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


@app.get("/posts")
async def get_posts(limit: int = 20, offset: int = 0, language: str = None):
    """Get posts from database, excluding sample data."""
    posts = db.get_posts(limit=limit, offset=offset, language=language)
    # Filter out sample posts
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
        
    except Exception as e:
        print(f"LLM API error: {e}")
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
    
    # Create prompt
    prompt = f"""You are an OVHcloud customer support analyst. Analyze the following customer feedback posts and generate {max_actions} specific, actionable recommended actions.

Statistics:
- Total posts: {stats.get('total', 0)}
- Negative posts (last 48h): {stats.get('recent_negative', 0)}
- Spike detected: {stats.get('spike_detected', False)}
- Top product impacted: {stats.get('top_product', 'N/A')}
- Top issue: {stats.get('top_issue', 'N/A')}

Recent negative posts to analyze:
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

Generate specific, actionable recommended actions that an OVHcloud support team should take. Each action should:
1. Be specific and actionable (not generic)
2. Address the actual issues found in the posts
3. Include an appropriate emoji icon
4. Have a priority level (high/medium/low) based on urgency and impact

Format your response as a JSON array with this structure:
[
  {{
    "icon": "🔍",
    "text": "Investigate: [specific issue] (last 48h)",
    "priority": "high"
  }},
  {{
    "icon": "📣",
    "text": "Check: [specific thing to check]",
    "priority": "medium"
  }},
  {{
    "icon": "💬",
    "text": "Prepare: [specific response/macro]",
    "priority": "medium"
  }}
]

Focus on actions that directly address the issues found in the posts. Be specific - mention actual products, errors, or issues mentioned in the posts. Use appropriate emojis (🔍 for investigate, 📣 for check/announce, 💬 for communication, ⚠️ for alerts, etc.)."""

    # Try to use LLM API (OpenAI, Anthropic, or local)
    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    
    if not api_key and llm_provider in ['openai', 'anthropic']:
        # Fallback: Generate actions using rule-based approach
        return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)
    
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
        
    except Exception as e:
        print(f"LLM API error: {e}")
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
    """Fallback rule-based action generation when LLM is not available."""
    actions = []
    
    # Action 1: Investigate if spike detected
    if stats.get('spike_detected') and stats.get('recent_negative', 0) > 0:
        top_product = stats.get('top_product', '')
        if top_product and top_product != 'N/A':
            actions.append(RecommendedAction(
                icon='🔍',
                text=f'Investigate: {top_product} issues (last 48h)',
                priority='high'
            ))
        else:
            actions.append(RecommendedAction(
                icon='🔍',
                text='Investigate: Negative feedback spike (last 48h)',
                priority='high'
            ))
    
    # Action 2: Check status page if spike detected
    if stats.get('spike_detected'):
        actions.append(RecommendedAction(
            icon='📣',
            text='Check: Status page or ongoing incident',
            priority='high'
        ))
    
    # Action 3: Prepare support response
    top_product = stats.get('top_product', '')
    if top_product and top_product != 'N/A' and stats.get('recent_negative', 0) > 0:
        actions.append(RecommendedAction(
            icon='💬',
            text=f'Prepare: Support macro / canned response for {top_product}',
            priority='medium'
        ))
    elif stats.get('recent_negative', 0) > 0:
        actions.append(RecommendedAction(
            icon='💬',
            text='Prepare: Support macro / canned response',
            priority='medium'
        ))
    
    # Limit to max_actions
    return actions[:max_actions]


@app.post("/api/recommended-actions", response_model=RecommendedActionsResponse)
async def get_recommended_actions(request: RecommendedActionRequest):
    """Generate recommended actions based on customer feedback posts using LLM."""
    try:
        actions = await generate_recommended_actions_with_llm(
            request.posts, 
            request.recent_posts, 
            request.stats, 
            request.max_actions
        )
        return RecommendedActionsResponse(actions=actions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommended actions: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend HTML file based on UI_VERSION config."""
    # Check for UI version in .app_config or environment variable
    app_config_path = Path(__file__).resolve().parents[2] / "backend" / ".app_config"
    ui_version = "v2"  # default to v2 now
    
    if app_config_path.exists():
        with open(app_config_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("UI_VERSION="):
                    ui_version = line.split("=", 1)[1].strip()
                    break
    
    # Also check environment variable (takes precedence)
    ui_version = os.getenv('UI_VERSION', ui_version)
    
    if ui_version == "v2":
        frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "v2" / "index.html"
        if frontend_path.exists():
            content = open(frontend_path, "r", encoding="utf-8").read()
            # Replace relative paths with /v2/ paths for static files
            content = content.replace('href="css/', 'href="/v2/css/')
            content = content.replace('src="js/', 'src="/v2/js/')
            return content
        else:
            raise HTTPException(status_code=404, detail="Frontend v2 not found")
    else:
        frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "index.html"
        if frontend_path.exists():
            return open(frontend_path, "r", encoding="utf-8").read()
        else:
            raise HTTPException(status_code=404, detail="Frontend v1 not found")


@app.get("/v1", response_class=HTMLResponse)
async def serve_frontend_v1():
    """Serve the v1 frontend HTML file."""
    frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "index.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        raise HTTPException(status_code=404, detail="Frontend v1 not found")


@app.get("/v2", response_class=HTMLResponse)
async def serve_frontend_v2():
    """Serve the v2 frontend HTML file."""
    frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "v2" / "index.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        raise HTTPException(status_code=404, detail="Frontend v2 not found")


# Mount static files for v2 frontend
frontend_v2_path = Path(__file__).resolve().parents[2] / "frontend" / "v2"
if frontend_v2_path.exists():
    app.mount("/v2", StaticFiles(directory=str(frontend_v2_path), html=False), name="v2-static")
    
    # Also mount at root level for CSS/JS files when v2 is default
    app.mount("/css", StaticFiles(directory=str(frontend_v2_path / "css"), html=False), name="v2-css")
    app.mount("/js", StaticFiles(directory=str(frontend_v2_path / "js"), html=False), name="v2-js")


class UIVersionPayload(BaseModel):
    version: str = Field(..., pattern="^(v1|v2)$")

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
