"""
Input Validators

URL validation and sanitization for SSRF protection.
"""

import ipaddress
import logging
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URLValidationError(Exception):
    """Raised when URL validation fails."""
    pass


# Private/internal IP ranges that should be blocked
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("100.64.0.0/10"),    # Shared address space (CGN)
    ipaddress.ip_network("192.0.0.0/24"),     # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),     # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),   # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6 ranges
    ipaddress.ip_network("::1/128"),          # Loopback
    ipaddress.ip_network("fc00::/7"),         # Unique local
    ipaddress.ip_network("fe80::/10"),        # Link-local
    ipaddress.ip_network("ff00::/8"),         # Multicast
]

# Blocked hostnames
BLOCKED_HOSTNAMES = [
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",     # GCP metadata
    "metadata.google.com",
    "169.254.169.254",              # AWS/Azure/GCP metadata IP
    "instance-data",                # AWS metadata hostname
]

# Allowed URL schemes
ALLOWED_SCHEMES = ["http", "https"]

# Maximum URL length
MAX_URL_LENGTH = 2048


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is in a private/internal range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        # Not a valid IP address
        return False


def resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname to IP address."""
    try:
        # Use getaddrinfo for IPv4 and IPv6 support
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if results:
            # Return the first IP address
            return results[0][4][0]
        return None
    except socket.gaierror:
        return None
    except Exception as e:
        logger.warning(f"Error resolving hostname {hostname}: {e}")
        return None


def validate_scan_url(url: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate and sanitize a URL for scanning.

    Performs SSRF protection by:
    1. Checking URL scheme (only http/https allowed)
    2. Validating URL format
    3. Blocking private/internal IP addresses
    4. Blocking known metadata endpoints
    5. Resolving hostnames to check for private IPs

    Args:
        url: The URL to validate

    Returns:
        Tuple of (is_valid, sanitized_url or error_message, resolved_ip)

    Raises:
        URLValidationError: If the URL is invalid or blocked
    """
    # Check URL length
    if len(url) > MAX_URL_LENGTH:
        raise URLValidationError(
            f"URL exceeds maximum length of {MAX_URL_LENGTH} characters"
        )

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise URLValidationError(f"Invalid URL format: {e}")

    # Validate scheme
    if not parsed.scheme:
        raise URLValidationError("URL must include a scheme (http:// or https://)")

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise URLValidationError(
            f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are allowed."
        )

    # Validate hostname
    if not parsed.hostname:
        raise URLValidationError("URL must include a valid hostname")

    hostname = parsed.hostname.lower()

    # Check against blocked hostnames
    if hostname in BLOCKED_HOSTNAMES:
        raise URLValidationError(
            f"Hostname '{hostname}' is not allowed for security reasons"
        )

    # Check if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        if is_private_ip(hostname):
            raise URLValidationError(
                "Scanning private/internal IP addresses is not allowed"
            )
        resolved_ip = hostname
    except ValueError:
        # Not an IP address, it's a hostname - resolve it
        resolved_ip = resolve_hostname(hostname)

        if resolved_ip is None:
            raise URLValidationError(
                f"Unable to resolve hostname '{hostname}'. Please check the URL."
            )

        # Check if resolved IP is private
        if is_private_ip(resolved_ip):
            logger.warning(
                f"SSRF attempt blocked: {hostname} resolves to private IP {resolved_ip}"
            )
            raise URLValidationError(
                "The hostname resolves to a private/internal address which is not allowed"
            )

    # Check for suspicious port numbers (optional - could block non-standard ports)
    if parsed.port:
        # Allow common web ports
        allowed_ports = [80, 443, 8080, 8443, 3000, 5000, 8000]
        if parsed.port not in allowed_ports:
            logger.info(f"Allowing non-standard port {parsed.port} for URL: {url}")

    # Reconstruct sanitized URL
    sanitized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        sanitized_url += f"?{parsed.query}"

    return True, sanitized_url, resolved_ip


def validate_url_simple(url: str) -> str:
    """
    Simple URL validation that returns the sanitized URL or raises an error.

    Args:
        url: The URL to validate

    Returns:
        Sanitized URL string

    Raises:
        URLValidationError: If the URL is invalid or blocked
    """
    _, sanitized_url, _ = validate_scan_url(url)
    return sanitized_url
