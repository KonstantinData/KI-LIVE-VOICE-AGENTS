"""Add conversation cost events.

Revision ID: 0002_conversation_cost_events
Revises: 0001_initial_schema
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_conversation_cost_events"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create per-conversation provider cost event table."""
    op.create_table(
        "conversation_cost_events",
        sa.Column("studio_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("component", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("input_text_tokens", sa.Integer(), nullable=False),
        sa.Column("input_audio_tokens", sa.Integer(), nullable=False),
        sa.Column("input_image_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_text_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_audio_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_image_tokens", sa.Integer(), nullable=False),
        sa.Column("output_text_tokens", sa.Integer(), nullable=False),
        sa.Column("output_audio_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("pricing_snapshot", sa.String(length=120), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["studio_id"], ["studios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cost_events_studio_created",
        "conversation_cost_events",
        ["studio_id", "created_at"],
    )
    op.create_index(
        "ix_cost_events_conversation_created",
        "conversation_cost_events",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_cost_events_provider_event",
        "conversation_cost_events",
        ["provider", "provider_event_id"],
    )


def downgrade() -> None:
    """Drop per-conversation provider cost event table."""
    op.drop_index(
        "ix_cost_events_provider_event", table_name="conversation_cost_events"
    )
    op.drop_index(
        "ix_cost_events_conversation_created", table_name="conversation_cost_events"
    )
    op.drop_index(
        "ix_cost_events_studio_created", table_name="conversation_cost_events"
    )
    op.drop_table("conversation_cost_events")
