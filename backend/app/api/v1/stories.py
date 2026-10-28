"""Photo stories: owners post them, administrators review them.

The home page reads them through ``/api/home/stories`` (``app.api.v1.home``).
An owner reaches only their own listing's stories: a shop through
``OwnedBusiness`` (404 for anyone else's), a service profile through the
caller's own profile, never an id from the request.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from sqlalchemy import select

from app.core.dependencies import (
    AdminUser,
    AppSettings,
    CurrentUser,
    DbSession,
    OwnedBusiness,
    OwnTalentProfile,
)
from app.core.errors import NotFoundError
from app.core.uploads import read_at_most
from app.models.story import STORY_PENDING, StoryImage
from app.schemas.story import AdminStoryOut, StoryOut
from app.services.stories import StoryService, story_out

owner_router = APIRouter(tags=["stories"])
admin_router = APIRouter(prefix="/admin/stories", tags=["admin-stories"])

Caption = Annotated[str | None, Form(max_length=200)]
Photo = Annotated[UploadFile, File(description="The story's photograph")]


def _own(db: DbSession, story_id: uuid.UUID, **listing: uuid.UUID) -> StoryImage:
    column, value = next(iter(listing.items()))
    story = db.execute(
        select(StoryImage).where(
            StoryImage.id == story_id, getattr(StoryImage, column) == value
        )
    ).scalar_one_or_none()
    if story is None:
        raise NotFoundError()
    return story


# --- A shop's stories -------------------------------------------------------


@owner_router.get("/my/businesses/{business_id}/stories", response_model=list[StoryOut])
def business_stories(
    business: OwnedBusiness, db: DbSession, settings: AppSettings
) -> list[StoryOut]:
    stories = StoryService(db, settings).of_listing(business_id=business.id)
    return [story_out(story) for story in stories]


@owner_router.post(
    "/my/businesses/{business_id}/stories",
    response_model=StoryOut,
    status_code=status.HTTP_201_CREATED,
)
def post_business_story(
    business: OwnedBusiness,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Photo,
    caption: Caption = None,
) -> StoryOut:
    story = StoryService(db, settings).post(
        owner_id=user.id,
        business_id=business.id,
        data=read_at_most(file.file, settings.max_upload_bytes),
        content_type=file.content_type,
        caption=caption,
    )
    return story_out(story)


@owner_router.delete(
    "/my/businesses/{business_id}/stories/{story_id}", response_model=list[StoryOut]
)
def delete_business_story(
    story_id: uuid.UUID, business: OwnedBusiness, db: DbSession, settings: AppSettings
) -> list[StoryOut]:
    service = StoryService(db, settings)
    service.delete(_own(db, story_id, business_id=business.id))
    return [story_out(story) for story in service.of_listing(business_id=business.id)]


# --- A service profile's stories --------------------------------------------


@owner_router.get("/my/talent/stories", response_model=list[StoryOut])
def talent_stories(
    profile: OwnTalentProfile, db: DbSession, settings: AppSettings
) -> list[StoryOut]:
    stories = StoryService(db, settings).of_listing(talent_profile_id=profile.id)
    return [story_out(story) for story in stories]


@owner_router.post(
    "/my/talent/stories", response_model=StoryOut, status_code=status.HTTP_201_CREATED
)
def post_talent_story(
    profile: OwnTalentProfile,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Photo,
    caption: Caption = None,
) -> StoryOut:
    story = StoryService(db, settings).post(
        owner_id=user.id,
        talent_profile_id=profile.id,
        data=read_at_most(file.file, settings.max_upload_bytes),
        content_type=file.content_type,
        caption=caption,
    )
    return story_out(story)


@owner_router.delete("/my/talent/stories/{story_id}", response_model=list[StoryOut])
def delete_talent_story(
    story_id: uuid.UUID, profile: OwnTalentProfile, db: DbSession, settings: AppSettings
) -> list[StoryOut]:
    service = StoryService(db, settings)
    service.delete(_own(db, story_id, talent_profile_id=profile.id))
    return [story_out(story) for story in service.of_listing(talent_profile_id=profile.id)]


# --- Review -------------------------------------------------------------------


@admin_router.get("", response_model=list[AdminStoryOut])
def story_queue(
    db: DbSession,
    admin: AdminUser,
    settings: AppSettings,
    state: Annotated[
        Literal["PENDING_REVIEW", "APPROVED", "REJECTED"], Query(alias="status")
    ] = STORY_PENDING,  # type: ignore[assignment]
) -> list[AdminStoryOut]:
    return StoryService(db, settings).queue(state)


@admin_router.post("/{story_id}/approve", response_model=StoryOut)
def approve_story(
    story_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> StoryOut:
    service = StoryService(db, settings)
    return story_out(service.approve(service.get(story_id)))


@admin_router.post("/{story_id}/reject", response_model=StoryOut)
def reject_story(
    story_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> StoryOut:
    service = StoryService(db, settings)
    return story_out(service.reject(service.get(story_id)))


@admin_router.delete("/{story_id}", response_model=StoryOut)
def delete_story(
    story_id: uuid.UUID, db: DbSession, admin: AdminUser, settings: AppSettings
) -> StoryOut:
    service = StoryService(db, settings)
    story = service.get(story_id)
    out = story_out(story)
    service.delete(story)
    return out
