"""The admin panel's «Connect Google Drive» card. See ``app.services.gdrive_oauth``.

Every staff role reads the status (it holds no secret: an email address, a
folder link and the last run's counts). Connecting, disconnecting and a copy
on demand are the manager's (``app/core/permissions.py``).
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.dependencies import AdminUser, AppSettings, DbSession
from app.core.errors import AppError
from app.core.i18n import translate
from app.models.enums import StaffRole, UserRole
from app.models.user import User
from app.schemas.common import MessageResponse
from app.services import drive_replica, gdrive_oauth
from app.storage.factory import get_storage

logger = logging.getLogger("app.api.gdrive")

admin_router = APIRouter(prefix="/admin/gdrive", tags=["admin-gdrive"])
public_router = APIRouter(prefix="/integrations/gdrive", tags=["integrations"])


class LastRunOut(BaseModel):
    at: str
    copied: int | None = None
    already: int | None = None
    failed: int | None = None
    error: str | None = None


class GdriveStatusOut(BaseModel):
    #: The OAuth client is configured on the server, so the button can work.
    available: bool
    #: A service account in the environment is doing the copy instead.
    service_account: bool
    connected: bool
    email: str | None = None
    folder_url: str | None = None
    connected_at: str | None = None
    last_run: LastRunOut | None = None


class ConnectOut(BaseModel):
    url: str


def _status(db: DbSession, settings: AppSettings) -> GdriveStatusOut:
    connection = gdrive_oauth.load(db, settings)
    last = gdrive_oauth.last_run(db)
    return GdriveStatusOut(
        available=gdrive_oauth.available(settings),
        service_account=bool(settings.gdrive_folder_id and settings.gdrive_service_account_json),
        connected=connection is not None,
        email=connection.email if connection else None,
        folder_url=(
            f"https://drive.google.com/drive/folders/{connection.folder_id}" if connection else None
        ),
        connected_at=connection.connected_at if connection else None,
        last_run=LastRunOut(**last) if last else None,
    )


@admin_router.get("", response_model=GdriveStatusOut)
def gdrive_status(db: DbSession, settings: AppSettings, admin: AdminUser) -> GdriveStatusOut:
    return _status(db, settings)


@admin_router.post("/connect", response_model=ConnectOut)
def gdrive_connect(settings: AppSettings, admin: AdminUser) -> ConnectOut:
    if not gdrive_oauth.available(settings):
        raise AppError("gdrive.not_configured", status_code=409)
    return ConnectOut(url=gdrive_oauth.start_url(settings, admin.id))


@admin_router.post("/disconnect", response_model=GdriveStatusOut)
def gdrive_disconnect(db: DbSession, settings: AppSettings, admin: AdminUser) -> GdriveStatusOut:
    with httpx.Client(timeout=20) as client:
        gdrive_oauth.forget(db, settings, client)
    return _status(db, settings)


@admin_router.post("/run", response_model=MessageResponse)
def gdrive_run(
    background: BackgroundTasks, db: DbSession, settings: AppSettings, admin: AdminUser
) -> MessageResponse:
    if gdrive_oauth.load(db, settings) is None and not (
        settings.gdrive_folder_id and settings.gdrive_service_account_json
    ):
        raise AppError("gdrive.not_connected", status_code=409)
    background.add_task(_run_now, settings)
    return MessageResponse(message=translate("gdrive.started"))


def _run_now(settings: AppSettings) -> None:
    try:
        drive_replica.replicate_if_first(settings, get_storage())
    except Exception:  # recorded on the card by replicate_configured
        logger.exception("Google Drive copy on demand failed")


@public_router.get("/callback", include_in_schema=False)
def gdrive_callback(
    db: DbSession,
    settings: AppSettings,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """Where Google sends the manager back. No session here: the signed
    ``state`` says who started it, and it must still be an active manager."""
    back = settings.public_base_url.rstrip("/") + "/admin/site-settings?gdrive="
    admin_id = gdrive_oauth.read_state(settings, state) if state else None
    user = db.get(User, admin_id) if admin_id else None
    if (
        error
        or not code
        or user is None
        or not user.is_active
        or user.role != UserRole.ADMIN
        or user.staff_role != StaffRole.MANAGER
        or not gdrive_oauth.available(settings)
    ):
        return RedirectResponse(back + "error", status_code=303)
    try:
        with httpx.Client(timeout=30) as client:
            gdrive_oauth.finish(db, settings, code, client)
    except (httpx.HTTPError, ValueError, KeyError):
        logger.exception("Google Drive connection failed")
        return RedirectResponse(back + "error", status_code=303)
    return RedirectResponse(back + "connected", status_code=303)
