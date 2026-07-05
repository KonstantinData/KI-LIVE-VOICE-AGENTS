"""KEA website intake agent for kitchen project conversations."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lisa.system_prompt import build_lisa_system_prompt
from src.agents.lisa.tools.book_appointment import BookAppointmentTool
from src.agents.lisa.tools.extract_lead_data import ExtractLeadDataTool
from src.core.base_agent import BaseAgent
from src.core.llm import LLMClient
from src.core.tool_registry import ToolRegistry
from src.db.models.conversation import Conversation
from src.db.models.lead import Lead
from src.db.models.message import Message
from src.db.models.studio import Studio

log = structlog.get_logger()

# System-Prompt für die Zusammenfassungsgenerierung
_SUMMARY_SYSTEM_PROMPT = """Du bist ein präziser Assistent, der Gesprächszusammenfassungen erstellt.
Erstelle eine kompakte Zusammenfassung für das Team. Maximal 5–8 Sätze.
Format: Was will der Kunde? Was wurde besprochen? Was ist der nächste Schritt?
Hebe Wichtiges hervor: Budget, Zeitrahmen, Besonderheiten, offene Fragen.
Schreibe aus der Perspektive des Studios — nüchtern, informativ, kein Marketing."""


class LisaAgent(BaseAgent):
    """
    KEA — website project-intake assistant.

    Handles first contact, controlled project intake, upload/contact handoff,
    and conversation summaries.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        # Wird in process_message gesetzt, damit get_tools() Zugriff hat
        self._current_conversation_id: UUID | None = None
        self._current_studio_id: UUID | None = None
        self._current_studio_slug: str = ""
        self._current_visitor_id: str = ""

    # ──────────────────────────────────────────────────────────────────────────
    # Pflichtmethoden aus BaseAgent
    # ──────────────────────────────────────────────────────────────────────────

    def get_system_prompt(
        self,
        studio: Studio,
        knowledge_snippets: list[str],
        lead_summary: str | None,
    ) -> str:
        return build_lisa_system_prompt(
            studio=studio,
            knowledge_snippets=knowledge_snippets,
            lead_summary=lead_summary,
        )

    def get_tools(self) -> ToolRegistry:
        """
        Gibt die Tool-Registry mit den auf die aktuelle Konversation
        zugeschnittenen Tools zurück.
        """
        registry = ToolRegistry()

        if self._current_conversation_id and self._current_studio_id:
            registry.register(
                ExtractLeadDataTool(
                    session=self._session,
                    studio_id=self._current_studio_id,
                    conversation_id=self._current_conversation_id,
                    visitor_id=self._current_visitor_id,
                )
            )
            if self._current_studio_slug != "mein-kuechenexperte":
                registry.register(
                    BookAppointmentTool(
                        session=self._session,
                        studio_id=self._current_studio_id,
                        visitor_id=self._current_visitor_id,
                    )
                )

        return registry

    def get_knowledge_categories(self) -> list[str]:
        """Lisa sucht in allen relevanten Wissenskategorien."""
        return ["faq", "sortiment", "referenzen", "aktionen", "studio"]

    # ──────────────────────────────────────────────────────────────────────────
    # process_message — setzt Kontext für Tools, dann super()
    # ──────────────────────────────────────────────────────────────────────────

    async def process_message(
        self,
        user_message: str,
        conversation: Conversation,
        studio: Studio,
    ) -> str:
        """
        Setzt den Konversationskontext für die Tools und ruft dann
        den Standard-7-Schritte-Loop aus BaseAgent auf.
        """
        self._current_conversation_id = conversation.id
        self._current_studio_id = studio.id
        self._current_studio_slug = studio.slug
        self._current_visitor_id = conversation.visitor_id

        return await super().process_message(user_message, conversation, studio)

    def get_contextual_tools(
        self,
        conversation: Conversation,
        studio: Studio,
    ) -> ToolRegistry:
        """Returns Lisa's tool registry bound to a specific conversation."""
        self._current_conversation_id = conversation.id
        self._current_studio_id = studio.id
        self._current_studio_slug = studio.slug
        self._current_visitor_id = conversation.visitor_id
        return self.get_tools()

    # ──────────────────────────────────────────────────────────────────────────
    # finalize_conversation — Zusammenfassung bei Gesprächsende
    # ──────────────────────────────────────────────────────────────────────────

    async def finalize_conversation(
        self,
        conversation: Conversation,
        studio: Studio,
    ) -> None:
        """
        Wird beim WebSocket-Disconnect aufgerufen.

        1. Konversation als "closed" markieren
        2. Alle Nachrichten laden
        3. Zusammenfassung via LLM generieren
        4. In Lead.summary speichern (falls Lead verknüpft)
        """
        # Konversation schließen
        conversation.status = "closed"

        # Alle Nachrichten laden
        msg_result = await self._session.execute(
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.studio_id == studio.id)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
        )
        messages: list[Message] = list(msg_result.scalars().all())

        if not messages:
            log.info("lisa.finalize.no_messages", conversation_id=str(conversation.id))
            return

        # Gesprächsprotokoll für die Zusammenfassung aufbauen
        transcript = "\n".join(
            f"{'Kunde' if m.role == 'user' else 'Lisa'}: {m.content}"
            for m in messages
        )

        # Zusammenfassung via LLM generieren
        llm = LLMClient()
        try:
            response = await llm.chat(
                system_prompt=_SUMMARY_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Bitte erstelle eine Zusammenfassung für das Team "
                            f"des Studios '{studio.name}'.\n\n"
                            f"Gesprächsprotokoll:\n{transcript}"
                        ),
                    }
                ],
            )
            summary = response.content
        except Exception as e:
            log.warning("lisa.finalize.summary_failed", error=str(e))
            summary = f"[Automatische Zusammenfassung fehlgeschlagen: {e}]"

        # Zusammenfassung im Lead speichern
        if conversation.lead_id:
            lead_result = await self._session.execute(
                select(Lead)
                .where(Lead.id == conversation.lead_id)
                .where(Lead.studio_id == studio.id)
            )
            lead = lead_result.scalar_one_or_none()
            if lead:
                lead.summary = summary
                log.info(
                    "lisa.finalize.summary_saved",
                    lead_id=str(lead.id),
                    score=lead.score,
                )

        # Zusammenfassung auch in Conversation speichern
        conversation.summary = summary

        log.info(
            "lisa.finalize.done",
            conversation_id=str(conversation.id),
            message_count=len(messages),
        )
