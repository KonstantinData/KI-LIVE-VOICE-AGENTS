"""
Google Calendar Integration
===========================
Kapselt alle Zugriffe auf die Google Calendar API.

Ablauf:
1. Studio-Admin authorisiert die App via OAuth (einmalig)
2. Tokens werden in Berater.calendar_tokens gespeichert
3. Bei Terminbuchung: Tokens laden → Termin anlegen → event_id zurück

Verwendete Google-Bibliotheken (bereits in requirements.txt):
- google-auth, google-auth-oauthlib, google-api-python-client
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.api.config import get_settings

log = structlog.get_logger()
settings = get_settings()

# Scopes: Kalender lesen + schreiben
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]

# OAuth-Konfiguration aus Settings
_CLIENT_CONFIG = {
    "web": {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uris": [settings.google_redirect_uri],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


# ──────────────────────────────────────────────────────────────────────────────
# OAuth Flow
# ──────────────────────────────────────────────────────────────────────────────


def build_auth_url(state: str) -> str:
    """
    Erzeugt die OAuth-URL für den Studio-Admin.

    Der `state`-Parameter wird am Ende zurückgegeben und enthält die berater_id,
    damit wir nach dem Callback wissen, für welchen Berater die Tokens gelten.
    """
    flow = Flow.from_client_config(
        _CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # immer refresh_token anfordern
        state=state,
    )
    return auth_url


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """
    Tauscht den Authorization-Code gegen Access- und Refresh-Token.

    Gibt ein dict zurück, das direkt in Berater.calendar_tokens gespeichert wird.
    """
    flow = Flow.from_client_config(
        _CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
    }


def _credentials_from_tokens(tokens: dict[str, Any]) -> Credentials:
    """Baut Credentials-Objekt aus gespeichertem Token-Dict."""
    return Credentials(
        token=tokens.get("token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri=tokens.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=tokens.get("client_id", settings.google_client_id),
        client_secret=tokens.get("client_secret", settings.google_client_secret),
        scopes=tokens.get("scopes", SCOPES),
    )


def refresh_tokens_if_needed(tokens: dict[str, Any]) -> dict[str, Any]:
    """
    Erneuert den Access-Token falls abgelaufen.
    Gibt das aktualisierte Token-Dict zurück (zum Zurückspeichern in DB).
    """
    creds = _credentials_from_tokens(tokens)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        tokens["token"] = creds.token
        log.info("google_calendar.token_refreshed")
    return tokens


# ──────────────────────────────────────────────────────────────────────────────
# Calendar API
# ──────────────────────────────────────────────────────────────────────────────


def get_free_slots(
    tokens: dict[str, Any],
    calendar_id: str = "primary",
    days_ahead: int = 14,
    duration_minutes: int = 90,
) -> list[dict[str, str]]:
    """
    Gibt freie Zeitfenster der nächsten `days_ahead` Tage zurück.

    Nutzt die FreeBusy-API um belegte Zeiten zu finden und berechnet
    daraus verfügbare Slots (Mo–Fr 09:00–18:00, Sa 10:00–16:00).

    Rückgabe: Liste von {"start": "2026-03-15T10:00:00+01:00", "end": "..."}
    """
    tokens = refresh_tokens_if_needed(tokens)
    creds = _credentials_from_tokens(tokens)
    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=days_ahead)

    # Belegte Zeiten abfragen
    body = {
        "timeMin": now.isoformat(),
        "timeMax": time_max.isoformat(),
        "items": [{"id": calendar_id}],
    }
    try:
        freebusy = service.freebusy().query(body=body).execute()
        busy_periods = freebusy.get("calendars", {}).get(calendar_id, {}).get("busy", [])
    except HttpError as e:
        log.error("google_calendar.freebusy_failed", error=str(e))
        return []

    # Kandidaten-Slots generieren (Geschäftszeiten)
    slots = []
    current = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if current < now:
        current += timedelta(days=1)

    while current < time_max:
        weekday = current.weekday()  # 0=Mo, 6=So
        if weekday == 6:  # Sonntag überspringen
            current += timedelta(days=1)
            continue

        # Geschäftszeiten je Tag
        day_start_hour = 9
        day_end_hour = 18 if weekday < 5 else 16  # Sa endet um 16:00

        slot_start = current.replace(hour=day_start_hour, minute=0, second=0)
        day_end = current.replace(hour=day_end_hour, minute=0, second=0)

        while slot_start + timedelta(minutes=duration_minutes) <= day_end:
            slot_end = slot_start + timedelta(minutes=duration_minutes)

            # Prüfen ob Slot frei ist
            is_busy = any(
                _overlaps(slot_start, slot_end, b["start"], b["end"])
                for b in busy_periods
            )
            if not is_busy:
                slots.append({
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                })

            slot_start += timedelta(minutes=30)  # 30-Minuten-Raster

        current += timedelta(days=1)
        current = current.replace(hour=0, minute=0, second=0)

    return slots[:10]  # Maximal 10 Vorschläge zurückgeben


def _overlaps(
    s1: datetime,
    e1: datetime,
    s2_str: str,
    e2_str: str,
) -> bool:
    """Prüft ob zwei Zeiträume sich überschneiden."""
    from dateutil import parser as dtparser
    s2 = dtparser.parse(s2_str)
    e2 = dtparser.parse(e2_str)
    return s1 < e2 and e1 > s2


def create_calendar_event(
    tokens: dict[str, Any],
    summary: str,
    start_dt: datetime,
    duration_minutes: int,
    description: str = "",
    attendee_email: str | None = None,
    calendar_id: str = "primary",
) -> str | None:
    """
    Erstellt einen Termin im Google Calendar des Beraters.

    Gibt die Google Calendar Event-ID zurück (für external_calendar_id in DB).
    Gibt None zurück wenn die Erstellung fehlschlägt.
    """
    tokens = refresh_tokens_if_needed(tokens)
    creds = _credentials_from_tokens(tokens)
    service = build("calendar", "v3", credentials=creds)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_body: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Europe/Berlin",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Europe/Berlin",
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 30},
            ],
        },
    }

    if attendee_email:
        event_body["attendees"] = [{"email": attendee_email}]

    try:
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates="all" if attendee_email else "none",
        ).execute()
        event_id = event.get("id")
        log.info("google_calendar.event_created", event_id=event_id)
        return event_id
    except HttpError as e:
        log.error("google_calendar.create_event_failed", error=str(e))
        return None
