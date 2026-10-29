"""The site's menu: which sections it links, in what order, under what name.

The owners asked (29 Oct 2026) to show, hide, reorder and rename the menu's
items -- the header row, its drawer and the footer read the same list. The
items themselves are fixed: each is a page that exists, so an administrator
chooses among them and names them, but cannot point the menu somewhere new.

Stored as JSON in one ``site_settings`` row (``site_menu``). Reading it, an
unknown id is dropped and a missing one is appended **shown** under its
catalog name: a section added in code appears in the menu as it always did
until somebody decides otherwise. A blank label means the catalog's own.
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.dependencies import AdminUser, DbSession
from app.models.site_setting import SiteSetting

public_router = APIRouter(tags=["menu"])
admin_router = APIRouter(prefix="/admin", tags=["admin-menu"])

MENU_KEY = "site_menu"

#: Every item the menu can show, in the default order. The frontend maps
#: each id to its page and catalog label (``components/layout/navigation.ts``).
ITEMS: tuple[str, ...] = (
    "home",
    "products",
    "services",
    "jobs",
    "blog",
    "news",
    "workshops",
    "about",
    "contact",
)


class MenuItem(BaseModel):
    id: str
    visible: bool = True
    label_ar: str | None = Field(default=None, max_length=40)
    label_en: str | None = Field(default=None, max_length=40)

    @field_validator("label_ar", "label_en", mode="before")
    @classmethod
    def _blank_is_default(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class SiteMenu(BaseModel):
    items: list[MenuItem] = Field(default_factory=list)


def _normalise(items: list[MenuItem]) -> list[MenuItem]:
    seen: set[str] = set()
    kept: list[MenuItem] = []
    for item in items:
        if item.id in ITEMS and item.id not in seen:
            seen.add(item.id)
            kept.append(item)
    return kept + [MenuItem(id=name) for name in ITEMS if name not in seen]


def _read(db: Session) -> SiteMenu:
    row = db.get(SiteSetting, MENU_KEY)
    stored: list[MenuItem] = []
    if row is not None:
        try:
            stored = SiteMenu.model_validate_json(row.value).items
        except ValueError:
            stored = []
    return SiteMenu(items=_normalise(stored))


@public_router.get("/menu", response_model=SiteMenu)
def site_menu(db: DbSession) -> SiteMenu:
    return _read(db)


@admin_router.put("/menu", response_model=SiteMenu)
def save_site_menu(payload: SiteMenu, db: DbSession, admin: AdminUser) -> SiteMenu:
    menu = SiteMenu(items=_normalise(payload.items))
    value = json.dumps(menu.model_dump(), ensure_ascii=False)
    row = db.get(SiteSetting, MENU_KEY)
    if row is None:
        db.add(SiteSetting(key=MENU_KEY, value=value))
    else:
        row.value = value
    db.commit()
    return _read(db)
