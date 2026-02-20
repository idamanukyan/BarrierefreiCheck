"""
Request Timeout Middleware

Enforces request timeout limits to prevent long-running requests from
consuming resources indefinitely.
"""

import asyncio
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Default timeout in seconds
DEFAULT_TIMEOUT = 30.0

# Extended timeout for specific paths (in seconds)
EXTENDED_TIMEOUT_PATHS = {
    "/api/v1/scans": 60.0,      # Scan creation may take longer
    "/api/v1/reports": 120.0,   # PDF generation can be slow
    "/api/v1/export": 60.0,     # Data export may process large datasets
    "/api/v1/health/deep": 10.0,  # Health checks should be fast
}

# Paths that should skip timeout (long-polling, websockets, etc.)
SKIP_TIMEOUT_PATHS = [
    "/api/v1/ws",
    "/metrics",
]


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces request timeout limits.

    - Default timeout: 30 seconds
    - Extended timeouts for specific endpoints
    - Returns 504 Gateway Timeout on timeout
    """

    def __init__(self, app, default_timeout: float = DEFAULT_TIMEOUT):
        super().__init__(app)
        self.default_timeout = default_timeout

    def _get_timeout(self, path: str) -> float | None:
        """Get timeout for a specific path."""
        # Check if path should skip timeout
        for skip_path in SKIP_TIMEOUT_PATHS:
            if path.startswith(skip_path):
                return None

        # Check for extended timeout paths
        for prefix, timeout in EXTENDED_TIMEOUT_PATHS.items():
            if path.startswith(prefix):
                return timeout

        return self.default_timeout

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request with timeout enforcement."""
        path = request.url.path
        timeout = self._get_timeout(path)

        # Skip timeout for specified paths
        if timeout is None:
            return await call_next(request)

        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            method = request.method
            logger.warning(
                f"Request timeout: {method} {path} exceeded {timeout}s",
                extra={
                    "method": method,
                    "path": path,
                    "timeout": timeout,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )

            return JSONResponse(
                status_code=504,
                content={
                    "error": "Gateway Timeout",
                    "message": f"Request exceeded maximum allowed time of {timeout} seconds",
                    "code": "REQUEST_TIMEOUT",
                }
            )
