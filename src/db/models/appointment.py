"""SQLAlchemy Model für Beratungstermine."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import Base, UUIDMixin, utcnow


class Appointment(UUIDMixin, Base):
    """Ein Beratungstermin."""

    __tablename__ = "appointments"

    studio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("studios.id", ondelete="CASCADE"),
        nullable=False,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    berater_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("berater.id", ondelete="CASCADE"),
        nullable=False,
    )
    datetime_: Mapped[datetime] = mapped_column(
        "datetime",
        DateTime(timezone=True),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled", nullable=False)
    external_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmation_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    __table_args__ = (Index("ix_appointments_studio_id", "studio_id"),)

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} status={self.status!r}>"
