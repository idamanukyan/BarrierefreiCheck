"""
Custom Exceptions and Error Handling

Provides structured error responses for the API.
"""

import logging
from typing import Any, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from app.middleware.correlation_id import get_correlation_id

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error: str
    message: str
    details: Optional[Any] = None
    correlation_id: Optional[str] = None


class AppException(HTTPException):
    """Base application exception with structured response."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: Optional[Any] = None,
    ):
        self.error = error
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail=message)


# Specific exception types
class BadRequestError(AppException):
    """400 Bad Request - Invalid input."""

    def __init__(self, message: str = "Bad request", details: Optional[Any] = None):
        super().__init__(HTTP_400_BAD_REQUEST, "bad_request", message, details)


class UnauthorizedError(AppException):
    """401 Unauthorized - Authentication required."""

    def __init__(self, message: str = "Authentication required", details: Optional[Any] = None):
        super().__init__(HTTP_401_UNAUTHORIZED, "unauthorized", message, details)


class ForbiddenError(AppException):
    """403 Forbidden - Insufficient permissions."""

    def __init__(self, message: str = "Access denied", details: Optional[Any] = None):
        super().__init__(HTTP_403_FORBIDDEN, "forbidden", message, details)


class NotFoundError(AppException):
    """404 Not Found - Resource not found."""

    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(HTTP_404_NOT_FOUND, "not_found", message, details)


class ConflictError(AppException):
    """409 Conflict - Resource conflict."""

    def __init__(self, message: str = "Resource conflict", details: Optional[Any] = None):
        super().__init__(HTTP_409_CONFLICT, "conflict", message, details)


class ValidationError(AppException):
    """422 Unprocessable Entity - Validation failed."""

    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", message, details)


class RateLimitError(AppException):
    """429 Too Many Requests - Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Any] = None):
        super().__init__(HTTP_429_TOO_MANY_REQUESTS, "rate_limit_exceeded", message, details)


class InternalError(AppException):
    """500 Internal Server Error - Unexpected error."""

    def __init__(self, message: str = "Internal server error", details: Optional[Any] = None):
        super().__init__(HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", message, details)


class ServiceUnavailableError(AppException):
    """503 Service Unavailable - External service down."""

    def __init__(self, message: str = "Service temporarily unavailable", details: Optional[Any] = None):
        super().__init__(HTTP_503_SERVICE_UNAVAILABLE, "service_unavailable", message, details)


class PlanLimitError(AppException):
    """403 Forbidden - Plan limit exceeded."""

    def __init__(self, message: str = "Plan limit exceeded", details: Optional[Any] = None):
        super().__init__(HTTP_403_FORBIDDEN, "plan_limit_exceeded", message, details)


# Exception handlers
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler for application exceptions."""
    correlation_id = get_correlation_id()

    logger.warning(
        f"Application error: {exc.error} - {exc.message}",
        extra={"details": exc.details, "status_code": exc.status_code}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.error,
            message=exc.message,
            details=exc.details,
            correlation_id=correlation_id,
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for generic HTTP exceptions."""
    correlation_id = get_correlation_id()

    logger.warning(f"HTTP error: {exc.status_code} - {exc.detail}")

    # Map status codes to error types
    error_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
        503: "service_unavailable",
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=error_map.get(exc.status_code, "error"),
            message=str(exc.detail),
            correlation_id=correlation_id,
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions."""
    correlation_id = get_correlation_id()

    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_error",
            message="An unexpected error occurred. Please try again later.",
            correlation_id=correlation_id,
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for Pydantic validation errors."""
    from pydantic import ValidationError as PydanticValidationError

    correlation_id = get_correlation_id()

    if isinstance(exc, PydanticValidationError):
        errors = exc.errors()
    else:
        # FastAPI's RequestValidationError
        errors = exc.errors() if hasattr(exc, "errors") else str(exc)

    logger.warning(f"Validation error: {errors}")

    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message="Request validation failed",
            details=errors,
            correlation_id=correlation_id,
        ).model_dump(),
    )
