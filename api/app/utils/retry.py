"""
Retry Utilities

Provides decorators and utilities for retrying operations that may fail
due to transient errors (network issues, database connection drops, etc.).
"""

import asyncio
import functools
import logging
import time
from typing import Callable, Type, Tuple, TypeVar, Any

from sqlalchemy.exc import (
    OperationalError,
    InterfaceError,
    DBAPIError,
    TimeoutError as SQLAlchemyTimeoutError,
)

logger = logging.getLogger(__name__)

# Type variable for return type preservation
T = TypeVar('T')

# Default transient exception types for database operations
DB_TRANSIENT_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    OperationalError,
    InterfaceError,
    DBAPIError,
    SQLAlchemyTimeoutError,
    ConnectionError,
    TimeoutError,
)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = DB_TRANSIENT_EXCEPTIONS,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.exceptions = exceptions

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt using exponential backoff."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


# Default configuration
DEFAULT_RETRY_CONFIG = RetryConfig()


def is_transient_db_error(exception: Exception) -> bool:
    """
    Check if an exception is a transient database error that can be retried.

    Transient errors are typically:
    - Connection timeouts
    - Connection pool exhaustion
    - Temporary network issues
    - Database server restarts

    Non-transient errors (should not retry):
    - Integrity errors (unique constraint violations)
    - Syntax errors
    - Permission errors
    """
    if isinstance(exception, OperationalError):
        error_str = str(exception).lower()
        # Check for specific transient error patterns
        transient_patterns = [
            'connection',
            'timeout',
            'timed out',
            'network',
            'server closed',
            'connection reset',
            'broken pipe',
            'could not connect',
            'connection refused',
            'pool',
            'too many connections',
            'server has gone away',
            'lost connection',
            'connection terminated',
        ]
        return any(pattern in error_str for pattern in transient_patterns)

    return isinstance(exception, DB_TRANSIENT_EXCEPTIONS)


def retry_on_db_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
) -> Callable:
    """
    Decorator for retrying synchronous functions on transient database errors.

    Usage:
        @retry_on_db_error(max_retries=3)
        def get_user(db: Session, user_id: str) -> User:
            return db.query(User).filter(User.id == user_id).first()

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds (caps exponential backoff)
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.exceptions as e:
                    last_exception = e

                    if not is_transient_db_error(e):
                        # Not a transient error, don't retry
                        raise

                    if attempt < config.max_retries:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Transient DB error in {func.__name__} "
                            f"(attempt {attempt + 1}/{config.max_retries + 1}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"DB operation {func.__name__} failed after "
                            f"{config.max_retries + 1} attempts: {e}"
                        )

            # All retries exhausted
            raise last_exception  # type: ignore

        return wrapper

    return decorator


def async_retry_on_db_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
) -> Callable:
    """
    Decorator for retrying async functions on transient database errors.

    Usage:
        @async_retry_on_db_error(max_retries=3)
        async def get_user(db: AsyncSession, user_id: str) -> User:
            result = await db.execute(select(User).filter(User.id == user_id))
            return result.scalar_one_or_none()

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds (caps exponential backoff)
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.exceptions as e:
                    last_exception = e

                    if not is_transient_db_error(e):
                        # Not a transient error, don't retry
                        raise

                    if attempt < config.max_retries:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Transient DB error in {func.__name__} "
                            f"(attempt {attempt + 1}/{config.max_retries + 1}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"DB operation {func.__name__} failed after "
                            f"{config.max_retries + 1} attempts: {e}"
                        )

            # All retries exhausted
            raise last_exception  # type: ignore

        return wrapper

    return decorator


def execute_with_retry(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    **kwargs: Any,
) -> T:
    """
    Execute a function with retry logic for transient database errors.

    Useful for one-off operations where you don't want to use a decorator.

    Usage:
        user = execute_with_retry(
            lambda: db.query(User).filter(User.id == user_id).first(),
            max_retries=3
        )

    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Result of the function
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
    )

    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except config.exceptions as e:
            last_exception = e

            if not is_transient_db_error(e):
                raise

            if attempt < config.max_retries:
                delay = config.get_delay(attempt)
                logger.warning(
                    f"Transient DB error (attempt {attempt + 1}/{config.max_retries + 1}), "
                    f"retrying in {delay:.1f}s: {e}"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"DB operation failed after {config.max_retries + 1} attempts: {e}"
                )

    raise last_exception  # type: ignore


async def async_execute_with_retry(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    **kwargs: Any,
) -> T:
    """
    Execute an async function with retry logic for transient database errors.

    Usage:
        user = await async_execute_with_retry(
            lambda: db.execute(select(User).filter(User.id == user_id)),
            max_retries=3
        )

    Args:
        func: Async function to execute
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Result of the function
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
    )

    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except config.exceptions as e:
            last_exception = e

            if not is_transient_db_error(e):
                raise

            if attempt < config.max_retries:
                delay = config.get_delay(attempt)
                logger.warning(
                    f"Transient DB error (attempt {attempt + 1}/{config.max_retries + 1}), "
                    f"retrying in {delay:.1f}s: {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"DB operation failed after {config.max_retries + 1} attempts: {e}"
                )

    raise last_exception  # type: ignore
