"""
Field Encryption Service

Provides encryption and decryption for sensitive PII fields in the database.
Uses Fernet symmetric encryption from the cryptography library.

IMPORTANT: The encryption key must be kept secret and backed up securely.
Losing the key means losing access to all encrypted data.
"""

import base64
import hashlib
import logging
import os
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""
    pass


class FieldEncryption:
    """
    Handles encryption and decryption of sensitive database fields.

    Uses Fernet symmetric encryption which provides:
    - AES 128-bit encryption in CBC mode
    - HMAC using SHA256 for authentication
    - Automatic handling of IV (initialization vector)

    The encryption key is derived from the JWT secret to avoid
    managing another secret, but a dedicated key is recommended
    for production deployments.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryption service.

        Args:
            encryption_key: Base64-encoded 32-byte key, or None to derive from JWT secret
        """
        self._fernet: Optional[Fernet] = None
        self._key = encryption_key

    def _get_fernet(self) -> Fernet:
        """Get or create the Fernet instance."""
        if self._fernet is None:
            key = self._derive_key()
            self._fernet = Fernet(key)
        return self._fernet

    def _derive_key(self) -> bytes:
        """
        Derive a Fernet-compatible key.

        If FIELD_ENCRYPTION_KEY is set, use it directly.
        Otherwise, derive from JWT_SECRET using SHA256.
        """
        # Check for dedicated encryption key first
        encryption_key = self._key or getattr(settings, 'field_encryption_key', None)

        if encryption_key:
            # If a dedicated key is provided, it should be a valid Fernet key
            try:
                # Validate it's a proper Fernet key
                Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
                return encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            except Exception:
                logger.warning("Invalid FIELD_ENCRYPTION_KEY format, deriving from JWT_SECRET")

        # Derive key from JWT secret
        # Use SHA256 to get 32 bytes, then base64 encode for Fernet
        jwt_secret = settings.jwt_secret
        if not jwt_secret:
            raise EncryptionError("No encryption key available. Set JWT_SECRET or FIELD_ENCRYPTION_KEY.")

        # Create a deterministic 32-byte key from the JWT secret
        key_bytes = hashlib.sha256(jwt_secret.encode()).digest()
        return base64.urlsafe_b64encode(key_bytes)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string prefixed with 'enc:'

        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            return plaintext

        # Don't re-encrypt already encrypted values
        if plaintext.startswith("enc:"):
            return plaintext

        try:
            fernet = self._get_fernet()
            encrypted = fernet.encrypt(plaintext.encode('utf-8'))
            # Prefix with 'enc:' to identify encrypted values
            return f"enc:{encrypted.decode('utf-8')}"
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt value: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: The encrypted string (with 'enc:' prefix)

        Returns:
            Decrypted plaintext string

        Raises:
            EncryptionError: If decryption fails
        """
        if not ciphertext:
            return ciphertext

        # Only decrypt values that were encrypted (have 'enc:' prefix)
        if not ciphertext.startswith("enc:"):
            return ciphertext

        try:
            fernet = self._get_fernet()
            # Remove the 'enc:' prefix
            encrypted_data = ciphertext[4:].encode('utf-8')
            decrypted = fernet.decrypt(encrypted_data)
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("Decryption failed: Invalid token (wrong key or corrupted data)")
            raise EncryptionError("Failed to decrypt value: Invalid token")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt value: {e}")

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted."""
        return value is not None and value.startswith("enc:")


# Singleton instance
_encryption_instance: Optional[FieldEncryption] = None


def get_field_encryption() -> FieldEncryption:
    """Get the singleton encryption instance."""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = FieldEncryption()
    return _encryption_instance


def encrypt_field(value: Optional[str]) -> Optional[str]:
    """
    Encrypt a field value.

    Convenience function for encrypting individual values.

    Args:
        value: The plaintext value to encrypt

    Returns:
        Encrypted value with 'enc:' prefix, or None if input is None
    """
    if value is None:
        return None
    return get_field_encryption().encrypt(value)


def decrypt_field(value: Optional[str]) -> Optional[str]:
    """
    Decrypt a field value.

    Convenience function for decrypting individual values.

    Args:
        value: The encrypted value (with 'enc:' prefix)

    Returns:
        Decrypted plaintext value, or None if input is None
    """
    if value is None:
        return None
    return get_field_encryption().decrypt(value)


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Use this to generate a key for the FIELD_ENCRYPTION_KEY setting.

    Returns:
        Base64-encoded 32-byte key suitable for Fernet
    """
    return Fernet.generate_key().decode('utf-8')
