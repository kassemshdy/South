"""add articles

Revision ID: 22bb94847e57
Revises: a2d2e3589dee
Create Date: 2026-09-14 18:17:19.439705+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '22bb94847e57'
down_revision = 'a2d2e3589dee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('articles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('section', sa.Enum('BLOG', 'NEWS', name='article_section'), nullable=False),
    sa.Column('slug', sa.String(length=180), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('cover_url', sa.String(), nullable=True),
    sa.Column('cover_storage_key', sa.String(), nullable=True),
    sa.Column('is_published', sa.Boolean(), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_articles'))
    )
    op.create_index('ix_articles_section_published', 'articles', ['section', 'is_published', 'published_at'], unique=False)
    op.create_index(op.f('ix_articles_slug'), 'articles', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_articles_slug'), table_name='articles')
    op.drop_index('ix_articles_section_published', table_name='articles')
    op.drop_table('articles')
