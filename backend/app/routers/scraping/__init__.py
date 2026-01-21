"""Scraping router module."""
from fastapi import APIRouter
from .endpoints import router as endpoints_router
from .jobs import router as jobs_router, _run_scrape_for_source, JOBS
from .base import set_limiter

# Combine all routers
router = APIRouter()
router.include_router(endpoints_router)
router.include_router(jobs_router)

__all__ = ['router', 'set_limiter', '_run_scrape_for_source', 'JOBS']

