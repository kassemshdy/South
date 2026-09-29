"""The site's own contact details and social accounts: read by anyone, set by
an admin. See ``SiteSetting``."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core.dependencies import AdminUser, DbSession
from app.models.site_setting import SITE_SETTING_KEYS, SiteSetting
from app.schemas.site_setting import SiteSettingsIn, SiteSettingsOut

public_router = APIRouter(prefix="/site-settings", tags=["site-settings"])
admin_router = APIRouter(prefix="/admin/site-settings", tags=["admin-site-settings"])


def _current(db: DbSession) -> SiteSettingsOut:
    rows = {row.key: row.value for row in db.execute(select(SiteSetting)).scalars()}
    return SiteSettingsOut(**{key: rows.get(key) for key in SITE_SETTING_KEYS})


@public_router.get("", response_model=SiteSettingsOut)
def site_settings(db: DbSession) -> SiteSettingsOut:
    return _current(db)


@admin_router.get("", response_model=SiteSettingsOut)
def admin_site_settings(db: DbSession, admin: AdminUser) -> SiteSettingsOut:
    return _current(db)


@admin_router.put("", response_model=SiteSettingsOut)
def update_site_settings(
    payload: SiteSettingsIn, db: DbSession, admin: AdminUser
) -> SiteSettingsOut:
    values = payload.model_dump()
    for key in SITE_SETTING_KEYS:
        value = values.get(key)
        row = db.get(SiteSetting, key)
        if value is None:
            if row is not None:
                db.delete(row)
        elif row is None:
            db.add(SiteSetting(key=key, value=str(value)))
        else:
            row.value = str(value)
    db.commit()
    return _current(db)
