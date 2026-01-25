"""
AccessibilityChecker API - Main Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers.scans import router as scans_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 Starting AccessibilityChecker API...")
    init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down AccessibilityChecker API...")


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

# CORS Configuration
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.app_env,
    }


# Include routers
app.include_router(scans_router, prefix="/api/v1/scans", tags=["Scans"])


# TODO: Add additional routers
# from app.routers import auth, reports, users, billing
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
# app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
# app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
# app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
