"""
Scheduler Service
=================
What:    APScheduler setup and recurring maintenance jobs.
Does:    Starts background jobs, including GDPR retention cleanup.
Why:     Production must enforce storage limitation instead of retaining raw data forever.
Who:     FastAPI lifespan startup/shutdown.
Depends: apscheduler, sqlalchemy, src.api.config, src.db.database, src.db.models
"""

from datetime import datetime, timedelta, timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete, select

from src.api.config import get_settings
from src.db.database import AsyncSessionLocal
from src.db.models.conversation import Conversation
from src.db.models.event import Event
from src.db.models.feedback import Feedback
from src.db.models.lead import Lead

log = structlog.get_logger()
settings = get_settings()
scheduler = AsyncIOScheduler()


async def run_retention_cleanup() -> None:
    """Deletes or anonymizes data according to configured retention windows."""
    now = datetime.now(timezone.utc)
    conversation_cutoff = now - timedelta(days=settings.retention_conversation_days)
    lead_cutoff = now - timedelta(days=settings.retention_unconverted_lead_days)
    feedback_cutoff = now - timedelta(days=settings.retention_feedback_days)
    event_cutoff = now - timedelta(days=settings.retention_event_days)

    async with AsyncSessionLocal() as session:
        old_conversations = await session.execute(
            select(Conversation)
            .where(Conversation.studio_id.is_not(None))
            .where(Conversation.status == "closed")
            .where(Conversation.updated_at < conversation_cutoff)
        )
        deleted_conversations = 0
        for conversation in old_conversations.scalars().all():
            await session.delete(conversation)
            deleted_conversations += 1

        stale_leads = await session.execute(
            select(Lead)
            .where(Lead.studio_id.is_not(None))
            .where(Lead.status.notin_(["appointment", "converted"]))
            .where(Lead.updated_at < lead_cutoff)
        )
        anonymized_leads = 0
        for lead in stale_leads.scalars().all():
            lead.name = None
            lead.email = None
            lead.phone = None
            lead.profile = {"anonymized": True}
            lead.summary = None
            lead.status = "anonymized"
            anonymized_leads += 1

        old_feedback = await session.execute(
            select(Feedback.id)
            .where(Feedback.studio_id.is_not(None))
            .where(Feedback.created_at < feedback_cutoff)
        )
        old_event = await session.execute(
            select(Event.id)
            .where(Event.studio_id.is_not(None))
            .where(Event.created_at < event_cutoff)
        )
        deleted_feedback = len(old_feedback.scalars().all())
        deleted_events = len(old_event.scalars().all())

        await session.execute(
            delete(Feedback)
            .where(Feedback.studio_id.is_not(None))
            .where(Feedback.created_at < feedback_cutoff)
        )
        await session.execute(
            delete(Event)
            .where(Event.studio_id.is_not(None))
            .where(Event.created_at < event_cutoff)
        )

        await session.commit()

    log.info(
        "retention.cleanup_completed",
        deleted_conversations=deleted_conversations,
        anonymized_leads=anonymized_leads,
        deleted_feedback=deleted_feedback,
        deleted_events=deleted_events,
    )


def setup_scheduler() -> None:
    """Configures and starts recurring scheduler jobs."""
    if scheduler.running:
        return
    scheduler.add_job(
        run_retention_cleanup,
        "cron",
        hour=2,
        minute=15,
        id="retention_cleanup",
        replace_existing=True,
    )
    scheduler.start()
    log.info("scheduler.started")


def shutdown_scheduler() -> None:
    """Stops the scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown()
        log.info("scheduler.stopped")
