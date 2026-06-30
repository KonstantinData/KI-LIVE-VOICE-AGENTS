"""
Feedback Routes
===============
What:    Tenant-scoped feedback endpoints for agent answer quality.
Does:    Lists and creates feedback linked to assistant messages.
Why:     Human review and corrections are required for continuous improvement and governance.
Who:     Dashboard feedback page and widget/admin feedback controls.
Depends: fastapi, sqlalchemy, src.api.deps, src.api.schemas, src.db.models
"""

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, select

from src.api.deps import CurrentStudio, DBSession
from src.api.schemas import FeedbackCreate, FeedbackResponse
from src.db.models.conversation import Conversation
from src.db.models.feedback import Feedback
from src.db.models.message import Message

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.get("/", response_model=list[FeedbackResponse])
async def list_feedback(
    studio: CurrentStudio,
    session: DBSession,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[FeedbackResponse]:
    """Lists feedback for the current studio."""
    result = await session.execute(
        select(Feedback)
        .where(Feedback.studio_id == studio.id)
        .order_by(desc(Feedback.created_at))
        .limit(limit)
    )
    return [FeedbackResponse.model_validate(row) for row in result.scalars().all()]


@router.post("/", response_model=FeedbackResponse, status_code=201)
async def create_feedback(
    payload: FeedbackCreate,
    studio: CurrentStudio,
    session: DBSession,
) -> FeedbackResponse:
    """Creates feedback after verifying that the message belongs to the current studio."""
    result = await session.execute(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Message.id == payload.message_id)
        .where(Conversation.studio_id == studio.id)
    )
    message = result.scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    feedback = Feedback(
        id=uuid.uuid4(),
        studio_id=studio.id,
        message_id=payload.message_id,
        rating=payload.rating,
        correction=payload.correction,
    )
    session.add(feedback)
    await session.flush()
    await session.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)
