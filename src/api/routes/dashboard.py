"""
Dashboard Routes
================
What:    Aggregated KPI endpoints for the admin dashboard.
Does:    Counts tenant-owned leads, conversations, appointments, follow-ups, and feedback.
Why:     Operators need a compact production overview without ad hoc client-side aggregation.
Who:     Dashboard landing page.
Depends: fastapi, sqlalchemy, src.api.deps, src.db.models
"""

from fastapi import APIRouter
from sqlalchemy import func, select

from src.api.deps import CurrentStudio, DBSession
from src.db.models.appointment import Appointment
from src.db.models.conversation import Conversation
from src.db.models.feedback import Feedback
from src.db.models.followup import FollowUp
from src.db.models.lead import Lead

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def _count(session: DBSession, statement) -> int:
    """Executes a count statement and returns zero for NULL results."""
    result = await session.execute(statement)
    return int(result.scalar_one() or 0)


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
