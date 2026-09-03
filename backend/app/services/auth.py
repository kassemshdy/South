"""Authentication: OTP challenge/verify for owners, password login for admins."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.otp.base import OtpProvider
from app.core.config import Settings
from app.core.errors import (
    AuthenticationError,
    RateLimitedError,
    ValidationError,
)
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.core.security import (
    create_access_token,
    generate_otp_code,
    hash_otp_code,
    verify_otp_code,
    verify_password,
)
from app.models.auth import OtpRequest
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.otp import OtpRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session, settings: Settings, otp_provider: OtpProvider) -> None:
        self._db = db
        self._settings = settings
        self._provider = otp_provider
        self._users = UserRepository(db)
        self._otps = OtpRepository(db)
        self._limiter = DatabaseRateLimiter(db)

        self._phone_rule = RateLimitRule(
            bucket="otp_send_phone",
            limit=settings.otp_send_per_phone_limit,
            window_seconds=settings.otp_send_per_phone_window_seconds,
        )
        self._ip_rule = RateLimitRule(
            bucket="otp_send_ip",
            limit=settings.otp_send_per_ip_limit,
            window_seconds=settings.otp_send_per_ip_window_seconds,
        )

    # --- OTP ---------------------------------------------------------------

    def request_otp(self, phone_number: str, *, client_ip: str | None) -> tuple[int, str | None]:
        """Issue a challenge. Returns (ttl_seconds, debug_code_or_None)."""
        phone_status = self._limiter.hit(self._phone_rule, phone_number)
        if not phone_status.allowed:
            raise RateLimitedError(
                phone_status.retry_after_seconds, "auth.otp.rate_limited_phone"
            )

        if client_ip:
            ip_status = self._limiter.hit(self._ip_rule, client_ip)
            if not ip_status.allowed:
                raise RateLimitedError(
                    ip_status.retry_after_seconds, "auth.otp.rate_limited_ip"
                )

        code = self._provider.fixed_code() or generate_otp_code(self._settings.otp_code_length)

        # Only the newest code may be redeemed.
        self._otps.invalidate_active_for_phone(phone_number)
        self._otps.add(
            OtpRequest(
                phone_number=phone_number,
                code_hash=hash_otp_code(code),
                expires_at=datetime.now(UTC) + timedelta(seconds=self._settings.otp_ttl_seconds),
                request_ip=client_ip,
            )
        )

        result = self._provider.send(phone_number, code)
        if not result.delivered:
            raise ValidationError(
                "auth.otp.delivery_failed", code="otp_delivery_failed", status_code=502
            )

        self._db.commit()
        # debug_code is set only by development providers, and the API layer
        # additionally refuses to expose it outside development.
        return self._settings.otp_ttl_seconds, result.debug_code

    def verify_otp(self, phone_number: str, code: str) -> tuple[User, str, datetime]:
        challenge = self._otps.latest_active_for_phone(phone_number)
        if challenge is None:
            raise AuthenticationError("auth.otp.not_found", code="otp_not_found")

        if challenge.attempt_count >= self._settings.otp_max_verify_attempts:
            challenge.consumed_at = datetime.now(UTC)
            self._db.commit()
            raise RateLimitedError(
                self._settings.otp_ttl_seconds, "auth.otp.too_many_attempts"
            )

        challenge.attempt_count += 1

        if not verify_otp_code(code, challenge.code_hash):
            self._db.commit()
            raise AuthenticationError("auth.otp.invalid", code="otp_invalid")

        challenge.consumed_at = datetime.now(UTC)

        user = self._users.get_by_phone(phone_number)
        if user is None:
            user = self._users.create_owner(phone_number)
            logger.info("New owner account created", extra={"user_id": str(user.id)})
        elif not user.is_active:
            self._db.commit()
            raise AuthenticationError("auth.account.disabled", code="account_disabled")

        token, expires_at = create_access_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        )
        self._db.commit()
        return user, token, expires_at

    # --- Administrators ----------------------------------------------------

    def login_admin(self, email: str, password: str) -> tuple[User, str, datetime]:
        user = self._users.get_by_email(email)

        # Same error and roughly the same work for unknown email, wrong password
        # and non-admin accounts, so the endpoint does not enumerate admins.
        if user is None or not verify_password(password, user.password_hash):
            logger.warning("Failed admin login", extra={"email": email})
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )
        if user.role is not UserRole.ADMIN or not user.is_active:
            logger.warning("Non-admin attempted admin login", extra={"user_id": str(user.id)})
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )

        token, expires_at = create_access_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        )
        return user, token, expires_at
