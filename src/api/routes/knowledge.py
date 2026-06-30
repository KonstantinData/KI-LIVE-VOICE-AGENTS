"""
Knowledge Routes
================
What:    Tenant-scoped knowledge base management endpoints.
Does:    Lists, creates, and deletes knowledge chunks without exposing embeddings.
Why:     Lisa needs studio-specific source material and staff need a manageable MVP UI.
Who:     Dashboard knowledge page and future ingestion jobs.
Depends: fastapi, sqlalchemy, src.api.deps, src.api.schemas, src.db.models.knowledge_chunk
"""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, select

from src.api.deps import CurrentStudio, DBSession
from src.api.schemas import KnowledgeChunkCreate, KnowledgeChunkResponse
from src.db.models.knowledge_chunk import KnowledgeChunk

router = APIRouter(prefix="/knowledge", tags=["Wissensbasis"])


@router.get("/", response_model=list[KnowledgeChunkResponse])
async def list_knowledge(
    studio: CurrentStudio,
    session: DBSession,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[KnowledgeChunkResponse]:
    """Lists knowledge chunks for the current studio."""
    statement = select(KnowledgeChunk).where(KnowledgeChunk.studio_id == studio.id)
    if category:
        statement = statement.where(KnowledgeChunk.category == category)
    statement = statement.order_by(desc(KnowledgeChunk.updated_at)).limit(limit)
    result = await session.execute(statement)
    return [KnowledgeChunkResponse.model_validate(row) for row in result.scalars().all()]


@router.post("/", response_model=KnowledgeChunkResponse, status_code=201)
async def create_knowledge(
    payload: KnowledgeChunkCreate,
    studio: CurrentStudio,
    session: DBSession,
) -> KnowledgeChunkResponse:
    """Creates a knowledge chunk; embedding generation is deferred to ingestion."""
    chunk = KnowledgeChunk(
        id=uuid.uuid4(),
        studio_id=studio.id,
        category=payload.category,
        title=payload.title,
        content=payload.content,
        metadata_=payload.metadata_,
    )
    session.add(chunk)
    await session.flush()
    await session.refresh(chunk)
    return KnowledgeChunkResponse.model_validate(chunk)


@router.delete("/{chunk_id}")
async def delete_knowledge(chunk_id: UUID, studio: CurrentStudio, session: DBSession) -> dict:
    """Deletes a knowledge chunk owned by the current studio."""
    result = await session.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.id == chunk_id)
        .where(KnowledgeChunk.studio_id == studio.id)
    )
    chunk = result.scalar_one_or_none()
    if chunk is None:
        raise HTTPException(status_code=404, detail="Knowledge chunk not found")
    await session.delete(chunk)
    return {"success": True}
