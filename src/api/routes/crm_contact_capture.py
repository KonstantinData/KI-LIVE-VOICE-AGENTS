"""CRM contact capture intake routes.

This module receives sanitized contact-capture handoffs from the public website
and writes them to the append-only CRM intake ledger. It does not create
contacts, leads, conversations, activities, files, transcripts, or AI analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
import secrets
import uuid
from typing import Any

import asyncpg
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.api.config import get_settings

router = APIRouter(prefix="/crm", tags=["CRM Intake"])

CRM_TENANT_ID = "mein-kuechenexperte"
ALLOWED_CHANNELS = {"contact_form", "agent_webhook", "upload_owner", "voice"}
ALLOWED_PURPOSES = {
    "contact_request",
    "callback_request",
    "consultation_inquiry",
    "upload_owner_identification",
}
FORBIDDEN_RAW_KEYS = {
    "raw_payload",
    "raw_message",
    "transcript",
    "upload_content",
    "file_content",
    "pdf_base64",
    "secret",
    "token",
}


def _reject_forbidden_raw_keys(value: Any, path: str = "") -> None:
    """Rejects nested raw payload fields before they reach the intake ledger."""
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = str(key).lower()
            if normalized_key in FORBIDDEN_RAW_KEYS:
                location = f"{path}.{normalized_key}" if path else normalized_key
                raise ValueError(f"forbidden_raw_field:{location}")
            _reject_forbidden_raw_keys(nested, f"{path}.{normalized_key}" if path else normalized_key)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_forbidden_raw_keys(nested, f"{path}[{index}]")


class ContactHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(max_length=120)
    last_name: str = Field(max_length=120)
    full_name: str = Field(max_length=240)
    email: str = Field(max_length=254)
    phone: str = Field(default="", max_length=80)
    preferred_channel: str = Field(default="unknown", max_length=30)


class CrmContactCaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    channel_type: str
    purpose: str
    case_id: str = Field(min_length=1, max_length=160)
    decision: str
    validation_errors: list[str] = Field(default_factory=list)
    contact_handoff: ContactHandoff | None = None
    consent: dict[str, Any] = Field(default_factory=dict)
    linked_context: dict[str, Any] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)
    audit_context: dict[str, Any] = Field(default_factory=dict)
    retention: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tenant_id")
    @classmethod
    def tenant_must_match(cls, value: str) -> str:
        if value != CRM_TENANT_ID:
            raise ValueError("invalid_tenant")
        return value

    @field_validator("channel_type")
    @classmethod
    def channel_must_be_allowed(cls, value: str) -> str:
        if value not in ALLOWED_CHANNELS:
            raise ValueError("invalid_channel")
        return value

    @field_validator("purpose")
    @classmethod
    def purpose_must_be_allowed(cls, value: str) -> str:
        if value not in ALLOWED_PURPOSES:
            raise ValueError("invalid_purpose")
        return value

    @field_validator("decision")
    @classmethod
    def decision_must_be_allowed(cls, value: str) -> str:
        if value not in {"accepted", "rejected"}:
            raise ValueError("invalid_decision")
        return value

    @field_validator(
        "consent",
        "linked_context",
        "source",
        "audit_context",
        "retention",
        mode="before",
    )
    @classmethod
    def metadata_must_not_contain_raw_payloads(cls, value: Any) -> Any:
        _reject_forbidden_raw_keys(value)
        return value

    @model_validator(mode="after")
    def validate_handoff_boundary(self) -> "CrmContactCaptureRequest":
        if self.decision == "accepted" and self.contact_handoff is None:
            raise ValueError("accepted_capture_requires_contact_handoff")
        if self.decision == "rejected" and self.contact_handoff is not None:
            raise ValueError("rejected_capture_must_not_include_contact_handoff")
        return self


class CrmContactCaptureResponse(BaseModel):
    success: bool
    ledger_id: str
    decision: str


def _jsonable(value: Any) -> str:
    """Returns compact JSON for Postgres JSON text columns."""
    import json

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _normalize_postgres_url(url: str) -> str:
    """Accept SQLAlchemy asyncpg URLs while storing through asyncpg directly."""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def persist_crm_contact_capture(payload: CrmContactCaptureRequest) -> str:
    """Writes one sanitized capture to the append-only CRM intake ledger."""
    settings = get_settings()
    database_url = settings.crm_contact_capture_database_url.strip()
    if not database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="crm_contact_capture_database_not_configured",
        )

    ledger_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    contact_handoff = (
        payload.contact_handoff.model_dump(mode="json") if payload.contact_handoff else None
    )
    status_value = "captured" if payload.decision == "accepted" else "rejected"

    try:
        conn = await asyncpg.connect(_normalize_postgres_url(database_url))
    except (OSError, ValueError, asyncpg.PostgresError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="crm_contact_capture_database_unavailable",
        ) from exc
    try:
        await conn.execute(
            """
            INSERT INTO crm_contact_captures (
                id,
                tenant_id,
                case_id,
                channel_type,
                purpose,
                decision,
                validation_errors_json,
                contact_handoff_json,
                consent_json,
                linked_context_json,
                source_json,
                audit_context_json,
                retention_json,
                status,
                created_at,
                updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
            )
            """,
            ledger_id,
            payload.tenant_id,
            payload.case_id,
            payload.channel_type,
            payload.purpose,
            payload.decision,
            _jsonable(payload.validation_errors),
            _jsonable(contact_handoff) if contact_handoff is not None else None,
            _jsonable(payload.consent),
            _jsonable(payload.linked_context),
            _jsonable(payload.source),
            _jsonable(payload.audit_context),
            _jsonable(payload.retention),
            status_value,
            now,
            now,
        )
    finally:
        await conn.close()

    return ledger_id


@router.post("/contact-captures", response_model=CrmContactCaptureResponse)
async def create_crm_contact_capture(
    payload: CrmContactCaptureRequest,
    x_crm_intake_secret: str = Header(default=""),
) -> CrmContactCaptureResponse:
    """Accepts one sanitized contact handoff from a trusted website backend."""
    settings = get_settings()
    expected_secret = settings.crm_contact_capture_intake_secret.strip()
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="crm_contact_capture_intake_secret_not_configured",
        )
    if not x_crm_intake_secret or not secrets.compare_digest(
        x_crm_intake_secret,
        expected_secret,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    ledger_id = await persist_crm_contact_capture(payload)
    return CrmContactCaptureResponse(
        success=True,
        ledger_id=ledger_id,
        decision=payload.decision,
    )
