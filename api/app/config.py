"""
Application Configuration

Manages environment variables and application settings.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
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
    # SECURITY: jwt_secret MUST be set via environment variable in production
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # S3/MinIO
    # SECURITY: s3_access_key and s3_secret_key MUST be set via environment variables
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_screenshots: str = "screenshots"
    s3_bucket_reports: str = "reports"

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # Email/SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "noreply@barrierefrei-check.de"
    FROM_NAME: str = "BarrierefreiCheck"

    # Scan Settings
    max_concurrent_scans: int = 10
    scan_timeout_seconds: int = 300
    default_crawl_limit: int = 100
    max_crawl_limit: int = 1000

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        if not v or v == "":
            # In development, generate a warning but allow startup
            import warnings
            warnings.warn(
                "JWT_SECRET is not set! This is a critical security risk. "
                "Set JWT_SECRET environment variable before deploying to production.",
                UserWarning,
            )
            # Return a random secret for development only
            import secrets
            return secrets.token_urlsafe(32)
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
