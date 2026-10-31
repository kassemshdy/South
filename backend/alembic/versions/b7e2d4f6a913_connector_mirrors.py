"""connector mirrors: drop the built-in Shopify tables where they exist

``a3d9e2c1b7f4`` first shipped (to the test environment only) with Janoubona
talking to Shopify itself: ``shopify_connections`` holding encrypted tokens
and ``shopify_product_links``. The Shopify side then moved to the shared
Shopify Connector service, and that revision was rewritten to create the
mirror tables instead. A database that ran the first version has the old
tables and lacks the new ones; this revision puts it right, and is a no-op
on any database that ran the rewritten one.

Revision ID: b7e2d4f6a913
Revises: a3d9e2c1b7f4
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision = "b7e2d4f6a913"
down_revision = "a3d9e2c1b7f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "shopify_product_links" in tables:
        op.drop_table("shopify_product_links")
    if "shopify_connections" in tables:
        op.drop_table("shopify_connections")
    op.execute("DROP TYPE IF EXISTS shopify_connection_status")
    # The rewritten a3d9e2c1b7f4 creates only what is absent; run it again
    # for the databases that ran its first version.
    path = Path(__file__).with_name("a3d9e2c1b7f4_third_party_commerce.py")
    spec = importlib.util.spec_from_file_location("a3d9e2c1b7f4", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.upgrade()


def downgrade() -> None:
    pass
