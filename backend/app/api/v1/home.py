"""The home page's sections: their order, and the stories row.

The home page is a list of sections an administrator can reorder and hide
(the owners' request, 27 Oct 2026): the three the page always had -- the
cover photograph, the pitch with its video and chooser, the slogan band --
and the browsing sections an e-commerce home has -- search, categories,
stories, live counts, newest products, shops, services and news.

The order is one row in ``site_settings`` (``home_layout``), written as
``id:1,id:0,...`` (1 shown, 0 hidden). Reading it, an unknown id is dropped
and a section that is missing is appended **hidden**: the page visitors see
changes only when an administrator switches a section on -- except one in
``SHOWN_ON_ARRIVAL``, which shows nothing until it is given content. The manager
reviews the new sections first at ``/?preview=home``, which shows the
proposed page on live data without saving anything.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import AdminUser, DbSession
from app.models.site_setting import SiteSetting
from app.schemas.story import StoryGroupOut
from app.services.stories import home_story_groups

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
    "activities",
    "search",
    "categories",
    "stories",
    "reels",
    "stats",
    "products",
    "top_rated_products",
    "top_viewed_products",
    "most_ordered_products",
    "testimonials",
    "workshops",
    "online_workshops",
    "category_products",
    "shops",
    "talents",
    "news",
    "blog",
)

ORIGINAL = frozenset({"cover", "hero", "slogan"})

#: Sections shown as soon as they exist, placed after the section named, on a
#: fresh site and on a saved layout alike. Only for a section that renders
#: nothing until an administrator gives it content, so a deploy still changes
#: nothing a visitor sees: the activities carousel (the owners' ticket, 29
#: Oct 2026) is empty until an activity with a photograph is kept.
SHOWN_ON_ARRIVAL: dict[str, str] = {"activities": "slogan"}

class HomeSection(BaseModel):
    id: str
    visible: bool = True


class HomeLayout(BaseModel):
    sections: list[HomeSection] = Field(default_factory=list)


def _normalise(sections: list[HomeSection]) -> list[HomeSection]:
    seen: set[str] = set()
    kept: list[HomeSection] = []
    for section in sections:
        if section.id in SECTIONS and section.id not in seen:
            seen.add(section.id)
            kept.append(HomeSection(id=section.id, visible=section.visible))
    for name in SECTIONS:
        if name in seen:
            continue
        if name in SHOWN_ON_ARRIVAL:
            ids = [section.id for section in kept]
            after = SHOWN_ON_ARRIVAL[name]
            at = ids.index(after) + 1 if after in ids else len(kept)
            kept.insert(at, HomeSection(id=name, visible=True))
        else:
            kept.append(HomeSection(id=name, visible=name in ORIGINAL and not sections))
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


@public_router.get("/stories", response_model=list[StoryGroupOut])
def home_stories(db: DbSession) -> list[StoryGroupOut]:
    """The photo stories showing now, one circle per listing (see
    ``app.models.story``). Only what is already public: the listings'
    approved-only queries decide whose stories can be seen."""
    return home_story_groups(db)
