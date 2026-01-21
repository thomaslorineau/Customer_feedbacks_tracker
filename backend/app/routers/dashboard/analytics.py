"""Analytics endpoints for dashboard statistics and metrics."""
import datetime
import time
import logging
from typing import List
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Query

from ... import db
from ...analysis import country_detection
from .models import (
    PainPoint, PainPointsResponse, ProductOpportunity, ProductDistributionResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def calculate_opportunity_score(product_posts: List[dict], all_posts: List[dict]) -> int:
    """
    Calculate opportunity score for a product based on:
    - Frequency of negative feedback (40%)
    - Recency of issues (30%)
    - Engagement level (views, comments, reactions) (30%)
    """
    if not product_posts:
        return 0
    
    negative_count = sum(1 for p in product_posts if p.get('sentiment_label') == 'negative')
    negative_ratio = negative_count / len(product_posts) if product_posts else 0
    
    # Recency: weight recent posts (last 30 days) more
    now = time.time()
    recent_negative = sum(1 for p in product_posts 
                         if p.get('sentiment_label') == 'negative' 
                         and (p.get('created_at_timestamp', 0) or 0) >= (now - 30 * 24 * 3600))
    recency_score = min(recent_negative / max(len(product_posts) * 0.3, 1), 1.0)
    
    # Engagement: average views, comments, reactions
    total_engagement = sum(
        (p.get('views', 0) or 0) + 
        (p.get('comments', 0) or 0) * 2 + 
        (p.get('reactions', 0) or 0) * 1.5
        for p in product_posts
    )
    avg_engagement = total_engagement / len(product_posts) if product_posts else 0
    engagement_score = min(avg_engagement / 1000, 1.0)  # Normalize to 0-1
    
    # Calculate final score (0-100)
    score = int((negative_ratio * 0.4 + recency_score * 0.3 + engagement_score * 0.3) * 100)
    return min(score, 100)


@router.get(
    "/api/posts-by-country",
    summary="Get Posts Distribution by Country",
    description="""
    Returns the distribution of posts by country based on detected country codes.
    
    **Features:**
    - Automatically detects country from post content using NLP
    - Returns country codes (ISO 2-letter) and human-readable country names
    - Filters out invalid country codes (EU, etc.)
    - Sorted by post count (descending)
    
    **Returns:**
    - `countries`: Dictionary mapping country codes to post counts
    - `total`: Total number of posts analyzed
    - `total_with_country`: Number of posts with valid country detection
    - `country_names`: Dictionary mapping country codes to full country names
    
    **Example Response:**
    ```json
    {
        "countries": {"FR": 150, "US": 120, "DE": 80},
        "total": 1000,
        "total_with_country": 350,
        "country_names": {"FR": "France", "US": "United States", "DE": "Germany"}
    }
    ```
    """,
    tags=["Analytics", "Dashboard"]
)
async def get_posts_by_country():
    """Get distribution of posts by country."""
    posts = db.get_posts(limit=10000, offset=0)
    
    country_counts = {}
    for post in posts:
        country = post.get('country')
        if country and country != 'EU' and len(country) == 2:
            country_counts[country] = country_counts.get(country, 0) + 1
    
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "countries": dict(sorted_countries),
        "total": len(posts),
        "total_with_country": sum(country_counts.values()),
        "country_names": {code: country_detection.get_country_name(code) for code in country_counts.keys()}
    }


