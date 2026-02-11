"""
Cache Service

Redis-based caching for frequently accessed data.
Includes circuit breaker protection for Redis failures.
"""

import json
import logging
from typing import Any, Optional
from functools import wraps

import redis
from app.config import settings
from app.services.resilience import redis_circuit_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)

# Redis connection pool
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client with connection pooling."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis connection established")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    """
    Get value from cache.

    Returns None if Redis is unavailable or circuit breaker is open.
    This allows the application to gracefully degrade without caching.
    """
    # Check circuit breaker state
    if redis_circuit_breaker.state.value == "open":
        logger.debug("Redis circuit breaker open, skipping cache get")
        return None

    client = get_redis_client()
    if client is None:
        return None
    try:
        value = client.get(key)
        if value:
            return json.loads(value)
    except redis.RedisError as e:
        logger.warning(f"Cache get error for key {key}: {e}")
        # Record failure for circuit breaker (simplified sync version)
        redis_circuit_breaker._failure_count += 1
        if redis_circuit_breaker._failure_count >= redis_circuit_breaker.failure_threshold:
            redis_circuit_breaker._state = redis_circuit_breaker._state.__class__("open")
            import time
            redis_circuit_breaker._last_failure_time = time.time()
            logger.warning("Redis circuit breaker opened due to repeated failures")
    except json.JSONDecodeError as e:
        logger.warning(f"Cache JSON decode error for key {key}: {e}")
    return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """
    Set value in cache with TTL.

    Returns False if Redis is unavailable or circuit breaker is open.
    """
    # Check circuit breaker state
    if redis_circuit_breaker.state.value == "open":
        logger.debug("Redis circuit breaker open, skipping cache set")
        return False

    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl_seconds, json.dumps(value, default=str))
        # Reset failure count on success
        redis_circuit_breaker._failure_count = 0
        return True
    except (redis.RedisError, TypeError) as e:
        logger.warning(f"Cache set error for key {key}: {e}")
        redis_circuit_breaker._failure_count += 1
        if redis_circuit_breaker._failure_count >= redis_circuit_breaker.failure_threshold:
            redis_circuit_breaker._state = redis_circuit_breaker._state.__class__("open")
            import time
            redis_circuit_breaker._last_failure_time = time.time()
    return False


def cache_delete(key: str) -> bool:
    """
    Delete value from cache.

    Returns False if Redis is unavailable or circuit breaker is open.
    """
    # Check circuit breaker state
    if redis_circuit_breaker.state.value == "open":
        return False

    client = get_redis_client()
    if client is None:
        return False
    try:
        client.delete(key)
        redis_circuit_breaker._failure_count = 0
        return True
    except redis.RedisError as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
        redis_circuit_breaker._failure_count += 1
    return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching pattern."""
    client = get_redis_client()
    if client is None:
        return 0
    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
    except redis.RedisError as e:
        logger.warning(f"Cache delete pattern error for {pattern}: {e}")
    return 0


def cache_exists(key: str) -> bool:
    """Check if key exists in cache."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        return client.exists(key) > 0
    except redis.RedisError as e:
        logger.warning(f"Cache exists error for key {key}: {e}")
    return False


# Token blacklist functions
def blacklist_token(token: str, ttl_seconds: int) -> bool:
    """
    Add a token to the blacklist.

    Used for logout to invalidate JWT tokens before their natural expiry.
    TTL should match the remaining lifetime of the token.
    """
    if ttl_seconds <= 0:
        return True  # Token already expired, no need to blacklist

    client = get_redis_client()
    if client is None:
        logger.warning("Redis unavailable - token blacklist not persisted")
        return False
    try:
        key = f"token_blacklist:{token}"
        client.setex(key, ttl_seconds, "1")
        logger.debug(f"Token blacklisted for {ttl_seconds}s")
        return True
    except redis.RedisError as e:
        logger.error(f"Failed to blacklist token: {e}")
    return False


def is_token_blacklisted(token: str, fail_closed: bool = True) -> bool:
    """
    Check if a token has been blacklisted (logged out).

    Security: By default, fails closed (returns True) when Redis is unavailable.
    This prevents revoked tokens from being used during Redis outages.
    Set fail_closed=False only for non-security-critical checks.

    Args:
        token: The JWT token to check
        fail_closed: If True (default), returns True when Redis unavailable
                    to err on the side of security

    Returns:
        True if token is blacklisted or cannot be verified (when fail_closed=True)
        False if token is not blacklisted
    """
    client = get_redis_client()
    if client is None:
        if fail_closed:
            logger.warning("Redis unavailable - failing closed for token blacklist check")
            return True  # Fail closed: assume token is blacklisted for security
        return False
    try:
        return client.exists(f"token_blacklist:{token}") > 0
    except redis.RedisError as e:
        logger.warning(f"Failed to check token blacklist: {e}")
        if fail_closed:
            logger.warning("Redis error - failing closed for token blacklist check")
            return True  # Fail closed: assume token is blacklisted for security
    return False


