"""Dashboard router module."""
from fastapi import APIRouter
from .analytics import router as analytics_router
from .insights import router as insights_router
from .posts import router as posts_router

# Combine all routers
router = APIRouter()
router.include_router(analytics_router)
router.include_router(insights_router)
router.include_router(posts_router)

__all__ = ['router']





