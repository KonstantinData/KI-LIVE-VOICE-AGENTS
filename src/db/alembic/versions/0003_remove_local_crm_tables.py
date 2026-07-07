"""Remove local CRM tables from the runtime database.

Revision ID: 0003_remove_local_crm_tables
Revises: 0002_conversation_cost_events
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_remove_local_crm_tables"
down_revision: str | None = "0002_conversation_cost_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop local CRM ownership tables; CRM is external."""
    op.drop_table("conversation_cost_events")
    op.drop_table("followups")
    op.drop_table("appointments")
    op.drop_index("ix_feedback_studio_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_table("berater")
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_column("lead_id")
    op.drop_index("ix_leads_studio_status_score", table_name="leads")
    op.drop_index("ix_leads_studio_id", table_name="leads")
    op.drop_table("leads")


def downgrade() -> None:
    """Recreate legacy local CRM tables for rollback."""
    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("studio_id", sa.Uuid(), nullable=False),
        sa.Column("visitor_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_channel", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["studio_id"], ["studios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_studio_id", "leads", ["studio_id"])
    op.create_index(
        "ix_leads_studio_status_score", "leads", ["studio_id", "status", "score"]
    )
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.add_column(sa.Column("lead_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_conversations_lead_id_leads",
            "leads",
            ["lead_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_table(
        "berater",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("studio_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("specialization", sa.String(length=255), nullable=True),
        sa.Column("calendar_provider", sa.String(length=50), nullable=True),
        sa.Column("calendar_tokens", sa.JSON(), nullable=True),
        sa.Column("working_hours", sa.JSON(), nullable=True),
        sa.Column("appointment_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["studio_id"], ["studios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_berater_studio_id", "berater", ["studio_id"])
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("studio_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("correction", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["studio_id"], ["studios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_studio_id", "feedback", ["studio_id"])
    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("studio_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("berater_id", sa.Uuid(), nullable=True),
        sa.Column("datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("external_calendar_id", sa.String(length=255), nullable=True),
        sa.Column("confirmation_sent", sa.Boolean(), nullable=False),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["berater_id"], ["berater.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["studio_id"], ["studios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointments_studio_id", "appointments", ["studio_id"])
    op.create_table(
        "followups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("studio_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("autonomy_level", sa.String(length=50), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["studio_id"], ["studios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_followups_studio_id", "followups", ["studio_id"])
    op.create_table(
        "conversation_cost_events",
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.Column(
            "estimated_cost_usd", sa.Numeric(precision=12, scale=6), nullable=True
        ),
        sa.Column("pricing_snapshot", sa.String(length=80), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["studio_id"], ["studios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_cost_events_studio_created",
        "conversation_cost_events",
        ["studio_id", "created_at"],
    )
