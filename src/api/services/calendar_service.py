"""
Calendar Service
================
What:    Service wrapper around Google Calendar operations.
Does:    Exposes free-slot lookup, event creation, and disabled-state checks.
Why:     Keeps integration availability explicit and testable instead of leaving stubs.
Who:     Appointment workflows and future dashboard actions.
Depends: structlog, src.api.config, src.core.google_calendar
"""

from datetime import datetime
from typing import Any

import structlog

from src.api.config import get_settings
from src.core.google_calendar import create_calendar_event, get_free_slots

log = structlog.get_logger()
settings = get_settings()


class CalendarServiceDisabledError(RuntimeError):
    """Raised when calendar sync is disabled or not configured."""


class CalendarService:
    """Google Calendar integration guarded by ENABLE_CALENDAR_SYNC."""

    def _ensure_enabled(self, tokens: dict[str, Any] | None = None) -> dict[str, Any]:
        """Checks that calendar sync is enabled and tokens are present."""
        if not settings.enable_calendar_sync:
            raise CalendarServiceDisabledError("Calendar sync is disabled")
        if not settings.google_client_id or not settings.google_client_secret:
            raise CalendarServiceDisabledError("Google OAuth credentials are not configured")
        if tokens is None:
            raise CalendarServiceDisabledError("Calendar tokens are missing")
        return tokens

    async def get_free_slots(
        self,
        tokens: dict[str, Any] | None,
        days_ahead: int = 14,
        duration_minutes: int = 90,
    ) -> list[dict[str, str]]:
        """Returns free slots for a connected Google Calendar."""
        checked_tokens = self._ensure_enabled(tokens)
        return get_free_slots(
            tokens=checked_tokens,
            days_ahead=days_ahead,
            duration_minutes=duration_minutes,
        )

    async def create_event(
        self,
        tokens: dict[str, Any] | None,
        summary: str,
        start_dt: datetime,
        duration_minutes: int,
        description: str = "",
        attendee_email: str | None = None,
    ) -> str | None:
        """Creates a Google Calendar event and returns its provider ID."""
        checked_tokens = self._ensure_enabled(tokens)
        return create_calendar_event(
            tokens=checked_tokens,
            summary=summary,
            start_dt=start_dt,
            duration_minutes=duration_minutes,
            description=description,
            attendee_email=attendee_email,
        )

    async def delete_event(self, _tokens: dict[str, Any] | None, _event_id: str) -> None:
        """Reserved for future cancellation support."""
        self._ensure_enabled(_tokens)
        raise CalendarServiceDisabledError("Calendar event deletion is not enabled in MVP")
