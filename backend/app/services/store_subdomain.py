"""``<sub>.janobona.com`` for a connected store.

The owner picks the name: business slugs keep Arabic script and cannot be
hostnames. We create the DNS record; Shopify's Admin API has no way to
attach a domain to a store, so the owner then adds it once in Shopify
(Settings -> Domains -> Connect existing domain), and the store's primary
domain -- read back on ``shop/update`` -- is what visitors are sent to.
"""

from __future__ import annotations

import logging
import re

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.integrations.cloudflare import CloudflareDns, CloudflareError
from app.models.integration import ShopifyConnection

logger = logging.getLogger(__name__)

SUBDOMAIN = re.compile(r"^[a-z0-9](?:-?[a-z0-9]){1,30}$")

#: Names the site itself uses or may want, and names that invite phishing.
RESERVED = frozenset(
    {
        "admin", "api", "app", "assets", "auth", "blog", "cdn", "dashboard", "dev",
        "develop", "docs", "ftp", "help", "imap", "janobona", "login", "mail", "media",
        "mx", "ns1", "ns2", "pay", "payment", "pop", "shop", "shops", "smtp", "staging",
        "static", "status", "store", "support", "test", "web", "webmail", "www",
    }
)


def validate_subdomain(value: str) -> str:
    value = value.strip().lower()
    if not SUBDOMAIN.fullmatch(value):
        raise ValidationError("shopify.bad_subdomain", code="bad_subdomain")
    if value in RESERVED:
        raise ValidationError("shopify.reserved_subdomain", code="reserved_subdomain")
    return value


class StoreSubdomainService:
    def __init__(self, settings: Settings, http: httpx.Client) -> None:
        self._settings = settings
        self._http = http

    def _dns(self) -> CloudflareDns | None:
        if not self._settings.cloudflare_enabled:
            return None
        assert self._settings.cloudflare_api_token and self._settings.cloudflare_zone_id
        return CloudflareDns(
            self._http, self._settings.cloudflare_api_token, self._settings.cloudflare_zone_id
        )

    def hostname(self, subdomain: str) -> str:
        return f"{subdomain}.{self._settings.store_subdomain_base}"

    def assign(self, db: Session, connection: ShopifyConnection, raw: str) -> ShopifyConnection:
        dns = self._dns()
        if dns is None:
            raise NotFoundError("shopify.subdomains_off")
        if not connection.is_live:
            raise NotFoundError("shopify.not_connected")
        subdomain = validate_subdomain(raw)
        if subdomain == connection.subdomain:
            return connection
        taken = db.scalars(
            select(ShopifyConnection.id).where(
                ShopifyConnection.subdomain == subdomain, ShopifyConnection.id != connection.id
            )
        ).first()
        if taken is not None:
            raise ConflictError("shopify.subdomain_taken", code="subdomain_taken")
        try:
            record_id = dns.create_cname(self.hostname(subdomain))
        except CloudflareError as exc:
            logger.warning("Creating a store CNAME failed: %s", exc)
            raise ConflictError("shopify.subdomain_failed", code="subdomain_failed") from exc
        old = connection.cf_dns_record_id
        connection.subdomain = subdomain
        connection.cf_dns_record_id = record_id
        db.commit()
        if old:
            self._delete_record(dns, old)
        return connection

    def release(self, connection: ShopifyConnection) -> None:
        """Remove the record; the caller removes or clears the row."""
        dns = self._dns()
        if dns is not None and connection.cf_dns_record_id:
            self._delete_record(dns, connection.cf_dns_record_id)
        connection.cf_dns_record_id = None
        connection.subdomain = None

    @staticmethod
    def _delete_record(dns: CloudflareDns, record_id: str) -> None:
        try:
            dns.delete(record_id)
        except (CloudflareError, httpx.HTTPError):
            logger.warning("Deleting a store CNAME failed", exc_info=True)
