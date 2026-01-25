"""
API Routers

FastAPI router modules for API endpoints.
"""

from app.routers.scans import router as scans_router

__all__ = ["scans_router"]
