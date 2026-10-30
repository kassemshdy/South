"""A shop's own Shopify store: connect, push, and the address visitors get.

Every route answers 404 while ``SHOPIFY_API_KEY`` and its companions are
unset, which is also how the dashboard knows not to offer the card.

The OAuth callback and the webhooks are unauthenticated by our session by
nature -- Shopify calls them -- and are authenticated by Shopify's HMAC
instead, checked before anything is read.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.core.config import Settings
from app.core.dependencies import AppSettings, CurrentUser, DbSession, OwnedBusiness
from app.core.errors import AppError, NotFoundError
from app.core.i18n import translate
from app.integrations.shopify.client import verify_webhook_hmac
from app.models.business import Business, BusinessItem
from app.models.integration import IntegrationOutbox, ShopifyProductLink
from app.schemas.common import MessageResponse
from app.schemas.integration import (
    ShopifyInstallIn,
    ShopifyInstallOut,
    ShopifyStatusOut,
    SubdomainIn,
    SyncQueuedOut,
)
from app.services.shopify_connection import ShopifyConnectionService, dashboard_url
from app.services.store_subdomain import StoreSubdomainService

logger = logging.getLogger(__name__)

owner_router = APIRouter(tags=["integrations"])
public_router = APIRouter(tags=["integrations"])

HTTP_TIMEOUT = 20.0


def get_http_client() -> Iterator[httpx.Client]:
    """One outbound client per request; replaced in tests."""
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        yield client


HttpClient = Annotated[httpx.Client, Depends(get_http_client)]


def require_shopify(settings: AppSettings) -> Settings:
    if not settings.shopify_enabled:
        raise NotFoundError("shopify.unavailable")
    return settings


ShopifySettings = Annotated[Settings, Depends(require_shopify)]


def _status(db: DbSession, business: Business, settings: Settings) -> ShopifyStatusOut:
    connection = business.shopify_connection
    base = ShopifyStatusOut(
        connected=False,
        signup_url=settings.shopify_signup_url,
        subdomains_available=settings.cloudflare_enabled,
        subdomain_base=settings.store_subdomain_base,
    )
    if connection is None:
        return base
    synced = db.scalar(
        select(func.count())
        .select_from(ShopifyProductLink)
        .join(BusinessItem, BusinessItem.id == ShopifyProductLink.item_id)
        .where(BusinessItem.business_id == business.id)
    )
    pending = db.scalar(
        select(func.count())
        .select_from(IntegrationOutbox)
        .where(IntegrationOutbox.business_id == business.id, IntegrationOutbox.done_at.is_(None))
    )
    hostname = (
        f"{connection.subdomain}.{settings.store_subdomain_base}" if connection.subdomain else None
    )
    return base.model_copy(
        update={
            "connected": connection.is_live,
            "shop_domain": connection.shop_domain,
            "status": connection.status,
            "storefront_url": f"https://{connection.storefront_host}",
            "currency": connection.currency,
            "subdomain": connection.subdomain,
            "subdomain_hostname": hostname,
            "subdomain_live": hostname is not None and connection.primary_domain == hostname,
            "connected_at": connection.connected_at,
            "last_sync_at": connection.last_sync_at,
            "last_error": connection.last_error,
            "synced_products": synced or 0,
            "pending_pushes": pending or 0,
        }
    )


@owner_router.get("/businesses/{business_id}/shopify", response_model=ShopifyStatusOut)
def shopify_status(
    business: OwnedBusiness, db: DbSession, settings: ShopifySettings
) -> ShopifyStatusOut:
    return _status(db, business, settings)


@owner_router.post("/businesses/{business_id}/shopify/install", response_model=ShopifyInstallOut)
def shopify_install(
    payload: ShopifyInstallIn,
    business: OwnedBusiness,
    user: CurrentUser,
    db: DbSession,
    settings: ShopifySettings,
    http: HttpClient,
) -> ShopifyInstallOut:
    """The URL the browser goes to next; the route itself redirects nothing."""
    url = ShopifyConnectionService(db, settings, http).start(business, user, payload.shop)
    return ShopifyInstallOut(authorize_url=url)


@owner_router.post("/businesses/{business_id}/shopify/sync", response_model=SyncQueuedOut)
def shopify_sync(
    business: OwnedBusiness, db: DbSession, settings: ShopifySettings, http: HttpClient
) -> SyncQueuedOut:
    return SyncQueuedOut(queued=ShopifyConnectionService(db, settings, http).sync_now(business))


@owner_router.delete("/businesses/{business_id}/shopify", response_model=MessageResponse)
def shopify_disconnect(
    business: OwnedBusiness, db: DbSession, settings: ShopifySettings, http: HttpClient
) -> MessageResponse:
    ShopifyConnectionService(db, settings, http).disconnect(business)
    return MessageResponse(message=translate("shopify.disconnected"))


@owner_router.post("/businesses/{business_id}/shopify/subdomain", response_model=ShopifyStatusOut)
def shopify_subdomain(
    payload: SubdomainIn,
    business: OwnedBusiness,
    db: DbSession,
    settings: ShopifySettings,
    http: HttpClient,
) -> ShopifyStatusOut:
    connection = business.shopify_connection
    if connection is None:
        raise NotFoundError("shopify.not_connected")
    StoreSubdomainService(settings, http).assign(db, connection, payload.subdomain)
    return _status(db, business, settings)


@public_router.get("/integrations/shopify/callback", include_in_schema=False)
def shopify_callback(
    request: Request, db: DbSession, settings: ShopifySettings, http: HttpClient
) -> RedirectResponse:
    """Where Shopify sends the owner back. Always ends on their dashboard."""
    service = ShopifyConnectionService(db, settings, http)
    params = dict(request.query_params)
    try:
        business = service.complete(params)
    except AppError as exc:
        logger.warning("Shopify callback refused: %s", exc.code)
        try:
            business_id = service.read_state(params.get("state", ""))["bid"]
        except AppError:
            return RedirectResponse(settings.public_base_url.rstrip("/") + "/dashboard")
        return RedirectResponse(dashboard_url(settings, business_id, exc.code))
    return RedirectResponse(dashboard_url(settings, business.id, "connected"))


@public_router.post("/integrations/shopify/webhooks", include_in_schema=False)
async def shopify_webhook(
    request: Request, db: DbSession, settings: ShopifySettings, http: HttpClient
) -> Response:
    body = await request.body()
    assert settings.shopify_api_secret
    if not verify_webhook_hmac(
        body, request.headers.get("X-Shopify-Hmac-Sha256"), settings.shopify_api_secret
    ):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    topic = request.headers.get("X-Shopify-Topic", "")
    shop = request.headers.get("X-Shopify-Shop-Domain", "")
    # The handler is synchronous database work; keep it off the event loop.
    await run_in_threadpool(
        ShopifyConnectionService(db, settings, http).handle_webhook, topic, shop
    )
    return Response(status_code=status.HTTP_200_OK)
