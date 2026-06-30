"""
Google Calendar OAuth Routes
==============================
Ermöglicht Studio-Admins, ihren Google Calendar mit dem System zu verbinden.

Ablauf:
1. Admin ruft GET /google-calendar/connect?berater_id=<uuid> auf
2. Wird zu Google OAuth weitergeleitet
3. Nach Zustimmung: Google leitet zu /google-calendar/callback zurück
4. Callback tauscht Code gegen Tokens und speichert sie in Berater.calendar_tokens
5. Ab jetzt kann book_appointment echte Kalendereinträge erstellen

Endpunkte:
- GET /google-calendar/connect      → OAuth-URL generieren & weiterleiten
- GET /google-calendar/callback     → Code einlösen, Tokens speichern
- GET /google-calendar/status/{id}  → Verbindungsstatus eines Beraters prüfen
- DELETE /google-calendar/disconnect/{id} → Tokens löschen
"""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.api.deps import CurrentStudio, CurrentUser
from src.core.google_calendar import build_auth_url, exchange_code_for_tokens
from src.db.database import get_session
from src.db.models.berater import Berater

log = structlog.get_logger()
router = APIRouter(prefix="/google-calendar", tags=["Google Calendar"])
settings = get_settings()


def _encode_oauth_state(berater_id: uuid.UUID, studio_id: uuid.UUID) -> str:
    """Creates a short-lived signed OAuth state token."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    return jwt.encode(
        {
            "berater_id": str(berater_id),
            "studio_id": str(studio_id),
            "purpose": "google_calendar_oauth",
            "exp": expires_at,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _decode_oauth_state(state: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Validates and decodes the OAuth state token."""
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != "google_calendar_oauth":
            raise JWTError("Invalid purpose")
        return uuid.UUID(payload["berater_id"]), uuid.UUID(payload["studio_id"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger state-Parameter",
        ) from exc


# ──────────────────────────────────────────────────────────────────────────────
# OAuth initiieren
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/connect")
async def start_oauth(
    berater_id: uuid.UUID,
    studio: CurrentStudio,
    _user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """
    Startet den Google OAuth-Flow für einen Berater.

    Leitet den Admin direkt zu Google weiter.
    Nach der Zustimmung landet Google am /callback-Endpoint.
    """
    if (
        not settings.enable_calendar_sync
        or not settings.google_client_id
        or not settings.google_client_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Calendar integration is not configured",
        )

    # Prüfen ob Berater existiert
    result = await session.execute(
        select(Berater)
        .where(Berater.id == berater_id)
        .where(Berater.studio_id == studio.id)
        .where(Berater.is_active == True)  # noqa: E712
    )
    berater = result.scalar_one_or_none()
    if not berater:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Berater {berater_id} nicht gefunden",
        )

    state = _encode_oauth_state(berater_id, studio.id)
    auth_url = build_auth_url(state=state)
    log.info("google_calendar.oauth_started", berater_id=str(berater_id))
    return RedirectResponse(url=auth_url)


# ──────────────────────────────────────────────────────────────────────────────
# OAuth Callback
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Google leitet nach der Zustimmung hierher mit code + state zurück.

    Tauscht den Code gegen Tokens und speichert sie im Berater-Datensatz.
    """
    if (
        not settings.enable_calendar_sync
        or not settings.google_client_id
        or not settings.google_client_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Calendar integration is not configured",
        )

    berater_id, studio_id = _decode_oauth_state(state)

    result = await session.execute(
        select(Berater)
        .where(Berater.id == berater_id)
        .where(Berater.studio_id == studio_id)
    )
    berater = result.scalar_one_or_none()
    if not berater:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Berater {berater_id} nicht gefunden",
        )

    # Code gegen Tokens tauschen
    try:
        tokens = exchange_code_for_tokens(code)
    except Exception as e:
        log.error("google_calendar.token_exchange_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token-Exchange fehlgeschlagen: {e}",
        )

    # Tokens + Zeitstempel in DB speichern
    tokens["connected_at"] = datetime.now(timezone.utc).isoformat()
    berater.calendar_tokens = tokens
    berater.calendar_provider = "google"

    log.info(
        "google_calendar.oauth_completed",
        berater_id=str(berater_id),
        berater_name=berater.name,
    )

    return {
        "success": True,
        "message": f"Google Calendar für {berater.name} erfolgreich verbunden.",
        "berater_id": str(berater_id),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Status & Disconnect
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/status/{berater_id}")
async def calendar_status(
    berater_id: uuid.UUID,
    studio: CurrentStudio,
    _user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Gibt den Verbindungsstatus des Google Calendars zurück."""
    result = await session.execute(
        select(Berater)
        .where(Berater.id == berater_id)
        .where(Berater.studio_id == studio.id)
    )
    berater = result.scalar_one_or_none()
    if not berater:
        raise HTTPException(status_code=404, detail="Berater nicht gefunden")

    connected = (
        berater.calendar_provider == "google"
        and berater.calendar_tokens is not None
        and "refresh_token" in (berater.calendar_tokens or {})
    )

    return {
        "berater_id": str(berater_id),
        "berater_name": berater.name,
        "calendar_connected": connected,
        "calendar_provider": berater.calendar_provider,
        "connected_at": (berater.calendar_tokens or {}).get("connected_at"),
    }


@router.delete("/disconnect/{berater_id}")
async def disconnect_calendar(
    berater_id: uuid.UUID,
    studio: CurrentStudio,
    _user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Löscht die Google Calendar Verbindung eines Beraters."""
    result = await session.execute(
        select(Berater)
        .where(Berater.id == berater_id)
        .where(Berater.studio_id == studio.id)
    )
    berater = result.scalar_one_or_none()
    if not berater:
        raise HTTPException(status_code=404, detail="Berater nicht gefunden")

    berater.calendar_tokens = None
    berater.calendar_provider = None

    log.info("google_calendar.disconnected", berater_id=str(berater_id))
    return {"success": True, "message": f"Google Calendar für {berater.name} getrennt."}
