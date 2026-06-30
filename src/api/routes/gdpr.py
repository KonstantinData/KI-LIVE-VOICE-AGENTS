"""
GDPR Rights Routes
==================
What:    Tenant-scoped operational endpoints for GDPR export and deletion requests.
Does:    Exports or deletes all known visitor/lead data across MVP tables.
Why:     Art. 15, 17, and 20 GDPR require actionable data access, portability, and deletion.
Who:     Authorized studio staff handling verified customer rights requests.
Depends: fastapi, sqlalchemy, src.api.deps, src.db.models
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, select

from src.api.deps import CurrentStudio, DBSession
from src.db.models.appointment import Appointment
from src.db.models.conversation import Conversation
from src.db.models.feedback import Feedback
from src.db.models.followup import FollowUp
from src.db.models.lead import Lead
from src.db.models.message import Message

router = APIRouter(prefix="/gdpr", tags=["DSGVO"])


async def _resolve_leads(
    session: DBSession,
    studio_id: UUID,
    visitor_id: str | None,
    lead_id: UUID | None,
) -> list[Lead]:
    """Resolves matching tenant-owned leads by visitor or lead ID."""
    if not visitor_id and not lead_id:
        raise HTTPException(status_code=400, detail="visitor_id or lead_id is required")

    statement = select(Lead).where(Lead.studio_id == studio_id)
    if lead_id:
        statement = statement.where(Lead.id == lead_id)
    else:
        statement = statement.where(Lead.visitor_id == visitor_id)
    result = await session.execute(statement)
    return list(result.scalars().all())


async def _load_subject_data(
    session: DBSession,
    studio_id: UUID,
    visitor_id: str | None,
    lead_id: UUID | None,
) -> dict[str, Any]:
    """Loads all tenant-owned data linked to a verified data-subject request."""
    leads = await _resolve_leads(session, studio_id, visitor_id, lead_id)
    visitor_ids = {lead.visitor_id for lead in leads}
    if visitor_id:
        visitor_ids.add(visitor_id)
    lead_ids = {lead.id for lead in leads}

    conversation_filters = []
    if lead_ids:
        conversation_filters.append(Conversation.lead_id.in_(lead_ids))
    if visitor_ids:
        conversation_filters.append(Conversation.visitor_id.in_(visitor_ids))

    conversations_result = await session.execute(
        select(Conversation)
        .where(Conversation.studio_id == studio_id)
        .where(or_(*conversation_filters))
    )
    conversations = list(conversations_result.scalars().all())
    conversation_ids = {conversation.id for conversation in conversations}

    messages: list[Message] = []
    feedback: list[Feedback] = []
    if conversation_ids:
        messages_result = await session.execute(
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.studio_id == studio_id)
            .where(Message.conversation_id.in_(conversation_ids))
            .order_by(Message.created_at.asc())
        )
        messages = list(messages_result.scalars().all())
        message_ids = {message.id for message in messages}
        if message_ids:
            feedback_result = await session.execute(
                select(Feedback)
                .where(Feedback.studio_id == studio_id)
                .where(Feedback.message_id.in_(message_ids))
            )
            feedback = list(feedback_result.scalars().all())

    appointments: list[Appointment] = []
    followups: list[FollowUp] = []
    if lead_ids:
        appointments_result = await session.execute(
            select(Appointment)
            .where(Appointment.studio_id == studio_id)
            .where(Appointment.lead_id.in_(lead_ids))
        )
        followups_result = await session.execute(
            select(FollowUp)
            .where(FollowUp.studio_id == studio_id)
            .where(FollowUp.lead_id.in_(lead_ids))
        )
        appointments = list(appointments_result.scalars().all())
        followups = list(followups_result.scalars().all())

    return {
        "leads": jsonable_encoder(leads),
        "conversations": jsonable_encoder(conversations),
        "messages": jsonable_encoder(messages),
        "appointments": jsonable_encoder(appointments),
        "followups": jsonable_encoder(followups),
        "feedback": jsonable_encoder(feedback),
    }


@router.get("/export")
async def gdpr_export(
    studio: CurrentStudio,
    session: DBSession,
    visitor_id: str | None = Query(default=None, max_length=255),
    lead_id: UUID | None = None,
) -> dict[str, Any]:
    """Exports all tenant-owned data for a verified GDPR request."""
    return await _load_subject_data(session, studio.id, visitor_id, lead_id)


@router.delete("/delete")
async def gdpr_delete(
    studio: CurrentStudio,
    session: DBSession,
    visitor_id: str | None = Query(default=None, max_length=255),
    lead_id: UUID | None = None,
) -> dict[str, Any]:
    """Deletes all tenant-owned visitor/lead data for a verified GDPR request."""
    data = await _load_subject_data(session, studio.id, visitor_id, lead_id)
    lead_ids = {UUID(row["id"]) for row in data["leads"]}
    conversation_ids = {UUID(row["id"]) for row in data["conversations"]}

    if conversation_ids:
        conversations_result = await session.execute(
            select(Conversation)
            .where(Conversation.studio_id == studio.id)
            .where(Conversation.id.in_(conversation_ids))
        )
        for conversation in conversations_result.scalars().all():
            await session.delete(conversation)

    if lead_ids:
        leads_result = await session.execute(
            select(Lead).where(Lead.studio_id == studio.id).where(Lead.id.in_(lead_ids))
        )
        for lead in leads_result.scalars().all():
            await session.delete(lead)

    return {
        "success": True,
        "deleted": {
            "leads": len(data["leads"]),
            "conversations": len(data["conversations"]),
            "messages": len(data["messages"]),
            "appointments": len(data["appointments"]),
            "followups": len(data["followups"]),
            "feedback": len(data["feedback"]),
        },
    }
