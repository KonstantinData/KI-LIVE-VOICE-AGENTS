"""
Tool: book_appointment
======================
Lisa ruft dieses Tool auf, wenn der Kunde einem Beratungstermin zustimmt.

Ablauf:
1. Lead laden (muss via extract_lead_data angelegt worden sein)
2. Ersten Berater mit Google Calendar Verbindung suchen
3. Falls verbunden: Termin in Google Calendar anlegen + Appointment in DB
4. Immer: FollowUp für das Team anlegen
5. Lead-Status auf "appointment" setzen

Falls kein Berater mit Calendar verbunden ist:
→ Nur FollowUp speichern (manuell nachfassen)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.tool_registry import BaseTool
from src.db.models.appointment import Appointment
from src.db.models.berater import Berater
from src.db.models.followup import FollowUp
from src.db.models.lead import Lead

log = structlog.get_logger()


class BookAppointmentTool(BaseTool):
    """
    Bucht einen Beratungstermin.

    Versucht zuerst einen echten Google Calendar-Eintrag zu erstellen.
    Fällt auf manuellen FollowUp zurück wenn kein Calendar verbunden ist.
    """

    name = "book_appointment"
    description = (
        "Buche einen Beratungstermin, wenn der Kunde zustimmt. "
        "Übergib Wunschtermin (Datum/Uhrzeit als Text), Namen und Kontaktdaten. "
        "Der Termin wird gespeichert und das Studio-Team wird benachrichtigt."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "wished_datetime": {
                "type": "string",
                "description": "Gewünschter Termin als Text (z.B. 'Mittwoch 16 Uhr', '15. April nachmittags')",
            },
            "customer_name": {
                "type": "string",
                "description": "Name des Kunden",
            },
            "customer_email": {
                "type": "string",
                "description": "E-Mail des Kunden für die Terminbestätigung",
            },
            "customer_phone": {
                "type": "string",
                "description": "Telefonnummer des Kunden",
            },
            "notes": {
                "type": "string",
                "description": "Besondere Wünsche oder Infos für den Berater",
            },
        },
        "required": ["wished_datetime"],
    }

    def __init__(
        self,
        session: AsyncSession,
        studio_id: UUID,
        visitor_id: str,
    ) -> None:
        self._session = session
        self._studio_id = studio_id
        self._visitor_id = visitor_id

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Bucht Termin — mit Google Calendar falls verfügbar, sonst als FollowUp."""
        wished_datetime = kwargs.get("wished_datetime", "")
        customer_name = kwargs.get("customer_name", "")
        customer_email = kwargs.get("customer_email", "")
        notes = kwargs.get("notes", "")

        # Lead laden
        result = await self._session.execute(
            select(Lead)
            .where(Lead.studio_id == self._studio_id)
            .where(Lead.visitor_id == self._visitor_id)
        )
        lead = result.scalar_one_or_none()

        if lead is None:
            log.warning("book_appointment.no_lead", visitor_id=self._visitor_id)
            return {
                "success": False,
                "message": (
                    "Kein Lead-Datensatz gefunden. "
                    "Bitte zuerst extract_lead_data aufrufen."
                ),
            }

        lead.status = "appointment"

        # Berater mit Google Calendar Verbindung suchen
        berater_result = await self._session.execute(
            select(Berater)
            .where(Berater.studio_id == self._studio_id)
            .where(Berater.is_active == True)  # noqa: E712
        )
        berater_list = list(berater_result.scalars().all())
        berater_with_calendar = next(
            (
                b for b in berater_list
                if b.calendar_provider == "google"
                and b.calendar_tokens
                and "refresh_token" in b.calendar_tokens
            ),
            None,
        )

        # FollowUp-Inhalt aufbauen
        content_parts = [f"Terminwunsch: {wished_datetime}"]
        if customer_name:
            content_parts.append(f"Kunde: {customer_name}")
        if customer_email:
            content_parts.append(f"E-Mail: {customer_email}")
        if notes:
            content_parts.append(f"Notizen: {notes}")

        external_calendar_id: str | None = None
        calendar_booked = False

        # Google Calendar Termin anlegen falls verfügbar
        if berater_with_calendar:
            adviser_name = berater_with_calendar.name
            external_calendar_id = await self._try_create_calendar_event(
                berater=berater_with_calendar,
                wished_datetime=wished_datetime,
                customer_name=customer_name,
                customer_email=customer_email,
                notes=notes,
            )
            if external_calendar_id:
                calendar_booked = True
                content_parts.append(f"Google Calendar Event-ID: {external_calendar_id}")

        # Appointment in DB speichern falls Calendar gebucht
        if berater_with_calendar and calendar_booked:
            appointment = Appointment(
                id=uuid.uuid4(),
                studio_id=self._studio_id,
                lead_id=lead.id,
                berater_id=berater_with_calendar.id,
                datetime_=_next_business_day_at_10(),
                duration_minutes=berater_with_calendar.appointment_duration_minutes,
                status="scheduled",
                external_calendar_id=external_calendar_id,
                notes=notes or None,
            )
            self._session.add(appointment)

        # FollowUp immer anlegen
        followup_type = "appointment_confirmed" if calendar_booked else "appointment_request"
        followup = FollowUp(
            id=uuid.uuid4(),
            studio_id=self._studio_id,
            lead_id=lead.id,
            type=followup_type,
            channel="widget",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
            content="\n".join(content_parts),
            status="pending",
            autonomy_level="manual" if not calendar_booked else "auto",
        )
        self._session.add(followup)

        log.info(
            "book_appointment.saved",
            lead_id=str(lead.id),
            wished_datetime=wished_datetime,
            calendar_booked=calendar_booked,
        )

        if calendar_booked:
            return {
                "success": True,
                "calendar_booked": True,
                "message": (
                    f"Terminwunsch für '{wished_datetime}' wurde im Kalender von "
                    f"{adviser_name} eingetragen. "
                    "Eine Bestätigung wird versendet."
                ),
            }

        return {
            "success": True,
            "calendar_booked": False,
            "message": (
                f"Terminwunsch für '{wished_datetime}' wurde gespeichert. "
                "Das Studio-Team wird sich zur Bestätigung melden."
            ),
            "next_step": "manual_confirmation_required",
        }

    async def _try_create_calendar_event(
        self,
        berater: Berater,
        wished_datetime: str,
        customer_name: str,
        customer_email: str,
        notes: str,
    ) -> str | None:
        """
        Versucht einen Google Calendar Termin zu erstellen.
        Gibt event_id zurück oder None bei Fehler.
        """
        from src.core.google_calendar import create_calendar_event, refresh_tokens_if_needed

        try:
            if berater.calendar_tokens is None:
                return None
            tokens = refresh_tokens_if_needed(berater.calendar_tokens)
            berater.calendar_tokens = tokens

            summary = f"Küchenberatung: {customer_name}" if customer_name else "Küchenberatung"
            description_parts = [f"Terminwunsch: {wished_datetime}"]
            if customer_email:
                description_parts.append(f"Kontakt: {customer_email}")
            if notes:
                description_parts.append(f"Anmerkungen: {notes}")

            event_id = create_calendar_event(
                tokens=tokens,
                summary=summary,
                start_dt=_next_business_day_at_10(),
                duration_minutes=berater.appointment_duration_minutes,
                description="\n".join(description_parts),
                attendee_email=customer_email or None,
            )
            return event_id

        except Exception as e:
            log.warning(
                "book_appointment.calendar_failed",
                berater_id=str(berater.id),
                error=str(e),
            )
            return None


def _next_business_day_at_10() -> datetime:
    """Gibt den nächsten Werktag um 10:00 Uhr zurück."""
    dt = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
    dt += timedelta(days=1)
    while dt.weekday() >= 5:  # Sa=5, So=6
        dt += timedelta(days=1)
    return dt
