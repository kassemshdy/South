"""Connecting a shop's own Shopify store to its Janobona listing.

The owner owns the store and pays Shopify for it (the owners' decision, 30
Oct 2026); Janobona is an app they install on it, through Shopify's OAuth:

1. ``start`` -- the dashboard asks for an authorize URL. The shop name is
   checked against ``*.myshopify.com`` before anything else, and a signed
   ``state`` carries who asked, for which listing, and their session
   version, because the callback arrives without our session.
2. ``complete`` -- Shopify sends the browser back with a code. Its HMAC,
   the state and the shop are all checked, the code is exchanged for an
   offline token, which is stored encrypted (``app/core/crypto.py``), and
   every product is queued for a first push.
3. ``disconnect`` -- the token is revoked and the row deleted. The products
   already in the store are left there: they are the owner's.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.integrations.shopify import client as shopify
from app.models.business import Business
from app.models.enums import BusinessStatus, ShopifyConnectionStatus
from app.models.integration import ShopifyConnection
from app.models.user import User
from app.services import outbox
from app.services.shopify_sync import client_for, refresh_shop, register_webhooks

logger = logging.getLogger(__name__)

STATE_AUDIENCE = "shopify-install"
STATE_TTL = timedelta(minutes=15)
CALLBACK_PATH = "/api/integrations/shopify/callback"
WEBHOOK_PATH = "/api/integrations/shopify/webhooks"


def callback_url(settings: Settings) -> str:
    return settings.public_base_url.rstrip("/") + CALLBACK_PATH


def webhook_url(settings: Settings) -> str:
    return settings.public_base_url.rstrip("/") + WEBHOOK_PATH


def dashboard_url(settings: Settings, business_id: uuid.UUID | str, outcome: str) -> str:
    return (
        settings.public_base_url.rstrip("/")
        + f"/dashboard/businesses/{business_id}/items?shopify={outcome}"
    )


class ShopifyConnectionService:
    def __init__(self, db: Session, settings: Settings, http: httpx.Client) -> None:
        self._db = db
        self._settings = settings
        self._http = http

    # --- 1. The authorize URL ----------------------------------------------

    def start(self, business: Business, user: User, shop_input: str) -> str:
        if business.status is not BusinessStatus.APPROVED:
            raise ValidationError("shopify.not_approved", code="shopify_not_approved")
        shop = shopify.normalize_shop(shop_input)
        if not shopify.is_shop_domain(shop):
            raise ValidationError("shopify.bad_shop", code="shopify_bad_shop")
        now = datetime.now(UTC)
        state = jwt.encode(
            {
                "aud": STATE_AUDIENCE,
                "sub": str(user.id),
                "tv": user.token_version,
                "bid": str(business.id),
                "shop": shop,
                "nonce": secrets.token_urlsafe(12),
                "iat": int(now.timestamp()),
                "exp": int((now + STATE_TTL).timestamp()),
            },
            self._settings.secret_key,
            algorithm=self._settings.jwt_algorithm,
        )
        assert self._settings.shopify_api_key
        return shopify.authorize_url(
            shop,
            api_key=self._settings.shopify_api_key,
            scopes=self._settings.shopify_scopes,
            redirect_uri=callback_url(self._settings),
            state=state,
        )

    # --- 2. The callback ---------------------------------------------------

    def read_state(self, state: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                state,
                self._settings.secret_key,
                algorithms=[self._settings.jwt_algorithm],
                audience=STATE_AUDIENCE,
            )
        except jwt.PyJWTError as exc:
            raise ValidationError("shopify.bad_callback", code="shopify_bad_state") from exc

    def complete(self, params: dict[str, str]) -> Business:
        assert self._settings.shopify_api_key and self._settings.shopify_api_secret
        if not shopify.verify_query_hmac(params, self._settings.shopify_api_secret):
            raise ValidationError("shopify.bad_callback", code="shopify_bad_hmac")
        claims = self.read_state(params.get("state", ""))
        shop = params.get("shop", "")
        if not shopify.is_shop_domain(shop) or shop != claims.get("shop"):
            raise ValidationError("shopify.bad_callback", code="shopify_shop_mismatch")

        # Still the owner, still signed in with the same session version,
        # still an approved listing -- any of these can change in fifteen
        # minutes.
        business = self._db.get(Business, uuid.UUID(claims["bid"]))
        user = self._db.get(User, uuid.UUID(claims["sub"]))
        if (
            business is None
            or user is None
            or business.owner_id != user.id
            or user.token_version != claims.get("tv")
        ):
            raise NotFoundError("business.not_found")
        if business.status is not BusinessStatus.APPROVED:
            raise ValidationError("shopify.not_approved", code="shopify_not_approved")

        taken = self._db.scalars(
            select(ShopifyConnection).where(
                ShopifyConnection.shop_domain == shop,
                ShopifyConnection.business_id != business.id,
            )
        ).first()
        if taken is not None:
            raise ConflictError("shopify.shop_taken", code="shopify_shop_taken")

        token, scopes = shopify.exchange_code(
            self._http,
            shop,
            api_key=self._settings.shopify_api_key,
            api_secret=self._settings.shopify_api_secret,
            code=params.get("code", ""),
        )
        connection = business.shopify_connection
        if connection is None:
            connection = ShopifyConnection(business_id=business.id)
            self._db.add(connection)
            business.shopify_connection = connection
        elif connection.shop_domain != shop:
            # Another store: what was linked belongs to the old one.
            connection.primary_domain = None
        connection.shop_domain = shop
        connection.access_token_enc = encrypt_secret(self._settings, token)
        connection.scopes = scopes
        connection.status = ShopifyConnectionStatus.CONNECTED
        connection.connected_at = datetime.now(UTC)
        connection.last_error = None
        try:
            client = client_for(connection, self._settings, self._http)
            refresh_shop(connection, client)
            register_webhooks(client, webhook_url(self._settings))
        except shopify.ShopifyError as exc:
            connection.last_error = str(exc)
        self._db.flush()
        outbox.enqueue_full_sync(self._db, business)
        self._db.commit()
        logger.info("Shopify store connected", extra={"business_id": str(business.id)})
        return business

    # --- 3. Disconnecting --------------------------------------------------

    def disconnect(self, business: Business) -> None:
        connection = business.shopify_connection
        if connection is None:
            raise NotFoundError("shopify.not_connected")
        if connection.is_live:
            try:
                token = decrypt_secret(self._settings, connection.access_token_enc)
                shopify.revoke_token(self._http, connection.shop_domain, token)
            except Exception:
                logger.warning("Revoking a Shopify token failed", exc_info=True)
        from app.services.store_subdomain import StoreSubdomainService

        StoreSubdomainService(self._settings, self._http).release(connection)
        self._db.delete(connection)
        self._db.commit()

    def sync_now(self, business: Business) -> int:
        connection = business.shopify_connection
        if connection is None or not connection.is_live:
            raise NotFoundError("shopify.not_connected")
        count = outbox.enqueue_full_sync(self._db, business)
        self._db.commit()
        return count

    # --- Webhooks ----------------------------------------------------------

    def handle_webhook(self, topic: str, shop: str) -> None:
        connection = self._db.scalars(
            select(ShopifyConnection).where(ShopifyConnection.shop_domain == shop)
        ).first()
        if connection is None:
            return
        if topic == "app/uninstalled":
            connection.status = ShopifyConnectionStatus.UNINSTALLED
        elif topic == "shop/update" and connection.is_live:
            try:
                refresh_shop(connection, client_for(connection, self._settings, self._http))
            except shopify.ShopifyError as exc:
                connection.last_error = str(exc)
        elif topic == "shop/redact":
            # Shopify's instruction, 48 hours after uninstall, to forget the
            # store: the connection goes; the listing is ours and stays.
            from app.services.store_subdomain import StoreSubdomainService

            StoreSubdomainService(self._settings, self._http).release(connection)
            self._db.delete(connection)
        # customers/data_request and customers/redact: we hold no data about
        # any store's customers, so there is nothing to send or erase.
        self._db.commit()


# --- When a listing or an account is deleted ---------------------------------
#
# The rows go by cascade with the listing; what lives elsewhere -- our app
# installed on the owner's store, the DNS record -- is undone after the
# commit, best effort, like the files AccountDeletionService removes.


ForgottenStore = tuple[str, str, str | None]


def remember_stores(businesses: list[Business]) -> list[ForgottenStore]:
    return [
        (c.shop_domain, c.access_token_enc, c.cf_dns_record_id)
        for c in (b.shopify_connection for b in businesses)
        if c is not None
    ]


def forget_stores(stores: list[ForgottenStore], settings: Settings) -> None:
    if not stores:
        return
    from app.integrations.cloudflare import CloudflareDns

    with httpx.Client(timeout=20) as http:
        for shop, token_enc, record_id in stores:
            try:
                if settings.integration_encryption_key:
                    shopify.revoke_token(http, shop, decrypt_secret(settings, token_enc))
                if record_id and settings.cloudflare_api_token and settings.cloudflare_zone_id:
                    CloudflareDns(
                        http, settings.cloudflare_api_token, settings.cloudflare_zone_id
                    ).delete(record_id)
            except Exception:
                logger.warning("Undoing a deleted listing's store failed", exc_info=True)
