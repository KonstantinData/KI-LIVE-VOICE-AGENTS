"""SQLAlchemy Model für Berater."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import Base, UUIDMixin, utcnow


class Berater(UUIDMixin, Base):
    """Ein Berater in einem Küchenstudio."""

    __tablename__ = "berater"

    studio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("studios.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calendar_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    calendar_tokens: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    working_hours: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    appointment_duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    __table_args__ = (Index("ix_berater_studio_id", "studio_id"),)

    def __repr__(self) -> str:
        return f"<Berater id={self.id} name={self.name!r}>"
