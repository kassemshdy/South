"""Encryption at rest for credentials third parties issue to us.

A connected Shopify store's access token is a secret that can edit that
store's products, so the column holds ciphertext only. The key is
``INTEGRATION_ENCRYPTION_KEY`` -- an environment variable, never in the
database -- which is what keeps the hourly SQL copy sent to Telegram
(``telegram_db_backup``) from carrying a usable token.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings


class CredentialCipherError(Exception):
    """Encryption is not configured, or a stored value cannot be read."""


def _fernet(settings: Settings) -> Fernet:
    if not settings.integration_encryption_key:
        raise CredentialCipherError("INTEGRATION_ENCRYPTION_KEY is not set")
    try:
        return Fernet(settings.integration_encryption_key.encode())
    except ValueError as exc:
        raise CredentialCipherError("INTEGRATION_ENCRYPTION_KEY is not a Fernet key") from exc


def encrypt_secret(settings: Settings, plaintext: str) -> str:
    return _fernet(settings).encrypt(plaintext.encode()).decode()


def decrypt_secret(settings: Settings, ciphertext: str) -> str:
    try:
        return _fernet(settings).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise CredentialCipherError("stored credential cannot be decrypted") from exc
