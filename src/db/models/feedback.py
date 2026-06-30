"""SQLAlchemy Model für Feedback zu Agent-Antworten."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import Base, UUIDMixin, utcnow


class Feedback(UUIDMixin, Base):
    """Feedback / Bewertung einer Agent-Antwort."""

    __tablename__ = "feedback"

    studio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("studios.id", ondelete="CASCADE"),
        nullable=False,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    __table_args__ = (Index("ix_feedback_studio_id", "studio_id"),)

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} rating={self.rating}>"
