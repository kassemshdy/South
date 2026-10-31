"""A shop's own Shopify store, through the shared Shopify Connector.

Every route answers 404 while ``CONNECTOR_URL`` and its companions are
unset, which is also how the dashboard knows not to offer the card.

The owner routes keep the paths the dashboard already uses and ask the
connector; the connector's webhooks arrive at
``/integrations/connector/webhooks``, authenticated by its signature (not by
our session), checked before anything is read.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select

from app.core.config import Settings
from app.core.dependencies import AppSettings, DbSession, OwnedBusiness
from app.core.errors import AppError, NotFoundError
from app.core.i18n import translate
from app.models.business import Business, BusinessItem
from app.models.integration import IntegrationOutbox, ItemLink
from app.schemas.common import MessageResponse
from app.schemas.integration import (
    ShopifyInstallIn,
    ShopifyInstallOut,
    ShopifyStatusOut,
    SubdomainIn,
    SyncQueuedOut,
)
from app.services.connector import (
    ConnectorUnavailable,
    StoreConnectionService,
    handle_event,
    verify_signature,
)

logger = logging.getLogger(__name__)

owner_router = APIRouter(tags=["integrations"])
public_router = APIRouter(tags=["integrations"])

HTTP_TIMEOUT = 20.0


def get_http_client() -> Iterator[httpx.Client]:
    """One outbound client per request; replaced in tests."""
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        yield client


HttpClient = Annotated[httpx.Client, Depends(get_http_client)]


def require_connector(settings: AppSettings) -> Settings:
    if not settings.connector_enabled:
        raise NotFoundError("shopify.unavailable")
    return settings


ConnectorSettings = Annotated[Settings, Depends(require_connector)]


def _unavailable() -> AppError:
    return AppError("shopify.unavailable", code="connector_unavailable", status_code=503)


def _status(
    db: DbSession, business: Business, tenant: dict[str, Any], store: dict[str, Any] | None
) -> ShopifyStatusOut:
    base = ShopifyStatusOut(
        connected=False,
        signup_url=tenant.get("signup_url"),
        subdomains_available=bool(tenant.get("subdomains_available")),
        subdomain_base=tenant.get("subdomain_base") or "",
    )
    if store is None:
        return base
    synced = db.scalar(
        select(func.count())
        .select_from(ItemLink)
        .join(BusinessItem, BusinessItem.id == ItemLink.item_id)
        .where(BusinessItem.business_id == business.id, ItemLink.state == "SYNCED")
    )
    pending = db.scalar(
        select(func.count())
        .select_from(IntegrationOutbox)
        .where(IntegrationOutbox.business_id == business.id, IntegrationOutbox.done_at.is_(None))
    )
    return base.model_copy(
        update={
            "connected": store.get("status") == "CONNECTED",
            "shop_domain": store.get("shop_domain"),
            "status": store.get("status"),
            "storefront_url": store.get("storefront_url"),
            "currency": store.get("currency"),
            "subdomain": store.get("subdomain"),
            "subdomain_hostname": store.get("subdomain_hostname"),
            "subdomain_live": bool(store.get("subdomain_live")),
            "connected_at": store.get("connected_at"),
            "last_sync_at": store.get("last_sync_at"),
            "last_error": store.get("last_error"),
            "synced_products": synced or 0,
            # Ours still to send, plus the connector's still to push.
            "pending_pushes": (pending or 0) + int(store.get("jobs_pending") or 0),
        }
    )


@owner_router.get("/businesses/{business_id}/shopify", response_model=ShopifyStatusOut)
def shopify_status(
    business: OwnedBusiness, db: DbSession, settings: ConnectorSettings, http: HttpClient
) -> ShopifyStatusOut:
    try:
        tenant, store = StoreConnectionService(db, settings, http).status(business)
    except ConnectorUnavailable as exc:
        raise _unavailable() from exc
    return _status(db, business, tenant, store)


@owner_router.post("/businesses/{business_id}/shopify/install", response_model=ShopifyInstallOut)
def shopify_install(
    payload: ShopifyInstallIn,
    business: OwnedBusiness,
    db: DbSession,
    settings: ConnectorSettings,
    http: HttpClient,
) -> ShopifyInstallOut:
    """The URL the browser goes to next; the connector sends it back here."""
    try:
        url = StoreConnectionService(db, settings, http).start(business, payload.shop)
    except ConnectorUnavailable as exc:
        raise _unavailable() from exc
    return ShopifyInstallOut(authorize_url=url)


@owner_router.post("/businesses/{business_id}/shopify/sync", response_model=SyncQueuedOut)
def shopify_sync(
    business: OwnedBusiness, db: DbSession, settings: ConnectorSettings, http: HttpClient
) -> SyncQueuedOut:
    return SyncQueuedOut(queued=StoreConnectionService(db, settings, http).sync_now(business))


@owner_router.delete("/businesses/{business_id}/shopify", response_model=MessageResponse)
def shopify_disconnect(
    business: OwnedBusiness, db: DbSession, settings: ConnectorSettings, http: HttpClient
) -> MessageResponse:
    try:
        StoreConnectionService(db, settings, http).disconnect(business)
    except ConnectorUnavailable as exc:
        raise _unavailable() from exc
    return MessageResponse(message=translate("shopify.disconnected"))


@owner_router.post("/businesses/{business_id}/shopify/subdomain", response_model=ShopifyStatusOut)
def shopify_subdomain(
    payload: SubdomainIn,
    business: OwnedBusiness,
    db: DbSession,
    settings: ConnectorSettings,
    http: HttpClient,
) -> ShopifyStatusOut:
    service = StoreConnectionService(db, settings, http)
    try:
        service.subdomain(business, payload.subdomain)
        tenant, store = service.status(business)
    except ConnectorUnavailable as exc:
        raise _unavailable() from exc
    return _status(db, business, tenant, store)


@public_router.post("/integrations/connector/webhooks", include_in_schema=False)
async def connector_webhook(
    request: Request, db: DbSession, settings: ConnectorSettings
) -> Response:
    body = await request.body()
    assert settings.connector_webhook_secret
    if not verify_signature(
        settings.connector_webhook_secret, body, request.headers.get("X-Connector-Signature")
    ):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        envelope = json.loads(body)
        event, data = str(envelope["event"]), dict(envelope["data"])
    except (ValueError, KeyError, TypeError):
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    # Synchronous database work; keep it off the event loop.
    await run_in_threadpool(handle_event, db, event, data)
    return Response(status_code=status.HTTP_200_OK)
