"""
API Versioning Middleware

Adds deprecation headers and version information to API responses.
"""

from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add API version information to responses.

    Adds headers for:
    - Current API version
    - Deprecation warnings for old versions
    - Sunset dates for deprecated endpoints
    """

    def __init__(
        self,
        app,
        current_version: str = "1",
        deprecated_versions: dict = None,
    ):
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            current_version: Current API version number
            deprecated_versions: Dict mapping version to sunset date
                                 e.g., {"1": "2026-06-01"}
        """
        super().__init__(app)
        self.current_version = current_version
        self.deprecated_versions = deprecated_versions or {}

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Add API version header
        response.headers["X-API-Version"] = self.current_version

        # Check if request is to a deprecated API version
        path = request.url.path
        for version, sunset_date in self.deprecated_versions.items():
            if f"/api/v{version}/" in path:
                # Add deprecation headers per RFC 8594
                response.headers["Deprecation"] = "true"
                response.headers["Sunset"] = sunset_date

                # Add Link header pointing to newer version
                if version != self.current_version:
                    new_path = path.replace(
                        f"/api/v{version}/",
                        f"/api/v{self.current_version}/"
                    )
                    response.headers["Link"] = (
                        f'<{new_path}>; rel="successor-version"'
                    )
                break

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce maximum request body size.
    """

    def __init__(self, app, max_size_bytes: int = 10 * 1024 * 1024):
        """
        Initialize the middleware.

        Args:
            app: The ASGI application
            max_size_bytes: Maximum allowed request body size in bytes (default 10MB)
        """
        super().__init__(app)
        self.max_size_bytes = max_size_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size_bytes:
                    from starlette.responses import JSONResponse
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body too large. Maximum size is {self.max_size_bytes // (1024 * 1024)}MB."
                        }
                    )
            except ValueError:
                pass  # Invalid Content-Length header, let it through

        return await call_next(request)
