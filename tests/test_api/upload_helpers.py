"""Shared helpers for upload API tests."""

from __future__ import annotations

import uuid

from src.db.models.studio import Studio


async def auth_headers(client) -> dict[str, str]:
    """Returns dashboard auth headers for protected upload routes."""
    response = await client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def seed_studio(db_session, slug: str = "mein-kuechenexperte") -> Studio:
    """Creates an active studio for upload tests."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug=slug,
        api_key=f"test-api-key-{uuid.uuid4()}",
        config={"agent_name": "KEA"},
        is_active=True,
    )
    db_session.add(studio)
    await db_session.flush()
    return studio
