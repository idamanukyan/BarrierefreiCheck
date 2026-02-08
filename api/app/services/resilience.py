"""
Resilience Patterns

Circuit breaker and retry logic for external service calls.
"""

import asyncio
import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Type

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping calls to failing services.

    Usage:
        stripe_breaker = CircuitBreaker("stripe", failure_threshold=5, recovery_timeout=30)

        @stripe_breaker
        async def call_stripe_api():
            ...
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exceptions: tuple = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    async def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on circuit state."""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time and \
                   time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker '{self.name}' entering half-open state")
                    return True
                return False

            # HALF_OPEN - allow one request to test
            return True

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info(f"Circuit breaker '{self.name}' closed after successful call")

    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' reopened after failed test")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
                )

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if not await self._should_allow_request():
                logger.warning(f"Circuit breaker '{self.name}' is open, rejecting request")
                raise CircuitBreakerError(
                    f"Service '{self.name}' is currently unavailable. Please try again later."
                )

            try:
                result = await func(*args, **kwargs)
                await self._record_success()
                return result
            except self.expected_exceptions as e:
                await self._record_failure()
                raise

        return wrapper

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator for retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Optional callback called on each retry (exception, attempt_number)

    Usage:
        @retry_with_backoff(max_retries=3, exceptions=(ConnectionError, TimeoutError))
        async def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )

                    if on_retry:
                        on_retry(e, attempt + 1)

                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# Pre-configured circuit breakers for external services

# Stripe payment API - higher threshold, longer recovery
stripe_circuit_breaker = CircuitBreaker(
    name="stripe",
    failure_threshold=5,
    recovery_timeout=30,
    expected_exceptions=(Exception,),
)

# MinIO/S3 storage - moderate threshold
minio_circuit_breaker = CircuitBreaker(
    name="minio",
    failure_threshold=3,
    recovery_timeout=15,
    expected_exceptions=(Exception,),
)

# Redis cache - low threshold, quick recovery (critical for auth)
redis_circuit_breaker = CircuitBreaker(
    name="redis",
    failure_threshold=3,
    recovery_timeout=10,
    expected_exceptions=(Exception,),
)

# Email service - higher threshold (non-critical)
email_circuit_breaker = CircuitBreaker(
    name="email",
    failure_threshold=5,
    recovery_timeout=60,
    expected_exceptions=(Exception,),
)

# Database - very low threshold, quick recovery (critical)
database_circuit_breaker = CircuitBreaker(
    name="database",
    failure_threshold=2,
    recovery_timeout=5,
    expected_exceptions=(Exception,),
)


def with_circuit_breaker(breaker: CircuitBreaker, fallback_value: Any = None):
    """
    Decorator that wraps a function with circuit breaker and optional fallback.

    If the circuit is open and a fallback_value is provided, returns the fallback
    instead of raising CircuitBreakerError.

    Usage:
        @with_circuit_breaker(redis_circuit_breaker, fallback_value=None)
        async def get_from_cache(key):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                # Apply circuit breaker
                wrapped = breaker(func)
                return await wrapped(*args, **kwargs)
            except CircuitBreakerError:
                if fallback_value is not None:
                    logger.info(
                        f"Circuit breaker '{breaker.name}' open, returning fallback value"
                    )
                    return fallback_value
                raise
        return wrapper
    return decorator


def sync_with_circuit_breaker(breaker: CircuitBreaker, fallback_value: Any = None):
    """
    Synchronous version of circuit breaker wrapper for non-async functions.

    Usage:
        @sync_with_circuit_breaker(redis_circuit_breaker, fallback_value=None)
        def get_from_cache_sync(key):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Check circuit state synchronously
            if breaker._state == CircuitState.OPEN:
                if breaker._last_failure_time and \
                   time.time() - breaker._last_failure_time >= breaker.recovery_timeout:
                    breaker._state = CircuitState.HALF_OPEN
                else:
                    if fallback_value is not None:
                        logger.info(
                            f"Circuit breaker '{breaker.name}' open, returning fallback"
                        )
                        return fallback_value
                    raise CircuitBreakerError(
                        f"Service '{breaker.name}' is currently unavailable."
                    )

            try:
                result = func(*args, **kwargs)
                # Record success
                breaker._failure_count = 0
                if breaker._state == CircuitState.HALF_OPEN:
                    breaker._state = CircuitState.CLOSED
                return result
            except breaker.expected_exceptions:
                # Record failure
                breaker._failure_count += 1
                breaker._last_failure_time = time.time()
                if breaker._state == CircuitState.HALF_OPEN:
                    breaker._state = CircuitState.OPEN
                elif breaker._failure_count >= breaker.failure_threshold:
                    breaker._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker '{breaker.name}' opened after "
                        f"{breaker._failure_count} failures"
                    )
                raise
        return wrapper
    return decorator
