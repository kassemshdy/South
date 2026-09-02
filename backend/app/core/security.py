"""Password hashing, OTP code hashing and JWT issuing/verification."""

from __future__ import annotations

import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import AuthenticationError

_settings = get_settings()


# --- Passwords (administrators) -------------------------------------------


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        # Malformed hash in the database — treat as a failed login, never a 500.
        return False


# --- OTP codes -------------------------------------------------------------


def generate_otp_code(length: int) -> str:
    """Cryptographically random numeric code, zero-padded to ``length``."""
    upper = 10**length
    return str(secrets.randbelow(upper)).zfill(length)


def hash_otp_code(code: str) -> str:
    return bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()


def verify_otp_code(code: str, code_hash: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode(), code_hash.encode())
    except ValueError:
        return False


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# --- JWT -------------------------------------------------------------------


def create_access_token(
    *,
    user_id: uuid.UUID,
    role: str,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    """Issue a signed access token; returns the token and its expiry."""
    now = datetime.now(UTC)
    expires_at = now + (
        expires_delta or timedelta(minutes=_settings.access_token_ttl_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        # Lets us revoke every token for a user by bumping User.token_version.
        "tv": token_version,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    token = jwt.encode(payload, _settings.secret_key, algorithm=_settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            _settings.secret_key,
            algorithms=[_settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError(
            "انتهت صلاحية الجلسة. يرجى تسجيل الدخول مجدداً.", code="token_expired"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("جلسة غير صالحة.", code="invalid_token") from exc
