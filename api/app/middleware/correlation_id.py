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


def setup_logging_with_correlation_id(
    level: int = logging.INFO,
    json_format: bool = False,
) -> None:
    """
    Configure logging to include correlation IDs.

    Args:
        level: Logging level (default INFO)
        json_format: If True, output logs in JSON format (for production)

    Call this during application startup.
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.addFilter(CorrelationIdFilter())

    if json_format:
        # Use JSON formatter for production (structured logging)
        try:
            from pythonjsonlogger import jsonlogger

            class CustomJsonFormatter(jsonlogger.JsonFormatter):
                """Custom JSON formatter with additional fields."""

                def add_fields(self, log_record, record, message_dict):
                    super().add_fields(log_record, record, message_dict)
                    log_record['timestamp'] = record.created
                    log_record['level'] = record.levelname
                    log_record['logger'] = record.name
                    log_record['correlation_id'] = getattr(record, 'correlation_id', None)
                    # Remove redundant fields
                    log_record.pop('levelname', None)
                    log_record.pop('name', None)

            formatter = CustomJsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s',
                json_ensure_ascii=False,
            )
        except ImportError:
            # Fallback to text format if python-json-logger not installed
            logger.warning("python-json-logger not installed, using text format")
            formatter = logging.Formatter(
                "%(asctime)s [%(correlation_id)s] %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
    else:
        # Text format for development (human-readable)
        formatter = logging.Formatter(
            "%(asctime)s [%(correlation_id)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
