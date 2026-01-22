"""Dashboard routers."""
from fastapi import APIRouter
from . import insights, posts

router = APIRouter()

# Include sub-routers (no prefix, routes already have their paths defined)
router.include_router(insights.router, tags=["Dashboard", "Insights"])
router.include_router(posts.router, tags=["Dashboard", "Posts"])
