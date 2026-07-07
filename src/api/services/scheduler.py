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
from src.api.services.project_uploads import delete_expired_upload_files

log = structlog.get_logger()
settings = get_settings()
scheduler = AsyncIOScheduler()


async def run_retention_cleanup() -> None:
    """Deletes or anonymizes data according to configured retention windows."""
    now = datetime.now(timezone.utc)
    conversation_cutoff = now - timedelta(days=settings.retention_conversation_days)
    upload_cutoff = now - timedelta(days=settings.retention_upload_days)
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

        (
            deleted_upload_files,
            deleted_orphan_upload_files,
        ) = await delete_expired_upload_files(
            session=session,
            cutoff=upload_cutoff,
        )

        old_event = await session.execute(
            select(Event.id)
            .where(Event.studio_id.is_not(None))
            .where(Event.created_at < event_cutoff)
        )
        deleted_events = len(old_event.scalars().all())

        await session.execute(
            delete(Event)
            .where(Event.studio_id.is_not(None))
            .where(Event.created_at < event_cutoff)
        )

        await session.commit()

    log.info(
        "retention.cleanup_completed",
        deleted_conversations=deleted_conversations,
        deleted_upload_files=deleted_upload_files,
        deleted_orphan_upload_files=deleted_orphan_upload_files,
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
