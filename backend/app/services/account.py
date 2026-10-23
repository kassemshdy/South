"""Deleting one's own account, and everything it put on the platform."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessItem
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
        for business in self._db.scalars(select(Business).where(Business.owner_id == user_id)):
            self._drop_business(business)
        profile = self._db.scalars(
            select(TalentProfile).where(TalentProfile.owner_id == user_id)
        ).first()
        if profile is not None:
            self._drop_profile(profile)

        self._db.delete(user)
        self._db.commit()
        logger.info("Account deleted", extra={"user_id": str(user_id), "files": len(keys)})
        self._remove(keys)

    # --- One listing, by an administrator --------------------------------
    #
    # The same promise as above, one listing at a time: the row and every
    # file it pointed at. The owner's account stays.

    def delete_business(self, business: Business) -> None:
        keys = _with_thumbnails(self._business_files(business))
        business_id = business.id
        self._drop_business(business)
        self._db.commit()
        logger.info("Business deleted", extra={"business_id": str(business_id)})
        self._remove(keys)

    def delete_profile(self, profile: TalentProfile) -> None:
        keys = _with_thumbnails(self._profile_files(profile))
        profile_id = profile.id
        self._drop_profile(profile)
        self._db.commit()
        logger.info("Talent profile deleted", extra={"profile_id": str(profile_id)})
        self._remove(keys)

    def delete_item(self, item: BusinessItem) -> None:
        keys = _with_thumbnails(self._item_files(item))
        item_id = item.id
        ViewCounterService(self._db).forget(ViewSubject.PRODUCT, item_id)
        self._db.delete(item)
        self._db.commit()
        logger.info("Item deleted", extra={"item_id": str(item_id)})
        self._remove(keys)

    # --- internals ----------------------------------------------------------

    def _drop_business(self, business: Business) -> None:
        counters = ViewCounterService(self._db)
        counters.forget(ViewSubject.BUSINESS, business.id)
        for item in business.items:
            counters.forget(ViewSubject.PRODUCT, item.id)
        self._db.delete(business)

    def _drop_profile(self, profile: TalentProfile) -> None:
        ViewCounterService(self._db).forget(ViewSubject.TALENT, profile.id)
        self._db.delete(profile)

    def _remove(self, keys: list[str]) -> None:
        """After the commit, never before -- see the class docstring."""
        for key in keys:
            try:
                if self._storage.exists(key):
                    self._storage.delete(key)
            except Exception:  # a leftover file must not undo the deletion
                logger.warning("Could not delete a file of a deleted listing", extra={"key": key})

    @staticmethod
    def _item_files(item: BusinessItem) -> list[str | None]:
        return [item.image_storage_key, *(image.storage_key for image in item.images)]

    def _business_files(self, business: Business) -> list[str | None]:
        keys: list[str | None] = [business.logo_storage_key, business.cover_storage_key]
        keys += [image.storage_key for image in business.images]
        keys += [document.storage_key for document in business.documents]
        for item in business.items:
            keys += self._item_files(item)
        return keys

    @staticmethod
    def _profile_files(profile: TalentProfile) -> list[str | None]:
        return [profile.photo_storage_key, *(image.storage_key for image in profile.images)]

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
            keys += self._business_files(business)
        profile = self._db.scalars(
            select(TalentProfile).where(TalentProfile.owner_id == user.id)
        ).first()
        if profile is not None:
            keys += self._profile_files(profile)
        for ticket in self._db.scalars(
            select(FeedbackTicket).where(FeedbackTicket.reporter_id == user.id)
        ):
            keys += [attachment.storage_key for attachment in ticket.attachments]
        return _with_thumbnails(keys)


def _with_thumbnails(keys: list[str | None]) -> list[str]:
    present = [key for key in keys if key]
    thumbs = [thumbnail_key(key) for key in present]
    return present + [thumb for thumb in thumbs if thumb]
