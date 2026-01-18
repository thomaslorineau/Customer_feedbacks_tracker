"""Base scraper class with common functionality."""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from .http_client import get_http_client
from .scraper_logging import ScrapingLogger

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers with common functionality.
    
    Provides:
    - Async HTTP client with retry logic
    - Structured logging
    - Error handling
    - Metrics tracking
    """
    
    def __init__(self, source_name: str):
        """
        Args:
            source_name: Name of the source (e.g., "Trustpilot", "GitHub")
        """
        self.source_name = source_name
        self.logger = ScrapingLogger(source_name)
        self._http_client = None
    
    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = await get_http_client()
        return self._http_client
    
    @abstractmethod
    async def scrape(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Scrape data from the source.
        
        Args:
            query: Search query
            limit: Maximum number of items to return
        
        Returns:
            List of item dictionaries with keys:
            - source: str
            - author: str
            - content: str
            - url: str
            - created_at: str (ISO format)
            - sentiment_score: float (optional)
            - sentiment_label: str (optional)
        """
        pass
    
    async def _fetch_get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Make GET request with logging and error handling."""
        import time
        client = await self._get_client()
        start_time = time.time()  # Use time.time() instead of asyncio.get_event_loop().time()
        
        try:
            self.logger.log_request_start(url, "GET")
            response = await client.get(
                url,
                source_name=self.source_name,
                headers=headers,
                params=params,
                **kwargs
            )
            duration = time.time() - start_time
            self.logger.log_request_success(url, duration, response.status_code)
            return response
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_request_error(url, e, duration)
            raise
    
    async def _fetch_post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Make POST request with logging and error handling."""
        import time
        client = await self._get_client()
        start_time = time.time()  # Use time.time() instead of asyncio.get_event_loop().time()
        
        try:
            self.logger.log_request_start(url, "POST")
            response = await client.post(
                url,
                source_name=self.source_name,
                headers=headers,
                json=json,
                data=data,
                **kwargs
            )
            duration = time.time() - start_time
            self.logger.log_request_success(url, duration, response.status_code)
            return response
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_request_error(url, e, duration)
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get scraping metrics."""
        return self.logger.get_metrics()


