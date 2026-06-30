"""
Follow-up Routes
================
What:    Tenant-scoped follow-up endpoints.
Does:    Lists and updates manual or automated follow-up tasks.
Why:     Follow-ups are the handoff mechanism when Lisa cannot autonomously complete an action.
Who:     Dashboard follow-up page and operational staff.
Depends: fastapi, sqlalchemy, src.api.deps, src.api.schemas, src.db.models.followup
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, select

from src.api.deps import CurrentStudio, DBSession
from src.api.schemas import FollowUpResponse, FollowUpUpdate
from src.db.models.followup import FollowUp

router = APIRouter(prefix="/followups", tags=["Follow-ups"])


@router.get("/", response_model=list[FollowUpResponse])
async def list_followups(
    studio: CurrentStudio,
    session: DBSession,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[FollowUpResponse]:
    """Lists follow-ups for the current studio."""
    statement = select(FollowUp).where(FollowUp.studio_id == studio.id)
    if status:
        statement = statement.where(FollowUp.status == status)
    statement = statement.order_by(desc(FollowUp.scheduled_at)).limit(limit)
    result = await session.execute(statement)
    return [FollowUpResponse.model_validate(row) for row in result.scalars().all()]


@router.put("/{followup_id}", response_model=FollowUpResponse)
async def update_followup(
    followup_id: UUID,
    payload: FollowUpUpdate,
    studio: CurrentStudio,
    session: DBSession,
) -> FollowUpResponse:
    """Updates a follow-up owned by the current studio."""
    result = await session.execute(
        select(FollowUp).where(FollowUp.id == followup_id).where(FollowUp.studio_id == studio.id)
    )
    followup = result.scalar_one_or_none()
    if followup is None:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(followup, field, value)
    session.add(followup)
    await session.flush()
    await session.refresh(followup)
    return FollowUpResponse.model_validate(followup)
