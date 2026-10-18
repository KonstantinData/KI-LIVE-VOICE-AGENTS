"""
Template for a new tenant-owned text agent.

1. Copy this template into a separate tenant/agent package.
2. Rename TemplateAgent to the new agent's implementation name.
3. Implement get_system_prompt(), get_tools(), get_knowledge_categories().
4. Add explicit tenant/profile dispatch in the owning runtime entry point.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.base_agent import BaseAgent
from src.core.tool_registry import ToolRegistry
from src.db.models.studio import Studio


class TemplateAgent(BaseAgent):
    """
    Vorlage-Agent. Erbt von BaseAgent und implementiert die drei
    abstrakten Methoden als minimale Beispiele.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def get_system_prompt(
        self,
        studio: Studio,
        knowledge_snippets: list[str],
        lead_summary: str | None,
    ) -> str:
        """Gibt den System-Prompt zurück. Hier deine Agent-Persönlichkeit eintragen."""
        knowledge_block = ""
        if knowledge_snippets:
            knowledge_block = "\n\n## Relevantes Wissen\n" + "\n\n---\n".join(knowledge_snippets)

        lead_block = ""
        if lead_summary:
            lead_block = f"\n\n## Bekanntes über diesen Kunden\n{lead_summary}"

        return f"""Du bist ein freundlicher KI-Assistent für {studio.name}.

Deine Aufgabe: Besucher freundlich empfangen und weiterhelfen.{knowledge_block}{lead_block}

Antworte immer auf Deutsch. Sei höflich und professionell."""

    def get_tools(self) -> ToolRegistry:
        """Gibt die verfügbaren Tools zurück. Hier eigene Tools registrieren."""
        registry = ToolRegistry()
        # Beispiel: registry.register(MeinTool())
        return registry

    def get_knowledge_categories(self) -> list[str]:
        """
        Gibt die Wissens-Kategorien zurück, die dieser Agent durchsucht.
        Beispiele: ["produkte", "preise", "oeffnungszeiten", "faq"]
        """
        return []
