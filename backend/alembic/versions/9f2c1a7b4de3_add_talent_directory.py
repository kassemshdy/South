"""add talent directory

Revision ID: 9f2c1a7b4de3
Revises: 85a19c3b95fc
Create Date: 2026-09-06 09:00:00.000000+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '9f2c1a7b4de3'
down_revision = '85a19c3b95fc'
branch_labels = None
depends_on = None

# Talent reuses the business moderation lifecycle, so these Postgres enum types
# already exist. create_type=False stops Alembic from re-issuing CREATE TYPE and
# failing with "type already exists".
business_status = postgresql.ENUM(
    'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'SUSPENDED',
    name='business_status', create_type=False,
)
image_kind = postgresql.ENUM(
    'LOGO', 'COVER', 'GALLERY', 'ITEM', name='image_kind', create_type=False,
)
moderation_action_type = postgresql.ENUM(
    'SUBMIT', 'APPROVE', 'REJECT', 'SUSPEND', 'REACTIVATE',
    name='moderation_action_type', create_type=False,
)


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table: str) -> bool:
    return _inspector().has_table(table)


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    return index in {i["name"] for i in _inspector().get_indexes(table)}


def upgrade() -> None:
    if not _has_table('talent_skills'):
        op.create_table(
            'talent_skills',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('name_ar', sa.String(length=120), nullable=False),
            sa.Column('slug', sa.String(length=140), nullable=False),
            sa.Column('icon', sa.String(length=64), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_talent_skills')),
        )
    if not _has_index('talent_skills', 'ix_talent_skills_is_active'):
        op.create_index(op.f('ix_talent_skills_is_active'), 'talent_skills', ['is_active'], unique=False)
    if not _has_index('talent_skills', 'ix_talent_skills_slug'):
        op.create_index(op.f('ix_talent_skills_slug'), 'talent_skills', ['slug'], unique=True)

    if not _has_table('talent_profiles'):
        op.create_table(
            'talent_profiles',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('owner_id', sa.UUID(), nullable=False),
            sa.Column('skill_id', sa.UUID(), nullable=True),
            sa.Column('custom_skill_text', sa.String(length=120), nullable=True),
            sa.Column('location_id', sa.UUID(), nullable=True),
            sa.Column('display_name', sa.String(length=160), nullable=False),
            sa.Column('slug', sa.String(length=180), nullable=False),
            sa.Column('headline', sa.String(length=300), nullable=True),
            sa.Column('bio', sa.Text(), nullable=True),
            sa.Column('years_experience', sa.Integer(), nullable=True),
            sa.Column('phone', sa.String(length=20), nullable=True),
            sa.Column('whatsapp', sa.String(length=20), nullable=True),
            sa.Column('email', sa.String(length=255), nullable=True),
            sa.Column('website', sa.String(length=500), nullable=True),
            sa.Column('photo_url', sa.String(length=500), nullable=True),
            sa.Column('photo_storage_key', sa.String(length=500), nullable=True),
            sa.Column('status', business_status, nullable=False),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('approved_by', sa.UUID(), nullable=True),
            sa.Column('search_text', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name=op.f('fk_talent_profiles_approved_by_users'), ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['location_id'], ['locations.id'], name=op.f('fk_talent_profiles_location_id_locations'), ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_talent_profiles_owner_id_users'), ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['skill_id'], ['talent_skills.id'], name=op.f('fk_talent_profiles_skill_id_talent_skills'), ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_talent_profiles')),
        )
    if not _has_index('talent_profiles', 'ix_talent_profiles_location_id'):
        op.create_index(op.f('ix_talent_profiles_location_id'), 'talent_profiles', ['location_id'], unique=False)
    if not _has_index('talent_profiles', 'ix_talent_profiles_owner_id'):
        op.create_index(op.f('ix_talent_profiles_owner_id'), 'talent_profiles', ['owner_id'], unique=True)
    if not _has_index('talent_profiles', 'ix_talent_profiles_skill_id'):
        op.create_index(op.f('ix_talent_profiles_skill_id'), 'talent_profiles', ['skill_id'], unique=False)
    if not _has_index('talent_profiles', 'ix_talent_profiles_slug'):
        op.create_index(op.f('ix_talent_profiles_slug'), 'talent_profiles', ['slug'], unique=True)
    if not _has_index('talent_profiles', 'ix_talent_profiles_status'):
        op.create_index(op.f('ix_talent_profiles_status'), 'talent_profiles', ['status'], unique=False)
    if not _has_index('talent_profiles', 'ix_talent_profiles_status_approved_at'):
        op.create_index('ix_talent_profiles_status_approved_at', 'talent_profiles', ['status', 'approved_at'], unique=False)
    if not _has_index('talent_profiles', 'ix_talent_profiles_status_created_at'):
        op.create_index('ix_talent_profiles_status_created_at', 'talent_profiles', ['status', 'created_at'], unique=False)

    if not _has_table('talent_images'):
        op.create_table(
            'talent_images',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('profile_id', sa.UUID(), nullable=False),
            sa.Column('url', sa.String(length=500), nullable=False),
            sa.Column('storage_key', sa.String(length=500), nullable=False),
            sa.Column('kind', image_kind, nullable=False),
            sa.Column('caption', sa.String(length=300), nullable=True),
            sa.Column('sort_order', sa.Integer(), nullable=False),
            sa.Column('width', sa.Integer(), nullable=True),
            sa.Column('height', sa.Integer(), nullable=True),
            sa.Column('size_bytes', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['profile_id'], ['talent_profiles.id'], name=op.f('fk_talent_images_profile_id_talent_profiles'), ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_talent_images')),
        )
    if not _has_index('talent_images', 'ix_talent_images_profile_id'):
        op.create_index(op.f('ix_talent_images_profile_id'), 'talent_images', ['profile_id'], unique=False)
    if not _has_index('talent_images', 'ix_talent_images_profile_kind_sort'):
        op.create_index('ix_talent_images_profile_kind_sort', 'talent_images', ['profile_id', 'kind', 'sort_order'], unique=False)

    if not _has_table('talent_moderation_actions'):
        op.create_table(
            'talent_moderation_actions',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('profile_id', sa.UUID(), nullable=False),
            sa.Column('admin_id', sa.UUID(), nullable=True),
            sa.Column('actor_id', sa.UUID(), nullable=True),
            sa.Column('action', moderation_action_type, nullable=False),
            sa.Column('from_status', business_status, nullable=True),
            sa.Column('to_status', business_status, nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_talent_moderation_actions_actor_id_users'), ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['admin_id'], ['users.id'], name=op.f('fk_talent_moderation_actions_admin_id_users'), ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['profile_id'], ['talent_profiles.id'], name=op.f('fk_talent_moderation_actions_profile_id_talent_profiles'), ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_talent_moderation_actions')),
        )
    if not _has_index('talent_moderation_actions', 'ix_talent_moderation_actions_profile_id'):
        op.create_index(op.f('ix_talent_moderation_actions_profile_id'), 'talent_moderation_actions', ['profile_id'], unique=False)

    # Substring search over the Arabic-normalized haystack, matching the
    # businesses index. Expressed as raw SQL because a GIN trigram index has no
    # SQLAlchemy model representation — which is why `alembic check` reports
    # this (and the equivalent businesses/business_items indexes) as drift.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_talent_profiles_search_text_trgm "
        "ON talent_profiles USING gin (search_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_talent_profiles_search_text_trgm")

    op.drop_index(op.f('ix_talent_moderation_actions_profile_id'), table_name='talent_moderation_actions')
    op.drop_table('talent_moderation_actions')

    op.drop_index('ix_talent_images_profile_kind_sort', table_name='talent_images')
    op.drop_index(op.f('ix_talent_images_profile_id'), table_name='talent_images')
    op.drop_table('talent_images')

    op.drop_index('ix_talent_profiles_status_created_at', table_name='talent_profiles')
    op.drop_index('ix_talent_profiles_status_approved_at', table_name='talent_profiles')
    op.drop_index(op.f('ix_talent_profiles_status'), table_name='talent_profiles')
    op.drop_index(op.f('ix_talent_profiles_slug'), table_name='talent_profiles')
    op.drop_index(op.f('ix_talent_profiles_skill_id'), table_name='talent_profiles')
    op.drop_index(op.f('ix_talent_profiles_owner_id'), table_name='talent_profiles')
    op.drop_index(op.f('ix_talent_profiles_location_id'), table_name='talent_profiles')
    op.drop_table('talent_profiles')

    op.drop_index(op.f('ix_talent_skills_slug'), table_name='talent_skills')
    op.drop_index(op.f('ix_talent_skills_is_active'), table_name='talent_skills')
    op.drop_table('talent_skills')
