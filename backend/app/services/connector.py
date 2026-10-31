"""Janoubona as a client of the shared Shopify Connector.

The connector (its own repository and service) holds the Shopify app, every
store's token and the Cloudflare zone; Janoubona only:

- asks it for an authorize URL when an owner presses Connect,
- tells it what each product is (through the outbox, so a rolled-back edit
  sends nothing and a crash after commit loses nothing),
- mirrors what it reports back through signed webhooks: the store's status
  and address in ``StoreLink``, each product's buy link in ``ItemLink``.

Our ids are the connector's refs: a business id is a ``store_ref``, an item
id a ``product_ref``. The connector never learns anything else about them.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ConflictError, NotFoundError, ValidationError
from app.models.business import Business, BusinessItem
from app.models.enums import BusinessStatus
from app.models.integration import IntegrationOutbox, ItemLink, StoreLink
from app.services import outbox

logger = logging.getLogger(__name__)

SIGNATURE_TOLERANCE_SECONDS = 300

#: The connector's error codes, mapped to the messages our owners read.
_ERRORS: dict[str, tuple[type[AppError], str, str]] = {
    "bad_shop": (ValidationError, "shopify.bad_shop", "shopify_bad_shop"),
    "bad_subdomain": (ValidationError, "shopify.bad_subdomain", "bad_subdomain"),
    "reserved_subdomain": (ValidationError, "shopify.reserved_subdomain", "reserved_subdomain"),
    "subdomain_taken": (ConflictError, "shopify.subdomain_taken", "subdomain_taken"),
    "subdomain_failed": (ConflictError, "shopify.subdomain_failed", "subdomain_failed"),
    "subdomains_off": (NotFoundError, "shopify.subdomains_off", "subdomains_off"),
    "store_not_found": (NotFoundError, "shopify.not_connected", "not_connected"),
    "not_connected": (NotFoundError, "shopify.not_connected", "not_connected"),
}


class ConnectorUnavailable(Exception):
    """The connector could not be reached or answered unexpectedly."""


class ConnectorClient:
    def __init__(self, settings: Settings, http: httpx.Client) -> None:
        assert settings.connector_url and settings.connector_api_key
        self._base = settings.connector_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {settings.connector_api_key}"}
        self._http = http

    def _call(self, method: str, path: str, json: Any = None) -> dict[str, Any]:
        try:
            response = self._http.request(
                method, self._base + path, headers=self._headers, json=json
            )
        except httpx.HTTPError as exc:
            raise ConnectorUnavailable(type(exc).__name__) from exc
        if response.status_code == 204:
            return {}
        try:
            body: dict[str, Any] = response.json()
        except ValueError as exc:
            raise ConnectorUnavailable(f"connector answered {response.status_code}") from exc
        if response.status_code >= 400:
            code = (body.get("error") or {}).get("code", "")
            if code in _ERRORS:
                error_class, message_key, our_code = _ERRORS[code]
                raise error_class(message_key, code=our_code)
            raise ConnectorUnavailable(f"connector answered {response.status_code} {code}")
        return body

    def tenant(self) -> dict[str, Any]:
        return self._call("GET", "/v1/tenant")

    def connect(self, store_ref: str, shop: str, return_url: str) -> str:
        body = self._call(
            "POST", f"/v1/stores/{store_ref}/connect", {"shop": shop, "return_url": return_url}
        )
        return str(body["authorize_url"])

    def store(self, store_ref: str) -> dict[str, Any] | None:
        try:
            return self._call("GET", f"/v1/stores/{store_ref}")
        except NotFoundError:
            return None

    def disconnect(self, store_ref: str) -> None:
        try:
            self._call("DELETE", f"/v1/stores/{store_ref}")
        except NotFoundError:
            return

    def subdomain(self, store_ref: str, subdomain: str) -> dict[str, Any]:
        return self._call("POST", f"/v1/stores/{store_ref}/subdomain", {"subdomain": subdomain})

    def put_product(
        self, store_ref: str, product_ref: str, product: dict[str, Any]
    ) -> dict[str, Any]:
        return self._call("PUT", f"/v1/stores/{store_ref}/products/{product_ref}", product)

    def delete_product(self, store_ref: str, product_ref: str) -> None:
        try:
            self._call("DELETE", f"/v1/stores/{store_ref}/products/{product_ref}")
        except NotFoundError:
            return


# --- What a product is, for the connector ---------------------------------------


def _absolute(url: str, settings: Settings) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return settings.public_base_url.rstrip("/") + "/" + url.lstrip("/")


def product_payload(item: BusinessItem, settings: Settings) -> dict[str, Any]:
    images = [item.image_url] if item.image_url else []
    images += [image.url for image in item.images]
    urls = [_absolute(u, settings) for u in dict.fromkeys(images)]
    return {
        "title": item.title,
        "description": item.description,
        "price": str(item.price) if item.price is not None else None,
        "currency": item.currency.value,
        # Shopify downloads images itself, so only public https addresses.
        "images": [u for u in urls if u.startswith("https://")],
        "available": item.is_available and item.business.status is BusinessStatus.APPROVED,
        "vendor": item.brand_name,
    }


def _record_item(db: Session, item_id: uuid.UUID, data: dict[str, Any]) -> None:
    link = db.scalars(select(ItemLink).where(ItemLink.item_id == item_id)).first()
    if link is None:
        link = ItemLink(item_id=item_id, state=str(data.get("state") or "QUEUED"))
        db.add(link)
    link.state = str(data.get("state") or link.state)
    link.handle = data.get("handle")
    link.active = bool(data.get("active"))
    link.buy_url = data.get("buy_url")
    link.error = data.get("error")
    if link.state == "SYNCED":
        link.synced_at = datetime.now(UTC)


def make_handlers(settings: Settings, http: httpx.Client) -> dict[str, outbox.Handler]:
    """The outbox handlers, bound to one HTTP client for the worker's life."""
    client = ConnectorClient(settings, http)

    def upsert(db: Session, entry: IntegrationOutbox) -> None:
        item = db.get(BusinessItem, uuid.UUID(entry.payload["item_id"]))
        if item is None or item.business_id != entry.business_id:
            return
        link = item.business.store_link
        if link is None or not link.is_live:
            return
        reply = client.put_product(
            str(item.business_id), str(item.id), product_payload(item, settings)
        )
        _record_item(db, item.id, reply)
        logger.info(
            "Product sent to the connector",
            extra={"business_id": str(item.business_id), "item_id": str(item.id)},
        )

    def delete(db: Session, entry: IntegrationOutbox) -> None:
        client.delete_product(str(entry.business_id), str(entry.payload["item_id"]))
        logger.info("Product removal sent", extra={"business_id": str(entry.business_id)})

    return {outbox.ITEM_UPSERT: upsert, outbox.ITEM_DELETE: delete}


