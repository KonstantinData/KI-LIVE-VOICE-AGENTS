"""SQLAlchemy Model für Wissens-Chunks mit Vektoren."""

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from src.db.models.base import Base, TimestampMixin, UUIDMixin


class KnowledgeChunk(UUIDMixin, TimestampMixin, Base):
    """Ein Wissens-Eintrag mit Embedding-Vektor für semantische Suche."""

    __tablename__ = "knowledge_chunks"

    studio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("studios.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_knowledge_chunks_studio_id", "studio_id"),
        # HNSW Index für schnelle Vektorsuche — wird via Alembic Migration gesetzt
    )

    def __repr__(self) -> str:
        return f"<KnowledgeChunk id={self.id} category={self.category!r}>"
