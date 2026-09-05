"""add business item slug and search_text

Revision ID: 85a19c3b95fc
Revises: ff08752870d6
Create Date: 2026-09-05 12:00:00.000000+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '85a19c3b95fc'
down_revision = 'ff08752870d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.core.arabic import build_search_text
    from app.services.slug import slugify_name

    op.add_column('business_items', sa.Column('slug', sa.String(length=180), nullable=True))
    op.add_column(
        'business_items', sa.Column('search_text', sa.Text(), nullable=False, server_default='')
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text('SELECT id, title, description FROM business_items')
    ).fetchall()

    used_slugs: set[str] = set()
    for row in rows:
        base = slugify_name(row.title, fallback_prefix='item')
        candidate = base
        suffix = 2
        while candidate in used_slugs:
            candidate = f'{base}-{suffix}'
            suffix += 1
        used_slugs.add(candidate)

        connection.execute(
            sa.text(
                'UPDATE business_items SET slug = :slug, search_text = :search_text '
                'WHERE id = :id'
            ),
            {
                'slug': candidate,
                'search_text': build_search_text(row.title, row.description),
                'id': row.id,
            },
        )

    op.alter_column('business_items', 'slug', nullable=False)
    op.alter_column('business_items', 'search_text', server_default=None)
    op.create_index(op.f('ix_business_items_slug'), 'business_items', ['slug'], unique=True)
    op.execute(
        "CREATE INDEX ix_business_items_search_text_trgm "
        "ON business_items USING gin (search_text gin_trgm_ops)"
    )
    # NOTE: a future autogenerate in this area will spuriously propose dropping
    # ix_business_items_title_trgm, ix_businesses_search_text_trgm, and this
    # migration's own ix_business_items_search_text_trgm — the same known
    # false positive as 730b8921ac10 and ff08752870d6 (raw-SQL GIN trigram
    # indexes aren't declared as SQLAlchemy Index objects, so autogenerate
    # can't match them against the models). Deliberately not dropped there.


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_business_items_search_text_trgm")
    op.drop_index(op.f('ix_business_items_slug'), table_name='business_items')
    op.drop_column('business_items', 'search_text')
    op.drop_column('business_items', 'slug')
