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
    # Try multiple paths for Docker and local dev compatibility
    possible_paths = [
        Path("/app/frontend/index.html"),  # Docker absolute path
        Path(__file__).resolve().parents[1] / "frontend" / "index.html",  # Docker relative
        Path(__file__).resolve().parents[2] / "frontend" / "index.html",  # Local dev
    ]
    
    frontend_path = None
    for path in possible_paths:
        if path.exists():
            frontend_path = path
            break
    
    if frontend_path and frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        from fastapi import HTTPException
        tried_paths = ", ".join(str(p) for p in possible_paths)
        logger.error(f"Scraping page not found. Tried: {tried_paths}")
        raise HTTPException(status_code=404, detail=f"Scraping page not found. Tried: {tried_paths}")


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/dashboard-analytics", response_class=HTMLResponse)
async def serve_frontend_dashboard():
    """Serve the dashboard analytics page."""
    # Try multiple paths for Docker and local dev compatibility
    # Docker: /app/frontend/dashboard/index.html (absolute path)
    # Local: backend/../frontend/dashboard/index.html (relative from backend/app/routers)
    possible_paths = [
        Path("/app/frontend/dashboard/index.html"),  # Docker absolute path
        Path(__file__).resolve().parents[1] / "frontend" / "dashboard" / "index.html",  # Docker relative
        Path(__file__).resolve().parents[2] / "frontend" / "dashboard" / "index.html",  # Local dev
    ]
    
    frontend_path = None
    for path in possible_paths:
        if path.exists():
            frontend_path = path
            break
    
    if frontend_path and frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        from fastapi import HTTPException
        tried_paths = ", ".join(str(p) for p in possible_paths)
        logger.error(f"Dashboard not found. Tried: {tried_paths}")
        raise HTTPException(status_code=404, detail=f"Dashboard page not found. Tried: {tried_paths}")


@router.get("/logs", response_class=HTMLResponse)
async def serve_logs_page():
    """Serve the scraping logs page."""
    # Try multiple paths for Docker and local dev compatibility
    possible_paths = [
        Path("/app/frontend/logs.html"),  # Docker absolute path
        Path(__file__).resolve().parents[1] / "frontend" / "logs.html",  # Docker relative
        Path(__file__).resolve().parents[2] / "frontend" / "logs.html",  # Local dev
    ]
    
    frontend_path = None
    for path in possible_paths:
        if path.exists():
            frontend_path = path
            break
    
    if frontend_path and frontend_path.exists():
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
    # Try multiple paths for Docker and local dev compatibility
    possible_paths = [
        Path("/app/frontend/improvements/index.html"),  # Docker absolute path
        Path(__file__).resolve().parents[1] / "frontend" / "improvements" / "index.html",  # Docker relative
        Path(__file__).resolve().parents[2] / "frontend" / "improvements" / "index.html",  # Local dev
    ]
    
    frontend_path = None
    for path in possible_paths:
        if path.exists():
            frontend_path = path
            break
    
    if frontend_path and frontend_path.exists():
        content = open(frontend_path, "r", encoding="utf-8").read()
        # Replace relative paths with absolute paths for static files
        content = content.replace('href="/dashboard/css/', 'href="/dashboard/css/')
        content = content.replace('src="/improvements/js/', 'src="/improvements/js/')
        return content
    else:
        from fastapi import HTTPException
        tried_paths = ", ".join(str(p) for p in possible_paths)
        logger.error(f"Improvements page not found. Tried: {tried_paths}")
        raise HTTPException(status_code=404, detail=f"Improvements page not found. Tried: {tried_paths}")


@router.get("/settings", response_class=HTMLResponse)
async def serve_settings():
    """Serve the settings page."""
    # Try multiple paths for Docker and local dev compatibility
    possible_paths = [
        Path("/app/frontend/dashboard/settings.html"),  # Docker absolute path
        Path(__file__).resolve().parents[1] / "frontend" / "dashboard" / "settings.html",  # Docker relative
        Path(__file__).resolve().parents[2] / "frontend" / "dashboard" / "settings.html",  # Local dev
    ]
    
    frontend_path = None
    for path in possible_paths:
        if path.exists():
            frontend_path = path
            break
    
    if frontend_path and frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        from fastapi import HTTPException
        tried_paths = ", ".join(str(p) for p in possible_paths)
        logger.error(f"Settings page not found. Tried: {tried_paths}")
        raise HTTPException(status_code=404, detail=f"Settings page not found. Tried: {tried_paths}")


@router.get("/cleanup-stale-job", response_class=HTMLResponse)
async def serve_cleanup_page():
    """Serve the cleanup page for stale jobs."""
    # Try multiple paths for Docker and local dev compatibility
    possible_paths = [
        Path("/app/frontend/cleanup-stale-job.html"),  # Docker absolute path
        Path(__file__).resolve().parents[1] / "frontend" / "cleanup-stale-job.html",  # Docker relative
        Path(__file__).resolve().parents[2] / "frontend" / "cleanup-stale-job.html",  # Local dev
    ]
    
    frontend_path = None
    for path in possible_paths:
        if path.exists():
            frontend_path = path
            break
    
    if frontend_path and frontend_path.exists():
        return open(frontend_path, "r", encoding="utf-8").read()
    else:
        from fastapi import HTTPException
        tried_paths = ", ".join(str(p) for p in possible_paths)
        logger.error(f"Cleanup page not found. Tried: {tried_paths}")
        raise HTTPException(status_code=404, detail=f"Cleanup page not found. Tried: {tried_paths}")

