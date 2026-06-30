"""
Studio Routes
=============
What:    Admin endpoints for reading and updating studio configuration.
Does:    Returns only the authenticated tenant's studio by default.
Why:     Dashboard needs a production-safe source for branding and tenant settings.
Who:     Dashboard settings page and internal admin tooling.
Depends: fastapi, src.api.deps, src.api.schemas
"""

from fastapi import APIRouter

from src.api.deps import CurrentStudio, DBSession
from src.api.schemas import StudioResponse, StudioUpdate

router = APIRouter(prefix="/studios", tags=["Studios"])


@router.get("/current", response_model=StudioResponse)
async def get_current_studio(studio: CurrentStudio) -> StudioResponse:
    """Returns the authenticated tenant's studio."""
    return StudioResponse.model_validate(studio)


@router.get("/", response_model=list[StudioResponse])
async def list_studios(studio: CurrentStudio) -> list[StudioResponse]:
    """Returns the current studio as a one-item list for MVP dashboard compatibility."""
    return [StudioResponse.model_validate(studio)]


@router.put("/current", response_model=StudioResponse)
async def update_current_studio(
    payload: StudioUpdate,
    studio: CurrentStudio,
    session: DBSession,
) -> StudioResponse:
    """Updates safe editable fields on the authenticated tenant's studio."""
    if payload.name is not None:
        studio.name = payload.name
    if payload.config is not None:
        studio.config = payload.config
    if payload.is_active is not None:
        studio.is_active = payload.is_active

    session.add(studio)
    await session.flush()
    await session.refresh(studio)
    return StudioResponse.model_validate(studio)
