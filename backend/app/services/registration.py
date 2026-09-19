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
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.captcha import verify_captcha
from app.core.config import Settings
from app.core.errors import RateLimitedError
from app.core.rate_limit import DatabaseRateLimiter, RateLimitRule
from app.models.enums import BusinessStatus
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.identity import IDENTITY_FIELDS
from app.schemas.registration import (
    BusinessRegistrationIn,
    RegistrationBase,
    RegistrationIdentityIn,
    TalentRegistrationIn,
)
from app.services.business import BusinessService
from app.services.talent import TalentService
from app.services.verification import VerificationDocumentService
from app.storage.factory import get_storage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApplicantDocument:
    """The ID scan an applicant attached, before there is an account for it."""

    data: bytes
    original_filename: str | None


class RegistrationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._users = UserRepository(db)
        self._limiter = DatabaseRateLimiter(db)
        self._documents = VerificationDocumentService(get_storage(), settings)
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

    def _claim_account(self, payload: RegistrationBase) -> User | None:
        """The account this application belongs to, or None to discard it.

        None when the number already has an account. That case is silently
        dropped rather than refused: answering differently would turn this
        endpoint into a way to ask whether a given number is registered, and
        attaching the listing to the existing account would let a stranger
        put a listing inside someone else's dashboard.
        """
        existing = self._users.get_by_phone(payload.login_phone)
        if existing is not None:
            logger.info(
                "Registration for a number that already has an account; discarded",
                extra={"user_id": str(existing.id)},
            )
            return None

        owner = self._users.create_owner(payload.login_phone)
        _apply_identity(owner, payload.identity)
        return owner

    # --- The applicant's document -------------------------------------------

    def _check_document(self, document: ApplicantDocument | None) -> None:
        """Refuse a bad file while there is still nothing to clean up."""
        if document is None:
            return
        self._documents.validate(document.data)

    def _attach_document(self, owner: User, document: ApplicantDocument | None) -> None:
        """Store the scan against the account this application just created.

        Only ever reached for an application that is being created: a number
        that already has an account never gets here, so an applicant cannot
        put a document on somebody else's account by guessing their number.

        ``store`` commits, which is what makes this one transaction rather
        than two — the account, the listing and the document land together or
        not at all.
        """
        if document is None:
            return
        self._documents.store(
            db=self._db,
            user=owner,
            data=document.data,
            original_filename=document.original_filename,
        )

    # --- Applications -------------------------------------------------------

    def register_business(
        self,
        payload: BusinessRegistrationIn,
        *,
        client_ip: str | None,
        document: ApplicantDocument | None = None,
    ) -> None:
        self._guard(payload.captcha_token, client_ip)
        # Before anything is created, so a file that is too large or is not a
        # document refuses the application rather than leaving an account
        # behind with nothing usable attached to it.
        self._check_document(document)

        owner = self._claim_account(payload)
        if owner is None:
            self._db.commit()
            return

        business = BusinessService(self._db).create(owner, payload.business)
        # Straight to the review queue: an applicant has no dashboard to
        # submit from, so creating it as a DRAFT would leave it invisible to
        # everyone including the administrator who has to act on it.
        business.status = BusinessStatus.PENDING_REVIEW
        self._attach_document(owner, document)
        self._db.commit()
        logger.info(
            "Business application received",
            extra={"business_id": str(business.id), "owner_id": str(owner.id)},
        )

    def register_talent(
        self,
        payload: TalentRegistrationIn,
        *,
        client_ip: str | None,
        document: ApplicantDocument | None = None,
    ) -> None:
        self._guard(payload.captcha_token, client_ip)
        self._check_document(document)

        owner = self._claim_account(payload)
        if owner is None:
            self._db.commit()
            return

        profile = TalentService(self._db).create(owner, payload.talent)
        profile.status = BusinessStatus.PENDING_REVIEW
        self._attach_document(owner, document)
        self._db.commit()
        logger.info(
            "Talent application received",
            extra={"profile_id": str(profile.id), "owner_id": str(owner.id)},
        )


def _apply_identity(owner: User, identity: RegistrationIdentityIn) -> None:
    """Write the applicant's identity onto the account they will sign into.

    Onto the ``users`` row rather than the listing, which is where identity
    lives everywhere else: one account holds one legal name however many
    businesses it owns, and no public schema carries any of these columns.
    The reviewer reads them back through ``OwnerIdentityOut`` on the review
    payload they are already looking at.

    Driven by ``IDENTITY_FIELDS`` rather than a written-out list, so a field
    added to the identity block arrives here without a second edit — the same
    reason ``PATCH /api/me`` iterates it.
    """
    values = identity.model_dump()
    for field in IDENTITY_FIELDS:
        if values.get(field) is not None:
            setattr(owner, field, values[field])
