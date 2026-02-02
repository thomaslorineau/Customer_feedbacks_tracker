import locale
from pathlib import Path
import os
import sys
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler

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

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

from . import database as db
from .keywords import keywords_base


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
    version="1.x",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files for dashboard frontend
# Try multiple paths for Docker and local dev compatibility
def find_frontend_path():
    """Find frontend directory using multiple fallback paths."""
    possible_paths = [
        Path("/app/frontend"),  # Docker absolute path
        Path(__file__).resolve().parents[1] / "frontend",  # Docker relative
        Path(__file__).resolve().parents[2] / "frontend",  # Local dev
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return None

# Mount docs directory FIRST (before other static files to avoid conflicts)
def find_docs_path():
    """Find docs directory using multiple fallback paths."""
    possible_paths = [
        Path("/app/docs"),  # Docker absolute path
        Path(__file__).resolve().parents[1] / "docs",  # Docker relative (backend/app -> backend -> docs)
        Path(__file__).resolve().parents[2] / "docs",  # Local dev (backend/app -> backend -> VibeCoding -> docs)
        Path(__file__).resolve().parents[2].parent / "docs",  # Alternative path
    ]
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found docs directory at: {path}")
            return path
    logger.warning(f"Docs directory not found. Tried paths: {[str(p) for p in possible_paths]}")
    return None

docs_path = find_docs_path()
if docs_path:
    # Verify the file exists before mounting
    test_file = docs_path / "SLIDE_PITCH_PROJET.html"
    if test_file.exists():
        app.mount("/docs", StaticFiles(directory=str(docs_path), html=True), name="docs")
        logger.info(f"✅ Docs directory mounted at /docs from {docs_path}")
        logger.info(f"✅ Test file exists: {test_file}")
    else:
        logger.warning(f"Docs directory found at {docs_path} but SLIDE_PITCH_PROJET.html not found")
else:
    logger.warning("Docs directory not found. Documentation files will not be served.")

frontend_path = find_frontend_path()
if frontend_path:
    # Mount dashboard CSS and JS
    dashboard_css_path = frontend_path / "dashboard" / "css"
    dashboard_js_path = frontend_path / "dashboard" / "js"
    if dashboard_css_path.exists():
        app.mount("/dashboard/css", StaticFiles(directory=str(dashboard_css_path), html=False), name="dashboard-css")
    if dashboard_js_path.exists():
        app.mount("/dashboard/js", StaticFiles(directory=str(dashboard_js_path), html=False), name="dashboard-js")

    # Mount assets (logos, images)
    assets_path = frontend_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path), html=False), name="assets")

    # Mount shared CSS files
    shared_css_path = frontend_path / "css"
    if shared_css_path.exists():
        app.mount("/css", StaticFiles(directory=str(shared_css_path), html=False), name="shared-css")

    # Mount shared JS files
    shared_js_path = frontend_path / "js"
    if shared_js_path.exists():
        app.mount("/js", StaticFiles(directory=str(shared_js_path), html=False), name="shared-js")

    # Mount improvements static files (must be before /improvements route)
    improvements_path = frontend_path / "improvements"
    if improvements_path.exists():
        improvements_js_path = improvements_path / "js"
        if improvements_js_path.exists():
            app.mount("/improvements/js", StaticFiles(directory=str(improvements_js_path), html=False), name="improvements-js")

if not frontend_path:
    logger.warning("Frontend directory not found. Static files will not be served.")

