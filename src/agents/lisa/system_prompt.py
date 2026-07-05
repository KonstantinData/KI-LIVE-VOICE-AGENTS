"""System prompt builder for KEA."""

from src.agents.lisa.prompts.conversation_contract import (
    KEA_CONVERSATION_CONTRACT,
    KEA_OFFER_GUIDANCE,
)
from src.agents.lisa.prompts.identity import LISA_IDENTITY
from src.agents.lisa.prompts.rules import LISA_RULES, LISA_TOOL_INSTRUCTIONS
from src.agents.lisa.prompts.tonality import LISA_TONALITY
from src.db.models.studio import Studio


def _get_studio_knowledge(studio: Studio) -> str:
    """
    Lädt die Studio-spezifische Wissensdatei anhand des Studio-Slugs.

    Für jedes neue Studio eine Datei in studio_knowledge/ anlegen.
    """
    if studio.slug == "mein-kuechenexperte":
        from src.agents.lisa.studio_knowledge.mein_kuechenexperte import (
            get_studio_context_text,
        )
        return get_studio_context_text()

    # Fallback: Minimal-Kontext aus Studio-Stammdaten
    return f"## Dein Studio: {studio.name}\n\nWeitere Informationen werden noch eingetragen."


def build_lisa_system_prompt(
    studio: Studio,
    knowledge_snippets: list[str] | None = None,
    lead_summary: str | None = None,
) -> str:
    """
    Baut den vollständigen System-Prompt für Lisa zusammen.

    Aufbau:
    1. Identität (wer Lisa ist, was ihre Aufgabe ist)
    2. Studio-Wissen (Öffnungszeiten, Sortiment, Berater, FAQ)
    3. Wissensbasis-Snippets (aus pgvector-Suche, falls vorhanden)
    4. Lead-Kontext (was Lisa bereits über diesen Kunden weiß)
    5. Tonalität (wie Lisa spricht)
    6. Regeln (was sie tut und nicht tut)
    7. Tool-Anweisungen (wann sie welches Tool aufruft)
    """
    sections: list[str] = []

    # 1. Identität
    sections.append(LISA_IDENTITY.format(studio_name=studio.name))

    # 2. Studio-Wissen
    sections.append("\n" + _get_studio_knowledge(studio))

    # 3. Wissensbasis-Snippets (aus pgvector — werden relevanter wenn DB befüllt ist)
    if knowledge_snippets:
        snippets_text = "\n\n---\n\n".join(knowledge_snippets)
        sections.append(
            f"\n## Zusätzliches Wissen aus deiner Wissensbasis\n\n{snippets_text}"
        )

    # 4. Lead-Kontext (Rückkehrender Besucher)
    if lead_summary:
        sections.append(
            f"\n## Was du bereits über diesen Kunden weißt\n\n{lead_summary}"
        )

    # 5. Tonalität
    sections.append("\n" + KEA_CONVERSATION_CONTRACT)

    sections.append("\n" + KEA_OFFER_GUIDANCE)

    sections.append("\n" + LISA_TONALITY)

    # 6. Regeln
    sections.append("\n" + LISA_RULES)

    # 7. Tool-Anweisungen
    sections.append("\n" + LISA_TOOL_INSTRUCTIONS)

    return "\n".join(sections)
