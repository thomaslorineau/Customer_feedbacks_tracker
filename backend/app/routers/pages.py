"""
HTML page routes for serving frontend pages.
"""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend HTML file - redirects to dashboard by default."""
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/scraping", response_class=HTMLResponse)
@router.get("/scraping-configuration", response_class=HTMLResponse)
async def serve_frontend_scraping():
    """Serve the scraping & configuration page."""
    frontend_path = Path(__file__).resolve().parents[3] / "frontend" / "index.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scraping page not found")


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/dashboard-analytics", response_class=HTMLResponse)
async def serve_frontend_dashboard():
    """Serve the dashboard analytics page."""
    frontend_path = Path(__file__).resolve().parents[3] / "frontend" / "dashboard" / "index.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Dashboard page not found")


@router.get("/logs", response_class=HTMLResponse)
async def serve_logs_page():
    """Serve the scraping logs page."""
    frontend_path = Path(__file__).resolve().parents[3] / "frontend" / "logs.html"
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


@router.get("/improvements", response_class=HTMLResponse)
async def serve_improvements():
    """Serve the improvements opportunities HTML file."""
    frontend_path = Path(__file__).resolve().parents[3] / "frontend" / "improvements" / "index.html"
    if frontend_path.exists():
        content = open(frontend_path, "r", encoding="utf-8").read()
        # Replace relative paths with absolute paths for static files
        content = content.replace('href="/dashboard/css/', 'href="/dashboard/css/')
        content = content.replace('src="/improvements/js/', 'src="/improvements/js/')
        return content
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Improvements page not found")


@router.get("/settings", response_class=HTMLResponse)
async def serve_settings():
    """Serve the settings page."""
    frontend_path = Path(__file__).resolve().parents[3] / "frontend" / "dashboard" / "settings.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Settings page not found")


@router.get("/cleanup-stale-job", response_class=HTMLResponse)
async def serve_cleanup_page():
    """Serve the cleanup page for stale jobs."""
    frontend_path = Path(__file__).resolve().parents[3] / "frontend" / "cleanup-stale-job.html"
    if frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Cleanup page not found")

