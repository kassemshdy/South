"""Sign-up and password reset by a code sent in an SMS.

The owners' decision (9 Nov 2026): someone types their mobile number, gets a
six-digit code from Janoubona, types it back and chooses a password. That
one flow both opens a new account and replaces a forgotten password, so the
answer never says which numbers already have an account -- the same reason
the application form answers one sentence whatever happened.

It runs beside the application form, not instead of it: an administrator
switches it on and off at /admin/site-settings (``SMS_SIGNUP_ENABLED_KEY``),
so a problem with the SMS provider sends people back to the form, which
needs no SMS at all.

Every code costs credit, so sending is guarded harder than checking:
the captcha, a resend wait per number, a limit per number and per address,
and a site-wide daily cap the administrator sets (``DAILY_CAP_KEY``,
default ``DEFAULT_DAILY_CAP``). Only mobile numbers are accepted: a
landline cannot receive the code and would only spend credit.

Only a keyed hash of each code is stored, it lives ``CODE_TTL`` and allows
``MAX_ATTEMPTS`` guesses. Staff accounts are never reached this way: a
code is not sent to an administrator's number, so an SMS can never replace
a staff password.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.captcha import verify_captcha
from app.core.config import Settings
from app.core.errors import AppError, RateLimitedError, ValidationError
from app.core.i18n import translate
from app.core.phone import normalize_phone
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.core.security import create_access_token, hash_password
from app.models.auth import PhoneCode
from app.models.enums import UserRole
from app.models.site_setting import SiteSetting
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.sms import SmsError, SmsService

logger = logging.getLogger(__name__)

SMS_SIGNUP_ENABLED_KEY = "sms_signup_enabled"
DAILY_CAP_KEY = "sms_daily_cap"
DEFAULT_DAILY_CAP = 300

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
RESEND_AFTER = timedelta(seconds=60)
DAY = 86400

#: Lebanese mobile numbers after +961: 3xxxxxx, and 70/71/76/78/79/81 plus six.
_MOBILE_RE = re.compile(r"^\+961(3\d{6}|7[01689]\d{6}|81\d{6})$")

_PER_PHONE = RateLimitRule(bucket="phone_code_phone", limit=5, window_seconds=3600)
_PER_IP = RateLimitRule(bucket="phone_code_ip", limit=10, window_seconds=3600)


@dataclass(frozen=True)
class PhoneSignupConfig:
    enabled: bool
    daily_cap: int


def read_config(db: Session) -> PhoneSignupConfig:
    enabled = db.get(SiteSetting, SMS_SIGNUP_ENABLED_KEY)
    cap = db.get(SiteSetting, DAILY_CAP_KEY)
    try:
        daily_cap = int(cap.value) if cap is not None and cap.value else DEFAULT_DAILY_CAP
    except ValueError:
        daily_cap = DEFAULT_DAILY_CAP
    return PhoneSignupConfig(
        enabled=enabled is not None and enabled.value == "1", daily_cap=daily_cap
    )


def write_config(db: Session, *, enabled: bool, daily_cap: int) -> PhoneSignupConfig:
    for key, value in (
        (SMS_SIGNUP_ENABLED_KEY, "1" if enabled else "0"),
        (DAILY_CAP_KEY, str(daily_cap)),
    ):
        row = db.get(SiteSetting, key)
        if row is None:
            db.add(SiteSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return read_config(db)


def _daily_rule(cap: int) -> RateLimitRule:
    return RateLimitRule(bucket="phone_code_daily", limit=cap, window_seconds=DAY)


def is_mobile(phone: str) -> bool:
    return bool(_MOBILE_RE.match(phone))


class PhoneAuthService:
    def __init__(self, db: Session, settings: Settings, sms: SmsService | None = None) -> None:
        self._db = db
        self._settings = settings
        self._sms = sms or SmsService(settings)
        self._users = UserRepository(db)
        self._limiter = DatabaseRateLimiter(db)

    # --- availability -------------------------------------------------------

    def available(self) -> bool:
        """On only while an administrator has switched it on *and* the SMS
        provider is configured -- either missing sends people to the form."""
        return read_config(self._db).enabled and self._sms.enabled

    def sent_today(self) -> int:
        return self._limiter.count(_daily_rule(DEFAULT_DAILY_CAP), "all")

    # --- sending ------------------------------------------------------------

    def request_code(
        self, raw_phone: str, *, captcha_token: str | None, client_ip: str | None
    ) -> None:
        """Send a code to ``raw_phone``. Returns the same way whether or not
        the number has an account; raises only for what the visitor can fix
        (the number's shape, waiting) or what nobody can (SMS is off)."""
        config = read_config(self._db)
        if not (config.enabled and self._sms.enabled):
            raise AppError(
                "phoneAuth.unavailable", code="phone_signup_unavailable", status_code=503
            )
        phone = normalize_phone(raw_phone)
        if not is_mobile(phone):
            raise ValidationError("phoneAuth.not_mobile", code="not_mobile")

        now = datetime.now(UTC)
        latest = self._latest(phone)
        if latest is not None and latest.created_at > now - RESEND_AFTER:
            wait = int((latest.created_at + RESEND_AFTER - now).total_seconds()) + 1
            raise RateLimitedError(wait, "phoneAuth.wait")
        for rule, identifier in ((_PER_PHONE, phone), (_PER_IP, client_ip)):
            if not identifier:
                continue
            status = self._limiter.check(rule, identifier)
            if not status.allowed:
                raise RateLimitedError(status.retry_after_seconds, "phoneAuth.rate_limited")
        daily = self._limiter.check(_daily_rule(config.daily_cap), "all")
        if not daily.allowed:
            logger.warning("SMS sign-up daily cap reached", extra={"cap": config.daily_cap})
            raise RateLimitedError(daily.retry_after_seconds, "phoneAuth.rate_limited")
        verify_captcha(captcha_token, self._settings, client_ip=client_ip)

        self._limiter.hit(_PER_PHONE, phone)
        if client_ip:
            self._limiter.hit(_PER_IP, client_ip)

        user = self._users.get_by_phone(phone)
        if user is not None and (user.role is not UserRole.OWNER or not user.is_active):
            # Nothing is sent to a staff or disabled account, and the answer
            # is the same as for anyone else.
            self._db.commit()
            logger.info(
                "Phone code not sent to a non-owner account", extra={"user_id": str(user.id)}
            )
            return

        self._purge(now)
        self._db.execute(
            update(PhoneCode)
            .where(PhoneCode.phone == phone, PhoneCode.used_at.is_(None))
            .values(used_at=now)
        )
        code = f"{secrets.randbelow(10**6):06d}"
        row = PhoneCode(phone=phone, code_hash=self._hash(phone, code), expires_at=now + CODE_TTL)
        self._db.add(row)
        self._limiter.hit(_daily_rule(config.daily_cap), "all")
        self._db.commit()

        try:
            # Latin text on purpose: the Arabic wording of the code was held
            # by the carrier as an unregistered one-time code, while
            # "Janoubona code 482913" arrived (tested 10 Nov 2026).
            self._sms.send(phone, translate("phoneAuth.sms", "ar", code=code))
        except SmsError as error:
            row.used_at = datetime.now(UTC)
            self._db.commit()
            logger.warning("Phone code SMS failed", extra={"reason": str(error)})
            raise AppError("phoneAuth.send_failed", code="sms_failed", status_code=502) from error

    # --- checking -----------------------------------------------------------

    def check_code(self, raw_phone: str, code: str) -> None:
        """Raise unless ``code`` is the live code for the number. Spends a
        guess; does not use the code up, so the password step can follow."""
        self._match(normalize_phone(raw_phone), code)

    def complete(self, raw_phone: str, code: str, password: str) -> tuple[User, str, datetime]:
        """Use the code: open the account, or replace its password, and sign
        in. Every other session of the account ends (``token_version``)."""
        phone = normalize_phone(raw_phone)
        row = self._match(phone, code)
        user = self._users.get_by_phone(phone)
        if user is None:
            user = self._users.create_owner(phone)
            logger.info("Account opened by SMS code")
        elif user.role is not UserRole.OWNER or not user.is_active:
            raise ValidationError("phoneAuth.code_invalid", code="invalid_code")
        row.used_at = datetime.now(UTC)
        user.password_hash = hash_password(password)
        user.must_change_password = False
        user.token_version = (user.token_version or 0) + 1
        self._db.commit()
        self._db.refresh(user)
        token, expires_at = create_access_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        )
        logger.info("Password set by SMS code", extra={"user_id": str(user.id)})
        return user, token, expires_at

    # --- internals ----------------------------------------------------------

    def _hash(self, phone: str, code: str) -> str:
        return hmac.new(
            self._settings.secret_key.encode(), f"{phone}:{code}".encode(), hashlib.sha256
        ).hexdigest()

    def _latest(self, phone: str) -> PhoneCode | None:
        return self._db.scalars(
            select(PhoneCode)
            .where(PhoneCode.phone == phone)
            .order_by(PhoneCode.created_at.desc())
            .limit(1)
        ).first()

    def _match(self, phone: str, code: str) -> PhoneCode:
        now = datetime.now(UTC)
        row = self._latest(phone)
        if (
            row is None
            or row.used_at is not None
            or row.expires_at <= now
            or row.attempts >= MAX_ATTEMPTS
        ):
            raise ValidationError("phoneAuth.code_expired", code="code_expired")
        row.attempts += 1
        if not hmac.compare_digest(row.code_hash, self._hash(phone, code.strip())):
            # Committed before raising: the guess must count even though the
            # request fails, or the attempt limit protects nothing.
            self._db.commit()
            raise ValidationError("phoneAuth.code_invalid", code="invalid_code")
        self._db.flush()
        return row

    def _purge(self, now: datetime) -> None:
        self._db.execute(delete(PhoneCode).where(PhoneCode.expires_at < now - timedelta(days=1)))
