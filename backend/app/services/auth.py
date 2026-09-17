"""Authentication: OTP or password for owners, password for administrators.

Owners have two ways in, deliberately, and both land on the same account
because it is keyed by phone number. The OTP challenge is the one that needs a
working SMS or WhatsApp gateway; the password is the one that does not, and it
exists because that gateway has not been obtainable. A password an
administrator issued is a way in exactly once — see ``must_change_password``.
"""

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
from app.core.passwords import generate_temporary_password
from app.core.phone import normalize_phone
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.core.security import (
    create_access_token,
    generate_otp_code,
    hash_otp_code,
    hash_password,
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
        # Password sign-in has no second factor and no code that expires, so
        # the only thing standing between a guessable password and an account
        # is how many guesses fit in the window. Keyed on the phone number,
        # because that is what an attacker is working through: an address
        # limit alone lets one host walk a list of numbers, and lets a shared
        # connection lock out a whole village.
        self._login_rule = RateLimitRule(
            bucket="password_login",
            limit=settings.password_login_per_phone_limit,
            window_seconds=settings.password_login_per_phone_window_seconds,
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

    def login_with_password(
        self, phone_number: str, password: str, *, client_ip: str | None = None
    ) -> tuple[User, str, datetime]:
        """Sign an owner in with the phone number and a password.

        Deliberately not `login_admin` with a different lookup: that one refuses
        anything but an administrator, and this one refuses an administrator —
        an admin signs in on the admin form, and keeping the two apart means a
        leaked owner password can never reach the admin panel.

        One error for every failure, as above, so the endpoint cannot be used
        to discover which numbers have accounts. An account with no password
        set — every account starts that way, before an administrator issues
        one — fails here too, because `verify_password` refuses a null hash.

        The budget is checked before anything is looked up, so it applies to a
        number with no account as well; spending it only on real accounts would
        make the difference measurable. Only *failures* are recorded, so
        signing in correctly never uses it up, and a run of wrong guesses ages
        out of the window on its own.
        """
        normalized = normalize_phone(phone_number)

        status = self._limiter.check(self._login_rule, normalized)
        if not status.allowed:
            raise RateLimitedError(status.retry_after_seconds, "auth.login.rate_limited")

        user = self._users.get_by_phone(normalized)

        if user is None or not verify_password(password, user.password_hash):
            self._record_failed_login(normalized)
            logger.warning(
                "Failed owner login",
                extra={"phone_number": normalized, "request_ip": client_ip},
            )
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )
        if user.role is UserRole.ADMIN or not user.is_active:
            self._record_failed_login(normalized)
            logger.warning(
                "Owner login refused for role", extra={"user_id": str(user.id)}
            )
            raise AuthenticationError(
                "auth.invalid_credentials", code="invalid_credentials"
            )

        token, expires_at = create_access_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        )
        return user, token, expires_at

    def _record_failed_login(self, phone_number: str) -> None:
        """Spend one guess, and commit it before the failure is raised.

        The commit is the point. The limiter only flushes, and the request
        that is about to raise never reaches a commit of its own — so without
        this the attempt is rolled back with the error and the budget never
        goes down, which is the whole of the protection.
        """
        self._limiter.hit(self._login_rule, phone_number)
        self._db.commit()

    def set_password(self, user: User, password: str) -> None:
        """Replace the account's password and end every other session.

        Bumping ``token_version`` invalidates tokens issued before this point,
        which is the whole value of the change when the old password went out
        over WhatsApp: whoever else read that chat is signed out.
        """
        user.password_hash = hash_password(password)
        user.must_change_password = False
        user.token_version += 1
        self._db.commit()
        logger.info("Password changed", extra={"user_id": str(user.id)})

    def issue_password(self, user: User) -> str:
        """Generate a password for ``user`` and return it once.

        The plaintext is returned to the caller and never stored, logged or
        sent anywhere by this application — an administrator relays it over
        their own WhatsApp. It is a way in exactly once: `must_change_password`
        blocks every owner route until it has been replaced.
        """
        password = generate_temporary_password()
        user.password_hash = hash_password(password)
        user.must_change_password = True
        # Any session opened with a previous password stops here.
        user.token_version += 1
        self._db.commit()
        logger.info("Password issued to account", extra={"user_id": str(user.id)})
        return password
