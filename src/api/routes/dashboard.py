"""
Dashboard Routes
================
What:    Aggregated KPI endpoints for the admin dashboard.
Does:    Counts tenant-owned leads, conversations, appointments, follow-ups, and feedback.
Why:     Operators need a compact production overview without ad hoc client-side aggregation.
Who:     Dashboard landing page.
Depends: fastapi, sqlalchemy, src.api.deps, src.db.models
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from src.api.deps import CurrentStudio, DBSession
from src.db.models.appointment import Appointment
from src.db.models.conversation import Conversation
from src.db.models.conversation_cost_event import ConversationCostEvent
from src.db.models.feedback import Feedback
from src.db.models.followup import FollowUp
from src.db.models.lead import Lead

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def _count(session: DBSession, statement) -> int:
    """Executes a count statement and returns zero for NULL results."""
    result = await session.execute(statement)
    return int(result.scalar_one() or 0)


def _decimal_to_float(value: Any) -> float:
    """Converts DB numeric values into stable JSON numbers."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _date_label(value: Any) -> str:
    """Formats SQL date buckets from Postgres or SQLite."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


async def _cost_breakdown(
    session: DBSession,
    *,
    studio_id,
    since: datetime,
    group_column,
) -> list[dict[str, Any]]:
    """Returns a grouped cost breakdown for a tenant-scoped report."""
    cost_sum = func.coalesce(func.sum(ConversationCostEvent.estimated_cost_usd), 0)
    token_sum = func.coalesce(func.sum(ConversationCostEvent.total_tokens), 0)
    result = await session.execute(
        select(
            group_column.label("name"),
            func.count(ConversationCostEvent.id).label("event_count"),
            token_sum.label("total_tokens"),
            cost_sum.label("estimated_cost_usd"),
        )
        .where(ConversationCostEvent.studio_id == studio_id)
        .where(ConversationCostEvent.created_at >= since)
        .group_by(group_column)
        .order_by(cost_sum.desc())
    )
    return [
        {
            "name": row.name or "unbekannt",
            "event_count": int(row.event_count or 0),
            "total_tokens": int(row.total_tokens or 0),
            "estimated_cost_usd": round(_decimal_to_float(row.estimated_cost_usd), 6),
        }
        for row in result.all()
    ]


@router.get("/stats")
async def get_dashboard_stats(studio: CurrentStudio, session: DBSession) -> dict:
    """Returns KPI stats for the current studio."""
    lead_count = await _count(
        session,
        select(func.count()).select_from(Lead).where(Lead.studio_id == studio.id),
    )
    qualified_leads = await _count(
        session,
        select(func.count())
        .select_from(Lead)
        .where(Lead.studio_id == studio.id)
        .where(Lead.status.in_(["qualified", "appointment"])),
    )
    active_conversations = await _count(
        session,
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.studio_id == studio.id)
        .where(Conversation.status == "active"),
    )
    appointments = await _count(
        session,
        select(func.count()).select_from(Appointment).where(Appointment.studio_id == studio.id),
    )
    pending_followups = await _count(
        session,
        select(func.count())
        .select_from(FollowUp)
        .where(FollowUp.studio_id == studio.id)
        .where(FollowUp.status == "pending"),
    )
    feedback_count = await _count(
        session,
        select(func.count()).select_from(Feedback).where(Feedback.studio_id == studio.id),
    )
    avg_score_result = await session.execute(
        select(func.avg(Lead.score)).where(Lead.studio_id == studio.id)
    )
    avg_score = avg_score_result.scalar_one()

    return {
        "studio": {"id": str(studio.id), "name": studio.name, "slug": studio.slug},
        "leads_total": lead_count,
        "leads_qualified": qualified_leads,
        "active_conversations": active_conversations,
        "appointments_total": appointments,
        "pending_followups": pending_followups,
        "feedback_total": feedback_count,
        "average_lead_score": round(float(avg_score or 0), 2),
    }


@router.get("/")
async def dashboard_root(studio: CurrentStudio, session: DBSession) -> dict:
    """Backward-compatible alias for dashboard stats."""
    return await get_dashboard_stats(studio, session)


@router.get("/costs")
async def get_cost_report(
    studio: CurrentStudio,
    session: DBSession,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """Returns tenant-scoped provider cost aggregates for dashboard reporting."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cost_sum = func.coalesce(func.sum(ConversationCostEvent.estimated_cost_usd), 0)
    token_sum = func.coalesce(func.sum(ConversationCostEvent.total_tokens), 0)
    audio_input_sum = func.coalesce(func.sum(ConversationCostEvent.input_audio_tokens), 0)
    audio_output_sum = func.coalesce(func.sum(ConversationCostEvent.output_audio_tokens), 0)
    image_input_sum = func.coalesce(func.sum(ConversationCostEvent.input_image_tokens), 0)

    summary_result = await session.execute(
        select(
            func.count(ConversationCostEvent.id).label("event_count"),
            func.count(func.distinct(ConversationCostEvent.conversation_id)).label(
                "conversation_count"
            ),
            token_sum.label("total_tokens"),
            audio_input_sum.label("input_audio_tokens"),
            audio_output_sum.label("output_audio_tokens"),
            image_input_sum.label("input_image_tokens"),
            cost_sum.label("estimated_cost_usd"),
        )
        .where(ConversationCostEvent.studio_id == studio.id)
        .where(ConversationCostEvent.created_at >= since)
    )
    summary = summary_result.one()

    day_bucket = func.date(ConversationCostEvent.created_at)
    daily_result = await session.execute(
        select(
            day_bucket.label("date"),
            func.count(ConversationCostEvent.id).label("event_count"),
            token_sum.label("total_tokens"),
            cost_sum.label("estimated_cost_usd"),
        )
        .where(ConversationCostEvent.studio_id == studio.id)
        .where(ConversationCostEvent.created_at >= since)
        .group_by(day_bucket)
        .order_by(day_bucket.asc())
    )

    recent_cost_sum = func.coalesce(func.sum(ConversationCostEvent.estimated_cost_usd), 0)
    recent_token_sum = func.coalesce(func.sum(ConversationCostEvent.total_tokens), 0)
    recent_result = await session.execute(
        select(
            ConversationCostEvent.conversation_id.label("conversation_id"),
            Conversation.visitor_id.label("visitor_id"),
            Conversation.channel.label("channel"),
            func.count(ConversationCostEvent.id).label("event_count"),
            recent_token_sum.label("total_tokens"),
            recent_cost_sum.label("estimated_cost_usd"),
            func.max(ConversationCostEvent.created_at).label("last_event_at"),
        )
        .join(Conversation, Conversation.id == ConversationCostEvent.conversation_id)
        .where(ConversationCostEvent.studio_id == studio.id)
        .where(Conversation.studio_id == studio.id)
        .where(ConversationCostEvent.created_at >= since)
        .group_by(
            ConversationCostEvent.conversation_id,
            Conversation.visitor_id,
            Conversation.channel,
        )
        .order_by(recent_cost_sum.desc(), func.max(ConversationCostEvent.created_at).desc())
        .limit(10)
    )

    return {
        "studio": {"id": str(studio.id), "name": studio.name, "slug": studio.slug},
        "period_days": days,
        "summary": {
            "event_count": int(summary.event_count or 0),
            "conversation_count": int(summary.conversation_count or 0),
            "total_tokens": int(summary.total_tokens or 0),
            "input_audio_tokens": int(summary.input_audio_tokens or 0),
            "output_audio_tokens": int(summary.output_audio_tokens or 0),
            "input_image_tokens": int(summary.input_image_tokens or 0),
            "estimated_cost_usd": round(
                _decimal_to_float(summary.estimated_cost_usd), 6
            ),
        },
        "daily": [
            {
                "date": _date_label(row.date),
                "event_count": int(row.event_count or 0),
                "total_tokens": int(row.total_tokens or 0),
                "estimated_cost_usd": round(
                    _decimal_to_float(row.estimated_cost_usd), 6
                ),
            }
            for row in daily_result.all()
        ],
        "by_component": await _cost_breakdown(
            session,
            studio_id=studio.id,
            since=since,
            group_column=ConversationCostEvent.component,
        ),
        "by_model": await _cost_breakdown(
            session,
            studio_id=studio.id,
            since=since,
            group_column=ConversationCostEvent.model,
        ),
        "by_channel": await _cost_breakdown(
            session,
            studio_id=studio.id,
            since=since,
            group_column=ConversationCostEvent.channel,
        ),
        "top_conversations": [
            {
                "conversation_id": str(row.conversation_id),
                "visitor_id": row.visitor_id,
                "channel": row.channel,
                "event_count": int(row.event_count or 0),
                "total_tokens": int(row.total_tokens or 0),
                "estimated_cost_usd": round(
                    _decimal_to_float(row.estimated_cost_usd), 6
                ),
                "last_event_at": row.last_event_at.isoformat()
                if row.last_event_at
                else None,
            }
            for row in recent_result.all()
        ],
    }
