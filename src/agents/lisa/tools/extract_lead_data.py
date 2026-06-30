"""
Tool: extract_lead_data
=======================
Lisa ruft dieses Tool auf, sobald sie neue Informationen über den Kunden gesammelt hat.
Es läuft unsichtbar im Hintergrund — bei JEDER relevanten Kundenaussage, nicht nur am Ende.

Was das Tool tut:
1. Lead in der DB anlegen oder aktualisieren (via visitor_id + studio_id)
2. Lead-Score berechnen
3. Conversation.lead_id setzen (Verknüpfung Gespräch ↔ Lead)
4. Bestätigung zurückgeben
"""

import uuid
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.tool_registry import BaseTool
from src.db.models.conversation import Conversation
from src.db.models.lead import Lead

log = structlog.get_logger()


def _calculate_score(profile: dict[str, Any]) -> float:
    """
    Berechnet den Lead-Score auf Basis der vorhandenen Informationen.

    Scoring:
    - Name bekannt:       +15
    - E-Mail bekannt:     +20
    - Telefon bekannt:    +15
    - Budget genannt:     +20
    - Zeitrahmen genannt: +15
    - Küchenstil bekannt: +10
    - Raumgröße bekannt:  + 5
    Maximum: 100 Punkte
    """
    score = 0.0
    if profile.get("name"):
        score += 15
    if profile.get("email"):
        score += 20
    if profile.get("phone"):
        score += 15
    if profile.get("budget_range"):
        score += 20
    if profile.get("timeline"):
        score += 15
    if profile.get("kitchen_style"):
        score += 10
    if profile.get("room_size"):
        score += 5
    return min(score, 100.0)


class ExtractLeadDataTool(BaseTool):
    """
    Extrahiert und speichert Lead-Daten aus dem laufenden Gespräch.

    Wird von Lisa bei JEDER neuen Kundeninformation aufgerufen.
    Braucht DB-Session, Studio-ID, Conversation-ID und Visitor-ID —
    werden beim Initialisieren übergeben (Dependency Injection).
    """

    name = "extract_lead_data"
    description = (
        "Speichere neue Informationen über den Kunden in der Datenbank. "
        "Rufe dieses Tool auf, sobald der Kunde etwas Relevantes sagt: "
        "Name, Budget, Küchenstil, Zeitrahmen, Kontaktdaten, Raumgröße. "
        "Nicht am Ende des Gesprächs — sofort bei jeder neuen Information. "
        "Das Tool läuft unsichtbar, der Kunde merkt nichts davon."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Vollständiger Name des Interessenten",
            },
            "email": {
                "type": "string",
                "description": "E-Mail-Adresse",
            },
            "phone": {
                "type": "string",
                "description": "Telefonnummer",
            },
            "kitchen_style": {
                "type": "string",
                "description": "Gewünschter Küchenstil (z.B. 'modern grifflos weiß', 'Landhausstil')",
            },
            "budget_range": {
                "type": "string",
                "description": "Ungefähres Budget (z.B. '15.000–20.000 EUR', 'ca. 25k')",
            },
            "timeline": {
                "type": "string",
                "description": "Gewünschter Zeitrahmen (z.B. 'Einzug November 2026', 'so bald wie möglich')",
            },
            "room_size": {
                "type": "string",
                "description": "Raumgröße oder Küchenform (z.B. 'L-Küche ca. 12 qm', 'Einbauküche 3 Meter')",
            },
            "special_requirements": {
                "type": "string",
                "description": "Besondere Wünsche (z.B. 'Wok-Anschluss', 'barrierefrei', 'Kochinsel')",
            },
            "notes": {
                "type": "string",
                "description": "Weitere Notizen für den Berater",
            },
        },
        "required": [],
    }

    def __init__(
        self,
        session: AsyncSession,
        studio_id: UUID,
        conversation_id: UUID,
        visitor_id: str,
    ) -> None:
        self._session = session
        self._studio_id = studio_id
        self._conversation_id = conversation_id
        self._visitor_id = visitor_id

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Erstellt oder aktualisiert den Lead und gibt Score + Status zurück."""
        # Vorhandenen Lead für diesen Besucher suchen
        result = await self._session.execute(
            select(Lead)
            .where(Lead.studio_id == self._studio_id)
            .where(Lead.visitor_id == self._visitor_id)
        )
        lead = result.scalar_one_or_none()

        if lead is None:
            lead = Lead(
                id=uuid.uuid4(),
                studio_id=self._studio_id,
                visitor_id=self._visitor_id,
                status="new",
                score=0.0,
                source_channel="widget",
                profile={},
            )
            self._session.add(lead)
            log.info("extract_lead.created", visitor_id=self._visitor_id)
        else:
            log.info("extract_lead.updated", lead_id=str(lead.id))

        # Profil-Felder zusammenführen (bestehende Daten + neue)
        profile = dict(lead.profile or {})
        field_map = {
            "name": "name",
            "email": "email",
            "phone": "phone",
            "kitchen_style": "kitchen_style",
            "budget_range": "budget_range",
            "timeline": "timeline",
            "room_size": "room_size",
            "special_requirements": "special_requirements",
            "notes": "notes",
        }
        for key, profile_key in field_map.items():
            if kwargs.get(key):
                profile[profile_key] = kwargs[key]

        # Top-Level-Felder aktualisieren
        if kwargs.get("name"):
            lead.name = kwargs["name"]
        if kwargs.get("email"):
            lead.email = kwargs["email"]
        if kwargs.get("phone"):
            lead.phone = kwargs["phone"]

        lead.profile = profile
        lead.score = _calculate_score(profile)

        # Status upgraden wenn Score hoch genug
        if lead.score >= 50 and lead.status == "new":
            lead.status = "qualified"

        # Conversation mit Lead verknüpfen
        conv_result = await self._session.execute(
            select(Conversation)
            .where(Conversation.id == self._conversation_id)
            .where(Conversation.studio_id == self._studio_id)
        )
        conversation = conv_result.scalar_one_or_none()
        if conversation and conversation.lead_id is None:
            conversation.lead_id = lead.id

        log.info(
            "extract_lead.scored",
            lead_id=str(lead.id),
            score=lead.score,
            status=lead.status,
        )

        return {
            "success": True,
            "lead_score": lead.score,
            "lead_status": lead.status,
            "fields_saved": [k for k in field_map if kwargs.get(k)],
        }
