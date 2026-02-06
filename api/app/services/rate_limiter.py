"""
Rate Limiter Service

Provides rate limiting for API endpoints using slowapi.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


def get_client_ip(request: Request) -> str:
    """
    Get client IP address, respecting X-Forwarded-For header.
    Use with caution - only trust this header if behind a trusted proxy.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(key_func=get_client_ip)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after": exc.detail
        }
    )


# Rate limit configurations
AUTH_RATE_LIMIT = "5/minute"  # 5 requests per minute for auth endpoints
REGISTER_RATE_LIMIT = "3/minute"  # 3 registrations per minute
PASSWORD_RESET_RATE_LIMIT = "3/minute"  # 3 password reset requests per minute
