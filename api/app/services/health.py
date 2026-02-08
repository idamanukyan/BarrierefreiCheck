"""
Health Check Service

Provides deep health checks for all system dependencies.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.config import settings

logger = logging.getLogger(__name__)


async def check_database() -> Dict[str, Any]:
    """Check database connectivity and response time."""
    start = datetime.now(timezone.utc)
    try:
        db = SessionLocal()
        try:
            # Execute a simple query to verify connection
            result = db.execute(text("SELECT 1"))
            result.fetchone()
            latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
            }
        finally:
            db.close()
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        return {
            "status": "unhealthy",
            "error": "Connection failed",
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity and response time."""
    start = datetime.now(timezone.utc)
    try:
        import redis
        r = redis.from_url(
            settings.redis_url,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        r.ping()
        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        # Get some stats
        info = r.info("memory")
        used_memory_mb = info.get("used_memory", 0) / (1024 * 1024)

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "used_memory_mb": round(used_memory_mb, 2),
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_minio() -> Dict[str, Any]:
    """Check MinIO/S3 connectivity."""
    start = datetime.now(timezone.utc)
    try:
        import httpx

        # Simple HEAD request to MinIO health endpoint
        endpoint = settings.s3_endpoint.rstrip("/")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{endpoint}/minio/health/live")

        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        if response.status_code == 200:
            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
            }
        else:
            return {
                "status": "degraded",
                "http_status": response.status_code,
                "latency_ms": round(latency_ms, 2),
            }
    except Exception as e:
        logger.error(f"MinIO health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health status.

    Returns health status for all dependencies:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Storage (MinIO)
    """
    from app.middleware.correlation_id import get_correlation_id

    # Run all health checks concurrently
    import asyncio
    db_check, redis_check, minio_check = await asyncio.gather(
        check_database(),
        check_redis(),
        check_minio(),
        return_exceptions=True,
    )

    # Handle any exceptions from gather
    if isinstance(db_check, Exception):
        db_check = {"status": "unhealthy", "error": str(db_check)}
    if isinstance(redis_check, Exception):
        redis_check = {"status": "unhealthy", "error": str(redis_check)}
    if isinstance(minio_check, Exception):
        minio_check = {"status": "unhealthy", "error": str(minio_check)}

    # Determine overall status
    statuses = [
        db_check.get("status", "unhealthy"),
        redis_check.get("status", "unhealthy"),
        minio_check.get("status", "unhealthy"),
    ]

    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": "0.1.0",
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": get_correlation_id(),
        "checks": {
            "database": db_check,
            "redis": redis_check,
            "storage": minio_check,
        },
    }


async def get_simple_health() -> Dict[str, Any]:
    """
    Get simple health status (for load balancer probes).

    Only checks if the application is running, not dependencies.
    """
    from app.middleware.correlation_id import get_correlation_id

    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.app_env,
        "correlation_id": get_correlation_id(),
    }
