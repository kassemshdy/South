"""Photo stories: posting, review, expiry and the home page's row.

See ``app.models.story`` for the decisions. Every query that reaches a
visitor goes through the listings' own ``public_query``, so a story of a
listing that is not approved is as invisible as the listing itself.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
from app.models.business import Business
from app.models.enums import ImageKind
from app.models.story import (
    STORY_APPROVED,
    STORY_LIFETIME,
    STORY_PENDING,
    STORY_REJECTED,
    StoryImage,
)
from app.models.talent import TalentProfile
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository
from app.schemas.story import AdminStoryOut, PublicStoryOut, StoryGroupOut, StoryOut
from app.services.images import ImageService
from app.storage.factory import get_storage

#: Stories waiting or showing at once, per listing: a row of circles, not a
#: gallery.
MAX_OPEN_STORIES = 10


def now() -> datetime:
    return datetime.now(UTC)


def story_out(story: StoryImage) -> StoryOut:
    return StoryOut(
        id=story.id,
        image_url=story.image_url,
        caption=story.caption,
        status=story.status,
        approved_at=story.approved_at,
        expires_at=story.expires_at,
        created_at=story.created_at,
    )


class StoryService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._images = ImageService(get_storage(), settings)

    # --- Owners -----------------------------------------------------------

    def of_listing(
        self,
        *,
        business_id: uuid.UUID | None = None,
        talent_profile_id: uuid.UUID | None = None,
    ) -> list[StoryImage]:
        self.purge_expired()
        stmt = select(StoryImage).order_by(StoryImage.created_at.desc())
        if business_id is not None:
            stmt = stmt.where(StoryImage.business_id == business_id)
        else:
            stmt = stmt.where(StoryImage.talent_profile_id == talent_profile_id)
        return list(self._db.scalars(stmt))

    def post(
        self,
        *,
        owner_id: uuid.UUID,
        data: bytes,
        content_type: str | None,
        caption: str | None,
        business_id: uuid.UUID | None = None,
        talent_profile_id: uuid.UUID | None = None,
    ) -> StoryImage:
        open_ = [
            story
            for story in self.of_listing(
                business_id=business_id, talent_profile_id=talent_profile_id
            )
            if story.status != STORY_REJECTED
        ]
        if len(open_) >= MAX_OPEN_STORIES:
            raise ConflictError("story.too_many", params={"limit": str(MAX_OPEN_STORIES)})
        listing_id = business_id or talent_profile_id
        assert listing_id is not None
        stored = self._images.process_and_store(
            data=data,
            content_type=content_type,
            owner_id=listing_id,
            kind=ImageKind.GALLERY,
            prefix="stories",
        )
        story = StoryImage(
            id=uuid.uuid4(),
            owner_id=owner_id,
            business_id=business_id,
            talent_profile_id=talent_profile_id,
            image_url=stored.url,
            image_storage_key=stored.key,
            caption=(caption or "").strip() or None,
            status=STORY_PENDING,
        )
        self._db.add(story)
        self._db.commit()
        self._db.refresh(story)
        return story

    def delete(self, story: StoryImage) -> None:
        key = story.image_storage_key
        self._db.delete(story)
        self._db.commit()
        self._images.delete(key)

    # --- Administrators ---------------------------------------------------

    def queue(self, status: str) -> list[AdminStoryOut]:
        self.purge_expired()
        stories = self._db.scalars(
            select(StoryImage)
            .where(StoryImage.status == status)
            .order_by(StoryImage.created_at.asc())
        )
        out: list[AdminStoryOut] = []
        for story in stories:
            if story.business_id is not None:
                business = self._db.get(Business, story.business_id)
                if business is None:
                    continue
                listing = ("business", business.id, business.name, business.slug)
            else:
                profile = self._db.get(TalentProfile, story.talent_profile_id)
                if profile is None:
                    continue
                listing = ("talent", profile.id, profile.display_name, profile.slug)
            out.append(
                AdminStoryOut(
                    **story_out(story).model_dump(),
                    listing_kind=listing[0],  # type: ignore[arg-type]
                    listing_id=listing[1],
                    listing_name=listing[2],
                    listing_slug=listing[3],
                )
            )
        return out

    def get(self, story_id: uuid.UUID) -> StoryImage:
        story = self._db.get(StoryImage, story_id)
        if story is None:
            raise NotFoundError()
        return story

    def approve(self, story: StoryImage) -> StoryImage:
        moment = now()
        story.status = STORY_APPROVED
        story.approved_at = moment
        story.expires_at = moment + STORY_LIFETIME
        self._db.commit()
        self._db.refresh(story)
        return story

    def reject(self, story: StoryImage) -> StoryImage:
        story.status = STORY_REJECTED
        story.approved_at = story.expires_at = None
        self._db.commit()
        self._db.refresh(story)
        return story

    def purge_expired(self) -> None:
        """A story past its day is gone, row and file. Done whenever stories
        are listed for an owner or an administrator, so nothing needs a
        scheduler; the public row filters by time and never shows one."""
        expired = list(
            self._db.scalars(
                select(StoryImage).where(
                    StoryImage.status == STORY_APPROVED, StoryImage.expires_at <= now()
                )
            )
        )
        if not expired:
            return
        keys = [story.image_storage_key for story in expired]
        for story in expired:
            self._db.delete(story)
        self._db.commit()
        for key in keys:
            self._images.delete(key)


def home_story_groups(db: Session) -> list[StoryGroupOut]:
    """The listings with a story showing now, the most recently approved
    first, each with its photographs oldest first."""
    live = (
        StoryImage.status == STORY_APPROVED,
        StoryImage.expires_at > now(),
    )
    groups: list[tuple[datetime, StoryGroupOut]] = []

    shops = BusinessRepository(db).public_query().with_only_columns(Business.id)
    rows = db.execute(
        select(StoryImage, Business)
        .join(Business, Business.id == StoryImage.business_id)
        .where(*live, StoryImage.business_id.in_(shops))
        .order_by(StoryImage.approved_at.asc())
    ).all()
    by_business: dict[uuid.UUID, tuple[Business, list[StoryImage]]] = {}
    for story, business in rows:
        by_business.setdefault(business.id, (business, []))[1].append(story)
    for business, stories in by_business.values():
        groups.append(
            (
                stories[-1].approved_at or now(),
                StoryGroupOut(
                    kind="business",
                    slug=business.slug,
                    name=business.name,
                    image_url=business.logo_url,
                    stories=[_public(story) for story in stories],
                ),
            )
        )

    people = TalentRepository(db).public_query().with_only_columns(TalentProfile.id)
    talent_rows = db.execute(
        select(StoryImage, TalentProfile)
        .join(TalentProfile, TalentProfile.id == StoryImage.talent_profile_id)
        .where(*live, StoryImage.talent_profile_id.in_(people))
        .order_by(StoryImage.approved_at.asc())
    ).all()
    by_profile: dict[uuid.UUID, tuple[TalentProfile, list[StoryImage]]] = {}
    for story, profile in talent_rows:
        by_profile.setdefault(profile.id, (profile, []))[1].append(story)
    for profile, stories in by_profile.values():
        groups.append(
            (
                stories[-1].approved_at or now(),
                StoryGroupOut(
                    kind="talent",
                    slug=profile.slug,
                    name=profile.display_name,
                    image_url=profile.photo_url,
                    stories=[_public(story) for story in stories],
                ),
            )
        )

    groups.sort(key=lambda pair: pair[0], reverse=True)
    return [group for _, group in groups]


def _public(story: StoryImage) -> PublicStoryOut:
    return PublicStoryOut(
        id=story.id,
        image_url=story.image_url,
        caption=story.caption,
        approved_at=story.approved_at or now(),
    )
