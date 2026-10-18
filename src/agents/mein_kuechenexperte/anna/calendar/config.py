"""Fail-closed configuration for ANNA's dedicated master calendar."""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

MASTER_CALENDAR = "kontakt@konstantinmilonas.de"


class CalendarError(Exception):
    """Public error code only; never include provider bodies or credentials."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CalendarConfig:
    tenant_id: str = ""
    authority_tenant: str = ""
    client_id: str = ""
    client_secret: str = field(default="", repr=False)
    redirect_uri: str = ""
    calendar_user: str = MASTER_CALENDAR
    encryption_key: str = field(default="", repr=False)
    data_dir: Path = Path("data/anna-calendar")
    api_token: str = field(default="", repr=False)
    mode: str = "disabled"
    timezone: str = "Europe/Berlin"
    weekly_hours: str = ""
    duration_minutes: str = ""
    buffer_minutes: str = ""
    minimum_notice_hours: str = "24"

    @classmethod
    def from_env(cls) -> "CalendarConfig":
        return cls(
            tenant_id=os.getenv("MS_TENANT_ID", ""),
            authority_tenant=os.getenv("MS_AUTHORITY_TENANT", os.getenv("MS_TENANT_ID", "")),
            client_id=os.getenv("MS_CLIENT_ID", ""),
            client_secret=os.getenv("MS_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("MS_REDIRECT_URI", ""),
            calendar_user=os.getenv("MS_CALENDAR_USER", MASTER_CALENDAR),
            encryption_key=os.getenv("ANNA_CALENDAR_ENCRYPTION_KEY", ""),
            data_dir=Path(os.getenv("ANNA_CALENDAR_DATA_DIR", "data/anna-calendar")),
            api_token=os.getenv("ANNA_CALENDAR_API_TOKEN", ""),
            mode=os.getenv("ANNA_CALENDAR_MODE", "disabled"),
            weekly_hours=os.getenv("ANNA_CALENDAR_WEEKLY_HOURS", ""),
            duration_minutes=os.getenv("ANNA_CALENDAR_DURATION_MINUTES", ""),
            buffer_minutes=os.getenv("ANNA_CALENDAR_BUFFER_MINUTES", ""),
            minimum_notice_hours=os.getenv("ANNA_CALENDAR_MINIMUM_NOTICE_HOURS", "24"),
        )

    def validate_policy(self):
        """Validate scheduling policy independently of OAuth configuration."""
        self.scheduling_policy()

    def notice_hours(self):
        """Return the internal minimum elapsed booking notice, at least 24 hours."""
        if not re.fullmatch(r"[0-9]+", str(self.minimum_notice_hours)):
            raise CalendarError("calendar_policy_invalid")
        hours = int(self.minimum_notice_hours)
        if not 24 <= hours <= 744:
            raise CalendarError("calendar_policy_invalid")
        return hours

    def scheduling_policy(self):
        """Return validated policy; production never guesses business decisions."""
        self.notice_hours()
        values = (self.weekly_hours, self.duration_minutes, self.buffer_minutes)
        if self.mode == "production" and any(str(value).strip() == "" for value in values):
            raise CalendarError("calendar_policy_required")
        try:
            raw = json.loads(self.weekly_hours) if self.weekly_hours else {str(day): [["09:00", "17:00"]] for day in range(5)}
            if not isinstance(raw, dict) or not raw or not set(raw) <= {str(day) for day in range(7)}:
                raise ValueError
            def minute(value):
                if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
                    raise ValueError
                hour, minutes = map(int, value.split(":"))
                return hour * 60 + minutes
            hours = {}
            for day, intervals in raw.items():
                if not isinstance(intervals, list):
                    raise ValueError
                parsed = []
                for interval in intervals:
                    if not isinstance(interval, list) or len(interval) != 2:
                        raise ValueError
                    start, end = map(minute, interval)
                    if start >= end:
                        raise ValueError
                    parsed.append((start, end))
                parsed.sort()
                if any(second[0] < first[1] for first, second in zip(parsed, parsed[1:])):
                    raise ValueError
                hours[int(day)] = tuple(parsed)
            duration = int(self.duration_minutes) if self.duration_minutes != "" else None
            buffer = int(self.buffer_minutes or "0")
            lengths = [end - start for intervals in hours.values() for start, end in intervals]
            if not lengths or not 0 <= buffer <= 120:
                raise ValueError
            if duration is not None and (not 15 <= duration <= 240 or duration > max(lengths)):
                raise ValueError
            return hours, duration, buffer
        except (ValueError, TypeError, AttributeError):
            raise CalendarError("calendar_policy_invalid") from None

    def validate(self) -> None:
        if self.mode not in {"test", "production"}:
            raise CalendarError("calendar_disabled")
        self.scheduling_policy()
        uri = urlsplit(self.redirect_uri)
        authority_tenant = self.authority_tenant or self.tenant_id
        if (
            not re.fullmatch(r"[a-zA-Z0-9.-]+", self.tenant_id)
            or self.tenant_id.lower() in {"common", "organizations", "consumers"}
            or authority_tenant.lower() != self.tenant_id.lower()
            or not self.client_id
            or not self.client_secret
            or not self.encryption_key
            or uri.scheme != "https"
            or not uri.hostname
            or uri.username
            or uri.query
            or uri.fragment
            or self.calendar_user.lower() != MASTER_CALENDAR
        ):
            raise CalendarError("calendar_not_configured")
