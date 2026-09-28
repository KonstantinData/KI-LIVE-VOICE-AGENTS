"""Resolve telephone grants without falling back to browser or legacy profiles."""

from copy import deepcopy
import os

from src.agents.anna.prompt import build_anna_prompt
from src.tenants.registry import get_tenant_profile
from .calendar_tools import calendar_enabled, calendar_tool_definitions


PHONE_CONTACT_TOOL = {
    "type": "function",
    "name": "submit_phone_contact_handoff",
    "description": (
        "Übermittelt nach ausdrücklicher Zustimmung Kontaktdaten, Gesprächszusammenfassung "
        "und Telefontranskript an Mein Küchenexperte und fordert die Zusammenfassung per E-Mail an."
    ),
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "first_name", "last_name", "email", "phone", "conversation_summary",
            "best_reachability", "preferred_channel", "contact_consent_confirmed",
            "transcript_consent_confirmed",
        ],
        "properties": {
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "conversation_summary": {"type": "string"},
            "best_reachability": {"type": "string"},
            "preferred_channel": {"type": "string", "enum": ["email", "phone"]},
            "additional_notes": {"type": "string"},
            "contact_consent_confirmed": {"type": "boolean"},
            "transcript_consent_confirmed": {"type": "boolean"},
        },
    },
}


def phone_session_config(tenant_id: str, agent_id: str) -> tuple[dict, str, int]:
    """Return a provider config only for an explicitly enabled telephone agent."""
    tenant = get_tenant_profile(tenant_id)
    if tenant.tenant_id != tenant_id:
        raise ValueError("Phone tenant identity mismatch")
    agent = tenant.phone_agent(agent_id)
    if agent.prompt_profile != "mein-kuechenexperte-phone-intake":
        raise ValueError("Unsupported phone prompt profile")
    calendar_available = calendar_enabled(tenant_id, agent_id)
    instructions = build_anna_prompt(tenant, agent, calendar_available=calendar_available)
    contact_tool = deepcopy(PHONE_CONTACT_TOOL)
    if os.getenv("ANNA_DIRECT_SMTP") == "true":
        contact_tool["description"] = (
            "Sendet nach Zustimmung Name, Rückrufdaten und Anliegen direkt per interner "
            "E-Mail zur persönlichen Bearbeitung. Sendet die abgestimmte Zusammenfassung zusätzlich an den "
            "Anrufer nur bei customer_summary_consent_confirmed=true und email_confirmed=true. "
            "Keine CRM-Speicherung oder Transkriptübermittlung. "
            "E-Mail-Adresse darf leer bleiben, wenn eine Rückrufnummer vorliegt. "
            "transcript_consent_confirmed bleibt false."
        )
        for field in ("customer_summary_consent_confirmed", "email_confirmed"):
            contact_tool["parameters"]["properties"][field] = {"type": "boolean"}
            contact_tool["parameters"]["required"].append(field)
    tools = [contact_tool] if "submit_phone_contact_handoff" in agent.tools else []
    if calendar_available:
        tools.extend(calendar_tool_definitions())
    return {
        "type": "realtime",
        "model": agent.model,
        "output_modalities": ["audio"],
        "instructions": instructions,
        "audio": {
            "input": {
                "format": {"type": "audio/pcmu"},
                "transcription": {"model": "gpt-4o-mini-transcribe"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 1200,
                    "create_response": True,
                    "interrupt_response": True,
                },
            },
            "output": {"format": {"type": "audio/pcmu"}, "voice": agent.voice},
        },
        "tools": tools,
        "max_output_tokens": 1024,
    }, agent.greeting, agent.max_call_seconds
