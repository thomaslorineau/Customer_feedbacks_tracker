"""Base utilities and helper functions for scraping router."""
import os
import re
import logging
from typing import List, Dict, Tuple

from ... import db
from ...analysis import sentiment, country_detection, relevance_scorer
from ...config import keywords_base

logger = logging.getLogger(__name__)

# Rate limiter instance (will be set from main.py)
limiter = None

def set_limiter(limiter_instance):
    """Set the limiter instance from main.py"""
    global limiter
    limiter = limiter_instance

# Relevance threshold
RELEVANCE_THRESHOLD = float(os.getenv('RELEVANCE_THRESHOLD', '0.3'))


def should_insert_post(post: dict) -> Tuple[bool, float]:
    """
    Détermine si un post doit être inséré en base selon son score de pertinence.
    
    Special case: All Trustpilot posts from ovhcloud.com are considered relevant
    (no relevance filtering applied).
    
    Returns:
        (should_insert: bool, relevance_score: float)
    """
    source = post.get('source', '').lower()
    url = post.get('url', '')
    
    if source == 'trustpilot' or 'trustpilot.com/review/ovhcloud.com' in url.lower():
        return True, 1.0
    
    relevance_score = relevance_scorer.calculate_relevance_score(post)
    is_relevant = relevance_scorer.is_relevant(post, threshold=RELEVANCE_THRESHOLD)
    
    return is_relevant, relevance_score


def sanitize_log_message(message: str) -> str:
    """Remove sensitive data from log messages (API keys, tokens, etc.)."""
    if not message:
        return message
    
    # Mask API keys (OpenAI, Anthropic, GitHub, etc.)
    message = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***REDACTED***', message)
    message = re.sub(r'sk-ant-[a-zA-Z0-9-]{20,}', 'sk-ant-***REDACTED***', message)
    message = re.sub(r'ghp_[a-zA-Z0-9]{20,}', 'ghp_***REDACTED***', message)
    message = re.sub(r'github_pat_[a-zA-Z0-9_]{20,}', 'github_pat_***REDACTED***', message)
    
    # Mask tokens in URLs
    message = re.sub(r'(token|api_key|apikey|password|secret)=[a-zA-Z0-9_-]+', r'\1=***REDACTED***', message, flags=re.IGNORECASE)
    
    return message


def log_scraping(source: str, level: str, message: str, details: dict = None):
    """Helper function to log scraping events to database and console."""
    try:
        # Sanitize message before logging
        sanitized_message = sanitize_log_message(message)
        try:
            db.add_scraping_log(source, level, sanitized_message, details)
        except Exception as e:
            # Don't fail the entire request if logging fails
            logger.warning(f"Failed to log scraping event: {e}")
        # Also log to console for immediate visibility
        level_emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "📝")
        logger.info(f"{level_emoji} [{source}] {sanitized_message}")
    except Exception as e:
        # Fallback: just log if everything fails
        logger.error(f"⚠️ [LOG ERROR] Failed to log: {e}")


def process_and_save_items(items: List[Dict], source_name: str) -> Tuple[int, int, int]:
    """
    Process scraped items: check relevance, analyze sentiment, detect country, and save to DB.
    
    Returns:
        (added: int, skipped_duplicates: int, errors: int)
    """
    added = 0
    skipped_duplicates = 0
    errors = 0
    
    if not items:
        return added, skipped_duplicates, errors
    
    for idx, it in enumerate(items):
        try:
            # Validate item structure
            if not isinstance(it, dict):
                errors += 1
                logger.warning(f"[{source_name}] Item {idx} is not a dict: {type(it)}")
                continue
            
            # Check relevance before processing
            try:
                is_relevant, relevance_score = should_insert_post(it)
            except Exception as e:
                errors += 1
                logger.warning(f"[{source_name}] Error checking relevance for item {idx}: {e}")
                continue
                
            if not is_relevant:
                logger.debug(f"[{source_name}] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                continue
            
            # Detect language first (needed for sentiment analysis)
            try:
                from ...analysis import language_detection
                detected_language = language_detection.detect_language_from_post(it)
                it['language'] = detected_language
            except Exception as e:
                logger.warning(f"[{source_name}] Error detecting language for item {idx}: {e}")
                it['language'] = it.get('language', 'unknown')
            
            # Analyze sentiment (with language-aware analysis)
            try:
                content = it.get('content') or ''
                language = it.get('language', 'unknown')
                an = sentiment.analyze(content, language=language)
                it['sentiment_score'] = an.get('score', 0.0)
                it['sentiment_label'] = an.get('label', 'neutral')
            except Exception as e:
                logger.warning(f"[{source_name}] Error analyzing sentiment for item {idx}: {e}")
                it['sentiment_score'] = 0.0
                it['sentiment_label'] = 'neutral'
            
            # Detect country
            try:
                country = country_detection.detect_country_from_post(it)
            except Exception as e:
                logger.warning(f"[{source_name}] Error detecting country for item {idx}: {e}")
                country = None
            
            # Insert into database
            try:
                inserted = db.insert_post({
                    'source': it.get('source', source_name),
                    'author': it.get('author', 'Unknown'),
                    'content': it.get('content', ''),
                    'url': it.get('url', ''),
                    'created_at': it.get('created_at', ''),
                    'sentiment_score': it.get('sentiment_score', 0.0),
                    'sentiment_label': it.get('sentiment_label', 'neutral'),
                    'language': it.get('language', 'unknown'),
                    'country': country,
                    'relevance_score': relevance_score,
                })
                
                if inserted:
                    added += 1
                    # Try to detect and update answered status automatically
                    try:
                        db.detect_and_update_answered_status(inserted, it)
                    except Exception as e:
                        logger.debug(f"[{source_name}] Could not auto-detect answered status for post {inserted}: {e}")
                else:
                    skipped_duplicates += 1
            except Exception as e:
                errors += 1
                logger.error(f"[{source_name}] Error inserting post {idx} to database: {e}", exc_info=True)
                log_scraping(source_name, "error", f"Database insert error for item {idx}: {type(e).__name__}: {str(e)[:200]}")
        except Exception as e:
            errors += 1
            error_type = type(e).__name__
            error_msg = str(e)[:200]  # Limit error message length
            logger.error(f"[{source_name}] Unexpected error processing item {idx}: {error_type}: {error_msg}", exc_info=True)
            log_scraping(source_name, "error", f"Processing error for item {idx}: {error_type}: {error_msg}")
    
    return added, skipped_duplicates, errors


def get_query_with_base_keywords(query: str, source_name: str) -> str:
    """Get query, using base keywords if query is empty or default."""
    if not query or query.strip() == "" or query == "OVH" or query == "OVH domain":
        base_keywords = keywords_base.get_all_base_keywords()
        if base_keywords:
            query = base_keywords[0] if len(base_keywords) == 1 else " ".join(base_keywords[:3])
            log_scraping(source_name, "info", f"Using base keywords: {query}")
    return query

