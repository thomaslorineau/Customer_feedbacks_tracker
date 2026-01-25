"""Structured logging for scrapers with context and metrics."""
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Import db de manière optionnelle pour éviter les dépendances circulaires
try:
    from .. import database as db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class ScrapingLogger:
    """Structured logger for scrapers with context and metrics tracking."""
    
    def __init__(self, source_name: str):
        """
        Args:
            source_name: Name of the source being scraped
        """
        self.source_name = source_name
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_duration': 0.0,
            'last_error': None,
            'last_error_time': None
        }
    
    def log(
        self,
        level: str,
        message: str,
        duration: Optional[float] = None,
        attempt: Optional[int] = None,
        error_type: Optional[str] = None,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log with structured context.
        
        Args:
            level: Log level (info, success, warning, error)
            message: Log message
            duration: Request duration in seconds
            attempt: Retry attempt number
            error_type: Type of error if any
            url: URL being requested
            details: Additional details dict
        """
        # Build structured message
        parts = [message]
        
        if duration is not None:
            parts.append(f"(duration: {duration:.2f}s)")
        
        if attempt is not None:
            parts.append(f"(attempt: {attempt})")
        
        if error_type:
            parts.append(f"(error: {error_type})")
        
        if url:
            # Truncate long URLs
            display_url = url[:80] + "..." if len(url) > 80 else url
            parts.append(f"(url: {display_url})")
        
        full_message = " ".join(parts)
        
        # Log to Python logger
        level_emoji = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }.get(level, "📝")
        
        log_func = {
            "info": logger.info,
            "success": logger.info,
            "warning": logger.warning,
            "error": logger.error
        }.get(level, logger.info)
        
        log_func(f"{level_emoji} [{self.source_name}] {full_message}")
        
        # Build details dict for DB
        db_details = details or {}
        if duration is not None:
            db_details['duration'] = duration
        if attempt is not None:
            db_details['attempt'] = attempt
        if error_type:
            db_details['error_type'] = error_type
        if url:
            db_details['url'] = url
        
        # Save to database
        if DB_AVAILABLE:
            try:
                db.add_scraping_log(
                    self.source_name,
                    level,
                    message,
                    str(db_details) if db_details else None
                )
            except Exception as e:
                # Don't fail scraping if logging fails
                logger.debug(f"Failed to save log to DB: {e}")
    
    def log_request_start(self, url: str, method: str = "GET"):
        """Log start of HTTP request."""
        self.metrics['total_requests'] += 1
        self.log(
            "info",
            f"Starting {method} request",
            url=url,
            details={'method': method}
        )
    
    def log_request_success(self, url: str, duration: float, status_code: int = None):
        """Log successful HTTP request."""
        self.metrics['successful_requests'] += 1
        self.metrics['total_duration'] += duration
        
        details = {'status_code': status_code} if status_code else {}
        self.log(
            "success",
            f"Request successful",
            duration=duration,
            url=url,
            details=details
        )
    
    def log_request_error(
        self,
        url: str,
        error: Exception,
        duration: Optional[float] = None,
        attempt: Optional[int] = None
    ):
        """Log failed HTTP request."""
        self.metrics['failed_requests'] += 1
        self.metrics['last_error'] = str(error)
        self.metrics['last_error_time'] = datetime.now().isoformat()
        
        error_type = type(error).__name__
        self.log(
            "error",
            f"Request failed: {error}",
            duration=duration,
            attempt=attempt,
            error_type=error_type,
            url=url,
            details={'error': str(error)}
        )
    
    def log_scraping_start(self, query: str, limit: int):
        """Log start of scraping operation."""
        self.log(
            "info",
            f"Starting scrape: query='{query}', limit={limit}",
            details={'query': query, 'limit': limit}
        )
    
    def log_scraping_success(self, items_count: int, duration: float):
        """Log successful scraping operation."""
        success_rate = (
            self.metrics['successful_requests'] / self.metrics['total_requests']
            if self.metrics['total_requests'] > 0
            else 0.0
        )
        
        self.log(
            "success",
            f"Scraping completed: {items_count} items found",
            duration=duration,
            details={
                'items_count': items_count,
                'success_rate': f"{success_rate:.1%}",
                'total_requests': self.metrics['total_requests']
            }
        )
    
    def log_scraping_error(self, error: Exception, duration: Optional[float] = None):
        """Log failed scraping operation."""
        error_type = type(error).__name__
        self.log(
            "error",
            f"Scraping failed: {error}",
            duration=duration,
            error_type=error_type,
            details={'error': str(error)}
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.copy()

