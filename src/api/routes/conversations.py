"""
Conversation Routes
===================
What:    Tenant-scoped conversation and message endpoints.
Does:    Lists conversations and exposes message history for the admin dashboard.
Why:     Human staff need reviewable chat transcripts for lead follow-up and QA.
Who:     Dashboard conversation pages.
Depends: fastapi, sqlalchemy, src.api.deps, src.api.schemas, src.db.models
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, select

from src.api.deps import CurrentStudio, DBSession
from src.api.schemas import ConversationResponse, MessageResponse
from src.db.models.conversation import Conversation
from src.db.models.message import Message

router = APIRouter(prefix="/conversations", tags=["Konversationen"])


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    studio: CurrentStudio,
    session: DBSession,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ConversationResponse]:
    """Lists conversations for the current studio."""
    statement = select(Conversation).where(Conversation.studio_id == studio.id)
    if status:
        statement = statement.where(Conversation.status == status)
    statement = statement.order_by(desc(Conversation.updated_at)).limit(limit)
    result = await session.execute(statement)
    return [ConversationResponse.model_validate(row) for row in result.scalars().all()]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    studio: CurrentStudio,
    session: DBSession,
) -> ConversationResponse:
    """Returns one conversation if it belongs to the current studio."""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.studio_id == studio.id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse.model_validate(conversation)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: UUID,
    studio: CurrentStudio,
    session: DBSession,
) -> list[MessageResponse]:
    """Lists messages for a tenant-owned conversation."""
    conversation_result = await session.execute(
        select(Conversation.id)
        .where(Conversation.id == conversation_id)
        .where(Conversation.studio_id == studio.id)
    )
    if conversation_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await session.execute(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Message.conversation_id == conversation_id)
        .where(Conversation.studio_id == studio.id)
        .order_by(Message.created_at.asc())
    )
    return [MessageResponse.model_validate(message) for message in result.scalars().all()]
