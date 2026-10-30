"""Third-party commerce: a shop's Shopify store, and partners reading our feed.

The investor's model (30 Oct 2026): Janobona is the door, not the shop. Each
business runs its own Shopify store, which it owns and keeps; payment and
delivery happen there (Yalla Pay is a Shopify app). Janobona pushes the
shop's products to that store and links visitors to it.

- ``ShopifyConnection`` -- one per business: which store, an encrypted
  offline token (``app/core/crypto.py``), and the address visitors are sent
  to. Never on a public payload except as that address.
- ``ShopifyProductLink`` -- which Shopify product a ``BusinessItem`` became,
  so a second push updates rather than duplicates.
- ``IntegrationOutbox`` -- pushes waiting to be sent. Written in the same
  transaction as the edit that caused them, so a rolled-back edit sends
  nothing and a crash between commit and push loses nothing.
- ``ApiPartner`` -- a company holding a key to the read-only partner feed.
  Named apart from ``PartnerRequest``, which is the "support the project"
  contact form.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, pg_enum, uuid_pk
from app.models.enums import ShopifyConnectionStatus

if TYPE_CHECKING:
    from app.models.business import Business, BusinessItem


class ShopifyConnection(Base, TimestampMixin):
    __tablename__ = "shopify_connections"

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Always "<name>.myshopify.com": the store's permanent address, which is
    # what the Admin API is called on, whatever domain visitors see.
    shop_domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    access_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[ShopifyConnectionStatus] = mapped_column(
        pg_enum(ShopifyConnectionStatus, "shopify_connection_status"),
        nullable=False,
        default=ShopifyConnectionStatus.CONNECTED,
    )
    # The domain the store answers on for visitors: its own, our subdomain
    # once connected in Shopify, or the myshopify one.
    primary_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # "<subdomain>.janoubona.net", chosen by the owner; Latin, unlike slugs.
    subdomain: Mapped[str | None] = mapped_column(String(63), nullable=True, unique=True)
    cf_dns_record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    business: Mapped[Business] = relationship(back_populates="shopify_connection")

    @property
    def is_live(self) -> bool:
        return self.status is ShopifyConnectionStatus.CONNECTED

    @property
    def storefront_host(self) -> str:
        return self.primary_domain or self.shop_domain


class ShopifyProductLink(Base, TimestampMixin):
    __tablename__ = "shopify_product_links"

    id: Mapped[uuid.UUID] = uuid_pk()
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_items.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    shopify_product_id: Mapped[str] = mapped_column(String(80), nullable=False)
    shopify_variant_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    # Whether the product is ACTIVE in the store; a DRAFT has no page to buy on.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Hash of what was last sent, so an edit that changes nothing Shopify
    # sees (a sort order, a view count) sends nothing.
    synced_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    item: Mapped[BusinessItem] = relationship(back_populates="shopify_link")


class IntegrationOutbox(Base, TimestampMixin):
    __tablename__ = "integration_outbox"
    __table_args__ = (Index("ix_integration_outbox_pending", "done_at", "next_attempt_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set when sent, or when it gave up; kept a while for the dashboard.
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiPartner(Base, TimestampMixin):
    __tablename__ = "api_partners"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # The first characters of the key, shown in the admin list so a key
    # can be recognised without being stored.
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Space-separated: "stores:read products:read".
    scopes: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def scope_set(self) -> frozenset[str]:
        return frozenset(self.scopes.split())
