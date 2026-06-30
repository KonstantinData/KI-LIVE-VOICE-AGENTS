"""
Lead Routes
===========
What:    Tenant-scoped lead endpoints for the admin dashboard.
Does:    Lists, reads, and updates lead records with mandatory studio filtering.
Why:     Studio operators need a production MVP workflow for reviewing captured leads.
Who:     Dashboard leads and lead detail pages.
Depends: fastapi, sqlalchemy, src.api.deps, src.api.schemas, src.db.models.lead
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, select

from src.api.deps import CurrentStudio, DBSession
from src.api.schemas import LeadResponse, LeadUpdate
from src.db.models.lead import Lead

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("/", response_model=list[LeadResponse])
async def list_leads(
    studio: CurrentStudio,
    session: DBSession,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[LeadResponse]:
    """Lists leads for the current studio."""
    statement = select(Lead).where(Lead.studio_id == studio.id)
    if status:
        statement = statement.where(Lead.status == status)
    statement = statement.order_by(desc(Lead.created_at)).limit(limit)
    result = await session.execute(statement)
    return [LeadResponse.model_validate(lead) for lead in result.scalars().all()]


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: UUID, studio: CurrentStudio, session: DBSession) -> LeadResponse:
    """Returns one lead if it belongs to the current studio."""
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id).where(Lead.studio_id == studio.id)
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead)


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    studio: CurrentStudio,
    session: DBSession,
) -> LeadResponse:
    """Updates safe editable fields on a lead."""
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id).where(Lead.studio_id == studio.id)
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    session.add(lead)
    await session.flush()
    await session.refresh(lead)
    return LeadResponse.model_validate(lead)
