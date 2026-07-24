"""Typed wire contract for Olivia's only executable Voice capability."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NAVIGATION_CONTRACT_VERSION = "1.1"
NAVIGATION_TOOL_NAME = "open_liquisto_destination"
NAVIGATION_DESTINATIONS = (
    "workbench.cockpit",
    "crm.overview",
    "crm.tasks",
)
IDENTIFIER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"

Identifier = Annotated[
    str,
    Field(min_length=1, max_length=200, pattern=IDENTIFIER_PATTERN),
]
DecisionDestination = Annotated[str, Field(min_length=1, max_length=100)]
DestinationId = Literal[
    "workbench.cockpit",
    "crm.overview",
    "crm.tasks",
]


class StrictNavigationModel(BaseModel):
    """Rejects every field not present in the canonical SCAS contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class EmptyNavigationParameters(StrictNavigationModel):
    """Navigation v1.1 deliberately permits no model-controlled parameters."""


class LiquistoNavigationToolArguments(StrictNavigationModel):
    """Exact model-controlled Realtime arguments; provider call_id is excluded."""

    contract_version: Literal["1.1"]
    request_id: Identifier
    tenant_id: Literal["liquisto"]
    agent_id: Literal["liquisto-assistant"]
    source: Literal["voice"]
    intent: Literal["navigate"]
    destination_id: DestinationId
    parameters: EmptyNavigationParameters


class LiquistoNavigationTransportEnvelope(LiquistoNavigationToolArguments):
    """Same-origin BFF request after binding the provider event call_id."""

    call_id: Identifier


class LiquistoNavigationDecision(StrictNavigationModel):
    """Exact SCAS decision returned as Realtime function_call_output."""

    contract_version: Literal["1.1"]
    request_id: Identifier
    call_id: Identifier
    decision_id: Identifier
    tenant_id: Literal["liquisto"]
    agent_id: Literal["liquisto-assistant"]
    source: Literal["voice"]
    intent: Literal["navigate"]
    status: Literal["allow", "deny"]
    destination_id: DecisionDestination
    parameters: EmptyNavigationParameters
    reason_code: Literal[
        "allowed",
        "request-invalid",
        "tenant-denied",
        "agent-denied",
        "destination-denied",
        "session-denied",
        "capability-denied",
        "authority-unavailable",
    ]
    decision_time: datetime
    message: str = Field(min_length=1, max_length=320)

    @field_validator("destination_id", "message")
    @classmethod
    def validate_bounded_text(cls, value: str) -> str:
        if not value.strip() or any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("value must be non-blank and contain no control characters")
        return value

    @field_validator("decision_time")
    @classmethod
    def validate_utc_decision_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("decision_time must be a timezone-aware UTC timestamp")
        return value

    @model_validator(mode="after")
    def validate_status_reason_pair(self) -> "LiquistoNavigationDecision":
        if (self.status == "allow") != (self.reason_code == "allowed"):
            raise ValueError("only reason_code allowed may have status allow")
        return self


class LiquistoNavigationCompletionRequest(StrictNavigationModel):
    """Exact internal receipt request after an allowed local route resolves."""

    contract_version: Literal["1.1"]
    request_id: Identifier
    call_id: Identifier
    decision_id: Identifier
    destination_id: DestinationId
    parameters: EmptyNavigationParameters


def liquisto_navigation_tool_definition() -> dict[str, Any]:
    """Returns the byte-aligned Realtime function schema agreed with SCAS."""

    identifier_schema = {
        "type": "string",
        "minLength": 1,
        "maxLength": 200,
        "pattern": IDENTIFIER_PATTERN,
    }
    return {
        "type": "function",
        "name": NAVIGATION_TOOL_NAME,
        "description": (
            "Open exactly one allowlisted Liquisto Workbench destination for the "
            "authenticated employee. This tool only requests navigation; SCAS "
            "revalidates the session, principal, tenant, capability, and destination."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "contract_version",
                "request_id",
                "tenant_id",
                "agent_id",
                "source",
                "intent",
                "destination_id",
                "parameters",
            ],
            "properties": {
                "contract_version": {
                    "type": "string",
                    "const": NAVIGATION_CONTRACT_VERSION,
                },
                "request_id": dict(identifier_schema),
                "tenant_id": {"type": "string", "const": "liquisto"},
                "agent_id": {
                    "type": "string",
                    "const": "liquisto-assistant",
                },
                "source": {"type": "string", "const": "voice"},
                "intent": {"type": "string", "const": "navigate"},
                "destination_id": {
                    "type": "string",
                    "enum": list(NAVIGATION_DESTINATIONS),
                },
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {},
                    "required": [],
                },
            },
        },
    }
