"""Seed-Daten: Erstellt ein Pilot-Studio für Tests."""

import asyncio
import secrets
import uuid

import structlog

from src.db.database import AsyncSessionLocal
from src.db.models.studio import Studio

log = structlog.get_logger()


async def seed() -> None:
    """Erstellt das Pilotstudio 'mein-kuechenexperte' falls nicht vorhanden."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Studio).where(Studio.slug == "mein-kuechenexperte")
        )
        existing = result.scalar_one_or_none()

        if existing:
            log.info("seed.studio_exists", slug="mein-kuechenexperte")
            return

        studio = Studio(
            id=uuid.uuid4(),
            name="Mein Küchenexperte",
            slug="mein-kuechenexperte",
            api_key=secrets.token_urlsafe(32),
            config={
                "primary_color": "#2563eb",
                "agent_name": "KEA",
                "welcome_message": (
                    "Hallo, ich bin KEA, der Küchen Expert Assistent von "
                    "Mein Küchenexperte. Möchten Sie Ihr Küchenprojekt kurz einordnen?"
                ),
            },
            is_active=True,
        )
        session.add(studio)
        await session.commit()
        log.info("seed.studio_created", slug="mein-kuechenexperte")


if __name__ == "__main__":
    asyncio.run(seed())
