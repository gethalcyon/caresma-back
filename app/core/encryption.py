"""
Encryption utilities for securing sensitive data at rest.
Uses Fernet symmetric encryption from the cryptography library.
"""
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
from typing import Optional
import os

from app.core.logging import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    _fernet: Optional[Fernet] = None
    _encryption_version: str = "v1"

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create Fernet instance with the encryption key."""
        if cls._fernet is None:
            from app.core.config import settings

            if not settings.ENCRYPTION_KEY:
                raise ValueError(
                    "ENCRYPTION_KEY not configured. Please set ENCRYPTION_KEY in your .env file. "
                    "Generate a key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )

            # The key should already be a valid Fernet key
            # If it's a password, derive a proper key
            key = settings.ENCRYPTION_KEY
            if len(key) != 44 or not key.endswith('='):
                # Derive a proper Fernet key from the password
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'caresma_salt_v1',  # In production, use a secure random salt
                    iterations=100000,
                    backend=default_backend()
                )
                key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
            else:
                key = key.encode()

            cls._fernet = Fernet(key)

        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> tuple[str, str]:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The text to encrypt

        Returns:
            Tuple of (encrypted_text, encryption_version)

        Raises:
            ValueError: If encryption key is not configured
        """
        if not plaintext:
            return plaintext, cls._encryption_version

        try:
            fernet = cls._get_fernet()
            encrypted_bytes = fernet.encrypt(plaintext.encode())
            encrypted_text = encrypted_bytes.decode()

            logger.debug(f"Successfully encrypted data (length: {len(plaintext)})")
            return encrypted_text, cls._encryption_version

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @classmethod
    def decrypt(cls, encrypted_text: str, encryption_version: Optional[str] = None) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted_text: The encrypted text to decrypt
            encryption_version: Version of encryption used (for key rotation support)

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If encryption key is not configured
            InvalidToken: If decryption fails (wrong key, corrupted data)
        """
        if not encrypted_text:
            return encrypted_text

        try:
            # Support for key rotation: use different keys based on version
            # For now, we only have v1
            if encryption_version and encryption_version != cls._encryption_version:
                logger.warning(
                    f"Decrypting with legacy encryption version: {encryption_version}"
                )
                # In the future, you can load different keys here

            fernet = cls._get_fernet()
            decrypted_bytes = fernet.decrypt(encrypted_text.encode())
            plaintext = decrypted_bytes.decode()

            logger.debug(f"Successfully decrypted data (length: {len(plaintext)})")
            return plaintext

        except InvalidToken as e:
            logger.error("Decryption failed: Invalid token or wrong encryption key")
            raise ValueError("Failed to decrypt data. The encryption key may be incorrect.")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    @classmethod
    def rotate_encryption(cls, old_encrypted: str, old_version: str) -> tuple[str, str]:
        """
        Re-encrypt data with a new key (for key rotation).

        Args:
            old_encrypted: Previously encrypted text
            old_version: Version of the old encryption

        Returns:
            Tuple of (new_encrypted_text, new_encryption_version)
        """
        # Decrypt with old key/version
        plaintext = cls.decrypt(old_encrypted, old_version)

        # Re-encrypt with current key/version
        return cls.encrypt(plaintext)


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        A URL-safe base64-encoded 32-byte key suitable for Fernet encryption
    """
    key = Fernet.generate_key()
    return key.decode()


# Convenience functions for direct use
def encrypt_text(plaintext: str) -> tuple[str, str]:
    """Encrypt plaintext. Returns (encrypted_text, version)."""
    return EncryptionService.encrypt(plaintext)


def decrypt_text(encrypted_text: str, version: Optional[str] = None) -> str:
    """Decrypt encrypted text."""
    return EncryptionService.decrypt(encrypted_text, version)
