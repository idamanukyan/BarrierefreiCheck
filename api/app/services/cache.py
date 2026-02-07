"""
Cache Service

Redis-based caching for frequently accessed data.
"""

import json
import logging
from typing import Any, Optional
from functools import wraps

import redis
from app.config import settings

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
    """Get value from cache."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        value = client.get(key)
        if value:
            return json.loads(value)
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.warning(f"Cache get error for key {key}: {e}")
    return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """Set value in cache with TTL."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except (redis.RedisError, TypeError) as e:
        logger.warning(f"Cache set error for key {key}: {e}")
    return False


def cache_delete(key: str) -> bool:
    """Delete value from cache."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except redis.RedisError as e:
        logger.warning(f"Cache delete error for key {key}: {e}")
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


def is_token_blacklisted(token: str) -> bool:
    """Check if a token has been blacklisted (logged out)."""
    client = get_redis_client()
    if client is None:
        return False  # Fail open if Redis unavailable (could also fail closed)
    try:
        return client.exists(f"token_blacklist:{token}") > 0
    except redis.RedisError as e:
        logger.warning(f"Failed to check token blacklist: {e}")
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
