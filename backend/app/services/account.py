"""Deleting one's own account, and everything it put on the platform."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import ViewSubject
from app.models.feedback import FeedbackTicket
from app.models.talent import TalentProfile
from app.models.user import User
from app.models.verification import OwnerVerificationDocument
from app.services.analytics import ViewCounterService
from app.services.images import thumbnail_key
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class AccountDeletionService:
    """Removes an account the way its owner would expect "delete" to mean.

    The rows go through the database's cascades -- listings, their products,
    orders and requests, testimonials, the talent profile, identity documents
    and the account's own tickets. The *files* do not cascade, so they are
    collected first and removed from storage once the rows are gone: an ID
    scan or a CV left in the bucket after its owner deleted their account is
    exactly the kind of leftover nobody would think to look for.

    Files are removed after the commit, never before: a failed transaction
    must not leave a live listing pointing at photographs that no longer
    exist. A file that fails to delete is logged and skipped rather than
    undoing the deletion the person asked for.
    """

    def __init__(self, db: Session, storage: StorageBackend) -> None:
        self._db = db
        self._storage = storage

    def delete(self, user: User) -> None:
        keys = self._files_of(user)
        user_id = user.id

        # One transaction: the services' own delete methods commit as they go,
        # and an account left half-deleted is worse than one not deleted.
        # View counters carry no foreign key, so they are purged by hand, as
        # those methods do.
        counters = ViewCounterService(self._db)
        for business in self._db.scalars(select(Business).where(Business.owner_id == user_id)):
            counters.forget(ViewSubject.BUSINESS, business.id)
            for item in business.items:
                counters.forget(ViewSubject.PRODUCT, item.id)
            self._db.delete(business)
        profile = self._db.scalars(
            select(TalentProfile).where(TalentProfile.owner_id == user_id)
        ).first()
        if profile is not None:
            counters.forget(ViewSubject.TALENT, profile.id)
            self._db.delete(profile)

        self._db.delete(user)
        self._db.commit()
        logger.info("Account deleted", extra={"user_id": str(user_id), "files": len(keys)})

        for key in keys:
            try:
                if self._storage.exists(key):
                    self._storage.delete(key)
            except Exception:  # a leftover file must not undo the deletion
                logger.warning("Could not delete a file of a deleted account", extra={"key": key})

    def _files_of(self, user: User) -> list[str]:
        keys: list[str | None] = [user.photo_storage_key]
        keys += [
            document.storage_key
            for document in self._db.scalars(
                select(OwnerVerificationDocument).where(
                    OwnerVerificationDocument.user_id == user.id
                )
            )
        ]
        for business in self._db.scalars(select(Business).where(Business.owner_id == user.id)):
            keys += [business.logo_storage_key, business.cover_storage_key]
            keys += [image.storage_key for image in business.images]
            keys += [document.storage_key for document in business.documents]
            for item in business.items:
                keys.append(item.image_storage_key)
                keys += [image.storage_key for image in item.images]
        profile = self._db.scalars(
            select(TalentProfile).where(TalentProfile.owner_id == user.id)
        ).first()
        if profile is not None:
            keys.append(profile.photo_storage_key)
            keys += [image.storage_key for image in profile.images]
        for ticket in self._db.scalars(
            select(FeedbackTicket).where(FeedbackTicket.reporter_id == user.id)
        ):
            keys += [attachment.storage_key for attachment in ticket.attachments]
        present = [key for key in keys if key]
        thumbs = [thumbnail_key(key) for key in present]
        return present + [thumb for thumb in thumbs if thumb]
