"""The site's static pages: read by anyone, written by an admin. See ``Page``."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core.dependencies import AdminUser, DbSession
from app.core.errors import NotFoundError
from app.models.page import PAGE_KEYS, Page
from app.schemas.page import PageIn, PageOut

public_router = APIRouter(prefix="/pages", tags=["pages"])
admin_router = APIRouter(prefix="/admin/pages", tags=["admin-pages"])


def _known(key: str) -> str:
    if key not in PAGE_KEYS:
        raise NotFoundError()
    return key


def _out(key: str, row: Page | None) -> PageOut:
    if row is None:
        return PageOut(key=key)
    return PageOut.model_validate(row, from_attributes=True)


@public_router.get("/{key}", response_model=PageOut)
def page(key: str, db: DbSession) -> PageOut:
    return _out(key, db.get(Page, _known(key)))


@admin_router.get("", response_model=list[PageOut])
def admin_pages(db: DbSession, admin: AdminUser) -> list[PageOut]:
    rows = {row.key: row for row in db.execute(select(Page)).scalars()}
    return [_out(key, rows.get(key)) for key in PAGE_KEYS]


@admin_router.put("/{key}", response_model=PageOut)
def update_page(key: str, payload: PageIn, db: DbSession, admin: AdminUser) -> PageOut:
    row = db.get(Page, _known(key))
    values = payload.model_dump()
    if all(value is None for value in values.values()):
        # Nothing left: the page is its built-in text again.
        if row is not None:
            db.delete(row)
            db.commit()
        return PageOut(key=key)
    if row is None:
        row = Page(key=key)
        db.add(row)
    for field, value in values.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _out(key, row)
