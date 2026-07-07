"""Shared helpers for public upload and widget runtime tests."""

import uuid

from src.db.models.studio import Studio


async def seed_studio(db_session, *, slug: str | None = None) -> Studio:
    """Creates a tenant studio with uploads enabled."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug=slug or f"upload-studio-{uuid.uuid4().hex}",
        api_key=f"upload-api-key-{uuid.uuid4()}",
        config={"agent_name": "KEA", "upload_enabled": True},
        is_active=True,
    )
    db_session.add(studio)
    await db_session.flush()
    return studio
