"""
API Key Model

Defines the APIKey table for programmatic API access.
"""

import uuid
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and its hash.

    Returns:
        tuple: (plain_key, hashed_key)
        - plain_key: The key to show to the user (only shown once)
        - hashed_key: The hash to store in the database
    """
    # Generate a secure random key with prefix for identification
    # Format: ac_live_xxxx or ac_test_xxxx (32 random chars)
    random_part = secrets.token_urlsafe(24)  # 32 chars
    plain_key = f"ac_live_{random_part}"

    # Hash the key for storage (we never store plain keys)
    hashed_key = hash_api_key(plain_key)

    return plain_key, hashed_key


def hash_api_key(plain_key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(plain_key.encode()).hexdigest()


class APIKey(Base):
    """API Key model for programmatic access."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Key identification (prefix shown to user, e.g., "ac_live_abc...xyz")
    key_prefix = Column(String(16), nullable=False)  # First 12 chars of key
    key_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 hash

    # Metadata
    name = Column(String(255), nullable=False)  # User-provided name
    description = Column(Text, nullable=True)

    # Permissions & Scopes
    scopes = Column(Text, nullable=True)  # JSON array of allowed scopes

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(String(20), default="0")  # Track API calls

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # None = never expires

    # Timestamps
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    user = relationship("User", backref="api_keys")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... ({self.name})>"

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    @classmethod
    def create_key(
        cls,
        user_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        scopes: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple["APIKey", str]:
        """
        Create a new API key for a user.

        Returns:
            tuple: (APIKey instance, plain_key)
            The plain_key should be shown to the user only once.
        """
        plain_key, hashed_key = generate_api_key()

        api_key = cls(
            user_id=user_id,
            key_prefix=plain_key[:12],  # Store prefix for identification
            key_hash=hashed_key,
            name=name,
            description=description,
            scopes=scopes,
            expires_at=expires_at,
        )

        return api_key, plain_key

    def record_usage(self) -> None:
        """Record that this API key was used."""
        self.last_used_at = utc_now()
        try:
            self.usage_count = str(int(self.usage_count or "0") + 1)
        except ValueError:
            self.usage_count = "1"
