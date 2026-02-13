"""
Security Headers Middleware

Adds security headers to all responses (similar to Helmet.js for Express).
"""

import hashlib
import base64
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    - Strict-Transport-Security: Enforces HTTPS
    - Content-Security-Policy: Controls resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """

    # Known style hashes for Swagger UI / ReDoc
    # These are SHA-256 hashes of inline styles used by the API documentation
    SWAGGER_STYLE_HASHES = [
        # Swagger UI inline styles
        "'sha256-pyVPiLlnqL9OWVoJPs/E6VVF5hBecRzM2gBiarnaqAo='",
    ]

    def __init__(
        self,
        app,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,
        report_only: bool = False,
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.report_only = report_only

    def _get_csp_for_path(self, path: str) -> str:
        """
        Get Content-Security-Policy based on the request path.

        API documentation pages need slightly relaxed CSP for Swagger UI/ReDoc.
        All other paths get strict CSP.
        """
        # API documentation pages need Swagger UI styles
        if path in ("/api/docs", "/api/redoc", "/api/openapi.json"):
            style_hashes = " ".join(self.SWAGGER_STYLE_HASHES)
            return (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net; "
                f"style-src 'self' {style_hashes} https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'self'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

        # Strict CSP for all other endpoints (pure API)
        return (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'none'"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - deny all framing for API
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTP Strict Transport Security (only in production)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        # Content Security Policy - path-aware
        csp = self._get_csp_for_path(request.url.path)
        csp_header = "Content-Security-Policy-Report-Only" if self.report_only else "Content-Security-Policy"
        response.headers[csp_header] = csp

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # Prevent caching of sensitive responses (for API)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        # Cross-Origin policies for additional security
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        return response
