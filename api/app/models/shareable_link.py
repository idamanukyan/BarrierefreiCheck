"""
Shareable Report Link Model

Defines the ShareableReportLink table for public report sharing with expiry.
"""

import uuid
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def generate_share_token() -> tuple[str, str]:
    """
    Generate a new share token and its hash.

    Returns:
        tuple: (plain_token, hashed_token)
        - plain_token: The token to share (shown only once when creating)
        - hashed_token: The hash to store in the database
    """
    # Generate a secure random token with prefix for identification
    # Format: sr_xxxx (24 random chars = 32 URL-safe chars)
    random_part = secrets.token_urlsafe(24)
    plain_token = f"sr_{random_part}"

    # Hash the token for storage (we never store plain tokens)
    hashed_token = hash_share_token(plain_token)

    return plain_token, hashed_token


def hash_share_token(plain_token: str) -> str:
    """Hash a share token for secure storage."""
    return hashlib.sha256(plain_token.encode()).hexdigest()


class ShareableReportLink(Base):
    """
    Shareable Report Link model for public report access.

    Allows users to share reports with external stakeholders (clients,
    developers, etc.) without requiring them to log in. Links have
    configurable expiration dates and track access statistics.
    """

    __tablename__ = "shareable_report_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Token identification (prefix shown to user, hash stored for lookup)
    token_prefix = Column(String(16), nullable=False)  # First 12 chars of token
    token_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 hash

    # Metadata
    name = Column(String(100), nullable=True)  # Optional friendly name (e.g., "Client Review")

    # Access control
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)  # Required expiration

    # Statistics
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    report = relationship("Report", backref="share_links")
    user = relationship("User", backref="share_links")

    def __repr__(self):
        return f"<ShareableReportLink {self.token_prefix}...>"

    @property
    def is_expired(self) -> bool:
        """Check if the share link has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the share link is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    @classmethod
    def create_link(
        cls,
        report_id: uuid.UUID,
        user_id: uuid.UUID,
        expires_at: datetime,
        name: Optional[str] = None,
    ) -> tuple["ShareableReportLink", str]:
        """
        Create a new shareable link for a report.

        Args:
            report_id: The report's UUID
            user_id: The owner's UUID
            expires_at: When the link expires
            name: Optional friendly name

        Returns:
            tuple: (ShareableReportLink instance, plain_token)
            The plain_token should be shown to the user only once.
        """
        plain_token, hashed_token = generate_share_token()

        link = cls(
            report_id=report_id,
            user_id=user_id,
            token_prefix=plain_token[:12],  # Store prefix for identification
            token_hash=hashed_token,
            name=name,
            expires_at=expires_at,
        )

        return link, plain_token

    def record_access(self) -> None:
        """Record that this share link was accessed."""
        self.last_accessed_at = utc_now()
        self.access_count = (self.access_count or 0) + 1

    def revoke(self) -> None:
        """Revoke this share link (soft delete)."""
        self.is_active = False
