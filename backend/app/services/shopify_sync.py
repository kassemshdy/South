"""Janobona -> Shopify: what a shop's product becomes in its own store.

One direction for now (the owners' decision, 30 Oct 2026): owners keep
editing on Janobona and the store follows. Variants, stock and orders are
the store's. Each ``BusinessItem`` becomes one Shopify product with a
single default variant, created with ``productSet`` the first time and
updated in place after that through ``ShopifyProductLink``.

Two things are never guessed:

- **Currency.** A product priced in a currency the store does not sell in
  is not pushed -- converting LBP to USD at a rate we made up would put a
  wrong price on someone's shop. The reason is recorded on the connection.
- **A missing price.** A product with no price has no checkout; it is not
  pushed either.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.crypto import decrypt_secret
from app.integrations.shopify.client import ShopifyClient, ShopifyError, raise_user_errors
from app.models.business import BusinessItem
from app.models.enums import BusinessStatus
from app.models.integration import IntegrationOutbox, ShopifyConnection, ShopifyProductLink
from app.services import outbox

logger = logging.getLogger(__name__)

SHOP_QUERY = "{ shop { currencyCode primaryDomain { host } } }"

PRODUCT_SET = """
mutation productSet($input: ProductSetInput!) {
  productSet(synchronous: true, input: $input) {
    product { id handle status variants(first: 1) { nodes { id } } }
    userErrors { field message }
  }
}
"""

PRODUCT_DELETE = """
mutation productDelete($input: ProductDeleteInput!) {
  productDelete(input: $input) { deletedProductId userErrors { field message } }
}
"""

PUBLICATIONS = "{ publications(first: 20) { nodes { id name } } }"

PUBLISH = """
mutation publish($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) { userErrors { field message } }
}
"""

ONLINE_STORE = "Online Store"

WEBHOOK_SUBSCRIBE = """
mutation subscribe($topic: WebhookSubscriptionTopic!, $url: URL!) {
  webhookSubscriptionCreate(
    topic: $topic, webhookSubscription: {callbackUrl: $url, format: JSON}
  ) { userErrors { field message } }
}
"""

#: The events the app listens for. Subscribed from code on every connect,
#: because a Partner Dashboard app has no form for them; the compliance
#: topics are the exception and are set by hand in the app's configuration.
WEBHOOK_TOPICS = ("APP_UNINSTALLED", "SHOP_UPDATE")


class SkipItem(Exception):
    """This product is deliberately not pushed; the reason is for the owner."""


def client_for(
    connection: ShopifyConnection, settings: Settings, http: httpx.Client
) -> ShopifyClient:
    token = decrypt_secret(settings, connection.access_token_enc)
    return ShopifyClient(http, connection.shop_domain, token, settings.shopify_api_version)


def refresh_shop(connection: ShopifyConnection, client: ShopifyClient) -> None:
    shop = client.graphql(SHOP_QUERY).get("shop") or {}
    connection.currency = shop.get("currencyCode")
    host = (shop.get("primaryDomain") or {}).get("host")
    if host:
        connection.primary_domain = host


def register_webhooks(client: ShopifyClient, callback_url: str) -> None:
    """Subscribe the store to ``WEBHOOK_TOPICS``; an existing one is fine."""
    for topic in WEBHOOK_TOPICS:
        result = (
            client.graphql(WEBHOOK_SUBSCRIBE, {"topic": topic, "url": callback_url}).get(
                "webhookSubscriptionCreate"
            )
            or {}
        )
        errors = [
            e
            for e in result.get("userErrors") or []
            if "taken" not in str(e.get("message", "")).lower()
            and "already" not in str(e.get("message", "")).lower()
        ]
        raise_user_errors({"userErrors": errors})


def _absolute(url: str, settings: Settings) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return settings.public_base_url.rstrip("/") + "/" + url.lstrip("/")


def _description_html(text: str | None) -> str:
    if not text:
        return ""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(
        "<p>" + html.escape(p).replace("\n", "<br>") + "</p>" for p in paragraphs
    )


def product_input(
    item: BusinessItem, connection: ShopifyConnection, settings: Settings
) -> dict[str, Any]:
    """The ``ProductSetInput`` for an item, without its Shopify id."""
    if item.price is None:
        raise SkipItem("no price")
    if connection.currency and item.currency.value != connection.currency:
        raise SkipItem(
            f"priced in {item.currency.value}, the store sells in {connection.currency}"
        )
    sellable = item.is_available and item.business.status is BusinessStatus.APPROVED
    images = [item.image_url] if item.image_url else []
    images += [image.url for image in item.images]
    data: dict[str, Any] = {
        "title": item.title,
        "descriptionHtml": _description_html(item.description),
        "status": "ACTIVE" if sellable else "DRAFT",
        "productOptions": [{"name": "Title", "values": [{"name": "Default Title"}]}],
        "variants": [
            {
                "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                "price": f"{item.price:.2f}",
            }
        ],
    }
    if item.brand_name:
        data["vendor"] = item.brand_name
    if images:
        data["files"] = [
            {"originalSource": _absolute(url, settings), "contentType": "IMAGE"}
            for url in dict.fromkeys(images)
        ]
    return data


def content_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def _online_store_publication(client: ShopifyClient) -> str | None:
    nodes = (client.graphql(PUBLICATIONS).get("publications") or {}).get("nodes") or []
    for node in nodes:
        if node.get("name") == ONLINE_STORE:
            return str(node["id"])
    return None


def push_item(
    db: Session, item: BusinessItem, connection: ShopifyConnection, client: ShopifyClient,
    settings: Settings,
) -> ShopifyProductLink | None:
    link = item.shopify_link
    try:
        data = product_input(item, connection, settings)
    except SkipItem as skip:
        connection.last_error = f"{item.title}: {skip}"
        logger.info(
            "Shopify product skipped",
            extra={"business_id": str(item.business_id), "item_id": str(item.id),
                   "reason": str(skip)},
        )
        return link
    digest = content_hash(data)
    if link is not None and link.synced_hash == digest:
        logger.debug("Shopify product unchanged", extra={"item_id": str(item.id)})
        return link
    action = "updated" if link is not None else "created"
    if link is not None:
        data["id"] = link.shopify_product_id
    result = client.graphql(PRODUCT_SET, {"input": data}).get("productSet") or {}
    raise_user_errors(result)
    product = result.get("product") or {}
    variants = (product.get("variants") or {}).get("nodes") or []
    now = datetime.now(UTC)
    if link is None:
        link = ShopifyProductLink(item_id=item.id)
        db.add(link)
        publication = _online_store_publication(client)
        if publication:
            published = client.graphql(
                PUBLISH, {"id": product["id"], "input": [{"publicationId": publication}]}
            ).get("publishablePublish") or {}
            raise_user_errors(published)
    link.shopify_product_id = str(product["id"])
    link.shopify_variant_id = str(variants[0]["id"]) if variants else None
    link.handle = str(product.get("handle") or "")
    link.active = product.get("status") == "ACTIVE"
    link.synced_hash = digest
    link.synced_at = now
    connection.last_sync_at = now
    # Ids only, like every other log line: a success must be visible, or a
    # quiet log cannot tell "sent" from "never tried".
    logger.info(
        "Shopify product pushed",
        extra={"business_id": str(item.business_id), "item_id": str(item.id),
               "action": action},
    )
    return link


def _live_connection(db: Session, business_id: uuid.UUID) -> ShopifyConnection | None:
    from sqlalchemy import select

    connection = db.scalars(
        select(ShopifyConnection).where(ShopifyConnection.business_id == business_id)
    ).first()
    return connection if connection is not None and connection.is_live else None


def make_handlers(settings: Settings, http: httpx.Client) -> dict[str, outbox.Handler]:
    """The outbox handlers, bound to one HTTP client for the worker's life."""

    def upsert(db: Session, entry: IntegrationOutbox) -> None:
        connection = _live_connection(db, entry.business_id)
        item = db.get(BusinessItem, uuid.UUID(entry.payload["item_id"]))
        if connection is None or item is None or item.business_id != entry.business_id:
            return
        client = client_for(connection, settings, http)
        try:
            push_item(db, item, connection, client, settings)
        except ShopifyError as exc:
            _record_error(db, connection, str(exc))
            raise

    def delete(db: Session, entry: IntegrationOutbox) -> None:
        connection = _live_connection(db, entry.business_id)
        if connection is None:
            return
        client = client_for(connection, settings, http)
        result = client.graphql(
            PRODUCT_DELETE, {"input": {"id": entry.payload["shopify_product_id"]}}
        ).get("productDelete") or {}
        errors = result.get("userErrors") or []
        # Already gone from the store (the owner deleted it there): done.
        if errors and not any("not exist" in str(e.get("message", "")) for e in errors):
            raise_user_errors(result)
        logger.info("Shopify product deleted", extra={"business_id": str(entry.business_id)})

    return {outbox.ITEM_UPSERT: upsert, outbox.ITEM_DELETE: delete}


def _record_error(db: Session, connection: ShopifyConnection, message: str) -> None:
    """Keep the error for the owner even though the entry's own work rolls back."""
    connection_id = connection.id
    db.rollback()
    fresh = db.get(ShopifyConnection, connection_id)
    if fresh is not None:
        fresh.last_error = message[:2000]
        db.commit()
