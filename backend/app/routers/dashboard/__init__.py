"""Dashboard routers."""
from fastapi import APIRouter
from . import insights, posts

router = APIRouter(prefix="/api")

# Include sub-routers (routes already have their paths defined, now with /api prefix)
router.include_router(insights.router, tags=["Dashboard", "Insights"])
router.include_router(posts.router, tags=["Dashboard", "Posts"])
