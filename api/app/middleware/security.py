"""
Security Headers Middleware

Adds security headers to all responses (similar to Helmet.js for Express).
"""

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

    def __init__(self, app, enable_hsts: bool = True, hsts_max_age: int = 31536000):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - allow framing from same origin only
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTP Strict Transport Security (only in production)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            )

        # Content Security Policy - restrictive default
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

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

        return response
