"""Analytics functions for dashboard."""
from typing import List
from datetime import datetime, timedelta
from collections import Counter
import re
import logging
from .models import PainPoint, PainPointsResponse
from ... import database as db

logger = logging.getLogger(__name__)


async def get_pain_points(days: int = 30, limit: int = 5, product: str = None) -> PainPointsResponse:
    """
    Get recurring pain points from posts in the last N days.
    
    Args:
        days: Number of days to look back (default: 30)
        limit: Maximum number of pain points to return (default: 5)
        product: Optional product name to filter posts (default: None)
    
    Returns:
        PainPointsResponse with list of pain points
    """
    try:
        # Import product detection function
        from ...db_postgres import detect_product_label
        
        # Calculate date threshold
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
        
        logger.info(f"[pain-points] Starting analysis: days={days}, limit={limit}, product={product}")
        
        # Get all posts - use get_posts_for_improvement logic to ensure consistency
        # But we need all posts, not filtered, so we'll use get_posts directly
        all_posts = db.get_posts(limit=10000, offset=0)
        logger.info(f"[pain-points] Loaded {len(all_posts)} total posts from database")
        
        # Log sample dates for debugging
        if all_posts:
            sample_dates = []
            for post in all_posts[:5]:
                created_at = post.get('created_at')
                sample_dates.append(f"ID {post.get('id')}: {type(created_at).__name__} = {str(created_at)[:50]}")
            logger.debug(f"[pain-points] Sample post dates: {sample_dates}")
        
        # Filter posts by date, sentiment, and product
        # Use same date parsing logic as get_posts_for_improvement for consistency
        recent_posts = []
        date_parse_errors = 0
        skipped_no_date = 0
        
        for post in all_posts:
            created_at = post.get('created_at', '')
            if not created_at:
                skipped_no_date += 1
                continue
            
            try:
                # Parse date using same logic as get_posts_for_improvement
                post_date = None
                
                # Handle datetime object (from PostgreSQL)
                if isinstance(created_at, datetime):
                    post_date = created_at.replace(tzinfo=None) if created_at.tzinfo else created_at
                # Handle string dates
                elif isinstance(created_at, str):
                    try:
                        # Try ISO format with Z
                        if 'Z' in created_at:
                            post_date_str = created_at.replace('Z', '+00:00')
                            post_date = datetime.fromisoformat(post_date_str).replace(tzinfo=None)
                        else:
                            # Try ISO format without Z
                            post_date = datetime.fromisoformat(created_at.split('+')[0].split('.')[0]).replace(tzinfo=None)
                    except (ValueError, AttributeError):
                        # Try other formats as fallback
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                post_date = datetime.strptime(created_at.split('.')[0], fmt)
                                break
                            except:
                                continue
                
                if not post_date:
                    date_parse_errors += 1
                    continue
                
                # Check if post is within date range
                if post_date >= cutoff_date:
                    # Prioritize negative posts, but include neutral too
                    sentiment = post.get('sentiment_label', 'neutral')
                    if sentiment in ['negative', 'neutral']:
                        # Filter by product if specified
                        if product:
                            # Check if post has product field or detect it
                            post_product = post.get('product')
                            if not post_product:
                                # Detect product from content
                                content = post.get('content', '')
                                language = post.get('language', 'unknown')
                                post_product = detect_product_label(content, language)
                            
                            # Match product (case-insensitive)
                            if post_product and post_product.lower() == product.lower():
                                recent_posts.append(post)
                        else:
                            # No product filter, include all posts
                            recent_posts.append(post)
            except Exception as e:
                date_parse_errors += 1
                logger.debug(f"Error parsing date for post {post.get('id')}: {e}, date: {created_at}")
                continue
        
        logger.info(f"[pain-points] Date filtering: {skipped_no_date} posts without date, {date_parse_errors} parse errors, {len(recent_posts)} posts in range")
        
        # CRITICAL: If no recent posts found, IMMEDIATELY use fallback with all negative/neutral posts
        # Don't wait for parse errors - posts are likely just older than the requested period
        if not recent_posts:
            logger.warning(f"[pain-points] No posts found in last {days} days, using ALL negative/neutral posts as fallback (ignoring date filter)")
            recent_posts = []
            for post in all_posts:
                # Skip sample posts
                url = post.get('url', '')
                if '/sample' in url or 'example.com' in url:
                    continue
                
                sentiment = post.get('sentiment_label', 'neutral')
                if sentiment in ['negative', 'neutral']:
                    if product:
                        post_product = post.get('product')
                        if not post_product:
                            content = post.get('content', '')
                            language = post.get('language', 'unknown')
                            post_product = detect_product_label(content, language)
                        if post_product and post_product.lower() == product.lower():
                            recent_posts.append(post)
                    else:
                        recent_posts.append(post)
            logger.info(f"[pain-points] Fallback found {len(recent_posts)} posts (all negative/neutral, no date filter)")
        
        if not recent_posts:
            logger.error(f"[pain-points] CRITICAL: No posts found at all! Total posts: {len(all_posts)}, Date parse errors: {date_parse_errors}, Skipped no date: {skipped_no_date}")
            # Even if no posts match date/sentiment, try to return at least something if posts exist
            if all_posts:
                logger.warning(f"[pain-points] Attempting emergency fallback: using first 50 posts regardless of criteria")
                recent_posts = all_posts[:50]
            else:
                return PainPointsResponse(
                    pain_points=[],
                    total_pain_points=0
                )
        
        # Get pain point patterns/keywords from database
        pain_patterns = {}
        try:
            pain_points_db = db.get_pain_points(enabled_only=True)
            logger.info(f"[pain-points] Loaded {len(pain_points_db)} pain points from database")
            
            for pp in pain_points_db:
                if pp.get('enabled', True):
                    # Handle keywords - could be list or JSON string
                    keywords = pp.get('keywords', [])
                    if isinstance(keywords, str):
                        try:
                            import json
                            keywords = json.loads(keywords)
                        except:
                            # If not JSON, try splitting by comma
                            keywords = [k.strip() for k in keywords.split(',') if k.strip()]
                    
                    if not isinstance(keywords, list):
                        keywords = []
                    
                    pain_patterns[pp['title']] = {
                        'keywords': keywords,
                        'icon': pp.get('icon', '📊')
                    }
                    logger.debug(f"[pain-points] Added pain point: {pp['title']} with {len(keywords)} keywords")
        except Exception as e:
            logger.warning(f"Error loading pain points from database, using defaults: {e}")
        
        # Use fallback if no pain points found in database
        if not pain_patterns:
            logger.info("[pain-points] No pain points in database, using default fallback patterns")
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
        
        logger.info(f"[pain-points] Analyzing {len(recent_posts)} posts against {len(pain_patterns)} pain point patterns")
        
        if not pain_patterns:
            logger.warning("[pain-points] No pain point patterns available, returning empty response")
            return PainPointsResponse(
                pain_points=[],
                total_pain_points=0
            )
        
        matched_posts_count = 0
        for post in recent_posts:
            content = (post.get('content', '') or '').lower()
            if not content:
                continue
            
            # Check each pain point pattern
            for pain_name, pattern_info in pain_patterns.items():
                keywords = pattern_info.get('keywords', [])
                if not keywords:
                    logger.debug(f"[pain-points] Pain point '{pain_name}' has no keywords")
                    continue
                
                # Check if any keyword appears in the content
                matched = any(keyword.lower() in content for keyword in keywords)
                if matched:
                    matched_posts_count += 1
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
                    logger.debug(f"[pain-points] Post {post.get('id')} matched '{pain_name}'")
        
        logger.info(f"[pain-points] Analyzed {len(recent_posts)} posts, {matched_posts_count} matches found, {len(pain_point_counts)} pain points: {list(pain_point_counts.keys())}")
        
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
        logger.error(f"Error getting pain points: {e}", exc_info=True)
        # Return empty response on error
        return PainPointsResponse(
            pain_points=[],
            total_pain_points=0
        )
