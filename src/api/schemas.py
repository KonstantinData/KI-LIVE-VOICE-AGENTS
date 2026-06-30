"""
API Schemas
===========
What:    Shared Pydantic response and request schemas for the MVP API.
Does:    Serializes SQLAlchemy models into stable JSON payloads for dashboard clients.
Why:     Keeps route modules concise and prevents accidental exposure of internal fields.
Who:     FastAPI route modules and tests.
Depends: pydantic
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudioResponse(BaseModel):
    """Public and admin-safe studio fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    config: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StudioUpdate(BaseModel):
    """Editable studio fields for the MVP admin dashboard."""

    name: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class LeadResponse(BaseModel):
    """Lead response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    studio_id: UUID
    visitor_id: str
    status: str
    score: float
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    profile: dict[str, Any] | None = None
    summary: str | None = None
    source_channel: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadUpdate(BaseModel):
    """Editable lead fields."""

    status: str | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    profile: dict[str, Any] | None = None
    summary: str | None = None


class MessageResponse(BaseModel):
    """Message response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    tool_calls: list[Any] | None = None
    token_count: int | None = None
    created_at: datetime


class ConversationResponse(BaseModel):
    """Conversation response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    studio_id: UUID
    lead_id: UUID | None = None
    visitor_id: str
    channel: str
    status: str
    summary: str | None = None
    metadata_: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AppointmentResponse(BaseModel):
    """Appointment response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    studio_id: UUID
    lead_id: UUID
    berater_id: UUID
    datetime_: datetime
    duration_minutes: int
    status: str
    external_calendar_id: str | None = None
    confirmation_sent: bool
    reminder_sent: bool
    notes: str | None = None
    created_at: datetime


class AppointmentCreate(BaseModel):
    """Creates a manually confirmed appointment."""

    lead_id: UUID
    berater_id: UUID
    datetime_: datetime
    duration_minutes: int = Field(default=60, gt=0, le=480)
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    """Editable appointment fields."""

    datetime_: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=480)
    status: str | None = None
    confirmation_sent: bool | None = None
    reminder_sent: bool | None = None
    notes: str | None = None


class FollowUpResponse(BaseModel):
    """Follow-up response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    studio_id: UUID
    lead_id: UUID
    type: str
    channel: str
    scheduled_at: datetime
    content: str | None = None
    status: str
    autonomy_level: str
    sent_at: datetime | None = None
    created_at: datetime


class FollowUpUpdate(BaseModel):
    """Editable follow-up fields."""

    status: str | None = None
    scheduled_at: datetime | None = None
    content: str | None = None
    sent_at: datetime | None = None


class KnowledgeChunkResponse(BaseModel):
    """Knowledge chunk response without raw embeddings."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    studio_id: UUID
    category: str
    title: str
    content: str
    metadata_: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeChunkCreate(BaseModel):
    """Creates a knowledge chunk; embedding generation can run later."""

    category: str
    title: str
    content: str
    metadata_: dict[str, Any] | None = None


class FeedbackResponse(BaseModel):
    """Feedback response model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    studio_id: UUID
    message_id: UUID
    rating: float | None = None
    correction: str | None = None
    created_at: datetime


class FeedbackCreate(BaseModel):
    """Creates feedback for an assistant message."""

    message_id: UUID
    rating: float | None = Field(default=None, ge=1, le=5)
    correction: str | None = None
