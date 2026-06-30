"""
Memory Management System
========================
What:    Memory manager for short-term and long-term agent memory.
Does:    Loads conversation context (recent messages + lead summaries); stores and retrieves lead history.
Why:     Agents need access to conversation history and accumulated knowledge about leads.
Who:     BaseAgent (via process_message), all concrete agents.
Depends: sqlalchemy, structlog, src.core.types, src.db.models.{conversation, lead, message}
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.types import AgentContext
from src.db.models.conversation import Conversation
from src.db.models.lead import Lead
from src.db.models.message import Message

log = structlog.get_logger()

CONTEXT_WINDOW_MESSAGES = 20  # Letzte N Nachrichten für Kurzzeit-Kontext


class MemoryManager:
    """
    Verwaltet Kurzzeit- und Langzeitgedächtnis.

    Kurzzeit: Letzte N Nachrichten der aktuellen Konversation
    Langzeit: Zusammenfassungen + extrahierte Fakten pro Lead
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_context(
        self, conversation_id: UUID, studio_id: UUID
    ) -> AgentContext:
        """
        Loads complete context for an agent invocation.
        
        Retrieves:
        - Last N messages from the conversation (short-term memory)
        - Lead summary if available (long-term memory)
        
        Args:
            conversation_id: ID of the current conversation
            studio_id: ID of the studio (for multi-tenant isolation)
            
        Returns:
            AgentContext with messages and lead summary
        """
        # Konversation laden
        conv_result = await self._session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.studio_id == studio_id)
        )
        conversation = conv_result.scalar_one()

        # Last N messages in chronological order
        # NOTE: We query in DESC order and reverse to get chronological order.
        # This is more efficient than ORDER BY ASC with OFFSET.
        msg_result = await self._session.execute(
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.studio_id == studio_id)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(CONTEXT_WINDOW_MESSAGES)
        )
        messages = list(reversed(msg_result.scalars().all()))

        # Lead-Zusammenfassung laden (falls vorhanden)
        lead_summary: str | None = None
        if conversation.lead_id:
            lead_result = await self._session.execute(
                select(Lead)
                .where(Lead.id == conversation.lead_id)
                .where(Lead.studio_id == studio_id)
            )
            lead = lead_result.scalar_one_or_none()
            if lead:
                lead_summary = lead.summary

        formatted_messages: list[dict[str, Any]] = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        return AgentContext(
            studio_id=studio_id,
            conversation_id=conversation_id,
            visitor_id=conversation.visitor_id,
            messages=formatted_messages,
            lead_summary=lead_summary,
        )

    async def store_summary(self, lead_id: UUID, studio_id: UUID, summary: str) -> None:
        """Speichert eine neue Zusammenfassung für einen Lead."""
        lead_result = await self._session.execute(
            select(Lead).where(Lead.id == lead_id).where(Lead.studio_id == studio_id)
        )
        lead = lead_result.scalar_one_or_none()
        if lead:
            lead.summary = summary
            log.info("memory.summary_stored", lead_id=str(lead_id))

    async def get_lead_history(self, lead_id: UUID, studio_id: UUID) -> str:
        """Gibt die gespeicherte Lead-Historie als Text zurück."""
        lead_result = await self._session.execute(
            select(Lead).where(Lead.id == lead_id).where(Lead.studio_id == studio_id)
        )
        lead = lead_result.scalar_one_or_none()
        if not lead or not lead.summary:
            return ""
        return lead.summary
