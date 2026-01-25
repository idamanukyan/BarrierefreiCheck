"""
AccessibilityChecker API - Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AccessibilityChecker API",
    description="BFSG Compliance & WCAG 2.1 Testing Platform API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "name": "AccessibilityChecker API",
        "version": "0.1.0",
        "status": "healthy",
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
    }


# TODO: Include routers
# from app.routers import auth, scans, reports, users, billing
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
# app.include_router(scans.router, prefix="/api/v1/scans", tags=["Scans"])
# app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
# app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
# app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
