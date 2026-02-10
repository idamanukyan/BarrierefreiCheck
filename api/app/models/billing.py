"""
Billing Models

Models for subscriptions, payments, and usage tracking.
"""

import uuid
from datetime import datetime, timezone


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.user import PlanType
import enum


class SubscriptionStatus(enum.Enum):
    """Subscription status types."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"


class PaymentStatus(enum.Enum):
    """Payment status types."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class ReportFormat(enum.Enum):
    """Report format types."""
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"


class Subscription(Base):
    """Subscription model for user plans."""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Plan info
    plan = Column(SQLEnum(PlanType), default=PlanType.FREE, nullable=False)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)

    # Stripe integration
    stripe_customer_id = Column(String(100), nullable=True, unique=True)
    stripe_subscription_id = Column(String(100), nullable=True, unique=True)
    stripe_price_id = Column(String(100), nullable=True)

    # Billing period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    canceled_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subscription {self.id} - {self.plan.value}>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]

    def get_limits(self) -> dict:
        """Get plan limits."""
        limits = {
            PlanType.FREE: {
                "scans_per_month": 5,
                "pages_per_scan": 1,
                "reports": False,
                "api_access": False,
                "white_label": False,
                "priority_support": False,
            },
            PlanType.STARTER: {
                "scans_per_month": 50,
                "pages_per_scan": 25,
                "reports": True,
                "api_access": False,
                "white_label": False,
                "priority_support": False,
            },
            PlanType.PROFESSIONAL: {
                "scans_per_month": -1,  # Unlimited
                "pages_per_scan": 100,
                "reports": True,
                "api_access": True,
                "white_label": True,
                "priority_support": True,
            },
            PlanType.AGENCY: {
                "scans_per_month": -1,  # Unlimited
                "pages_per_scan": 1000,
                "reports": True,
                "api_access": True,
                "white_label": True,
                "priority_support": True,
            },
            PlanType.ENTERPRISE: {
                "scans_per_month": -1,  # Unlimited
                "pages_per_scan": 5000,
                "reports": True,
                "api_access": True,
                "white_label": True,
                "priority_support": True,
            },
        }
        return limits.get(self.plan, limits[PlanType.FREE])


class Payment(Base):
    """Payment model for tracking transactions."""

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False, index=True)

    # Payment details
    amount = Column(Integer, nullable=False)  # Amount in cents
    currency = Column(String(3), default="EUR", nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Stripe integration
    stripe_payment_intent_id = Column(String(100), nullable=True, unique=True)
    stripe_invoice_id = Column(String(100), nullable=True)

    # Invoice details
    invoice_number = Column(String(50), nullable=True)
    invoice_pdf_url = Column(String(512), nullable=True)

    # Description
    description = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    paid_at = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id} - {self.amount/100:.2f} EUR>"

    @property
    def amount_formatted(self) -> str:
        """Get formatted amount."""
        return f"{self.amount / 100:.2f} {self.currency}"


class UsageRecord(Base):
    """Usage tracking for metered billing."""

    __tablename__ = "usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Usage tracking
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Counts
    scans_count = Column(Integer, default=0)
    pages_scanned = Column(Integer, default=0)
    reports_generated = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    def __repr__(self):
        return f"<UsageRecord {self.user_id} - {self.period_start}>"


class Report(Base):
    """Report model for generated accessibility reports."""

    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Report config
    format = Column(SQLEnum(ReportFormat), nullable=False)
    language = Column(String(2), default="de", nullable=False)
    include_screenshots = Column(Boolean, default=True)

    # Status
    status = Column(String(20), default="generating", nullable=False)  # generating, completed, failed
    error = Column(Text, nullable=True)

    # File info
    file_content = Column(Text, nullable=True)  # For small reports; for large files use storage
    file_path = Column(String(512), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    scan = relationship("Scan", backref="reports")
    user = relationship("User", backref="reports")

    def __repr__(self):
        return f"<Report {self.id} - {self.format.value}>"
