"""
Voice Tool Bridge
=================
What:    Server-side bridge for Lisa tools callable from Realtime sessions.
Does:    Converts tool definitions, validates allowlists, executes Lisa tools, and audits calls.
Why:     Browser voice sessions must never execute business tools directly.
Who:     Voice routes and Realtime data-channel tool events.
Depends: sqlalchemy, src.agents.lisa, src.core.tool_runner
"""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lisa.agent import LisaAgent
from src.core.tool_runner import ToolRunner
from src.db.models.conversation import Conversation
from src.db.models.event import Event
from src.db.models.studio import Studio

log = structlog.get_logger()

VOICE_TOOL_ALLOWLIST = {"extract_lead_data", "book_appointment"}


def to_realtime_tools(tool_definitions: list[dict]) -> list[dict]:
    """Converts internal tool definitions to OpenAI Realtime function tools."""
    realtime_tools = []
    for tool in tool_definitions:
        if tool["name"] not in VOICE_TOOL_ALLOWLIST:
            continue
        realtime_tools.append({
            "type": "function",
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        })
    return realtime_tools


async def execute_voice_tool(
    *,
    session: AsyncSession,
    studio: Studio,
    conversation: Conversation,
    tool_name: str,
    arguments: dict[str, Any],
    tool_call_id: str,
) -> dict[str, Any]:
    """Executes an allowlisted Lisa tool for a voice session."""
    if tool_name not in VOICE_TOOL_ALLOWLIST:
        log.warning("voice.tool_denied", tool=tool_name, studio=studio.slug)
        return {"success": False, "error": "Tool is not allowed for voice sessions."}

    agent = LisaAgent(session=session)
    registry = agent.get_contextual_tools(conversation, studio)
    result = await ToolRunner(registry).execute(tool_name, arguments)
    audit = Event(
        studio_id=studio.id,
        type="voice_tool_call",
        actor=f"voice:{conversation.visitor_id}",
        payload={
            "conversation_id": str(conversation.id),
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "success": result.success,
            "argument_keys": sorted(arguments.keys()),
        },
    )
    session.add(audit)
    if result.success:
        return {"success": True, "result": result.result}
    return {"success": False, "error": result.error}
