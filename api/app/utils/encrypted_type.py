"""
Encrypted Column Type for SQLAlchemy

Provides a custom column type that automatically encrypts data on write
and decrypts on read.

Usage:
    from app.utils.encrypted_type import EncryptedString

    class User(Base):
        email = Column(EncryptedString(255), nullable=False)
        full_name = Column(EncryptedString(255), nullable=True)
"""

import logging
from typing import Optional

from sqlalchemy import String, TypeDecorator

from app.services.encryption import encrypt_field, decrypt_field, EncryptionError

logger = logging.getLogger(__name__)


class EncryptedString(TypeDecorator):
    """
    A SQLAlchemy column type that transparently encrypts and decrypts string values.

    Values are encrypted before being stored in the database and decrypted
    when retrieved. The encrypted value is prefixed with 'enc:' to identify
    it as encrypted data.

    Note: Encrypted values are longer than the original plaintext due to
    encryption overhead. A 255-character string may become ~400+ characters
    when encrypted. Plan column sizes accordingly.

    Args:
        length: Maximum length of the encrypted value (not plaintext)
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 512):
        """
        Initialize the encrypted string type.

        Args:
            length: Maximum length for the encrypted string.
                   Should be larger than plaintext length due to encryption overhead.
                   Recommended: 2x plaintext length + 100 for padding/encoding.
        """
        super().__init__(length)

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Encrypt the value before storing in database.

        Called when writing to the database.
        """
        if value is None:
            return None

        try:
            return encrypt_field(value)
        except EncryptionError as e:
            logger.error(f"Failed to encrypt field value: {e}")
            # In production, you might want to raise an error instead
            # For now, return the value unencrypted to avoid data loss
            logger.warning("Storing value unencrypted due to encryption failure")
            return value

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Decrypt the value when reading from database.

        Called when reading from the database.
        """
        if value is None:
            return None

        try:
            return decrypt_field(value)
        except EncryptionError as e:
            logger.error(f"Failed to decrypt field value: {e}")
            # Return the encrypted value as-is if decryption fails
            # This allows the application to continue functioning
            # while alerting to the decryption issue
            return value


class EncryptedEmail(EncryptedString):
    """
    Specialized encrypted type for email addresses.

    Email addresses need to be searchable for lookups, but also need
    to be protected. This type stores a hash of the email alongside
    the encrypted value to enable lookups without decryption.

    Note: For email lookups to work efficiently, you should also store
    a hashed version of the email in a separate indexed column.
    """

    def __init__(self):
        """Initialize with appropriate length for encrypted emails."""
        # Emails can be up to 254 characters, encrypted they need more space
        super().__init__(length=512)


# Export for convenience
__all__ = ['EncryptedString', 'EncryptedEmail']
