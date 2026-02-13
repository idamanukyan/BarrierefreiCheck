"""
Rate Limiter Service

Provides rate limiting for API endpoints using slowapi.
"""

import ipaddress
import logging
from typing import Optional, Set

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
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
