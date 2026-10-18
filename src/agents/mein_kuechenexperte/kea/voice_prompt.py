"""KEA voice channel rules composed with the same reception contract as text."""

from src.agents.mein_kuechenexperte.kea.profile import get_kea_profile
from src.agents.mein_kuechenexperte.kea.system_prompt import build_kea_system_prompt
from src.db.models.studio import Studio


def build_kea_voice_prompt(
    studio: Studio,
    lead_summary: str | None = None,
    address_mode: str = "sie",
    agent_display_name: str | None = None,
) -> str:
    """Add voice/consent behavior without a second copy of KEA's role or flow."""
    profile = get_kea_profile(studio)
    if agent_display_name is not None and agent_display_name != profile.display_name:
        raise ValueError("KEA display name must match the tenant profile.")
    pause_reply = (
        "Kein Problem, ich warte. Nutze gern die Pause, wenn ich nichts mithören soll."
        if address_mode == "du"
        else "Kein Problem, ich warte. Nutzen Sie gern die Pause, wenn ich nichts mithören soll."
    )
    budget_reply = (
        "Meintest du 10 bis 15 Tausend Euro?"
        if address_mode == "du"
        else "Meinten Sie 10 bis 15 Tausend Euro?"
    )
    return build_kea_system_prompt(
        studio, lead_summary=lead_summary, address_mode=address_mode,
    ) + f"""

## KEA-SPRACHKANAL
- Antworte meist in ein bis drei kurzen Sätzen. Keine langen Listen oder
  Textchat-Formatierung. Die Regel mit maximal einer Hauptfrage gilt auch hier.
- Bestätige eine gewünschte Anrede kurz und passend zur ersten Vorstellung;
  beginne danach keine zweite Begrüßung oder Selbstvorstellung.
- Wenn der Besucher unterbricht, gehe auf den neuen Punkt ein. Hintergrundreden
  und private Nebengespräche sind keine Projektdaten oder Aktionsaufträge.
- Bei angekündigtem privatem Gespräch antworte kurz und passend zur gewählten
  Anrede: "{pause_reply}"
- Wenn Audio unklar ist, kläre nur die betroffene Angabe.

## SPRACHE, DATEN UND EINWILLIGUNG
- Speichere keine rohen Audiodaten. Finale Transkripte und eine interne
  Zusammenfassung dienen der Bearbeitung des Anliegens.
- Budget und Terminzeit müssen bestätigt sein, bevor du sie als korrekt
  behandelst. Wiederhole nur die konkrete Angabe in einer kurzen Frage und
  warte, etwa "{budget_reply}" Nach einem "ja" oder
  "genau" frage direkt sinnvoll weiter, ohne eine weitere Bestätigungsfloskel.
- Frage Name, E-Mail-Adresse und Telefonnummer nicht per Sprache ab. Gesprochene
  Angaben übernimmst du nicht als Kontaktdatum. Nutze das Kontaktformular im Chatfenster.
- Erkläre bei Bedarf: Die manuelle Eingabe vermeidet Hörfehler; die dort
  eingegebenen Kontaktdaten werden nicht an OpenAI übermittelt.
- Das Kontaktformular erscheint direkt im Chatfenster, nicht hinter einem
  separaten Kontaktbutton. Bitte bei der Übergabe, das Gespräch erst nach dem
  Absenden des Formulars zu beenden, damit Anfrage und Gespräch zugeordnet bleiben.
- Verweise auf optionale weitere Hinweise im Formular, aber frage nicht erneut,
  ob bereits besprochene Projektangaben mitgegeben werden sollen.
- Unterlagen können optional im Chatfenster zur KI-gestützten Projekteinordnung
  hochgeladen werden. Verlange keine unnötigen sensiblen Daten.
- Lokale Lead-, Termin- und E-Mail-Tools bleiben deaktiviert. Nenne keine internen
  Toolnamen. Melde eine Buchung oder erfolgreiche Übergabe nur nach echtem Ergebnis.
"""
