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

    # Field Encryption
    # SECURITY: If set, used for encrypting PII fields in the database
    # Must be a valid Fernet key (32 bytes, base64-encoded)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # If not set, encryption key is derived from JWT_SECRET
    field_encryption_key: Optional[str] = None

    # S3/MinIO
    # SECURITY: s3_access_key and s3_secret_key MUST be set via environment variables
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_screenshots: str = "screenshots"
    s3_bucket_reports: str = "reports"

    @field_validator("s3_access_key")
    @classmethod
    def validate_s3_access_key(cls, v: str, info) -> str:
        import os

        app_env = os.getenv("APP_ENV", "development").lower()
        is_production = app_env in ("production", "prod", "staging")

        if is_production and not v:
            raise ValueError(
                "S3_ACCESS_KEY must be set in production! "
                "Set the S3_ACCESS_KEY environment variable."
            )
        return v

    @field_validator("s3_secret_key")
    @classmethod
    def validate_s3_secret_key(cls, v: str, info) -> str:
        import os

        app_env = os.getenv("APP_ENV", "development").lower()
        is_production = app_env in ("production", "prod", "staging")

        if is_production and not v:
            raise ValueError(
                "S3_SECRET_KEY must be set in production! "
                "Set the S3_SECRET_KEY environment variable."
            )
        return v

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_publishable_key: Optional[str] = None

    @field_validator("stripe_webhook_secret")
    @classmethod
    def validate_stripe_webhook_secret(cls, v: Optional[str], info) -> Optional[str]:
        import os

        app_env = os.getenv("APP_ENV", "development").lower()
        is_production = app_env in ("production", "prod", "staging")
        stripe_key = os.getenv("STRIPE_SECRET_KEY")

        # Only require webhook secret if Stripe is configured
        if is_production and stripe_key and not v:
            import warnings
            warnings.warn(
                "STRIPE_WEBHOOK_SECRET is not set but STRIPE_SECRET_KEY is configured. "
                "Webhook signature verification will fail.",
                UserWarning,
            )
        return v

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Trusted Proxies (CIDR notation, comma-separated)
    # Only trust X-Forwarded-For from these networks
    # Example: "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    trusted_proxies: str = ""

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # Email/SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "noreply@barrierefrei-check.de"
    FROM_NAME: str = "BarrierefreiCheck"
    EMAIL_ENABLED: bool = True  # Set to False to disable email sending

    @field_validator("SMTP_USER")
    @classmethod
    def validate_smtp_config(cls, v: Optional[str], info) -> Optional[str]:
        import os

        app_env = os.getenv("APP_ENV", "development").lower()
        is_production = app_env in ("production", "prod", "staging")
        email_enabled = os.getenv("EMAIL_ENABLED", "true").lower() == "true"

        if is_production and email_enabled:
            smtp_host = os.getenv("SMTP_HOST", "localhost")
            # Warn if using localhost SMTP in production with email enabled
            if smtp_host == "localhost" and not v:
                import warnings
                warnings.warn(
                    "SMTP is configured with localhost in production. "
                    "Set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD for production email, "
                    "or set EMAIL_ENABLED=false to disable email sending.",
                    UserWarning,
                )
        return v

    # Scan Settings
    max_concurrent_scans: int = 10
    scan_timeout_seconds: int = 300
    default_crawl_limit: int = 100
    max_crawl_limit: int = 1000

    # GDPR Data Retention Settings
    # Default: 730 days (2 years) for German commercial records (HGB § 257)
    data_retention_days: int = 730

    # WebSocket Settings
    ws_ping_interval_seconds: int = 30  # Send ping every 30 seconds
    ws_max_connection_duration_seconds: int = 86400  # Max 24 hours per connection
    ws_idle_timeout_seconds: int = 300  # Disconnect after 5 minutes of inactivity

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        import os

        app_env = os.getenv("APP_ENV", "development").lower()
        is_production = app_env in ("production", "prod", "staging")

        if not v or v == "":
            if is_production:
                raise ValueError(
                    "JWT_SECRET must be set in production! "
                    "Set the JWT_SECRET environment variable with a secure, random value "
                    "of at least 32 characters."
                )
            # In development only, generate a random secret with a warning
            import warnings
            import secrets
            warnings.warn(
                "JWT_SECRET is not set! Generating a random secret for development. "
                "This means sessions will be invalidated on restart. "
                "Set JWT_SECRET environment variable to persist sessions.",
                UserWarning,
            )
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
