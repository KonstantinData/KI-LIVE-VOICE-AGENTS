"""SQLAlchemy Model für Chat-Konversationen."""

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import Base, TimestampMixin, UUIDMixin


class Conversation(UUIDMixin, TimestampMixin, Base):
    """Eine Chat-Konversation zwischen Visitor und Agent."""

    __tablename__ = "conversations"

    studio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("studios.id", ondelete="CASCADE"),
        nullable=False,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    visitor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="widget", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (Index("ix_conversations_studio_id", "studio_id"),)

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} status={self.status!r}>"
