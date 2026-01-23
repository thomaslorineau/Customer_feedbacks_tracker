"""
Admin routes for system administration.
"""
from pathlib import Path
import os
import json
import datetime
import time
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from .. import db
from ..auth.dependencies import require_auth, require_admin
from ..auth.models import TokenData

logger = logging.getLogger(__name__)

router = APIRouter()

# Import backup function
import sys
backend_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(backend_dir))
from scripts.backup_db import backup_database


# ============================================================================
# MODELS
# ============================================================================

class UIVersionPayload(BaseModel):
    version: str = Field(..., pattern="^(v1|v2)$")


# ============================================================================
# CLEANUP ENDPOINTS
# ============================================================================

@router.post('/admin/cleanup-hackernews-posts')
async def cleanup_hackernews_posts(
    current_user: TokenData = Depends(require_admin)
):
    """Clean up HackerNews posts. Admin only."""
    logger.info(f"Admin {current_user.username} triggered HackerNews posts cleanup")
    """
    Delete all posts from Hacker News (replaced by Reddit).
    """
    try:
        deleted_count = db.delete_hackernews_posts()
        return {
            'deleted': deleted_count,
            'message': f'Successfully removed {deleted_count} Hacker News posts from database'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/admin/duplicates-stats')
async def get_duplicates_stats():
    """Get duplicate posts statistics."""
    """
    Get statistics about duplicate posts before deletion.
    Returns counts of duplicates by URL and by content+author+source.
    """
    try:
        conn, is_duckdb = db.get_db_connection()
        c = conn.cursor()
        
        # Count duplicates by URL
        if is_duckdb:
            url_duplicates_query = """
                SELECT url, COUNT(*) as count
                FROM posts
                WHERE url IS NOT NULL AND url != ''
                GROUP BY url
                HAVING COUNT(*) > 1
            """
        else:
            url_duplicates_query = """
                SELECT url, COUNT(*) as count
                FROM posts
                WHERE url IS NOT NULL AND url != ''
                GROUP BY url
                HAVING COUNT(*) > 1
            """
        
        c.execute(url_duplicates_query)
        url_duplicates = c.fetchall()
        url_duplicates_count = sum(count - 1 for _, count in url_duplicates)  # -1 to keep one
        
        # Count duplicates by content+author+source
        if is_duckdb:
            content_duplicates_query = """
                SELECT content, author, source, COUNT(*) as count
                FROM posts
                WHERE content IS NOT NULL AND content != ''
                GROUP BY content, author, source
                HAVING COUNT(*) > 1
            """
        else:
            content_duplicates_query = """
                SELECT content, author, source, COUNT(*) as count
                FROM posts
                WHERE content IS NOT NULL AND content != ''
                GROUP BY content, author, source
                HAVING COUNT(*) > 1
            """
        
        c.execute(content_duplicates_query)
        content_duplicates = c.fetchall()
        content_duplicates_count = sum(count - 1 for _, _, _, count in content_duplicates)  # -1 to keep one
        
        # Total unique duplicate groups
        total_duplicate_groups = len(url_duplicates) + len(content_duplicates)
        
        # Total posts that would be deleted
        total_to_delete = url_duplicates_count + content_duplicates_count
        
        conn.close()
        
        return {
            'duplicates_by_url': {
                'groups': len(url_duplicates),
                'posts_to_delete': url_duplicates_count
            },
            'duplicates_by_content': {
                'groups': len(content_duplicates),
                'posts_to_delete': content_duplicates_count
            },
            'total': {
                'duplicate_groups': total_duplicate_groups,
                'posts_to_delete': total_to_delete
            }
        }
    except Exception as e:
        logger.error(f"Error getting duplicates stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/admin/backup-database')
async def trigger_backup(
    current_user: TokenData = Depends(require_admin)
):
    """Trigger a manual database backup. Admin only."""
    logger.info(f"Admin {current_user.username} triggered manual backup")
    try:
        db_path = backend_dir / "data.duckdb"
        success = backup_database(db_path, "production", keep_backups=30, backup_type="manual")
        
        if success:
            return {
                'success': True,
                'message': 'Backup created successfully'
            }
        else:
            raise HTTPException(status_code=500, detail='Backup failed - database may be corrupted')
    except Exception as e:
        logger.error(f"Error during manual backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/admin/cleanup-duplicates')
async def cleanup_duplicates():
    """
    Delete duplicate posts from the database.
    Duplicates are identified by same URL or same normalized content+author+source.
    Keeps the oldest post (lowest ID) and deletes the rest.
    
    Improved detection:
    - Normalizes HTML content (removes tags, whitespace)
    - Compares normalized content (first 200 chars) + author + source
    - Handles variations in HTML formatting
    """
    try:
        deleted_count = db.delete_duplicate_posts()
        return {
            'deleted': deleted_count,
            'message': f'Successfully removed {deleted_count} duplicate posts from database'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/admin/cleanup-non-ovh-posts')
async def cleanup_non_ovh_posts():
    """Clean up non-OVH posts."""
    logger.info("Non-OVH posts cleanup triggered")
    """
    Delete all posts from the database that do NOT mention OVH or its brands.
    Keeps posts containing: ovh, ovhcloud, ovh cloud, kimsufi, soyoustart
    """
    try:
        deleted_count = db.delete_non_ovh_posts()
        return {
            'deleted': deleted_count,
            'message': f'Successfully removed {deleted_count} non-OVH posts from database'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get('/admin/product-labels-stats')
async def get_product_labels_stats():
    """Get statistics about product labels in posts, validating against official OVH products."""
    """
    Analyze all posts and return statistics about product labels:
    - Total posts
    - Posts with detected product labels
    - Posts without product labels
    - Distribution of product labels
    - Validation: labels matching official OVH products vs invalid labels
    - Posts with incorrect or non-OVH product labels
    """
    import re
    
    try:
        # Official OVH products list (based on OVHcloud.com)
        # This is the authoritative list of valid OVH products
        OFFICIAL_OVH_PRODUCTS = {
            'VPS', 'Hosting', 'Domain', 'DNS', 'Email', 'Storage', 'CDN', 
            'Public Cloud', 'Private Cloud', 'Dedicated Server', 'API',
            'Load Balancer', 'Failover IP', 'SSL Certificate', 
            'Managed Kubernetes', 'Managed Databases', 'Network', 'IP'
        }
        
        # Product detection patterns (aligned with official OVH products from insights.py)
        # Based on OVHcloud.com official products list
        # Order matters: more specific patterns first
        product_patterns = [
            # Web & Hosting
            {'key': 'domain', 'pattern': re.compile(r'\b(domain|domaine|domain\s*name|domain\s*registration|domain\s*renewal|domain\s*transfer|domain\s*expiration|registrar|bureau\s*d\'enregistrement|whois|domain\s*management|\.ovh|\.com|\.net|\.org|\.fr|\.eu)\b', re.I), 'label': 'Domain'},
            {'key': 'dns', 'pattern': re.compile(r'\b(dns|dns\s*zone|dns\s*anycast|dnssec|dns\s*record|dns\s*configuration|nameserver|ns\s*record|a\s*record|mx\s*record|cname\s*record|txt\s*record|dns\s*management|dns\s*hosting)\b', re.I), 'label': 'DNS'},
            {'key': 'email', 'pattern': re.compile(r'\b(email|mail|smtp|imap|pop3|email\s*hosting|exchange|email\s*account)\b', re.I), 'label': 'Email'},
            {'key': 'web-hosting', 'pattern': re.compile(r'\b(web\s*host|hosting|hébergement|mutualisé|shared\s*host|web\s*hosting\s*plan|ovh\s*hosting)\b', re.I), 'label': 'Hosting'},
            
            # Cloud & Servers
            {'key': 'vps', 'pattern': re.compile(r'\b(vps|virtual\s*private\s*server|ovh\s*vps|vps\s*cloud|cloud\s*vps)\b', re.I), 'label': 'VPS'},
            {'key': 'dedicated', 'pattern': re.compile(r'\b(dedicated|dedicated\s*server|serveur\s*dédié|bare\s*metal|ovh\s*dedicated|server|serveur)\b', re.I), 'label': 'Dedicated Server'},
            {'key': 'public-cloud', 'pattern': re.compile(r'\b(public\s*cloud|publiccloud|ovh\s*public\s*cloud|public\s*cloud\s*instance|horizon|openstack)\b', re.I), 'label': 'Public Cloud'},
            {'key': 'private-cloud', 'pattern': re.compile(r'\b(private\s*cloud|privatecloud|ovh\s*private\s*cloud|vmware|vsphere|hosted\s*private\s*cloud)\b', re.I), 'label': 'Private Cloud'},
            {'key': 'kubernetes', 'pattern': re.compile(r'\b(kubernetes|k8s|managed\s*kubernetes|ovh\s*kubernetes)\b', re.I), 'label': 'Managed Kubernetes'},
            {'key': 'managed-databases', 'pattern': re.compile(r'\b(database|mysql|postgresql|mongodb|redis|managed\s*database|ovh\s*database)\b', re.I), 'label': 'Managed Databases'},
            
            # Storage & Backup
            {'key': 'object-storage', 'pattern': re.compile(r'\b(storage|object\s*storage|s3|cloud\s*storage|object\s*storage\s*s3|high\s*performance\s*storage)\b', re.I), 'label': 'Storage'},
            
            # Network & CDN
            {'key': 'cdn', 'pattern': re.compile(r'\b(cdn|content\s*delivery|content\s*delivery\s*network|ovh\s*cdn)\b', re.I), 'label': 'CDN'},
            {'key': 'load-balancer', 'pattern': re.compile(r'\b(load\s*balancer|loadbalancer|lb|ip\s*load\s*balancing)\b', re.I), 'label': 'Load Balancer'},
            {'key': 'failover-ip', 'pattern': re.compile(r'\b(failover\s*ip|failover|ip\s*failover|additional\s*ip)\b', re.I), 'label': 'Failover IP'},
            {'key': 'ssl-certificate', 'pattern': re.compile(r'\b(ssl|ssl\s*certificate|certificate|tls|https\s*certificate)\b', re.I), 'label': 'SSL Certificate'},
            {'key': 'network', 'pattern': re.compile(r'\b(network|vrack|private\s*network|vlan)\b', re.I), 'label': 'Network'},
            {'key': 'ip', 'pattern': re.compile(r'\b(ip\s*address|ipv4|ipv6|ip\s*block|ip\s*range)\b', re.I), 'label': 'IP'},
            
            # API
            {'key': 'api', 'pattern': re.compile(r'\b(api|rest\s*api|graphql|ovh\s*api|api\s*ovh|ovhcloud\s*api)\b', re.I), 'label': 'API'},
        ]
        
        def detect_product(content):
            """Detect product from post content."""
            if not content:
                return None
            content_lower = content.lower()
            for product in product_patterns:
                if product['pattern'].search(content_lower):
                    return product['label']
            return None
        
        # Get all posts from database
        all_posts = db.get_posts(limit=10000, offset=0)
        
        # Analyze posts
        total_posts = len(all_posts)
        posts_with_label = 0
        posts_without_label = 0
        label_distribution = {}
        invalid_labels = {}  # Labels that don't match official OVH products
        posts_with_invalid_labels = []  # Posts with invalid labels
        
        for post in all_posts:
            content = post.get('content', '') or ''
            detected_label = detect_product(content)
            
            if detected_label:
                posts_with_label += 1
                label_distribution[detected_label] = label_distribution.get(detected_label, 0) + 1
                
                # Validate against official OVH products
                if detected_label not in OFFICIAL_OVH_PRODUCTS:
                    invalid_labels[detected_label] = invalid_labels.get(detected_label, 0) + 1
                    posts_with_invalid_labels.append({
                        'id': post.get('id'),
                        'detected_label': detected_label,
                        'content_preview': content[:150] if content else 'No content'
                    })
            else:
                posts_without_label += 1
        
        # Sort labels by count
        sorted_labels = sorted(label_distribution.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate validation stats
        valid_labels_count = sum(count for label, count in label_distribution.items() if label in OFFICIAL_OVH_PRODUCTS)
        invalid_labels_count = sum(count for label, count in label_distribution.items() if label not in OFFICIAL_OVH_PRODUCTS)
        
        return {
            'total_posts': total_posts,
            'posts_with_label': posts_with_label,
            'posts_without_label': posts_without_label,
            'label_distribution': dict(sorted_labels),
            'coverage_percentage': round((posts_with_label / total_posts * 100) if total_posts > 0 else 0, 2),
            'validation': {
                'valid_labels_count': valid_labels_count,
                'invalid_labels_count': invalid_labels_count,
                'invalid_labels': dict(sorted(invalid_labels.items(), key=lambda x: x[1], reverse=True)),
                'posts_with_invalid_labels': posts_with_invalid_labels[:10],  # Limit to first 10 for display
                'official_products': sorted(list(OFFICIAL_OVH_PRODUCTS))
            }
        }
    except Exception as e:
        logger.error(f"Error getting product labels stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/update-product-labels")
async def update_product_labels(request: Request):
    """
    Met à jour les product labels de tous les posts en détectant automatiquement le produit.
    Cette fonction analyse le contenu de chaque post et met à jour la colonne 'product' dans la base de données.
    
    Args:
        request: Request body avec optionnellement 'limit' pour limiter le nombre de posts traités
    
    Returns:
        Statistiques sur les mises à jour effectuées
    """
    try:
        body = await request.json()
        limit = body.get('limit')  # None = all posts
        
        logger.info(f"Starting product labels update (limit: {limit or 'all'})...")
        
        result = db.update_all_posts_product_labels(limit=limit)
        
        return result
        
    except Exception as e:
        logger.error(f"Error updating product labels: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update product labels: {str(e)}")


# ============================================================================
# UI VERSION ENDPOINTS
# ============================================================================

@router.post("/admin/set-ui-version")
async def set_ui_version(
    payload: UIVersionPayload,
    current_user: TokenData = Depends(require_admin)
):
    """Set the UI version (v1 or v2). Admin only."""
    logger.info(f"Admin {current_user.username} set UI version to {payload.version}")
    version_str = payload.version
    if version_str not in ["v1", "v2"]:
        raise HTTPException(status_code=400, detail="Version must be 'v1' or 'v2'")
    
    app_config_path = Path(__file__).resolve().parents[2] / "backend" / ".app_config"
    
    # Read existing config
    config_lines = []
    if app_config_path.exists():
        with open(app_config_path, "r", encoding="utf-8") as f:
            config_lines = f.readlines()
    
    # Update or add UI_VERSION
    updated = False
    for i, line in enumerate(config_lines):
        if line.startswith("UI_VERSION="):
            config_lines[i] = f"UI_VERSION={version_str}\n"
            updated = True
            break
    
    if not updated:
        config_lines.append(f"UI_VERSION={version_str}\n")
    
    # Write back
    with open(app_config_path, "w", encoding="utf-8") as f:
        f.writelines(config_lines)
    
    # Update environment variable for current process
    os.environ['UI_VERSION'] = version_str
    
    return {"message": f"UI version set to {version_str}", "version": version_str}


@router.get("/admin/get-ui-version")
async def get_ui_version():
    """Get the current UI version."""
    app_config_path = Path(__file__).resolve().parents[2] / "backend" / ".app_config"
    ui_version = "v2"  # default to v2
    
    if app_config_path.exists():
        with open(app_config_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("UI_VERSION="):
                    ui_version = line.split("=", 1)[1].strip()
                    break
    
    return {"version": ui_version}


# ============================================================================
# LOGO ENDPOINTS
# ============================================================================

@router.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    """Upload OVHcloud logo file."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(('.svg', '.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only SVG, PNG, JPG, JPEG are allowed.")
    
    # Read file contents
    contents = await file.read()
    
    # Validate file size (max 5MB)
    if len(contents) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
    
    # Determine file extension
    file_ext = file.filename.split('.')[-1].lower()
    
    # Save to assets/logo directory
    assets_logo_path = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "logo"
    assets_logo_path.mkdir(parents=True, exist_ok=True)
    
    # If SVG or starts with SVG content, always save as .svg
    if file_ext == 'svg' or contents.startswith(b'<svg') or contents.startswith(b'<?xml'):
        logo_filename = "ovhcloud-logo.svg"
    else:
        logo_filename = f"ovhcloud-logo.{file_ext}"
    
    logo_path = assets_logo_path / logo_filename
    
    try:
        with open(logo_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"Logo uploaded successfully: {logo_filename}")
        return JSONResponse({
            "success": True,
            "message": f"Logo uploaded successfully as {logo_filename}",
            "filename": logo_filename,
            "path": f"/assets/logo/{logo_filename}"
        })
    except Exception as e:
        logger.error(f"Error saving logo: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save logo: {str(e)}")


@router.get("/api/logo-status")
async def get_logo_status():
    """Check if logo file exists."""
    assets_logo_path = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "logo"
    
    # Check for SVG first (preferred)
    svg_path = assets_logo_path / "ovhcloud-logo.svg"
    if svg_path.exists():
        file_size = svg_path.stat().st_size
        return {
            "exists": True,
            "filename": "ovhcloud-logo.svg",
            "path": "/assets/logo/ovhcloud-logo.svg",
            "size": file_size,
            "format": "svg"
        }
    
    # Check for other formats
    for ext in ['png', 'jpg', 'jpeg']:
        logo_path = assets_logo_path / f"ovhcloud-logo.{ext}"
        if logo_path.exists():
            file_size = logo_path.stat().st_size
            return {
                "exists": True,
                "filename": f"ovhcloud-logo.{ext}",
                "path": f"/assets/logo/ovhcloud-logo.{ext}",
                "size": file_size,
                "format": ext
            }
    
    return {
        "exists": False,
        "message": "No logo file found. Please upload one."
    }


# ============================================================================
# POWERPOINT REPORT ENDPOINT
# ============================================================================

@router.post("/api/generate-powerpoint-report")
async def generate_powerpoint_report_endpoint(request: Request):
    """
    Generate a PowerPoint report with key charts, insights, and recommendations.
    Accepts FormData with chart images from the dashboard.
    """
    form = await request.form()
    
    # Parse filters from form data
    filters_str = form.get('filters', '{}')
    try:
        filters = json.loads(filters_str) if isinstance(filters_str, str) else filters_str
    except:
        filters = {}
    
    include_recommendations = form.get('include_recommendations', 'true').lower() == 'true'
    include_analysis = form.get('include_analysis', 'true').lower() == 'true'
    
    # Get chart images
    timeline_file = form.get('timeline_chart')
    source_file = form.get('source_chart')
    sentiment_file = form.get('sentiment_chart')
    
    timeline_chart = await timeline_file.read() if timeline_file else None
    source_chart = await source_file.read() if source_file else None
    sentiment_chart = await sentiment_file.read() if sentiment_file else None
    
    chart_images = {
        'timeline': timeline_chart,
        'source': source_chart,
        'sentiment': sentiment_chart
    }
    
    logger.info(f"[PowerPoint Report] Starting generation with filters: {filters}")
    
    try:
        from .. import powerpoint_generator
        
        if not powerpoint_generator.PPTX_AVAILABLE:
            missing_deps = getattr(powerpoint_generator, 'MISSING_DEPENDENCIES', ['python-pptx', 'matplotlib', 'Pillow'])
            deps_str = ", ".join(missing_deps)
            raise HTTPException(
                status_code=503,
                detail=(
                    f"PowerPoint generation requires {deps_str}. "
                    f"Install with: pip install {' '.join(missing_deps)} "
                    f"or install all dependencies: pip install -r requirements.txt"
                )
            )
        
        # Get filtered posts based on request filters
        all_posts = db.get_posts(limit=10000, offset=0)
        
        # Apply filters (similar to state filtering logic)
        filtered_posts = all_posts
        if filters.get('search'):
            search_lower = filters['search'].lower()
            filtered_posts = [p for p in filtered_posts if search_lower in (p.get('content', '') or '').lower()]
        
        if filters.get('sentiment') and filters['sentiment'] != 'all':
            filtered_posts = [p for p in filtered_posts if p.get('sentiment_label') == filters['sentiment']]
        
        if filters.get('language') and filters['language'] != 'all':
            filtered_posts = [p for p in filtered_posts if p.get('language') == filters['language']]
        
        if filters.get('source') and filters['source'] != 'all':
            source_filter = filters['source']
            # Normalize GitHub sources: GitHub Issues and GitHub Discussions → GitHub
            filtered_posts = [p for p in filtered_posts if 
                             (p.get('source') == source_filter) or 
                             (source_filter == 'GitHub' and (p.get('source') == 'GitHub Issues' or p.get('source') == 'GitHub Discussions'))]
        
        # Date filtering
        if filters.get('dateFrom'):
            filtered_posts = [p for p in filtered_posts if p.get('created_at', '') >= filters['dateFrom']]
        if filters.get('dateTo'):
            filtered_posts = [p for p in filtered_posts if p.get('created_at', '') <= filters['dateTo']]
        
        # Calculate stats
        stats = {
            'total': len(filtered_posts),
            'positive': len([p for p in filtered_posts if p.get('sentiment_label') == 'positive']),
            'negative': len([p for p in filtered_posts if p.get('sentiment_label') == 'negative']),
            'neutral': len([p for p in filtered_posts if p.get('sentiment_label') == 'neutral' or not p.get('sentiment_label')])
        }
        
        # Get recommended actions
        recommended_actions = []
        if include_recommendations:
            try:
                # Import from dashboard router
                from .dashboard import get_recommended_actions, RecommendedActionRequest
                
                # Get recent posts for recommendations
                now = time.time()
                recent_posts = []
                for p in filtered_posts:
                    try:
                        created_at = p.get('created_at', '')
                        if created_at:
                            # Handle different date formats
                            try:
                                dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            except:
                                # Try parsing with strptime as fallback
                                try:
                                    dt = datetime.datetime.strptime(created_at.split('T')[0], '%Y-%m-%d')
                                except:
                                    continue
                            post_timestamp = dt.timestamp()
                            if post_timestamp >= (now - 48 * 3600):
                                recent_posts.append(p)
                    except Exception as e:
                        logger.debug(f"Error parsing post date: {e}")
                        continue
                
                # Call recommended actions endpoint logic
                actions_response = await get_recommended_actions(RecommendedActionRequest(
                    posts=filtered_posts[:30],
                    recent_posts=recent_posts[:20],
                    stats=stats,
                    max_actions=5
                ))
                recommended_actions = [{'icon': a.icon, 'text': a.text, 'priority': a.priority} for a in actions_response.actions]
            except Exception as e:
                logger.warning(f"Failed to get recommended actions for report: {e}")
        
        # Generate LLM analysis if requested
        llm_analysis = None
        if include_analysis:
            try:
                import httpx
                api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    # Generate brief analysis
                    prompt = f"""Analyze the following customer feedback data and provide 2-3 key bullet points (one sentence each):
- Total posts: {stats['total']}
- Positive: {stats['positive']}, Negative: {stats['negative']}, Neutral: {stats['neutral']}
- Active filters: {filters}

Format as bullet points, professional and executive-friendly."""
                    
                    llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
                    if llm_provider == 'openai' or (not os.getenv('LLM_PROVIDER') and api_key):
                        try:
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                response = await client.post(
                                    'https://api.openai.com/v1/chat/completions',
                                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                                    json={
                                        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                                        'messages': [
                                            {'role': 'system', 'content': 'You are a business analyst. Provide concise, professional insights.'},
                                            {'role': 'user', 'content': prompt}
                                        ],
                                        'temperature': 0.7,
                                        'max_tokens': 200
                                    }
                                )
                                response.raise_for_status()
                                result = response.json()
                                llm_analysis = result['choices'][0]['message']['content'].strip()
                        except httpx.HTTPStatusError as e:
                            if e.response.status_code == 401:
                                logger.warning(f"LLM API authentication failed (401) for PowerPoint report. Skipping LLM analysis.")
                            else:
                                logger.warning(f"LLM API error ({e.response.status_code}) for PowerPoint report: {e}. Skipping LLM analysis.")
                            llm_analysis = None
                        except Exception as e:
                            logger.warning(f"Failed to generate LLM analysis for report: {type(e).__name__}: {e}")
                            llm_analysis = None
                    elif llm_provider == 'anthropic':
                        # Anthropic handling would go here if needed
                        pass
            except Exception as e:
                logger.warning(f"Error generating LLM analysis: {type(e).__name__}: {e}")
                llm_analysis = None
        
        # Generate PowerPoint with chart images
        pptx_bytes = powerpoint_generator.generate_powerpoint_report(
            posts=filtered_posts,
            filters=filters,
            recommended_actions=recommended_actions,
            stats=stats,
            llm_analysis=llm_analysis,
            chart_images=chart_images
        )
        
        # Return as file download
        filename = f"OVH_Feedback_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        logger.error(f"Error generating PowerPoint report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


# ============================================================================
# LOGS ENDPOINTS
# ============================================================================

@router.get("/api/logs")
async def get_logs_api(source: Optional[str] = None, level: Optional[str] = None, limit: int = 1000, offset: int = 0):
    """Get scraping logs from the database."""
    try:
        logs = db.get_scraping_logs(source=source, level=level, limit=limit, offset=offset)
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Error fetching logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")


@router.delete("/api/logs")
async def clear_logs_api(source: Optional[str] = None, older_than_days: Optional[int] = None):
    """Clear scraping logs."""
    deleted = db.clear_scraping_logs(source=source, older_than_days=older_than_days)
    return {"deleted": deleted, "message": f"Deleted {deleted} log entries"}


@router.post("/admin/recheck-answered-status")
async def recheck_answered_status(request: Request):
    """
    Re-vérifie le statut answered des posts existants en re-scrapant leurs métadonnées depuis leurs URLs.
    
    Cette fonction récupère les posts existants qui ne sont pas marqués comme answered
    et re-scrape leurs métadonnées (comments, replies, etc.) depuis leurs URLs pour
    mettre à jour leur statut is_answered si une réponse a été apportée entre temps.
    
    Args:
        request: Request body avec optionnellement 'limit' pour limiter le nombre de posts traités
    
    Returns:
        Statistiques sur les posts vérifiés et mis à jour
    """
    try:
        import json
        body = await request.json()
        limit = body.get('limit')  # None = all unanswered posts
        
        logger.info(f"Starting re-check of answered status (limit: {limit or 'all unanswered'})...")
        
        # Use the async function from db.py
        result = await db.recheck_posts_answered_status(limit=limit, delay_between_requests=0.5)
        
        return result
        
    except Exception as e:
        logger.error(f"Error re-checking answered status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to re-check answered status: {str(e)}")