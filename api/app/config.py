"""
Application Configuration

Manages environment variables and application settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "AccessibilityChecker"
    app_env: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql://accesscheck:accesscheck_dev@localhost:5432/accessibilitychecker"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT Authentication
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # S3/MinIO
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_screenshots: str = "screenshots"
    s3_bucket_reports: str = "reports"

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Scan Settings
    max_concurrent_scans: int = 10
    scan_timeout_seconds: int = 300
    default_crawl_limit: int = 100
    max_crawl_limit: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
