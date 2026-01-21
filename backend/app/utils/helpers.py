"""Helper functions to reduce code duplication and improve maintainability."""
import logging
from typing import List, Dict, Any, Optional, Callable
from .. import db
from ..analysis import sentiment

logger = logging.getLogger(__name__)


def process_and_save_items(items: List[Dict[str, Any]], source_name: Optional[str] = None) -> int:
    """
    Process sentiment analysis and save items to database.
    
    This function reduces code duplication across scraper endpoints.
    
    Args:
        items: List of scraped items (dict with source, author, content, etc.)
        source_name: Optional source name for better logging
    
    Returns:
        Number of items successfully saved to database
    
    Example:
        >>> items = scraper.scrape_x("OVH", limit=10)
        >>> added = process_and_save_items(items, "X/Twitter")
        >>> print(f"Added {added} items")
    """
    if not items:
        logger.warning(f"No items to process{f' from {source_name}' if source_name else ''}")
        return 0
    
    added = 0
    errors = 0
    
    for item in items:
        try:
            # Skip sentiment analysis if already done by scraper
            if not item.get('sentiment_score'):
                analysis = sentiment.analyze(item.get('content') or '')
                item['sentiment_score'] = analysis['score']
                item['sentiment_label'] = analysis['label']
            
            # Insert into database
            db.insert_post({
                'source': item.get('source'),
                'author': item.get('author'),
                'content': item.get('content'),
                'url': item.get('url'),
                'created_at': item.get('created_at'),
                'sentiment_score': item.get('sentiment_score'),
                'sentiment_label': item.get('sentiment_label'),
                'language': item.get('language', 'unknown'),
            })
            added += 1
            
        except Exception as e:
            errors += 1
            logger.error(
                f"Failed to save item from {item.get('source', 'unknown')}: {e}",
                exc_info=False
            )
            continue
    
    if source_name:
        logger.info(f"Saved {added}/{len(items)} items from {source_name} to database")
        if errors > 0:
            logger.warning(f"Failed to save {errors} items from {source_name}")
    else:
        logger.info(f"Saved {added}/{len(items)} items to database")
    
    return added


def safe_scrape(
    scraper_func: Callable[[str, int], List[Dict[str, Any]]], 
    query: str, 
    limit: int, 
    source_name: str
) -> int:
    """
    Safely execute a scraper function and save results.
    
    Wraps scraper execution with error handling and logging.
    
    Args:
        scraper_func: The scraper function to call
        query: Search query
        limit: Maximum number of results
        source_name: Name of the source for logging
    
    Returns:
        Number of items successfully saved
    
    Example:
        >>> from ..scraper import x_scraper
        >>> added = safe_scrape(x_scraper.scrape_x, "OVH", 50, "X/Twitter")
    """
    try:
        logger.info(f"[{source_name}] Starting scrape: query='{query}', limit={limit}")
        items = scraper_func(query, limit=limit)
        logger.info(f"[{source_name}] Retrieved {len(items)} items")
        added = process_and_save_items(items, source_name)
        return added
    except Exception as e:
        logger.error(f"[{source_name}] Scraping failed: {type(e).__name__}", exc_info=True)
        return 0


def validate_query(query: str, max_length: int = 100) -> bool:
    """
    Validate query string for security.
    
    Args:
        query: Query string to validate
        max_length: Maximum allowed length
    
    Returns:
        True if valid, False otherwise
    
    Example:
        >>> validate_query("OVH domain")
        True
        >>> validate_query("'; DROP TABLE posts; --")
        False
    """
    if not query or len(query) > max_length:
        return False
    
    # Check for dangerous patterns
    dangerous_patterns = [
        '..',
        '/',
        '\\',
        '<script',
        'DROP TABLE',
        'DELETE FROM',
        'INSERT INTO',
        'UPDATE SET',
    ]
    
    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in query_lower:
            logger.warning(f"Blocked dangerous pattern in query: {pattern}")
            return False
    
    return True
