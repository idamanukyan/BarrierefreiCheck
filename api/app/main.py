"""
AccessibilityChecker API - Main Application Entry Point
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
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
from app.services.rate_limiter import limiter, rate_limit_exceeded_handler
from app.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
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
    setup_logging_with_correlation_id(level=log_level)
    logger.info("Starting AccessibilityChecker API...")
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
    version="0.1.0",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation ID middleware for request tracing
app.add_middleware(CorrelationIdMiddleware)

# Security headers middleware
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=settings.app_env == "production",
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "AccessibilityChecker API",
        "version": "0.1.0",
        "description": "BFSG Compliance & WCAG 2.1 Testing Platform",
        "docs": "/api/docs",
    }


# Health check
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    from app.middleware.correlation_id import get_correlation_id
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.app_env,
        "correlation_id": get_correlation_id(),
    }


# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(scans_router, prefix="/api/v1/scans", tags=["Scans"])
app.include_router(reports_router, prefix="/api/v1", tags=["Reports"])
app.include_router(billing_router, prefix="/api/v1", tags=["Billing"])