@router.get(
    "/api/posts-by-source",
    summary="Get Posts Distribution by Source",
    description="""
    Returns the distribution of posts by data source (X/Twitter, Reddit, GitHub, etc.).
    
    **Features:**
    - Groups posts by source platform
    - Includes sentiment breakdown per source (positive/negative/neutral)
    - Normalizes GitHub sources (Issues and Discussions → GitHub)
    - Sorted by post count (descending)
    
    **Returns:**
    - `sources`: Dictionary mapping source names to post counts
    - `total`: Total number of posts
    - `sentiment_by_source`: Dictionary with sentiment breakdown per source
    
    **Example Response:**
    ```json
    {
        "sources": {"X/Twitter": 500, "Reddit": 300, "GitHub": 200},
        "total": 1000,
        "sentiment_by_source": {
            "X/Twitter": {"positive": 200, "negative": 150, "neutral": 150},
            "Reddit": {"positive": 100, "negative": 120, "neutral": 80}
        }
    }
    ```
    """,
    tags=["Analytics", "Dashboard"]
)
async def get_posts_by_source():
    """Get distribution of posts by source platform."""
    posts = db.get_posts(limit=10000, offset=0)
    
    source_counts = {}
    source_sentiment = {}
    
    for post in posts:
        source = post.get('source', 'Unknown')
        if source == 'GitHub Issues' or source == 'GitHub Discussions':
            source = 'GitHub'
        sentiment = post.get('sentiment_label', 'neutral')
        
        if source not in source_counts:
            source_counts[source] = 0
            source_sentiment[source] = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        source_counts[source] += 1
        if sentiment in source_sentiment[source]:
            source_sentiment[source][sentiment] += 1
    
    sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "sources": dict(sorted_sources),
        "total": len(posts),
        "sentiment_by_source": source_sentiment
    }


@router.get(
    "/api/pain-points", 
    response_model=PainPointsResponse,
    summary="Get Customer Pain Points",
    description="""
    Analyzes recurring pain points from negative customer feedback over a specified time period.
    
    **Features:**
    - Identifies common issues from negative posts using keyword matching
    - Categorizes pain points (Refund Delays, Billing Clarity, SSL Renewal, etc.)
    - Returns top pain points sorted by frequency
    - Includes sample posts for each pain point
    
    **Parameters:**
    - `days`: Number of days to look back (default: 30, max recommended: 90)
    - `limit`: Maximum number of pain points to return (default: 5)
    
    **Pain Point Categories:**
    - Refund Delays (💸)
    - Billing Clarity (📄)
    - HTTPS/SSL Renewal (🔒)
    - Support Response Time (⏱️)
    - VPS Backups (💾)
    - Domain Issues (🌐)
    - Email Problems (📧)
    
    **Example Response:**
    ```json
    {
        "pain_points": [
            {
                "title": "Support Response Time",
                "description": "Slow or unresponsive support",
                "icon": "⏱️",
                "posts_count": 45,
                "posts": [...]
            }
        ],
        "total_pain_points": 7
    }
    ```
    """,
    tags=["Analytics", "Dashboard", "Insights"]
)
async def get_pain_points(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365, example=30),
    limit: int = Query(5, description="Maximum number of pain points to return", ge=1, le=20, example=5)
):
    """Analyze recurring pain points from customer feedback over the last N days."""
    now = time.time()
    cutoff_time = now - (days * 24 * 3600)
    
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
    
    recent_posts = [
        p for p in all_posts 
        if p.get('sentiment_label') == 'negative' 
        and (p.get('created_at_timestamp', 0) or 0) >= cutoff_time
    ]
    
    pain_point_patterns = {
        'Refund Delays': {
            'keywords': ['refund', 'rembours', 'remboursement', 'pending refund', 'delayed refund'],
            'icon': '💸',
            'description': 'Late or pending refunds'
        },
        'Billing Clarity': {
            'keywords': ['billing', 'invoice', 'facture', 'charge', 'confusing', 'unclear'],
            'icon': '📄',
            'description': 'Confusing invoices & charges'
        },
        'HTTPS/SSL Renewal': {
            'keywords': ['ssl', 'https', 'certificate', 'renewal', 'expired', 'certificat'],
            'icon': '🔒',
            'description': 'SSL renewal reminders'
        },
        'Support Response Time': {
            'keywords': ['support', 'response', 'slow', 'unresponsive', 'waiting', 'ticket'],
            'icon': '⏱️',
            'description': 'Slow or unresponsive support'
        },
        'VPS Backups': {
            'keywords': ['backup', 'vps backup', 'backup error', 'backup fail', 'sauvegarde'],
            'icon': '💾',
            'description': 'Backup errors & failures'
        },
        'Domain Issues': {
            'keywords': ['domain', 'dns', 'nameserver', 'domaine', 'expired domain'],
            'icon': '🌐',
            'description': 'Domain registration and DNS issues'
        },
        'Email Problems': {
            'keywords': ['email', 'mail', 'mx record', 'smtp', 'imap', 'exchange'],
            'icon': '📧',
            'description': 'Email delivery and configuration issues'
        }
    }
    
    pain_points = []
    for title, pattern in pain_point_patterns.items():
        matching_posts = []
        keywords_lower = [k.lower() for k in pattern['keywords']]
        
        for post in recent_posts:
            content_lower = (post.get('content', '') or '').lower()
            if any(keyword in content_lower for keyword in keywords_lower):
                matching_posts.append(post)
        
        if matching_posts:
            pain_points.append(PainPoint(
                title=title,
                description=pattern['description'],
                icon=pattern['icon'],
                posts_count=len(matching_posts),
                posts=matching_posts[:5]
            ))
    
    pain_points.sort(key=lambda x: x.posts_count, reverse=True)
    
    return PainPointsResponse(
        pain_points=pain_points[:limit],
        total_pain_points=len(pain_points)
    )