# --- The owner's actions ----------------------------------------------------------


def dashboard_url(settings: Settings, business_id: uuid.UUID) -> str:
    return settings.public_base_url.rstrip("/") + f"/dashboard/businesses/{business_id}/items"


class StoreConnectionService:
    def __init__(self, db: Session, settings: Settings, http: httpx.Client) -> None:
        self._db = db
        self._settings = settings
        self._client = ConnectorClient(settings, http)

    def start(self, business: Business, shop: str) -> str:
        if business.status is not BusinessStatus.APPROVED:
            raise ValidationError("shopify.not_approved", code="shopify_not_approved")
        return self._client.connect(
            str(business.id), shop, dashboard_url(self._settings, business.id)
        )

    def status(self, business: Business) -> tuple[dict[str, Any], dict[str, Any] | None]:
        return self._client.tenant(), self._client.store(str(business.id))

    def disconnect(self, business: Business) -> None:
        self._client.disconnect(str(business.id))
        link = business.store_link
        if link is not None:
            self._db.delete(link)
        self._forget_item_links(business)
        self._db.commit()

    def subdomain(self, business: Business, subdomain: str) -> dict[str, Any]:
        reply = self._client.subdomain(str(business.id), subdomain)
        _record_store(self._db, business, reply)
        self._db.commit()
        return reply

    def sync_now(self, business: Business) -> int:
        link = business.store_link
        if link is None or not link.is_live:
            raise NotFoundError("shopify.not_connected")
        count = outbox.enqueue_full_sync(self._db, business)
        self._db.commit()
        return count

    def _forget_item_links(self, business: Business) -> None:
        for link in self._db.scalars(
            select(ItemLink).join(BusinessItem).where(BusinessItem.business_id == business.id)
        ):
            self._db.delete(link)


# --- Webhooks from the connector ---------------------------------------------------


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    """``t=<unix>,v1=<hex HMAC-SHA256(secret, "{t}." + body)>``, at most 5 minutes old."""
    if not header:
        return False
    try:
        parts = dict(p.split("=", 1) for p in header.split(","))
        timestamp = int(parts["t"])
    except (ValueError, KeyError):
        return False
    if abs(time.time() - timestamp) > SIGNATURE_TOLERANCE_SECONDS:
        return False
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, parts.get("v1", ""))


def _record_store(db: Session, business: Business, data: dict[str, Any]) -> StoreLink:
    link = business.store_link
    if link is None:
        link = StoreLink(business_id=business.id, status=str(data.get("status") or "PENDING"))
        db.add(link)
        business.store_link = link
    link.status = str(data.get("status") or link.status)
    link.shop_domain = data.get("shop_domain")
    link.storefront_url = data.get("storefront_url")
    link.subdomain = data.get("subdomain")
    link.subdomain_hostname = data.get("subdomain_hostname")
    link.currency = data.get("currency")
    link.last_error = data.get("last_error")
    return link


def _uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def handle_event(db: Session, event: str, data: dict[str, Any]) -> None:
    business_id = _uuid(data.get("store_ref"))
    business = db.get(Business, business_id) if business_id else None
    if business is None:
        return
    if event in ("store.connected", "store.updated"):
        was_live = business.store_link is not None and business.store_link.is_live
        link = _record_store(db, business, data)
        if event == "store.connected":
            link.connected_at = datetime.now(UTC)
        db.flush()
        if link.is_live and not was_live:
            # Newly connected: send every product.
            outbox.enqueue_full_sync(db, business)
    elif event == "store.disconnected":
        if business.store_link is not None:
            db.delete(business.store_link)
        for item_link in db.scalars(
            select(ItemLink).join(BusinessItem).where(BusinessItem.business_id == business.id)
        ):
            db.delete(item_link)
    elif event in ("product.synced", "product.failed"):
        item_id = _uuid(data.get("product_ref"))
        item = db.get(BusinessItem, item_id) if item_id else None
        if item is not None and item.business_id == business.id:
            _record_item(db, item.id, data)
    db.commit()


# --- When a listing or an account is deleted ----------------------------------------


def remember_stores(businesses: list[Business]) -> list[str]:
    return [str(b.id) for b in businesses if b.store_link is not None]


def forget_stores(store_refs: list[str], settings: Settings) -> None:
    """After the commit: tell the connector, which revokes and removes the DNS record."""
    if not store_refs or not settings.connector_enabled:
        return
    with httpx.Client(timeout=20) as http:
        client = ConnectorClient(settings, http)
        for ref in store_refs:
            try:
                client.disconnect(ref)
            except Exception:
                logger.warning("Telling the connector a listing was deleted failed", exc_info=True)
