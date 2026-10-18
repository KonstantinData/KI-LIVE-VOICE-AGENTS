"""
System prompt builder for the template agent.

Keep role-specific prompt sections in the owning tenant/agent package.
"""

from src.db.models.studio import Studio


def build_system_prompt(
    studio: Studio,
    agent_name: str,
    role_description: str,
    knowledge_snippets: list[str] | None = None,
    lead_summary: str | None = None,
) -> str:
    """
    Baut den vollständigen System-Prompt aus Bausteinen zusammen.

    Args:
        studio: Das aktuelle Studio.
        agent_name: Public name selected by the tenant profile.
        role_description: Beschreibung der Rolle und Aufgaben.
        knowledge_snippets: Relevante Wissens-Chunks aus der Wissensbasis.
        lead_summary: Bekannte Informationen über den aktuellen Kunden.

    Returns:
        Vollständiger System-Prompt als String.
    """
    sections: list[str] = [
        f"# Du bist {agent_name} von {studio.name}",
        "",
        role_description,
    ]

    if knowledge_snippets:
        sections += [
            "",
            "## Relevantes Wissen aus deiner Wissensbasis",
            "",
            "\n\n---\n\n".join(knowledge_snippets),
        ]

    if lead_summary:
        sections += [
            "",
            "## Was du bereits über diesen Kunden weißt",
            "",
            lead_summary,
        ]

    sections += [
        "",
        "## Wichtige Regeln",
        "- Antworte immer auf Deutsch",
        "- Sei freundlich, professionell und hilfsbereit",
        "- Erfinde keine Informationen — wenn du etwas nicht weißt, sage es",
        "- Nutze deine Tools wenn sie zur Aufgabe passen",
    ]

    return "\n".join(sections)
