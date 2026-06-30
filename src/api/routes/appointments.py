"""
Appointment Routes
==================
What:    Tenant-scoped appointment endpoints.
Does:    Lists, creates, and updates manually confirmed consultation appointments.
Why:     The MVP must let staff manage bookings even when calendar automation is disabled.
Who:     Dashboard appointments page and Lisa's appointment workflow.
Depends: fastapi, sqlalchemy, src.api.deps, src.api.schemas, src.db.models
"""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, select

from src.api.deps import CurrentStudio, DBSession
from src.api.schemas import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from src.db.models.appointment import Appointment
from src.db.models.berater import Berater
from src.db.models.lead import Lead

router = APIRouter(prefix="/appointments", tags=["Termine"])


@router.get("/", response_model=list[AppointmentResponse])
async def list_appointments(
    studio: CurrentStudio,
    session: DBSession,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AppointmentResponse]:
    """Lists appointments for the current studio."""
    statement = select(Appointment).where(Appointment.studio_id == studio.id)
    if status:
        statement = statement.where(Appointment.status == status)
    statement = statement.order_by(desc(Appointment.datetime_)).limit(limit)
    result = await session.execute(statement)
    return [AppointmentResponse.model_validate(row) for row in result.scalars().all()]


@router.post("/", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    payload: AppointmentCreate,
    studio: CurrentStudio,
    session: DBSession,
) -> AppointmentResponse:
    """Creates a tenant-owned appointment after validating lead and adviser ownership."""
    lead = (
        await session.execute(
            select(Lead).where(Lead.id == payload.lead_id).where(Lead.studio_id == studio.id)
        )
    ).scalar_one_or_none()
    berater = (
        await session.execute(
            select(Berater)
            .where(Berater.id == payload.berater_id)
            .where(Berater.studio_id == studio.id)
            .where(Berater.is_active == True)  # noqa: E712
        )
    ).scalar_one_or_none()
    if lead is None or berater is None:
        raise HTTPException(status_code=404, detail="Lead or adviser not found")

    appointment = Appointment(
        id=uuid.uuid4(),
        studio_id=studio.id,
        lead_id=payload.lead_id,
        berater_id=payload.berater_id,
        datetime_=payload.datetime_,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
    )
    lead.status = "appointment"
    session.add_all([appointment, lead])
    await session.flush()
    await session.refresh(appointment)
    return AppointmentResponse.model_validate(appointment)


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: UUID,
    payload: AppointmentUpdate,
    studio: CurrentStudio,
    session: DBSession,
) -> AppointmentResponse:
    """Updates safe editable appointment fields."""
    result = await session.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .where(Appointment.studio_id == studio.id)
    )
    appointment = result.scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)
    session.add(appointment)
    await session.flush()
    await session.refresh(appointment)
    return AppointmentResponse.model_validate(appointment)
