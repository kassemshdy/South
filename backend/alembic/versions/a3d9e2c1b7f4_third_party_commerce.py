"""third-party commerce: store and product mirrors, outbox, partner API keys

The investor's model (30 Oct 2026): each shop sells through its own Shopify
store, run through the shared Shopify Connector service. Janoubona keeps a
mirror of what the connector reports (``store_links``, ``item_links``), an
outbox of pushes to it, and the keys of the partner feed. No credential for
Shopify or Cloudflare is stored here. New tables only, created if absent.

Revision ID: a3d9e2c1b7f4
Revises: f1a7c3e9b524
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "a3d9e2c1b7f4"
down_revision = "f1a7c3e9b524"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "store_links" not in existing:
        op.create_table(
            "store_links",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column(
                "business_id",
                sa.UUID(),
                sa.ForeignKey(
                    "businesses.id",
                    ondelete="CASCADE",
                    name="fk_store_links_business_id_businesses",
                ),
                nullable=False,
            ),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("shop_domain", sa.String(255), nullable=True),
            sa.Column("storefront_url", sa.String(300), nullable=True),
            sa.Column("subdomain", sa.String(63), nullable=True),
            sa.Column("subdomain_hostname", sa.String(255), nullable=True),
            sa.Column("currency", sa.String(3), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
            *_timestamps(),
            sa.UniqueConstraint("business_id", name="uq_store_links_business_id"),
        )

    if "item_links" not in existing:
        op.create_table(
            "item_links",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column(
                "item_id",
                sa.UUID(),
                sa.ForeignKey(
                    "business_items.id",
                    ondelete="CASCADE",
                    name="fk_item_links_item_id_business_items",
                ),
                nullable=False,
            ),
            sa.Column("state", sa.String(20), nullable=False),
            sa.Column("handle", sa.String(255), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("buy_url", sa.String(500), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
            *_timestamps(),
            sa.UniqueConstraint("item_id", name="uq_item_links_item_id"),
        )

    if "integration_outbox" not in existing:
        op.create_table(
            "integration_outbox",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column("kind", sa.String(60), nullable=False),
            sa.Column(
                "business_id",
                sa.UUID(),
                sa.ForeignKey(
                    "businesses.id",
                    ondelete="CASCADE",
                    name="fk_integration_outbox_business_id_businesses",
                ),
                nullable=False,
            ),
            sa.Column(
                "payload",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
            *_timestamps(),
        )
        op.create_index(
            "ix_integration_outbox_business_id", "integration_outbox", ["business_id"]
        )
        op.create_index(
            "ix_integration_outbox_pending", "integration_outbox", ["done_at", "next_attempt_at"]
        )

    if "api_partners" not in existing:
        op.create_table(
            "api_partners",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("key_prefix", sa.String(16), nullable=False),
            sa.Column("key_hash", sa.String(64), nullable=False),
            sa.Column("scopes", sa.String(200), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_by",
                sa.UUID(),
                sa.ForeignKey(
                    "users.id", ondelete="SET NULL", name="fk_api_partners_created_by_users"
                ),
                nullable=True,
            ),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            *_timestamps(),
            sa.UniqueConstraint("key_hash", name="uq_api_partners_key_hash"),
        )


def downgrade() -> None:
    op.drop_table("api_partners")
    op.drop_index("ix_integration_outbox_pending", table_name="integration_outbox")
    op.drop_index("ix_integration_outbox_business_id", table_name="integration_outbox")
    op.drop_table("integration_outbox")
    op.drop_table("item_links")
    op.drop_table("store_links")
