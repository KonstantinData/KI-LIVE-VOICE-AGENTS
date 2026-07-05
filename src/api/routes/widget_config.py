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
from src.tenants.registry import widget_config_from_profile

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

    return widget_config_from_profile(
        studio_slug=studio_row.slug,
        studio_name=studio_row.name,
        db_config=studio_row.config or {},
    )
