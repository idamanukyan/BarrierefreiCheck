"""
User Model

Defines the User table for authentication and user management.

PII Protection:
- full_name and company fields are encrypted at rest
- email is stored in plaintext for lookups but email_hash provides a searchable hash
- All PII is subject to GDPR data retention policies
"""

import hashlib
import uuid
from datetime import datetime, timezone


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.encrypted_type import EncryptedString
import enum


class PlanType(enum.Enum):
    """Subscription plan types."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    AGENCY = "agency"
    ENTERPRISE = "enterprise"


class User(Base):
    """
    User model for authentication and account management.

    PII Fields (encrypted at rest):
    - full_name: User's full name (encrypted)
    - company: Company/organization name (encrypted)

    Note: email is not encrypted to allow for efficient lookups,
    but it's protected through access controls and audit logging.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # PII fields - encrypted at rest
    # Using EncryptedString(512) to accommodate encryption overhead
    full_name = Column(EncryptedString(512), nullable=True)
    company = Column(EncryptedString(512), nullable=True)

    # Subscription
    plan = Column(SQLEnum(PlanType), default=PlanType.FREE, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User {self.email}>"

    @property
    def plan_limits(self) -> dict:
        """Get limits for the user's plan."""
        limits = {
            PlanType.FREE: {
                "pages_per_scan": 5,
                "domains": 1,
                "scans_per_month": 3,
                "history_days": 7,
            },
            PlanType.STARTER: {
                "pages_per_scan": 100,
                "domains": 1,
                "scans_per_month": 20,
                "history_days": 30,
            },
            PlanType.PROFESSIONAL: {
                "pages_per_scan": 500,
                "domains": 3,
                "scans_per_month": -1,  # Unlimited
                "history_days": 365,
            },
            PlanType.AGENCY: {
                "pages_per_scan": 1000,
                "domains": 10,
                "scans_per_month": -1,
                "history_days": -1,  # Unlimited
            },
            PlanType.ENTERPRISE: {
                "pages_per_scan": 5000,
                "domains": -1,
                "scans_per_month": -1,
                "history_days": -1,
            },
        }
        return limits.get(self.plan, limits[PlanType.FREE])
