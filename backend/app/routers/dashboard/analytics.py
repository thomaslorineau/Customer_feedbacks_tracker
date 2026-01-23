"""Analytics functions for dashboard."""
from typing import List
from datetime import datetime, timedelta
from collections import Counter
import re
import logging
from .models import PainPoint, PainPointsResponse
from ... import db

logger = logging.getLogger(__name__)


async def get_pain_points(days: int = 30, limit: int = 5) -> PainPointsResponse:
    """
    Get recurring pain points from posts in the last N days.
    
    Args:
        days: Number of days to look back (default: 30)
        limit: Maximum number of pain points to return (default: 5)
    
    Returns:
        PainPointsResponse with list of pain points
    """
    try:
        # Calculate date threshold
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
        
        # Get all posts (we'll filter by date in Python)
        all_posts = db.get_posts(limit=10000, offset=0)
        
        # Filter posts by date and sentiment
        recent_posts = []
        for post in all_posts:
            created_at = post.get('created_at', '')
            if not created_at:
                continue
            
            try:
                # Parse date (handle both ISO format and other formats)
                post_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if post_date.replace(tzinfo=None) >= cutoff_date:
                    # Prioritize negative posts, but include neutral too
                    sentiment = post.get('sentiment_label', 'neutral')
                    if sentiment in ['negative', 'neutral']:
                        recent_posts.append(post)
            except (ValueError, AttributeError):
                continue
        
        if not recent_posts:
            return PainPointsResponse(
                pain_points=[],
                total_pain_points=0
            )
        
        # Get pain point patterns/keywords from database
        try:
            pain_points_db = db.get_pain_points(enabled_only=True)
            pain_patterns = {}
            for pp in pain_points_db:
                if pp.get('enabled', True):
                    pain_patterns[pp['title']] = {
                        'keywords': pp.get('keywords', []),
                        'icon': pp.get('icon', '📊')
                    }
        except Exception as e:
            logger.warning(f"Error loading pain points from database, using defaults: {e}")
            # Fallback to default pain points if database fails
            pain_patterns = {
                'Performance Issues': {
                    'keywords': ['slow', 'lent', 'performance', 'lag', 'timeout', 'time out', 'slowly', 'slowness', 'slow response', 'slow loading', 'slowly loading'],
                    'icon': '🐌'
                },
                'Downtime & Outages': {
                    'keywords': ['down', 'outage', 'offline', 'unavailable', 'unreachable', 'not working', 'doesn\'t work', 'not accessible', 'service unavailable', 'error 503', 'error 502', 'error 500'],
                    'icon': '🔴'
                },
                'Billing Problems': {
                    'keywords': ['billing', 'invoice', 'payment', 'charge', 'charged', 'refund', 'cost', 'price', 'expensive', 'overcharge', 'facture', 'paiement', 'facturation'],
                    'icon': '💰'
                },
                'Support Issues': {
                    'keywords': ['support', 'ticket', 'help', 'assistance', 'response time', 'no response', 'no reply', 'customer service', 'service client'],
                    'icon': '🎧'
                },
                'Configuration Problems': {
                    'keywords': ['config', 'configuration', 'setup', 'install', 'installation', 'configure', 'setting', 'settings', 'cannot configure', 'can\'t configure'],
                    'icon': '⚙️'
                },
                'API & Integration Issues': {
                    'keywords': ['api', 'integration', 'endpoint', 'connection', 'connect', 'authentication', 'auth', 'token', 'credential'],
                    'icon': '🔌'
                },
                'Data Loss & Backup': {
                    'keywords': ['lost', 'delete', 'deleted', 'backup', 'restore', 'recovery', 'data loss', 'lost data', 'missing data'],
                    'icon': '💾'
                },
                'Security Concerns': {
                    'keywords': ['security', 'hack', 'breach', 'vulnerability', 'exploit', 'unauthorized', 'access', 'secure', 'protection'],
                    'icon': '🔒'
                },
                'Migration Problems': {
                    'keywords': ['migration', 'migrate', 'transfer', 'move', 'upgrade', 'update', 'migration failed', 'cannot migrate'],
                    'icon': '🚚'
                },
                'Network Issues': {
                    'keywords': ['network', 'connection', 'latency', 'bandwidth', 'ddos', 'attack', 'traffic', 'routing', 'dns'],
                    'icon': '🌐'
                }
            }
        
        # Count pain points
        pain_point_counts = {}
        pain_point_posts = {}
        
        for post in recent_posts:
            content = (post.get('content', '') or '').lower()
            if not content:
                continue
            
            # Check each pain point pattern
            for pain_name, pattern_info in pain_patterns.items():
                keywords = pattern_info['keywords']
                # Check if any keyword appears in the content
                if any(keyword.lower() in content for keyword in keywords):
                    if pain_name not in pain_point_counts:
                        pain_point_counts[pain_name] = 0
                        pain_point_posts[pain_name] = []
                    pain_point_counts[pain_name] += 1
                    # Store sample posts (max 3 per pain point)
                    if len(pain_point_posts[pain_name]) < 3:
                        pain_point_posts[pain_name].append({
                            'id': post.get('id'),
                            'content': post.get('content', '')[:200],
                            'source': post.get('source', 'Unknown')
                        })
        
        # Sort by count and take top N
        sorted_pain_points = sorted(
            pain_point_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        # Build response
        pain_points_list = []
        for pain_name, count in sorted_pain_points:
            pattern_info = pain_patterns[pain_name]
            # Generate description based on count
            if count >= 10:
                description = f"Frequently reported issue with {count} mentions in the last {days} days"
            elif count >= 5:
                description = f"Recurring issue mentioned {count} times recently"
            else:
                description = f"Issue mentioned {count} times in the last {days} days"
            
            pain_points_list.append(PainPoint(
                title=pain_name,
                description=description,
                icon=pattern_info['icon'],
                posts_count=count,
                posts=pain_point_posts.get(pain_name, [])
            ))
        
        return PainPointsResponse(
            pain_points=pain_points_list,
            total_pain_points=len(pain_points_list)
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting pain points: {e}", exc_info=True)
        # Return empty response on error
        return PainPointsResponse(
            pain_points=[],
            total_pain_points=0
        )
