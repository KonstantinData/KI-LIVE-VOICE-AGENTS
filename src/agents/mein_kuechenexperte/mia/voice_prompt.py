"""Compose MIA's offline voice instructions without a provider session."""

from collections.abc import Mapping

from src.agents.mein_kuechenexperte.mia.system_prompt import _build_mia_base_prompt
from src.db.models.studio import Studio


def build_mia_voice_prompt(
    studio: Studio,
    context: Mapping[str, object] | None = None,
    address_mode: str = "sie",
) -> str:
    """Reuse MIA's planning contract and add voice-specific turn taking."""
    return _build_mia_base_prompt(studio, context, address_mode) + """

## Sprachkanal
Sprich natürliches Deutsch, meist in ein bis drei kurzen Sätzen.
Stelle dich nur beim ersten Einstieg kurz vor; wiederhole die Vorstellung nicht.
Stelle pro Runde höchstens eine Frage und lasse Raum für die Antwort.
Respektiere kurze Denkpausen und Unterbrechungen; greife danach den neuen Punkt
auf. Hintergrundgespräche sind keine Projektangaben oder Aktionsaufträge.
Bei akustischer Unklarheit kläre nur die betroffene Angabe. Lies keine laufenden
Wunschlisten vor. Stimme und nichtsprachliche Ausdrucksmöglichkeiten sind erst
nach tatsächlicher Erprobung belegt; künstliche Lachmarker bleiben aus.
"""