def cached(key_prefix: str, ttl_seconds: int = 300):
    """
    Decorator for caching function results.

    Usage:
        @cached("dashboard:stats", ttl_seconds=60)
        async def get_dashboard_stats(user_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from prefix and arguments
            key_parts = [key_prefix]
            key_parts.extend(str(arg) for arg in args if arg is not None)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Execute function and cache result
            result = await func(*args, **kwargs)

            # Convert Pydantic models to dict for caching
            if hasattr(result, 'model_dump'):
                cache_value = result.model_dump()
            elif hasattr(result, 'dict'):
                cache_value = result.dict()
            else:
                cache_value = result

            cache_set(cache_key, cache_value, ttl_seconds)
            logger.debug(f"Cache miss for {cache_key}, cached result")
            return result
        return wrapper
    return decorator


def cache_get_with_stale(key: str) -> tuple[Optional[Any], bool]:
    """
    Get value from cache with stale flag.

    Returns a tuple of (value, is_stale).
    Stale values can be returned while revalidation happens in the background.
    """
    client = get_redis_client()
    if client is None:
        return None, False
    try:
        # Get value and its TTL
        pipe = client.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        results = pipe.execute()

        value_str = results[0]
        ttl = results[1]

        if value_str:
            value = json.loads(value_str)
            # Consider stale if less than 20% of original TTL remains
            # We store original TTL in metadata
            meta_key = f"{key}:meta"
            original_ttl_str = client.get(meta_key)
            if original_ttl_str:
                original_ttl = int(original_ttl_str)
                stale_threshold = original_ttl * 0.2
                is_stale = ttl > 0 and ttl < stale_threshold
            else:
                is_stale = False
            return value, is_stale
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.warning(f"Cache get with stale error for key {key}: {e}")
    return None, False


def cache_set_with_stale(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """
    Set value in cache with stale tracking.

    Stores the original TTL in a metadata key for stale detection.
    """
    client = get_redis_client()
    if client is None:
        return False
    try:
        pipe = client.pipeline()
        pipe.setex(key, ttl_seconds, json.dumps(value, default=str))
        pipe.setex(f"{key}:meta", ttl_seconds + 60, str(ttl_seconds))  # Keep meta slightly longer
        pipe.execute()
        return True
    except (redis.RedisError, TypeError) as e:
        logger.warning(f"Cache set with stale error for key {key}: {e}")
    return False


def cached_with_stale(
    key_prefix: str,
    ttl_seconds: int = 300,
    stale_ttl_seconds: int = 60,
):
    """
    Decorator implementing stale-while-revalidate caching pattern.

    Returns stale data immediately while refreshing in the background.
    This prevents cache stampede and provides better user experience.

    Args:
        key_prefix: Prefix for the cache key
        ttl_seconds: Time before data becomes stale
        stale_ttl_seconds: Additional time to serve stale data while revalidating

    Usage:
        @cached_with_stale("dashboard:stats", ttl_seconds=60, stale_ttl_seconds=30)
        async def get_dashboard_stats(user_id: str):
            ...
    """
    import asyncio

    def decorator(func):
        # Keep track of ongoing revalidations to prevent duplicate work
        _revalidating: set = set()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from prefix and arguments
            key_parts = [key_prefix]
            key_parts.extend(str(arg) for arg in args if arg is not None)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache_get(cache_key)

            if cached_value is not None:
                # Check if we should revalidate in background
                client = get_redis_client()
                if client:
                    try:
                        ttl = client.ttl(cache_key)
                        # If TTL is low (entering stale period), trigger background refresh
                        if ttl > 0 and ttl < stale_ttl_seconds and cache_key not in _revalidating:
                            _revalidating.add(cache_key)

                            async def revalidate():
                                try:
                                    result = await func(*args, **kwargs)
                                    cache_value = _convert_to_cacheable(result)
                                    cache_set(cache_key, cache_value, ttl_seconds + stale_ttl_seconds)
                                    logger.debug(f"Background revalidation complete for {cache_key}")
                                except Exception as e:
                                    logger.warning(f"Background revalidation failed for {cache_key}: {e}")
                                finally:
                                    _revalidating.discard(cache_key)

                            # Schedule background revalidation (fire and forget)
                            asyncio.create_task(revalidate())
                    except redis.RedisError:
                        pass

                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Cache miss - fetch fresh data
            result = await func(*args, **kwargs)
            cache_value = _convert_to_cacheable(result)
            cache_set(cache_key, cache_value, ttl_seconds + stale_ttl_seconds)
            logger.debug(f"Cache miss for {cache_key}, cached result")
            return result

        return wrapper
    return decorator


def _convert_to_cacheable(value: Any) -> Any:
    """Convert a value to a cacheable format."""
    if hasattr(value, 'model_dump'):
        return value.model_dump()
    elif hasattr(value, 'dict'):
        return value.dict()
    return value
