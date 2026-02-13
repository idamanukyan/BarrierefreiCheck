"""
AccessibilityChecker API - Main Application Entry Point
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

# Version from environment (set during Docker build) or default
__version__ = os.getenv("APP_VERSION", "0.1.0")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db
from app.routers.scans import router as scans_router
from app.routers.reports import router as reports_router
from app.routers.billing import router as billing_router
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.websocket import router as websocket_router
from app.routers.export import router as export_router
from app.services.rate_limiter import limiter, rate_limit_exceeded_handler
from app.services.metrics import MetricsMiddleware, get_metrics
from app.middleware import (
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
    APIVersionMiddleware,
    RequestSizeLimitMiddleware,
)
from app.middleware.correlation_id import setup_logging_with_correlation_id
from app.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)

logger = logging.getLogger(__name__)

# Maximum request body size (10 MB)
MAX_REQUEST_SIZE = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    log_level = logging.DEBUG if settings.debug else logging.INFO
    use_json_logging = settings.app_env == "production"
    setup_logging_with_correlation_id(level=log_level, json_format=use_json_logging)
    logger.info("Starting AccessibilityChecker API...", extra={
        "environment": settings.app_env,
        "debug": settings.debug,
        "json_logging": use_json_logging,
    })
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down AccessibilityChecker API...")


app = FastAPI(
    title="AccessibilityChecker API",
    description="""
## BFSG Compliance & WCAG 2.1 Testing Platform API

AccessibilityChecker helps German businesses and web agencies test their websites
for BFSG/WCAG 2.1 compliance.

### Features
- **Scan websites** for accessibility issues
- **German translations** for all error messages
- **BFSG mapping** to legal requirements
- **PDF reports** for documentation

### BFSG Deadline
⚠️ All German e-commerce websites must be accessible by **June 28, 2025**.
    """,
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter

# Exception handlers for structured error responses
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS Configuration
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

# Warn if using wildcard or localhost in production
if settings.app_env == "production":
    import logging
    _logger = logging.getLogger(__name__)
    if "*" in cors_origins:
        _logger.warning("CORS configured with wildcard (*) in production - this is insecure!")
    if any("localhost" in origin or "127.0.0.1" in origin for origin in cors_origins):
        _logger.warning("CORS includes localhost in production - this may be unintended")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    # Restrict to only methods actually used by the API
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    # Explicitly list allowed headers instead of wildcard
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Correlation-ID",
    ],
    # Expose headers that frontend may need to read
    expose_headers=[
        "X-Correlation-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)

# Correlation ID middleware for request tracing
app.add_middleware(CorrelationIdMiddleware)

# Security headers middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=settings.app_env == "production",
)

# Metrics middleware for Prometheus
app.add_middleware(MetricsMiddleware)

# API versioning middleware
app.add_middleware(
    APIVersionMiddleware,
    current_version="1",
    deprecated_versions={},  # Add versions here when deprecating, e.g., {"1": "2026-12-31"}
)

# Request size limit middleware (10MB max)
app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=MAX_REQUEST_SIZE)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "AccessibilityChecker API",
        "version": __version__,
        "description": "BFSG Compliance & WCAG 2.1 Testing Platform",
        "docs": "/api/docs",
    }


# Health check endpoints
@app.get("/api/v1/health")
async def health_check():
    """
    Simple health check endpoint.

    Used for load balancer probes. Only checks if the app is running.
    For detailed health status, use /api/v1/health/deep
    """
    from app.services.health import get_simple_health
    return await get_simple_health()


@app.get("/api/v1/health/deep")
async def health_check_deep():
    """
    Deep health check endpoint.

    Checks connectivity to all dependencies:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Storage (MinIO)

    Returns detailed status and latency information.
    """
    from app.services.health import get_system_health
    from fastapi.responses import JSONResponse

    health = await get_system_health()

    # Return 503 if system is unhealthy
    status_code = 200 if health["status"] != "unhealthy" else 503

    return JSONResponse(content=health, status_code=status_code)


# Prometheus metrics endpoint
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics()


# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(scans_router, prefix="/api/v1/scans", tags=["Scans"])
app.include_router(reports_router, prefix="/api/v1", tags=["Reports"])
app.include_router(billing_router, prefix="/api/v1", tags=["Billing"])
app.include_router(export_router, prefix="/api/v1", tags=["Export"])
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])
