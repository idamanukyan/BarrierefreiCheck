"""
Rate Limiter Service

Provides rate limiting for API endpoints using slowapi.
Supports user/plan-based rate limiting for different subscription tiers.
"""

import ipaddress
import logging
from typing import Optional, Set, Callable
from functools import wraps

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# Trusted proxy networks (configure via environment in production)
# Default includes common private networks and localhost
TRUSTED_PROXY_NETWORKS: Set[ipaddress.IPv4Network | ipaddress.IPv6Network] = set()


def _init_trusted_proxies():
    """Initialize trusted proxy networks from configuration."""
    global TRUSTED_PROXY_NETWORKS

    # Get trusted proxies from settings (comma-separated CIDR notation)
    trusted_proxies_str = getattr(settings, 'trusted_proxies', '')

    if trusted_proxies_str:
        for proxy in trusted_proxies_str.split(','):
            proxy = proxy.strip()
            if proxy:
                try:
                    TRUSTED_PROXY_NETWORKS.add(ipaddress.ip_network(proxy, strict=False))
                except ValueError as e:
                    logger.warning(f"Invalid trusted proxy CIDR: {proxy} - {e}")


def _is_trusted_proxy(ip_str: str) -> bool:
    """Check if an IP address is a trusted proxy."""
    if not TRUSTED_PROXY_NETWORKS:
        return False

    try:
        ip = ipaddress.ip_address(ip_str)
        for network in TRUSTED_PROXY_NETWORKS:
            if ip in network:
                return True
    except ValueError:
        return False

    return False


def get_client_ip(request: Request) -> str:
    """
    Get client IP address securely.

    Only respects X-Forwarded-For header if the direct connection is from
    a trusted proxy. This prevents IP spoofing attacks.

    Security: Configure TRUSTED_PROXIES environment variable with your
    reverse proxy IP addresses/networks in CIDR notation (comma-separated).
    Example: TRUSTED_PROXIES=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
    """
    # Initialize on first call if not already done
    if not TRUSTED_PROXY_NETWORKS:
        _init_trusted_proxies()

    # Get the direct connection IP
    direct_ip = get_remote_address(request)

    # Only trust X-Forwarded-For if request comes from a trusted proxy
    if _is_trusted_proxy(direct_ip):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain (original client)
            client_ip = forwarded.split(",")[0].strip()
            # Validate it's a valid IP address
            try:
                ipaddress.ip_address(client_ip)
                return client_ip
            except ValueError:
                logger.warning(f"Invalid IP in X-Forwarded-For: {client_ip}")
                return direct_ip

    return direct_ip


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
# Authentication
AUTH_RATE_LIMIT = "5/minute"  # 5 requests per minute for auth endpoints
REGISTER_RATE_LIMIT = "3/minute"  # 3 registrations per minute
PASSWORD_RESET_RATE_LIMIT = "3/minute"  # 3 password reset requests per minute

# Scans
SCAN_CREATE_LIMIT = "10/minute"  # Creating scans is resource-intensive
SCAN_READ_LIMIT = "60/minute"    # Reading scan data
SCAN_LIST_LIMIT = "30/minute"    # Listing scans

# Dashboard
DASHBOARD_RATE_LIMIT = "30/minute"  # Dashboard stats

# Reports
REPORT_CREATE_LIMIT = "10/minute"   # Report generation is resource-intensive
REPORT_DOWNLOAD_LIMIT = "30/minute" # Downloads are less intensive

# Export
EXPORT_RATE_LIMIT = "20/minute"  # Exports can be resource-intensive

# Billing
CHECKOUT_RATE_LIMIT = "5/minute"       # Prevent checkout abuse
SUBSCRIPTION_RATE_LIMIT = "10/minute"  # Subscription modifications

# Default for general endpoints
DEFAULT_RATE_LIMIT = "100/minute"


# ============================================================================
# Plan-Based Rate Limiting
# ============================================================================

# Rate limit multipliers by plan type
# Higher tier plans get higher rate limits
PLAN_RATE_MULTIPLIERS = {
    "free": 1.0,
    "starter": 2.0,
    "professional": 5.0,
    "agency": 10.0,
    "enterprise": 20.0,
}

