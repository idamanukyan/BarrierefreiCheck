"""
Correlation ID Middleware

Generates and propagates correlation IDs for request tracing across services.
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to store correlation ID for the current request
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Header names
CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"

logger = logging.getLogger(__name__)


def get_correlation_id() -> Optional[str]:
    """Get the correlation ID for the current request context."""
    return correlation_id_ctx.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles correlation IDs for request tracing.

    - Extracts correlation ID from incoming request headers
    - Generates a new one if not present
    - Adds it to response headers
    - Makes it available via context variable for logging
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get or generate correlation ID
        correlation_id = (
            request.headers.get(CORRELATION_ID_HEADER)
            or request.headers.get(REQUEST_ID_HEADER)
            or generate_correlation_id()
        )

        # Store in context variable for access in handlers/services
        token = correlation_id_ctx.set(correlation_id)

        try:
            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[CORRELATION_ID_HEADER] = correlation_id

            return response
        finally:
            # Reset context variable
            correlation_id_ctx.reset(token)


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to log records.

    Usage:
        handler = logging.StreamHandler()
        handler.addFilter(CorrelationIdFilter())
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(correlation_id)s] %(levelname)s %(name)s: %(message)s'
        ))
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "no-correlation-id"
        return True


def setup_logging_with_correlation_id(level: int = logging.INFO) -> None:
    """
    Configure logging to include correlation IDs.

    Call this during application startup.
    """
    # Create formatter with correlation ID
    formatter = logging.Formatter(
        "%(asctime)s [%(correlation_id)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handler with correlation ID filter
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
