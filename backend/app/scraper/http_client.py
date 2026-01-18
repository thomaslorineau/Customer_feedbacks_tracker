"""Shared async HTTP client for scrapers with connection pooling and retry logic."""
import httpx
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from .circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError

logger = logging.getLogger(__name__)

# Global client instance
_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


class AsyncHTTPClient:
    """Shared async HTTP client with retry logic and circuit breaker."""
    
    def __init__(
        self,
        timeout: float = 30.0,  # Increased from 15.0 for Trustpilot pagination
        connect_timeout: float = 10.0,  # Increased from 5.0
        max_connections: int = 20,
        max_keepalive_connections: int = 10,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        backoff_factor: float = 2.0
    ):
        """
        Args:
            timeout: Request timeout in seconds
            connect_timeout: Connection timeout in seconds
            max_connections: Maximum number of connections in pool
            max_keepalive_connections: Maximum keepalive connections
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            backoff_factor: Multiplier for exponential backoff
        """
        self.timeout = httpx.Timeout(timeout, connect=connect_timeout)
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Don't close shared client
        pass
    
    async def _ensure_client(self):
        """Ensure client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self.limits,
                follow_redirects=True
            )
    
    async def get(
        self,
        url: str,
        source_name: str = "unknown",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make GET request with retry logic and circuit breaker.
        
        Args:
            url: URL to request
            source_name: Name of source (for circuit breaker)
            headers: Request headers
            params: Query parameters
            **kwargs: Additional httpx.get() arguments
        
        Returns:
            httpx.Response
        
        Raises:
            httpx.HTTPError: If request fails after retries
            CircuitBreakerOpenError: If circuit breaker is open
        """
        await self._ensure_client()
        
        circuit_breaker = get_circuit_breaker(source_name)
        
        async def _make_request():
            return await self._client.get(
                url,
                headers=headers,
                params=params,
                **kwargs
            )
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await circuit_breaker.call_async(_make_request)
                
                # Check for HTTP errors that should trigger retry
                if response.status_code >= 500:
                    # Server error - retry
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (self.backoff_factor ** attempt)
                        logger.warning(
                            f"[HTTPClient:{source_name}] Server error {response.status_code} "
                            f"on attempt {attempt + 1}/{self.max_retries}. Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                
                # Success or client error (don't retry 4xx)
                return response
                
            except CircuitBreakerOpenError:
                # Circuit breaker is open, don't retry
                raise
            except (httpx.NetworkError, httpx.ConnectError, httpx.ReadTimeout) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.warning(
                        f"[HTTPClient:{source_name}] Network error on attempt {attempt + 1}/{self.max_retries}: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[HTTPClient:{source_name}] Failed after {self.max_retries} attempts: {e}")
            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    logger.warning(f"[HTTPClient:{source_name}] Client error {e.response.status_code}: {e}")
                    raise
                # Retry on 5xx errors
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.warning(
                        f"[HTTPClient:{source_name}] Server error {e.response.status_code} "
                        f"on attempt {attempt + 1}/{self.max_retries}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[HTTPClient:{source_name}] Failed after {self.max_retries} attempts: {e}")
                    raise
        
        # All retries exhausted
        if last_error:
            raise last_error
        raise httpx.HTTPError("Request failed after retries")
    
    async def post(
        self,
        url: str,
        source_name: str = "unknown",
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make POST request with retry logic and circuit breaker.
        
        Args:
            url: URL to request
            source_name: Name of source (for circuit breaker)
            headers: Request headers
            json: JSON body
            data: Form data
            **kwargs: Additional httpx.post() arguments
        
        Returns:
            httpx.Response
        """
        await self._ensure_client()
        
        circuit_breaker = get_circuit_breaker(source_name)
        
        async def _make_request():
            return await self._client.post(
                url,
                headers=headers,
                json=json,
                data=data,
                **kwargs
            )
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await circuit_breaker.call_async(_make_request)
                
                # Check for HTTP errors that should trigger retry
                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (self.backoff_factor ** attempt)
                        logger.warning(
                            f"[HTTPClient:{source_name}] Server error {response.status_code} "
                            f"on attempt {attempt + 1}/{self.max_retries}. Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        continue
                
                return response
                
            except CircuitBreakerOpenError:
                raise
            except (httpx.NetworkError, httpx.ConnectError, httpx.ReadTimeout) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.warning(
                        f"[HTTPClient:{source_name}] Network error on attempt {attempt + 1}/{self.max_retries}: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[HTTPClient:{source_name}] Failed after {self.max_retries} attempts: {e}")
            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    logger.warning(f"[HTTPClient:{source_name}] Client error {e.response.status_code}: {e}")
                    raise
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.warning(
                        f"[HTTPClient:{source_name}] Server error {e.response.status_code} "
                        f"on attempt {attempt + 1}/{self.max_retries}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[HTTPClient:{source_name}] Failed after {self.max_retries} attempts: {e}")
                    raise
        
        if last_error:
            raise last_error
        raise httpx.HTTPError("Request failed after retries")
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global singleton instance
_global_client: Optional[AsyncHTTPClient] = None


async def get_http_client() -> AsyncHTTPClient:
    """Get or create global HTTP client instance.
    
    Returns:
        Shared AsyncHTTPClient instance
    """
    global _global_client
    
    async with _client_lock:
        if _global_client is None:
            _global_client = AsyncHTTPClient()
            await _global_client._ensure_client()
        return _global_client


async def close_http_client():
    """Close global HTTP client."""
    global _global_client
    
    async with _client_lock:
        if _global_client:
            await _global_client.close()
            _global_client = None


