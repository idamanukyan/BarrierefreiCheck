"""
Domain Model

Defines the Domain table for managing user's monitored domains.
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Float, Integer
from sqlalchemy import Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def extract_domain(url: str) -> str:
    """
    Extract and normalize domain from URL.

    Removes www. prefix and converts to lowercase.

    Examples:
        https://www.example.com/page -> example.com
        http://example.com -> example.com
        example.com -> example.com
    """
    # Add scheme if missing
    if "://" not in url:
        url = f"https://{url}"

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]

    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]

    # Remove port if present
    if ":" in domain:
        domain = domain.split(":")[0]

    return domain.lower().strip()


class DomainStatus(enum.Enum):
    """Domain verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


class Domain(Base):
    """
    Domain model for managing user's monitored domains.

    Agencies can manage multiple domains within their plan limits.
    Each domain tracks scan statistics and can be used for filtering.
    """

    __tablename__ = "domains"

    __table_args__ = (
        Index('ix_domains_user_domain', 'user_id', 'domain', unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Domain information (normalized, e.g., "example.com")
    domain = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Verification status (for future domain ownership verification)
    status = Column(SQLEnum(DomainStatus), default=DomainStatus.PENDING, nullable=False)
    verification_token = Column(String(64), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Aggregated statistics (denormalized for quick dashboard access)
    total_scans = Column(Integer, default=0)
    last_scan_at = Column(DateTime, nullable=True)
    last_score = Column(Float, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", backref="domains")

    def __repr__(self):
        return f"<Domain {self.domain}>"

    @classmethod
    def normalize_domain(cls, url_or_domain: str) -> str:
        """Normalize a URL or domain string to canonical domain format."""
        return extract_domain(url_or_domain)

    @classmethod
    def create_domain(
        cls,
        user_id: uuid.UUID,
        domain: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "Domain":
        """
        Create a new domain for a user.

        Args:
            user_id: The user's UUID
            domain: URL or domain string (will be normalized)
            display_name: Optional friendly name
            description: Optional description

        Returns:
            Domain instance (not yet committed to DB)
        """
        normalized = extract_domain(domain)

        return cls(
            user_id=user_id,
            domain=normalized,
            display_name=display_name,
            description=description,
        )
