"""add feedback tickets

Revision ID: b3e7a1c9d2f4
Revises: 9f2c1a7b4de3
Create Date: 2026-09-06 13:00:00.000000+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'b3e7a1c9d2f4'
down_revision = '9f2c1a7b4de3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    feedback_status = sa.Enum(
        'BACKLOG', 'TODO', 'IN_PROGRESS', 'DONE', name='feedback_status'
    )
    feedback_priority = sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='feedback_priority')
    feedback_attachment_kind = sa.Enum(
        'SCREENSHOT', 'PHOTO', 'DOCUMENT', name='feedback_attachment_kind'
    )

    op.create_table(
        'feedback_tickets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('reporter_id', sa.UUID(), nullable=False),
        sa.Column('assignee_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', feedback_status, nullable=False),
        sa.Column('priority', feedback_priority, nullable=False),
        sa.Column('page_path', sa.String(length=500), nullable=True),
        sa.Column('client_context', sa.String(length=500), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], name=op.f('fk_feedback_tickets_assignee_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], name=op.f('fk_feedback_tickets_reporter_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_feedback_tickets')),
    )
    op.create_index(op.f('ix_feedback_tickets_assignee_id'), 'feedback_tickets', ['assignee_id'], unique=False)
    op.create_index(op.f('ix_feedback_tickets_reporter_id'), 'feedback_tickets', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_feedback_tickets_status'), 'feedback_tickets', ['status'], unique=False)
    op.create_index('ix_feedback_tickets_status_sort_order', 'feedback_tickets', ['status', 'sort_order'], unique=False)

    op.create_table(
        'feedback_attachments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('ticket_id', sa.UUID(), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('kind', feedback_attachment_kind, nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['feedback_tickets.id'], name=op.f('fk_feedback_attachments_ticket_id_feedback_tickets'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_feedback_attachments')),
    )
    op.create_index(op.f('ix_feedback_attachments_ticket_id'), 'feedback_attachments', ['ticket_id'], unique=False)

    op.create_table(
        'feedback_comments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('ticket_id', sa.UUID(), nullable=False),
        sa.Column('author_id', sa.UUID(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_feedback_comments_author_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['ticket_id'], ['feedback_tickets.id'], name=op.f('fk_feedback_comments_ticket_id_feedback_tickets'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_feedback_comments')),
    )
    op.create_index(op.f('ix_feedback_comments_ticket_id'), 'feedback_comments', ['ticket_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_feedback_comments_ticket_id'), table_name='feedback_comments')
    op.drop_table('feedback_comments')

    op.drop_index(op.f('ix_feedback_attachments_ticket_id'), table_name='feedback_attachments')
    op.drop_table('feedback_attachments')

    op.drop_index('ix_feedback_tickets_status_sort_order', table_name='feedback_tickets')
    op.drop_index(op.f('ix_feedback_tickets_status'), table_name='feedback_tickets')
    op.drop_index(op.f('ix_feedback_tickets_reporter_id'), table_name='feedback_tickets')
    op.drop_index(op.f('ix_feedback_tickets_assignee_id'), table_name='feedback_tickets')
    op.drop_table('feedback_tickets')

    sa.Enum(name='feedback_attachment_kind').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='feedback_priority').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='feedback_status').drop(op.get_bind(), checkfirst=True)
