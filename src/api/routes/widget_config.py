"""
Widget Configuration Routes
===========================
What:    Public endpoint for safe widget branding/configuration.
Does:    Returns non-secret settings for an active studio by slug.
Why:     Embedded widgets need runtime config without exposing admin APIs or API keys.
Who:     Website widget loader.
Depends: fastapi, sqlalchemy, src.api.deps, src.db.models.studio
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_session
from src.db.models.studio import Studio

router = APIRouter(prefix="/widget-config", tags=["Widget-Konfiguration"])


@router.get("/")
async def get_widget_config(
    studio: str = Query(..., min_length=1, max_length=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Returns public widget configuration for an active studio."""
    result = await session.execute(select(Studio).where(Studio.slug == studio))
    studio_row = result.scalar_one_or_none()
    if studio_row is None or not studio_row.is_active:
        raise HTTPException(status_code=404, detail="Studio not found")

    config = studio_row.config or {}
    return {
        "studio": studio_row.slug,
        "studio_name": studio_row.name,
        "primary_color": config.get("primary_color", "#2563eb"),
        "agent_name": config.get("agent_name", "Lisa"),
        "welcome_message": config.get(
            "welcome_message",
            "Hallo! Ich bin Lisa. Wie kann ich Ihnen helfen?",
        ),
        "privacy_url": config.get("privacy_url", "/datenschutz"),
        "retention_days": int(config.get("retention_days", 90)),
        "voice_enabled": bool(config.get("voice_enabled", False)),
    }
