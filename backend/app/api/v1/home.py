"""The home page's sections: their order, and the stories row.

The home page is a list of sections an administrator can reorder and hide
(the owners' request, 27 Oct 2026): the three the page always had -- the
cover photograph, the pitch with its video and chooser, the slogan band --
and the browsing sections an e-commerce home has -- search, categories,
stories, live counts, newest products, shops, services and news.

The order is one row in ``site_settings`` (``home_layout``), written as
``id:1,id:0,...`` (1 shown, 0 hidden). Reading it, an unknown id is dropped
and a section that is missing is appended **hidden**: the page visitors see
changes only when an administrator switches a section on. The manager
reviews the new sections first at ``/?preview=home``, which shows the
proposed page on live data without saving anything.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import AdminUser, DbSession
from app.models.business import Business
from app.models.site_setting import SiteSetting
from app.models.talent import TalentProfile
from app.repositories.business import BusinessRepository
from app.repositories.talent import TalentRepository

public_router = APIRouter(prefix="/home", tags=["home"])
admin_router = APIRouter(prefix="/admin/home", tags=["admin-home"])

LAYOUT_KEY = "home_layout"

#: Every section there is. A fresh site shows the original three
#: (``ORIGINAL``) and keeps the rest hidden until an administrator turns them
#: on, so a deploy changes nothing a visitor sees.
SECTIONS: tuple[str, ...] = (
    "cover",
    "hero",
    "slogan",
    "search",
    "categories",
    "stories",
    "stats",
    "products",
    "category_products",
    "shops",
    "talents",
    "news",
)

ORIGINAL = frozenset({"cover", "hero", "slogan"})

STORIES_LIMIT = 16


class HomeSection(BaseModel):
    id: str
    visible: bool = True


class HomeLayout(BaseModel):
    sections: list[HomeSection] = Field(default_factory=list)


class HomeStory(BaseModel):
    kind: Literal["business", "talent"]
    slug: str
    name: str
    image_url: str | None
    youtube_video_id: str


def _normalise(sections: list[HomeSection]) -> list[HomeSection]:
    seen: set[str] = set()
    kept: list[HomeSection] = []
    for section in sections:
        if section.id in SECTIONS and section.id not in seen:
            seen.add(section.id)
            kept.append(HomeSection(id=section.id, visible=section.visible))
    kept += [
        HomeSection(id=name, visible=name in ORIGINAL and not sections)
        for name in SECTIONS
        if name not in seen
    ]
    return kept


def _read(db: Session) -> HomeLayout:
    row = db.get(SiteSetting, LAYOUT_KEY)
    stored: list[HomeSection] = []
    if row is not None:
        for part in row.value.split(","):
            name, _, flag = part.partition(":")
            stored.append(HomeSection(id=name.strip(), visible=flag.strip() != "0"))
    return HomeLayout(sections=_normalise(stored))


@public_router.get("/layout", response_model=HomeLayout)
def home_layout(db: DbSession) -> HomeLayout:
    return _read(db)


@admin_router.put("/layout", response_model=HomeLayout)
def save_home_layout(payload: HomeLayout, db: DbSession, admin: AdminUser) -> HomeLayout:
    sections = _normalise(payload.sections)
    value = ",".join(f"{s.id}:{1 if s.visible else 0}" for s in sections)
    row = db.get(SiteSetting, LAYOUT_KEY)
    if row is None:
        db.add(SiteSetting(key=LAYOUT_KEY, value=value))
    else:
        row.value = value
    db.commit()
    return _read(db)


@public_router.get("/stories", response_model=list[HomeStory])
def home_stories(db: DbSession) -> list[HomeStory]:
    """Published shops and services with an introduction video, newest
    first -- the round avatars at the top of the home page. Only what is
    already public: the same approved-only queries the directories use."""
    stories: list[tuple[object, HomeStory]] = []
    businesses = BusinessRepository(db)
    for business in db.execute(
        businesses.public_query().where(Business.youtube_video_id.is_not(None))
    ).scalars():
        stories.append(
            (
                business.approved_at or business.created_at,
                HomeStory(
                    kind="business",
                    slug=business.slug,
                    name=business.name,
                    image_url=business.logo_url,
                    youtube_video_id=business.youtube_video_id or "",
                ),
            )
        )
    talents = TalentRepository(db)
    for profile in db.execute(
        talents.public_query().where(TalentProfile.youtube_video_id.is_not(None))
    ).scalars():
        stories.append(
            (
                profile.approved_at or profile.created_at,
                HomeStory(
                    kind="talent",
                    slug=profile.slug,
                    name=profile.display_name,
                    image_url=profile.photo_url,
                    youtube_video_id=profile.youtube_video_id or "",
                ),
            )
        )
    stories.sort(key=lambda pair: str(pair[0]), reverse=True)
    return [story for _, story in stories[:STORIES_LIMIT]]
