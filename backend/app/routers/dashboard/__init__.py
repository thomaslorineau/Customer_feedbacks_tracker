"""Dashboard router module."""
from fastapi import APIRouter
from .analytics import router as analytics_router
from .posts import router as posts_router
from .insights import router as insights_router

# Combine all routers
router = APIRouter()
router.include_router(analytics_router)
router.include_router(posts_router)
router.include_router(insights_router)

__all__ = ['router']


