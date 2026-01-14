import locale
from pathlib import Path

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

from . import db
from .scraper import x_scraper, stackoverflow, news, github, hackernews, trustpilot
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

# Enable CORS for frontend - restrict to localhost for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:*", "http://127.0.0.1:*", "file://"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class ScrapeRequest(BaseModel):
    """Validated scrape request with input validation."""
    query: str = Field(default="OVH", min_length=1, max_length=100)
    limit: int = Field(default=50, ge=1, le=1000)


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

            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                })
            print(f"✓ Added {len(items)} posts from X/Twitter for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping X (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # Stack Overflow
        try:
            items = stackoverflow.scrape_stackoverflow(query, limit=per_query_limit)
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                })
            print(f"✓ Added {len(items)} posts from Stack Overflow for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping Stack Overflow (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # Hacker News
        try:
            items = hackernews.scrape_hackernews(query, limit=per_query_limit)
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                })
            print(f"✓ Added {len(items)} posts from Hacker News for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping Hacker News (non-fatal): {type(e).__name__}")

        time.sleep(0.5)

        # GitHub Issues
        try:
            items = github.scrape_github_issues(query, limit=per_query_limit)
            for it in items:
                an = sentiment.analyze(it.get('content') or '')
                db.insert_post({
                    'source': it.get('source'),
                    'author': it.get('author'),
                    'content': it.get('content'),
                    'url': it.get('url'),
                    'created_at': it.get('created_at'),
                    'sentiment_score': an['score'],
                    'sentiment_label': an['label'],
                })
            print(f"✓ Added {len(items)} posts from GitHub Issues for '{query}'")
        except Exception as e:
            print(f"✗ Error scraping GitHub Issues (non-fatal): {type(e).__name__}")

        # small pause between queries to avoid bursts
        time.sleep(1.0)


@app.on_event("startup")
def startup_event():
    db.init_db()
    
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
    try:
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
    except Exception as e:
        print(f"[X SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

    return ScrapeResult(added=added)


# In-memory job store for background keyword scraping
JOBS = {}


def _run_scrape_for_source(source: str, query: str, limit: int):
    """Call the appropriate scraper and insert results into DB; return count added."""
    mapper = {
        'x': lambda q, l: x_scraper.scrape_x(q, limit=l),
        'github': lambda q, l: github.scrape_github_issues(q, limit=l),
        'stackoverflow': lambda q, l: stackoverflow.scrape_stackoverflow(q, limit=l),
        'hackernews': lambda q, l: hackernews.scrape_hackernews(q, limit=l),
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
    for it in items:
        try:
            an = sentiment.analyze(it.get('content') or '')
            db.insert_post({
                'source': it.get('source'),
                'author': it.get('author'),
                'content': it.get('content'),
                'url': it.get('url'),
                'created_at': it.get('created_at'),
                'sentiment_score': an['score'],
                'sentiment_label': an['label'],
                'language': it.get('language', 'unknown'),
            })
            added += 1
        except Exception:
            # ignore per-item failures
            continue
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


@app.post("/scrape/hackernews", response_model=ScrapeResult)
async def scrape_hackernews_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Hacker News discussions about OVH."""
    items = hackernews.scrape_hackernews(query, limit=limit)

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


@app.get("/posts")
async def get_posts(limit: int = 20, offset: int = 0, language: str = None):
    return db.get_posts(limit=limit, offset=offset, language=language)


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend HTML file."""
    frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "index.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")