# Plan-specific rate limits for different operation types
# Format: {plan_type: {operation_type: "limit/period"}}
PLAN_RATE_LIMITS = {
    "free": {
        "scan_create": "3/hour",
        "scan_read": "30/minute",
        "scan_list": "15/minute",
        "report_create": "3/hour",
        "report_download": "10/minute",
        "export": "5/minute",
        "api_default": "60/minute",
    },
    "starter": {
        "scan_create": "10/hour",
        "scan_read": "60/minute",
        "scan_list": "30/minute",
        "report_create": "10/hour",
        "report_download": "30/minute",
        "export": "20/minute",
        "api_default": "100/minute",
    },
    "professional": {
        "scan_create": "30/hour",
        "scan_read": "120/minute",
        "scan_list": "60/minute",
        "report_create": "30/hour",
        "report_download": "60/minute",
        "export": "40/minute",
        "api_default": "200/minute",
    },
    "agency": {
        "scan_create": "100/hour",
        "scan_read": "300/minute",
        "scan_list": "150/minute",
        "report_create": "100/hour",
        "report_download": "150/minute",
        "export": "100/minute",
        "api_default": "500/minute",
    },
    "enterprise": {
        "scan_create": "500/hour",
        "scan_read": "1000/minute",
        "scan_list": "500/minute",
        "report_create": "500/hour",
        "report_download": "500/minute",
        "export": "300/minute",
        "api_default": "1000/minute",
    },
}


def get_plan_rate_limit(plan_type: str, operation_type: str) -> str:
    """
    Get the rate limit for a specific plan and operation type.

    Args:
        plan_type: The user's subscription plan (free, starter, professional, agency, enterprise)
        operation_type: The type of operation (scan_create, scan_read, etc.)

    Returns:
        Rate limit string in format "count/period"
    """
    plan_type = plan_type.lower() if plan_type else "free"

    # Get plan limits, defaulting to free tier
    plan_limits = PLAN_RATE_LIMITS.get(plan_type, PLAN_RATE_LIMITS["free"])

    # Get specific operation limit, defaulting to api_default
    return plan_limits.get(operation_type, plan_limits.get("api_default", DEFAULT_RATE_LIMIT))


def get_user_plan_key(request: Request) -> str:
    """
    Get a rate limit key that includes user ID and plan type.

    This allows different users to have separate rate limit buckets,
    and enables plan-based rate limiting.

    Returns format: "user:{user_id}:{plan_type}" or falls back to IP-based key
    """
    # Try to get user from request state (set by authentication middleware)
    user = getattr(request.state, "user", None)

    if user:
        user_id = str(user.id) if hasattr(user, "id") else "unknown"
        plan_type = user.plan.value if hasattr(user, "plan") else "free"
        return f"user:{user_id}:{plan_type}"

    # Fall back to IP-based rate limiting for unauthenticated requests
    return get_client_ip(request)


def create_plan_based_limiter(operation_type: str) -> Callable:
    """
    Create a rate limiter that applies plan-based limits.

    This is a dynamic limit function that can be used with slowapi's
    @limiter.limit() decorator.

    Args:
        operation_type: The type of operation to rate limit

    Returns:
        A callable that returns the appropriate rate limit for the request
    """
    def dynamic_limit(request: Request) -> str:
        # Try to get user from request state
        user = getattr(request.state, "user", None)

        if user:
            plan_type = user.plan.value if hasattr(user, "plan") else "free"
            limit = get_plan_rate_limit(plan_type, operation_type)
            logger.debug(f"Plan-based rate limit for {plan_type}/{operation_type}: {limit}")
            return limit

        # For unauthenticated requests, use the most restrictive (free tier) limits
        return get_plan_rate_limit("free", operation_type)

    return dynamic_limit


# Pre-configured plan-based limiters for common operations
plan_limit_scan_create = create_plan_based_limiter("scan_create")
plan_limit_scan_read = create_plan_based_limiter("scan_read")
plan_limit_scan_list = create_plan_based_limiter("scan_list")
plan_limit_report_create = create_plan_based_limiter("report_create")
plan_limit_report_download = create_plan_based_limiter("report_download")
plan_limit_export = create_plan_based_limiter("export")
plan_limit_api_default = create_plan_based_limiter("api_default")


# Create a user-based limiter that uses user ID as the key
user_limiter = Limiter(key_func=get_user_plan_key)