# Enable CORS for frontend - restrict to specific ports for security
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
    
    # Content-Security-Policy
    # Allow Chart.js CDN, inline scripts for dashboard, and API calls
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:; "
        "connect-src 'self' https://api.openai.com https://api.anthropic.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp_policy
    
    # Only add HSTS if using HTTPS in production
    if os.getenv("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Global exception handler to ensure JSON responses for all errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure all exceptions return JSON responses, especially for scraper endpoints."""
    import traceback
    import sys
    error_type = type(exc).__name__
    error_msg = str(exc)
    
    # Skip handling for HTTPException and ValidationError (handled by specific handlers)
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        raise exc
    
    # Log the full traceback
    try:
        logger.error(f"Unhandled exception: {error_type}: {error_msg}", exc_info=True)
        # Also print to stderr to ensure we see it even if logging fails
        print(f"CRITICAL ERROR: {error_type}: {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    except Exception as log_error:
        # If logging fails, at least log to console
        print(f"ERROR: {error_type}: {error_msg}", file=sys.stderr)
        print(f"Also failed to log error: {log_error}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
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
    # Safely encode error detail to avoid ASCII encoding issues
    def safe_detail(detail):
        """Safely encode error detail to UTF-8."""
        if not detail:
            return ""
        try:
            if isinstance(detail, str):
                # Ensure UTF-8 encoding, replace problematic characters
                return detail.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            else:
                # If not a string, convert and clean
                detail_str = str(detail)
                return detail_str.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        except Exception:
            # Ultimate fallback: ASCII-only
            try:
                return str(detail).encode('ascii', errors='replace').decode('ascii', errors='replace')
            except Exception:
                return "An error occurred"
    
    safe_detail_text = safe_detail(exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": safe_detail_text}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors and ensure JSON responses."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


# Test route to verify docs mounting (temporary, for debugging)
@app.get("/test-docs")
async def test_docs():
    """Test endpoint to verify docs directory is accessible."""
    docs_path = find_docs_path()
    if docs_path:
        test_file = docs_path / "SLIDE_PITCH_PROJET.html"
        return {
            "docs_path": str(docs_path),
            "docs_path_exists": docs_path.exists(),
            "test_file": str(test_file),
            "test_file_exists": test_file.exists(),
            "mounted": True
        }
    return {"mounted": False, "error": "Docs path not found"}

# Include routers
from .routers import auth, config, scraping, dashboard, admin, email, pages

app.include_router(auth.router)
app.include_router(config.router)
app.include_router(scraping.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(email.router)
app.include_router(pages.router)

# Include async jobs router (for Docker/Redis mode)
try:
    from .routers import jobs as jobs_router
    app.include_router(jobs_router.router)
    logger.info("[ROUTER] Async jobs router enabled")
except ImportError as e:
    logger.warning(f"[ROUTER] Async jobs router not available: {e}")

# Set limiter for scraping router
scraping.set_limiter(limiter)

# Import scheduler job
from .scheduler.jobs import auto_scrape_job

# ===== SCHEDULER SETUP =====
scheduler = BackgroundScheduler()


@app.on_event("startup")
def startup_event():
    db.init_db()
    
    # Load API keys from database into environment variables
    # This ensures keys persist across Docker container restarts
    try:
        from .database import pg_get_config
        openai_key = pg_get_config('OPENAI_API_KEY')
        anthropic_key = pg_get_config('ANTHROPIC_API_KEY')
        mistral_key = pg_get_config('MISTRAL_API_KEY')
        llm_provider = pg_get_config('LLM_PROVIDER')
        discord_bot_token = pg_get_config('DISCORD_BOT_TOKEN')
        discord_guild_id = pg_get_config('DISCORD_GUILD_ID')
        
        if openai_key:
            os.environ['OPENAI_API_KEY'] = openai_key
            logger.info("✅ Loaded OpenAI API key from database")
        if anthropic_key:
            os.environ['ANTHROPIC_API_KEY'] = anthropic_key
            logger.info("✅ Loaded Anthropic API key from database")
        if mistral_key:
            os.environ['MISTRAL_API_KEY'] = mistral_key
            logger.info("✅ Loaded Mistral API key from database")
        if llm_provider:
            os.environ['LLM_PROVIDER'] = llm_provider
            logger.info(f"✅ Loaded LLM provider from database: {llm_provider}")
        if discord_bot_token:
            os.environ['DISCORD_BOT_TOKEN'] = discord_bot_token
            logger.info("✅ Loaded Discord bot token from database")
        if discord_guild_id:
            os.environ['DISCORD_GUILD_ID'] = discord_guild_id
            logger.info("✅ Loaded Discord guild ID from database")
    except Exception as e:
        logger.warning(f"Could not load API keys from database at startup: {e}")
    
    # Automatically clean up sample/fake posts on startup
    try:
        deleted_count = db.delete_sample_posts()
        if deleted_count > 0:
            logger.info(f"[CLEANUP] Removed {deleted_count} sample/fake posts from database")
    except Exception as e:
        logger.warning(f"[CLEANUP] Warning: Could not clean sample posts: {e}")
    
    # Automatically clean up non-OVH posts on startup
    try:
        deleted_count = db.delete_non_ovh_posts()
        if deleted_count > 0:
            logger.info(f"[CLEANUP] Removed {deleted_count} non-OVH posts from database")
        else:
            logger.info("[CLEANUP] All posts are OVH-related [OK]")
    except Exception as e:
        logger.warning(f"[CLEANUP] Warning: Could not clean non-OVH posts: {e}")
    
    # Start scheduler
    if not scheduler.running:
        # Auto-scrape job: every 3 hours
        scheduler.add_job(auto_scrape_job, 'interval', hours=3, id='auto_scrape')
        
        # Auto-backup job: every hour (keeps 24 hourly backups = 1 day)
        from .scheduler.jobs import auto_backup_job
        scheduler.add_job(auto_backup_job, 'interval', hours=1, id='auto_backup_hourly')
        
        # Daily backup job: every day at 2 AM (keeps 30 daily backups = 1 month)
        from .scheduler.jobs import daily_backup_job
        scheduler.add_job(daily_backup_job, 'cron', hour=2, minute=0, id='auto_backup_daily')
        
        # Recheck answered status: every 3 hours (checks 50 posts per run)
        from .scheduler.jobs import recheck_answered_status_job
        scheduler.add_job(recheck_answered_status_job, 'interval', hours=3, id='recheck_answered')
        
        scheduler.start()
        logger.info("[SCHEDULER] Started:")
        logger.info("  - Auto-scrape: every 3 hours")
        logger.info("  - Auto-backup (hourly): every hour (keeps 24 backups)")
        logger.info("  - Auto-backup (daily): daily at 2 AM (keeps 30 backups)")
        logger.info("  - Recheck answered: every 3 hours (50 posts/run)")


@app.on_event("shutdown")
def shutdown_event():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[SCHEDULER] Stopped")
