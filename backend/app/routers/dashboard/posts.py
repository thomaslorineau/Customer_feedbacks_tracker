"""Posts endpoints for retrieving and filtering posts."""
import datetime
import time
import logging
from typing import Optional
from fastapi import APIRouter

from ... import db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/posts")
async def get_posts(limit: int = 20, offset: int = 0, language: str = None):
    """Get posts from database, excluding sample data."""
    posts = db.get_posts(limit=limit, offset=offset, language=language)
    filtered = []
    for post in posts:
        url = post.get('url', '')
        is_sample = (
            '/sample' in url or
            'example.com' in url or
            '/status/174' in url or
            url == 'https://trustpilot.com/sample'
        )
        if not is_sample:
            try:
                created_at = post.get('created_at', '')
                if created_at:
                    dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    post['created_at_timestamp'] = dt.timestamp()
                else:
                    post['created_at_timestamp'] = 0
            except:
                post['created_at_timestamp'] = 0
            
            post['views'] = post.get('views', 0)
            post['comments'] = post.get('comments', 0)
            post['reactions'] = post.get('reactions', 0)
            
            filtered.append(post)
    return filtered


@router.get("/api/posts-for-improvement")
async def get_posts_for_improvement(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    language: Optional[str] = None,
    source: Optional[str] = None,
    sort_by: str = "opportunity_score"
):
    """Get posts ranked by priority score for improvement review."""
    all_posts = db.get_posts(limit=10000, offset=0)
    
    for post in all_posts:
        try:
            created_at = post.get('created_at', '')
            if created_at:
                dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                post['created_at_timestamp'] = dt.timestamp()
            else:
                post['created_at_timestamp'] = 0
        except:
            post['created_at_timestamp'] = 0
        post['views'] = post.get('views', 0)
        post['comments'] = post.get('comments', 0)
        post['reactions'] = post.get('reactions', 0)
    
    filtered = all_posts
    
    if search:
        search_lower = search.lower()
        filtered = [p for p in filtered if search_lower in (p.get('content', '') or '').lower()]
    
    if language and language != 'all':
        filtered = [p for p in filtered if p.get('language') == language]
    
    if source and source != 'all':
        filtered = [p for p in filtered if 
                   (p.get('source') == source) or 
                   (source == 'GitHub' and (p.get('source') == 'GitHub Issues' or p.get('source') == 'GitHub Discussions'))]
    
    now = time.time()
    posts_with_scores = []
    
    pain_point_keywords = []
    pain_point_patterns = {
        'Refund Delays': ['refund', 'rembours', 'remboursement', 'pending refund', 'delayed refund'],
        'Billing Clarity': ['billing', 'invoice', 'facture', 'charge', 'confusing', 'unclear'],
        'HTTPS/SSL Renewal': ['ssl', 'https', 'certificate', 'renewal', 'expired', 'certificat'],
        'Support Response Time': ['support', 'response', 'slow', 'unresponsive', 'waiting', 'ticket'],
        'VPS Backups': ['backup', 'vps backup', 'backup error', 'backup fail', 'sauvegarde'],
        'Domain Issues': ['domain', 'dns', 'nameserver', 'domaine', 'expired domain'],
        'Email Problems': ['email', 'mail', 'mx record', 'smtp', 'imap', 'exchange']
    }
    for pattern in pain_point_patterns.values():
        pain_point_keywords.extend([k.lower() for k in pattern])
    
    for post in filtered:
        content_lower = (post.get('content', '') or '').lower()
        
        sentiment_value = 0.0
        if post.get('sentiment_label') == 'negative':
            sentiment_value = 1.0
        elif post.get('sentiment_label') == 'neutral':
            sentiment_value = 0.5
        else:
            sentiment_value = 0.2
        
        keyword_matches = sum(1 for keyword in pain_point_keywords if keyword in content_lower)
        keyword_relevance = min(1.0, 0.1 + (keyword_matches * 0.3))
        
        post_time = post.get('created_at_timestamp', 0) or 0
        days_ago = (now - post_time) / (24 * 3600)
        if days_ago <= 7:
            recency_value = 1.0
        elif days_ago <= 30:
            recency_value = 0.7
        elif days_ago <= 90:
            recency_value = 0.4
        else:
            recency_value = 0.1
        
        priority_score = sentiment_value * keyword_relevance * recency_value
        priority_score_scaled = int(priority_score * 100)
        
        posts_with_scores.append({
            **post,
            'opportunity_score': priority_score_scaled,
            'priority_score': priority_score_scaled
        })
    
    if sort_by == 'opportunity_score':
        posts_with_scores.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
    elif sort_by == 'recent':
        posts_with_scores.sort(key=lambda x: x.get('created_at_timestamp', 0) or 0, reverse=True)
    elif sort_by == 'engagement':
        posts_with_scores.sort(key=lambda x: 
            (x.get('views', 0) or 0) + (x.get('comments', 0) or 0) + (x.get('reactions', 0) or 0), 
            reverse=True)
    
    paginated = posts_with_scores[offset:offset + limit]
    
    return {
        'posts': paginated,
        'total': len(posts_with_scores),
        'offset': offset,
        'limit': limit
    }


