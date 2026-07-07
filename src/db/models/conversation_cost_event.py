"""Conversation cost event model.

What: Stores provider token usage and estimated cost for one billable event.
Does: Links usage to studio, conversation, optional lead/message, provider, model, and channel.
Why: Cost accounting needs auditable per-chat events rather than only aggregate counters.
Who: Voice and upload routes create events; dashboard/reporting can aggregate them.
Depends on: sqlalchemy, src.db.models.base, studios/conversations/leads/messages tables.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import Base, UUIDMixin, utcnow


class ConversationCostEvent(UUIDMixin, Base):
    """One provider usage/cost event scoped to a tenant conversation."""

    __tablename__ = "conversation_cost_events"

    studio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("studios.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    component: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), default="openai", nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_text_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_audio_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_image_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_text_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_audio_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_image_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_text_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_audio_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
        nullable=True,
    )
    pricing_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_cost_events_studio_created", "studio_id", "created_at"),
        Index("ix_cost_events_conversation_created", "conversation_id", "created_at"),
        Index("ix_cost_events_provider_event", "provider", "provider_event_id"),
    )

    def __repr__(self) -> str:
        return f"<ConversationCostEvent id={self.id} event_type={self.event_type!r}>"
