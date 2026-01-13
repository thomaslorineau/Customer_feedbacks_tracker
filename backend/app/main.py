import locale

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from apscheduler.schedulers.background import BackgroundScheduler

from . import db
from .scraper import x_scraper, stackoverflow, news, github, hackernews, trustpilot
from .analysis import sentiment


app = FastAPI(title="ovh-complaints-tracker")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeResult(BaseModel):
    added: int


    # Définir la langue par défaut sur le français
    try:
        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    except locale.Error:
        # Fallback si la locale n'est pas disponible
        locale.setlocale(locale.LC_ALL, 'fr_FR')


# ===== SCHEDULER SETUP =====
scheduler = BackgroundScheduler()

def auto_scrape_job():
    """Scheduled job to scrape all sources automatically."""
    print("🔄 Running scheduled scrape...")
    
    queries = ["OVH domain", "OVH complaint", "OVH support"]
    
    for query in queries:
        # Scrape X (multi-query for better coverage)
        try:
            items = x_scraper.scrape_x_multi_queries(limit=10)
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
            print(f"✓ Added {len(items)} posts from X/Twitter")
        except Exception as e:
            print(f"✗ Error scraping X: {e}")
        
        # Scrape Stack Overflow
        try:
            items = stackoverflow.scrape_stackoverflow(query, limit=10)
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
            print(f"✓ Added {len(items)} posts from Stack Overflow")
        except Exception as e:
            print(f"✗ Error scraping Stack Overflow: {e}")
        
        # Scrape Hacker News
        try:
            items = hackernews.scrape_hackernews(query, limit=10)
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
            print(f"✓ Added {len(items)} posts from Hacker News")
        except Exception as e:
            print(f"✗ Error scraping Hacker News: {e}")
        
        # Scrape GitHub Issues
        try:
            items = github.scrape_github_issues(query, limit=10)
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
            print(f"✓ Added {len(items)} posts from GitHub Issues")
        except Exception as e:
            print(f"✗ Error scraping GitHub Issues: {e}")


@app.on_event("startup")
def startup_event():
    db.init_db()
    
    # Start scheduler
    if not scheduler.running:
        scheduler.add_job(auto_scrape_job, 'interval', hours=3, id='auto_scrape')
        scheduler.start()
        print("✅ Scheduler started - will auto-scrape every 3 hours")


@app.on_event("shutdown")
def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
        print("❌ Scheduler stopped")


@app.post("/scrape/x", response_model=ScrapeResult)
async def scrape_x_endpoint(query: str = None, limit: int = 50):
    """Scrape X/Twitter. If no query provided, uses multiple OVH-related queries."""
    try:
        print(f"[X SCRAPER] Starting with query={query}, limit={limit}")
        if query:
            items = x_scraper.scrape_x(query, limit=limit)
        else:
            # Use multi-query scraper for better coverage
            items = x_scraper.scrape_x_multi_queries(limit=limit)
        
        print(f"[X SCRAPER] Got {len(items)} items")
    except Exception as e:
        print(f"[X SCRAPER ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        # No fallback - only real data
        raise HTTPException(status_code=503, detail="X/Twitter scraper unavailable (snscrape incompatibility with Python 3.13)")

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
            })
            added += 1
    except Exception as e:
        print(f"[X SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return ScrapeResult(added=added)


@app.post("/scrape/stackoverflow", response_model=ScrapeResult)
async def scrape_stackoverflow_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Stack Overflow questions about OVH."""
    try:
        items = stackoverflow.scrape_stackoverflow(query, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        })
        added += 1
    return {'added': added}


@app.post("/scrape/github", response_model=ScrapeResult)
async def scrape_github_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape GitHub issues mentioning OVH."""
    try:
        items = github.scrape_github_issues(query, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        })
        added += 1
    return {'added': added}


@app.post("/scrape/hackernews", response_model=ScrapeResult)
async def scrape_hackernews_endpoint(query: str = "OVH", limit: int = 50):
    """Scrape Hacker News discussions about OVH."""
    try:
        items = hackernews.scrape_hackernews(query, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        })
        added += 1
    return {'added': added}


@app.post("/scrape/news", response_model=ScrapeResult)
async def scrape_news_endpoint(query: str, limit: int = 50):
    try:
        print(f"[NEWS SCRAPER] Starting with query={query}, limit={limit}")
        items = news.scrape_google_news(query, limit=limit)
        print(f"[NEWS SCRAPER] Got {len(items)} items")
    except Exception as e:
        print(f"[NEWS SCRAPER ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        # No fallback - only real data
        raise HTTPException(status_code=503, detail="Google News scraper unavailable")

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
    try:
        print(f"[TRUSTPILOT SCRAPER] Starting with query={query}, limit={limit}")
        items = trustpilot.scrape_trustpilot_reviews(query, limit=limit)
        print(f"[TRUSTPILOT SCRAPER] Got {len(items)} reviews")
    except Exception as e:
        print(f"[TRUSTPILOT SCRAPER ERROR] {type(e).__name__}: {str(e)}")
        # No fallback - only real data
        raise HTTPException(status_code=503, detail="Trustpilot scraper unavailable")

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
            })
            added += 1
    except Exception as e:
        print(f"[TRUSTPILOT SCRAPER DB ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return ScrapeResult(added=added)


@app.get("/posts")
async def get_posts(limit: int = 100):
    return db.get_posts(limit=limit)