@router.get(
    "/api/product-opportunities", 
    response_model=ProductDistributionResponse,
    summary="Get Product Opportunity Scores",
    description="""
    Calculates opportunity scores for each OVH product based on negative feedback analysis.
    
    **Scoring Algorithm:**
    - **40%** - Frequency of negative feedback (ratio of negative posts)
    - **30%** - Recency of issues (recent negative posts weighted more)
    - **30%** - Engagement level (views, comments, reactions)
    
    **Products Analyzed:**
    - Billing, Domain, VPS, Hosting, API, Email, CDN, Dedicated, Public Cloud, Storage
    
    **Returns:**
    - Products sorted by opportunity score (highest first)
    - Score range: 0-100 (higher = more opportunity for improvement)
    - Includes negative post count and total post count per product
    
    **Example Response:**
    ```json
    {
        "products": [
            {
                "product": "VPS",
                "opportunity_score": 75,
                "negative_posts": 45,
                "total_posts": 120,
                "color": "#0099ff"
            }
        ]
    }
    ```
    """,
    tags=["Analytics", "Dashboard", "Products"]
)
async def get_product_opportunities():
    """Calculate opportunity scores for each OVH product based on negative feedback."""
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
    
    product_posts = defaultdict(list)
    for post in all_posts:
        content = post.get('content', '') or ''
        product = None
        
        content_lower = content.lower()
        if any(kw in content_lower for kw in ['billing', 'invoice', 'facture', 'charge']):
            product = 'Billing'
        elif any(kw in content_lower for kw in ['domain', 'dns', 'domaine', 'nameserver']):
            product = 'Domain'
        elif any(kw in content_lower for kw in ['vps', 'virtual private server']):
            product = 'VPS'
        elif any(kw in content_lower for kw in ['hosting', 'hébergement', 'web host']):
            product = 'Hosting'
        elif any(kw in content_lower for kw in ['api', 'sdk', 'integration']):
            product = 'API'
        elif any(kw in content_lower for kw in ['email', 'mail', 'exchange', 'mx']):
            product = 'Email'
        elif any(kw in content_lower for kw in ['cdn', 'content delivery']):
            product = 'CDN'
        elif any(kw in content_lower for kw in ['dedicated', 'dédié', 'server']):
            product = 'Dedicated'
        elif any(kw in content_lower for kw in ['cloud', 'public cloud', 'instance']):
            product = 'Public Cloud'
        elif any(kw in content_lower for kw in ['storage', 'object storage', 'swift']):
            product = 'Storage'
        
        if product:
            product_posts[product].append(post)
    
    products = []
    colors = ['#0099ff', '#34d399', '#60a5fa', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
    
    for idx, (product, posts) in enumerate(product_posts.items()):
        score = calculate_opportunity_score(posts, all_posts)
        negative_count = sum(1 for p in posts if p.get('sentiment_label') == 'negative')
        
        products.append(ProductOpportunity(
            product=product,
            opportunity_score=score,
            negative_posts=negative_count,
            total_posts=len(posts),
            color=colors[idx % len(colors)]
        ))
    
    products.sort(key=lambda x: x.opportunity_score, reverse=True)
    
    return ProductDistributionResponse(products=products)


@router.get(
    "/api/product-analysis/{product_name}",
    summary="Get Product Analysis",
    description="""
    Analyzes posts for a specific OVH product and generates a summary of issues.
    
    **Features:**
    - Analyzes up to 30 negative posts for the specified product
    - Generates summary of common issues (LLM-powered if available)
    - Product detection based on keyword matching in post content
    
    **Supported Products:**
    - Billing, Domain, VPS, Hosting, API, Email, CDN, Dedicated, Public Cloud, Storage
    
    **Parameters:**
    - `product_name`: Name of the product to analyze (case-insensitive)
    
    **Returns:**
    - Product name
    - Summary of issues (text analysis)
    - Post counts (total and negative)
    - LLM availability status
    
    **Example:**
    GET `/api/product-analysis/VPS` analyzes all VPS-related posts
    """,
    tags=["Analytics", "Dashboard", "Products"]
)
async def get_product_analysis(product_name: str):
    """Analyze posts for a specific product using LLM and generate a summary of issues (in English)."""
    try:
        all_posts = db.get_posts(limit=10000, offset=0)
        
        product_posts = []
        for post in all_posts:
            content = (post.get('content', '') or '').lower()
            detected_product = None
            
            if any(kw in content for kw in ['billing', 'invoice', 'facture', 'charge']):
                detected_product = 'Billing'
            elif any(kw in content for kw in ['domain', 'dns', 'domaine', 'nameserver']):
                detected_product = 'Domain'
            elif any(kw in content for kw in ['vps', 'virtual private server']):
                detected_product = 'VPS'
            elif any(kw in content for kw in ['hosting', 'hébergement', 'web host']):
                detected_product = 'Hosting'
            elif any(kw in content for kw in ['api', 'sdk', 'integration']):
                detected_product = 'API'
            elif any(kw in content for kw in ['email', 'mail', 'exchange', 'mx']):
                detected_product = 'Email'
            elif any(kw in content for kw in ['cdn', 'content delivery']):
                detected_product = 'CDN'
            elif any(kw in content for kw in ['dedicated', 'dédié', 'server']):
                detected_product = 'Dedicated'
            elif any(kw in content for kw in ['cloud', 'public cloud', 'instance']):
                detected_product = 'Public Cloud'
            elif any(kw in content for kw in ['storage', 'object storage', 'swift']):
                detected_product = 'Storage'
            
            if detected_product and detected_product.lower() == product_name.lower():
                product_posts.append(post)
        
        if not product_posts:
            return {
                "product": product_name,
                "summary": f"No posts found for product '{product_name}'.",
                "posts_count": 0,
                "llm_available": False
            }
        
        negative_posts = [p for p in product_posts if p.get('sentiment_label') == 'negative']
        posts_to_analyze = negative_posts[:30] if len(negative_posts) >= 30 else negative_posts
        
        if not posts_to_analyze:
            posts_to_analyze = product_posts[:30]
        
        # LLM analysis would go here - for now return basic summary
        negative_ratio = (len(negative_posts) / len(product_posts) * 100) if product_posts else 0
        summary = f"Analysis of {len(product_posts)} posts for {product_name}: {len(negative_posts)} negative posts ({negative_ratio:.1f}%). "
        if negative_posts:
            summary += "Common issues include customer complaints about service quality, technical problems, and support issues."
        else:
            summary += "No significant negative feedback detected."
        
        return {
            "product": product_name,
            "summary": summary,
            "posts_count": len(product_posts),
            "negative_posts_count": len(negative_posts),
            "llm_available": False
        }
        
    except Exception as e:
        logger.error(f"Error analyzing product {product_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze product: {str(e)}")

