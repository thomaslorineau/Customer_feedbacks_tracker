"""Circuit Breaker pattern implementation for scrapers.

Prevents repeated calls to failing APIs by opening the circuit after
a threshold of failures, then attempting to close it after a timeout.
"""
import time
import logging
from enum import Enum
from typing import Optional, Dict
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"  # Normal operation, requests allowed
    OPEN = "OPEN"  # Circuit open, requests blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.
    
    After failure_threshold failures, the circuit opens and blocks requests
    for timeout seconds. Then it enters HALF_OPEN state to test recovery.
    """
    
    def __init__(
        self,
        source_name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Args:
            source_name: Name of the source (for logging)
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
            success_threshold: Successful calls needed in HALF_OPEN to close circuit
        """
        self.source_name = source_name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.lock = Lock()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection.
        
        Returns:
            Result of function call, or raises exception if circuit is open.
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"[CircuitBreaker:{self.source_name}] Entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker for {self.source_name} is OPEN. "
                    f"Last failure: {time.time() - self.last_failure_time:.1f}s ago"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func, *args, **kwargs):
        """Execute async function with circuit breaker protection.
        
        Returns:
            Result of function call, or raises exception if circuit is open.
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"[CircuitBreaker:{self.source_name}] Entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker for {self.source_name} is OPEN. "
                    f"Last failure: {time.time() - self.last_failure_time:.1f}s ago"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.timeout
    
    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"[CircuitBreaker:{self.source_name}] Circuit CLOSED after recovery")
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # Failure in HALF_OPEN means service not recovered
                self.state = CircuitState.OPEN
                logger.warning(f"[CircuitBreaker:{self.source_name}] Circuit OPENED again after HALF_OPEN failure")
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.error(
                        f"[CircuitBreaker:{self.source_name}] Circuit OPENED after {self.failure_count} failures. "
                        f"Will retry after {self.timeout}s"
                    )
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            logger.info(f"[CircuitBreaker:{self.source_name}] Manually reset to CLOSED")
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request is blocked."""
    pass


# Global registry of circuit breakers per source
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_breakers_lock = Lock()


def get_circuit_breaker(source_name: str, **kwargs) -> CircuitBreaker:
    """Get or create circuit breaker for a source.
    
    Args:
        source_name: Name of the source
        **kwargs: Additional arguments for CircuitBreaker constructor
    
    Returns:
        CircuitBreaker instance for the source
    """
    with _breakers_lock:
        if source_name not in _circuit_breakers:
            _circuit_breakers[source_name] = CircuitBreaker(source_name, **kwargs)
        return _circuit_breakers[source_name]


def reset_circuit_breaker(source_name: str):
    """Reset circuit breaker for a source."""
    with _breakers_lock:
        if source_name in _circuit_breakers:
            _circuit_breakers[source_name].reset()


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all circuit breakers."""
    with _breakers_lock:
        return _circuit_breakers.copy()


