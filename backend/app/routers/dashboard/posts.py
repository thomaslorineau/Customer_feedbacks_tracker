"""Posts endpoints for dashboard."""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging

from ... import db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/posts", tags=["Dashboard", "Posts"])
async def get_posts(
    limit: int = Query(100, description="Maximum number of posts to return", ge=1, le=10000, examples=[100]),
    offset: int = Query(0, description="Offset for pagination", ge=0, examples=[0]),
    language: Optional[str] = Query(None, description="Filter by language (optional)", examples=["en", "fr"])
):
    """
    Get posts from the database with pagination support.
    
    Returns a list of posts ordered by ID (most recent first).
    Supports filtering by language and pagination via limit/offset.
    """
    try:
        posts = db.get_posts(limit=limit, offset=offset, language=language)
        return posts
    except Exception as e:
        logger.error(f"Error fetching posts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch posts: {str(e)}")


@router.post("/posts/{post_id}/mark-answered", tags=["Dashboard", "Posts"])
async def mark_post_answered(post_id: int, answered: bool = True):
    """Marquer manuellement un post comme répondu ou non répondu."""
    success = db.update_post_answered_status(post_id, answered, method='manual')
    if not success:
        raise HTTPException(status_code=404, detail="Post not found or update failed")
    return {"success": True, "post_id": post_id, "answered": answered}


@router.get("/posts/stats/answered", tags=["Dashboard", "Posts"])
async def get_answered_stats():
    """Obtenir les statistiques de réponses."""
    stats = db.get_answered_stats()
    return stats


@router.get("/api/posts-for-improvement", tags=["Dashboard", "Posts"])
async def get_posts_for_improvement(
    limit: int = Query(20, description="Maximum number of posts to return", ge=1, le=1000),
    offset: int = Query(0, description="Offset for pagination", ge=0),
    sort_by: str = Query("opportunity_score", description="Sort field", examples=["opportunity_score", "created_at", "relevance_score"]),
    search: Optional[str] = Query(None, description="Search term"),
    language: Optional[str] = Query(None, description="Filter by language"),
    source: Optional[str] = Query(None, description="Filter by source"),
    date_from: Optional[str] = Query(None, description="Filter posts from this date (YYYY-MM-DD)")
):
    """
    Get posts for improvement review with opportunity scoring.
    
    Returns posts sorted by opportunity score (or other field) with filters.
    Opportunity score is calculated based on sentiment, relevance, and recency.
    """
    try:
        # Get all posts (we'll filter and sort in Python for now)
        all_posts = db.get_posts(limit=10000, offset=0)
        
        # Filter posts
        filtered_posts = []
        for post in all_posts:
            # Skip sample posts
            url = post.get('url', '')
            if '/sample' in url or 'example.com' in url:
                continue
            
            # Apply date filter
            if date_from:
                created_at = post.get('created_at', '')
                if created_at:
                    try:
                        from datetime import datetime
                        post_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        cutoff_date = datetime.fromisoformat(date_from)
                        if post_date.replace(tzinfo=None) < cutoff_date:
                            continue
                    except (ValueError, AttributeError):
                        continue
            
            # Apply filters
            if search:
                search_lower = search.lower()
                content = (post.get('content', '') or '').lower()
                if search_lower not in content:
                    continue
            
            if language and language != 'all':
                post_lang = (post.get('language', '') or '').lower()
                if post_lang != language.lower():
                    continue
            
            if source and source != 'all':
                post_source = (post.get('source', '') or '').lower()
                # Normalize source names
                if post_source == 'github issues' or post_source == 'github discussions':
                    post_source = 'github'
                if post_source != source.lower():
                    continue
            
            filtered_posts.append(post)
        
        # Calculate opportunity score for each post
        import time
        now = time.time()
        
        for post in filtered_posts:
            # Base score from relevance (scale 0-30)
            # relevance_score is typically 0.3-1.0, so we scale it to 0-30 points
            relevance_score = post.get('relevance_score', 0) or 0
            base_score = min(relevance_score * 30, 30)
            
            # Sentiment score (additive, 0-40 points)
            # Negative posts are most important for improvements
            sentiment_score = 0
            sentiment_label = post.get('sentiment_label', 'neutral')
            if sentiment_label == 'negative':
                sentiment_score = 40  # High priority for negative feedback
            elif sentiment_label == 'neutral':
                sentiment_score = 15  # Medium priority
            else:  # positive
                sentiment_score = 5   # Low priority
            
            # Recency score (additive, 0-20 points)
            # Recent posts are more actionable
            recency_score = 0
            created_at = post.get('created_at', '')
            if created_at:
                try:
                    from datetime import datetime
                    post_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    post_timestamp = post_date.timestamp()
                    days_old = (now - post_timestamp) / (24 * 3600)
                    if days_old < 7:
                        recency_score = 20  # Very recent
                    elif days_old < 30:
                        recency_score = 15  # Recent
                    elif days_old < 90:
                        recency_score = 10  # Moderately old
                    else:
                        recency_score = 5   # Old
                except:
                    recency_score = 10  # Default if date parsing fails
            
            # Engagement score (additive, 0-10 points)
            # Posts with high engagement indicate broader impact
            views = post.get('views', 0) or 0
            comments = post.get('comments', 0) or post.get('num_comments', 0) or 0
            reactions = post.get('reactions', 0) or 0
            engagement = views + (comments * 3) + (reactions * 2)
            # Scale: 0 engagement = 0 points, 1000+ engagement = 10 points
            engagement_score = min(engagement / 100, 10)
            
            # Calculate opportunity score (0-100)
            # Formula: base (0-30) + sentiment (0-40) + recency (0-20) + engagement (0-10)
            opportunity_score = min(
                base_score + sentiment_score + recency_score + engagement_score,
                100
            )
            
            post['opportunity_score'] = round(opportunity_score, 1)
        
        # Sort posts
        reverse_order = True  # Higher scores first
        if sort_by == 'opportunity_score':
            filtered_posts.sort(key=lambda p: p.get('opportunity_score', 0), reverse=reverse_order)
        elif sort_by == 'created_at':
            filtered_posts.sort(key=lambda p: p.get('created_at', ''), reverse=reverse_order)
        elif sort_by == 'relevance_score':
            filtered_posts.sort(key=lambda p: p.get('relevance_score', 0), reverse=reverse_order)
        
        # Apply pagination
        total = len(filtered_posts)
        paginated_posts = filtered_posts[offset:offset + limit]
        
        return {
            "posts": paginated_posts,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching posts for improvement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch posts: {str(e)}")
