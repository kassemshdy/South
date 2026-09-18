"""Public registration: an application that is already the listing.

Someone applies without an account. What gets stored is not a separate
"application" row but the real `Business` or `TalentProfile`, in
`PENDING_REVIEW`, owned by an account that has no password yet — so it cannot
be signed into until an administrator issues one.

Storing the real thing is the point. The moderation queue, the serializers and
the admin screens all work unchanged, approval has nothing to migrate, and
there is no second copy of every field to keep in step. The account being
password-less is what makes it safe: the row exists, but nobody can act as its
owner until a person has looked at the application.

Anonymous and therefore rate limited, on the same pattern as testimonials:
per address first, then per day across the whole site, so one sender rotating
addresses cannot bury the review queue.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.captcha import verify_captcha
from app.core.config import Settings
from app.core.errors import RateLimitedError
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.enums import BusinessStatus
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.registration import BusinessRegistrationIn, TalentRegistrationIn
from app.services.business import BusinessService
from app.services.talent import TalentService

logger = logging.getLogger(__name__)


class RegistrationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._users = UserRepository(db)
        self._limiter = DatabaseRateLimiter(db)
        self._ip_rule = RateLimitRule(
            bucket="registration_ip",
            limit=settings.registration_per_ip_limit,
            window_seconds=settings.registration_per_ip_window_seconds,
        )
        self._global_rule = RateLimitRule(
            bucket="registration_global",
            limit=settings.registration_per_day_limit,
            window_seconds=settings.registration_per_day_window_seconds,
        )

    # --- Guards -------------------------------------------------------------

    def _guard(self, captcha_token: str | None, client_ip: str | None) -> None:
        if client_ip:
            ip_status = self._limiter.hit(self._ip_rule, client_ip)
            if not ip_status.allowed:
                raise RateLimitedError(
                    ip_status.retry_after_seconds, "registration.rate_limited"
                )
        # Site-wide, so a sender rotating addresses still meets a ceiling.
        global_status = self._limiter.hit(self._global_rule, "all")
        if not global_status.allowed:
            raise RateLimitedError(
                global_status.retry_after_seconds, "registration.rate_limited"
            )
        verify_captcha(captcha_token, self._settings, client_ip=client_ip)

    def _claim_account(self, login_phone: str) -> User | None:
        """The account this application belongs to, or None to discard it.

        None when the number already has an account. That case is silently
        dropped rather than refused: answering differently would turn this
        endpoint into a way to ask whether a given number is registered, and
        attaching the listing to the existing account would let a stranger
        put a listing inside someone else's dashboard.
        """
        existing = self._users.get_by_phone(login_phone)
        if existing is not None:
            logger.info(
                "Registration for a number that already has an account; discarded",
                extra={"user_id": str(existing.id)},
            )
            return None
        return self._users.create_owner(login_phone)

    # --- Applications -------------------------------------------------------

    def register_business(
        self, payload: BusinessRegistrationIn, *, client_ip: str | None
    ) -> None:
        self._guard(payload.captcha_token, client_ip)
        owner = self._claim_account(payload.login_phone)
        if owner is None:
            self._db.commit()
            return

        business = BusinessService(self._db).create(owner, payload.business)
        # Straight to the review queue: an applicant has no dashboard to
        # submit from, so creating it as a DRAFT would leave it invisible to
        # everyone including the administrator who has to act on it.
        business.status = BusinessStatus.PENDING_REVIEW
        self._db.commit()
        logger.info(
            "Business application received",
            extra={"business_id": str(business.id), "owner_id": str(owner.id)},
        )

    def register_talent(
        self, payload: TalentRegistrationIn, *, client_ip: str | None
    ) -> None:
        self._guard(payload.captcha_token, client_ip)
        owner = self._claim_account(payload.login_phone)
        if owner is None:
            self._db.commit()
            return

        profile = TalentService(self._db).create(owner, payload.talent)
        profile.status = BusinessStatus.PENDING_REVIEW
        self._db.commit()
        logger.info(
            "Talent application received",
            extra={"profile_id": str(profile.id), "owner_id": str(owner.id)},
        )
