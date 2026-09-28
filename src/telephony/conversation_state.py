"""Ephemeral per-call state shared by Anna's telephone tools."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .dialect import appointment_language, spoken_clock


CONTACT_FIELDS = frozenset({"name", "email", "phone"})


def _clean(value: Any, limit: int = 254) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def _normalize(field_name: str, value: Any) -> str:
    text = _clean(value).casefold()
    if field_name == "email":
        return re.sub(r"\s+", "", text)
    if field_name == "phone":
        return "".join(character for character in text if character.isdigit())
    return text


@dataclass
class PhoneConversationState:
    """Keep customer-provided facts and confirmations for one telephone call."""

    customer_name: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    preferred_contact_method: str = ""
    appointment_type: str = ""
    preferred_day: str = ""
    preferred_date: str = ""
    preferred_week: str = ""
    preferred_time_of_day: str = ""
    preferred_time_of_day_set: bool = field(default=False, repr=False)
    preferred_time: str = ""
    preferred_time_approximate: bool = False
    appointment_request: bool = False
    availability_request: bool = False
    short_appointment_requested: bool = False
    time_clarification_required: bool = False
    clarification_question: str = ""
    excluded_periods: list[dict[str, str]] = field(default_factory=list)
    selected_slot: dict[str, str] | None = None
    request_topic: str = ""
    offered_slots: list[dict[str, str]] = field(default_factory=list)
    appointment_confirmed: bool = False
    lang: str = "de"
    _revisions: dict[str, int] = field(default_factory=dict, repr=False)
    _confirmed_revisions: dict[str, int] = field(default_factory=dict, repr=False)
    _ingested_turns: list[str] = field(default_factory=list, repr=False)
    _ambiguous_clock: str = field(default="", repr=False)

    @staticmethod
    def _confirmation_key(field_name: str) -> str:
        return "name" if field_name == "customer_name" else field_name

    def remember(
        self, field_name: str, value: Any, *, confirmed: bool = False,
        authoritative: bool = True,
    ) -> None:
        """Store the latest value and invalidate only a changed field's confirmation."""
        cleaned = _clean(value, 1600 if field_name == "request_topic" else 254)
        if not cleaned:
            return
        previous = getattr(self, field_name)
        key = self._confirmation_key(field_name)
        changed = _normalize(key, previous) != _normalize(key, cleaned)
        if changed and not authoritative and self.is_confirmed(key):
            return
        if changed:
            self._revisions[key] = self._revisions.get(key, 0) + 1
            self._confirmed_revisions.pop(key, None)
            if key in CONTACT_FIELDS:
                self._confirmed_revisions.pop("booking_consent", None)
        setattr(self, field_name, cleaned)
        if field_name == "customer_name":
            parts = cleaned.split()
            self.first_name = parts[0]
            self.last_name = " ".join(parts[1:])
        if confirmed:
            self._confirmed_revisions[key] = self._revisions.get(key, 0)

    def confirm(self, field_name: str, value: Any = "confirmed") -> bool:
        """Confirm a value idempotently; repeated confirmation cannot reset it."""
        if field_name == "booking_consent":
            self._revisions.setdefault(field_name, 0)
            self._confirmed_revisions[field_name] = self._revisions[field_name]
            return True
        target = "customer_name" if field_name == "name" else field_name
        cleaned = _clean(value)
        if cleaned:
            self.remember(target, cleaned)
        current = getattr(self, target, "")
        if not current:
            return False
        self._confirmed_revisions[field_name] = self._revisions.get(field_name, 0)
        return True

    def is_confirmed(self, field_name: str, value: Any | None = None) -> bool:
        if field_name == "booking_consent":
            return field_name in self._confirmed_revisions and (
                self._confirmed_revisions[field_name] == self._revisions.get(field_name, 0)
            )
        target = "customer_name" if field_name == "name" else field_name
        current = getattr(self, target, "") if value is None else value
        return bool(current) and self._confirmed_revisions.get(field_name) == self._revisions.get(
            field_name, 0,
        ) and _normalize(field_name, current) == _normalize(field_name, getattr(self, target, ""))

    def confirm_booking_email(self, value: str) -> None:
        """Bind the stated booking purpose to the corrected, confirmed email revision."""
        if self.is_confirmed("email", value):
            self._confirmed_revisions["booking_email"] = self._revisions.get("email", 0)

    @property
    def booking_email(self) -> str:
        """Return the confirmed booking e-mail address, or empty string."""
        if self._confirmed_revisions.get("booking_email") == self._revisions.get("email", 0):
            return self.email
        return ""

    def ingest_transcript(self, transcript: str) -> None:
        """Extract durable preferences from caller turns, applying later corrections last."""
        turns = [line for line in transcript.splitlines() if line.startswith("Anrufer:")]
        offset = len(self._ingested_turns) if turns[:len(self._ingested_turns)] == self._ingested_turns else 0
        self._ingested_turns = turns
        for line in turns[offset:]:
            text = _clean(line[8:], 1200)
            lowered = appointment_language(text)
            if re.search(r"\btermin\b", lowered):
                self.appointment_request = True
            if re.search(r"\b(?:frei|verfügbar)\b", lowered):
                self.availability_request = True
            if re.search(r"\bkurz\w*\s+termin\b", lowered):
                self.short_appointment_requested = True
            if re.search(r"\b(?:i(?:'d| would| want| need| have)|please|appointment|available|schedule)\b", lowered):
                self.lang = "en"
            excluded = bool(re.search(
                r"\bmorgen\s+nachmittag\b.*\b(?:nicht|kein)\b", lowered,
            ))
            if excluded:
                period = {"relative_day": "tomorrow", "time_of_day": "afternoon"}
                if period not in self.excluded_periods:
                    self.excluded_periods.append(period)
            elif re.search(r"\bmorgen\s+nachmittag\b.*\b(?:geht|passt)\s+doch\b", lowered):
                self.excluded_periods = [p for p in self.excluded_periods if p.get("relative_day") != "tomorrow"]
            match = re.search(
                r"\b(?:mein name ist|ich hei(?:ss|ß)e)\s+(.+?)(?:[,.]|\s+und\b|$)",
                text, flags=re.IGNORECASE,
            )
            if match:
                candidate = _clean(match.group(1), 160)
                if len(candidate.split()) >= 2:
                    self.remember("customer_name", candidate, confirmed=True)
            if re.search(r"\b(?:per|via)\s+e-?mail\b", lowered):
                self.remember("preferred_contact_method", "email")
            elif re.search(r"\b(?:telefonisch|per telefon)\b", lowered):
                self.remember("preferred_contact_method", "phone")
            time_mentions = []
            if re.search(
                r"\b(?:tageszeit(?:\s+ist)?\s+(?:mir\s+)?(?:jetzt\s+)?egal|"
                r"egal\s+(?:zu\s+)?welcher\s+tageszeit|egal\s+wann)\b",
                lowered,
            ):
                self.preferred_time_of_day = ""
                self.preferred_time_of_day_set = True
                self.preferred_time = ""
                self.time_clarification_required = False
                self.clarification_question = ""
                self._ambiguous_clock = ""
            else:
                time_mentions = []
                for pattern, canonical in (
                    (
                        r"\b(?:(?:am\s+)?(?:frühen|fruehen|früher|frueher)\s+abend|"
                        r"early\s+evening)\b",
                        "early_evening",
                    ),
                    (r"\b(?:vormittags?|morning)\b", "morning"),
                    (r"\b(?:nachmittags?|afternoon)\b", "afternoon"),
                    (
                        r"(?<!frühen )(?<!fruehen )(?<!früher )(?<!frueher )"
                        r"(?<!early )\b(?:abends?|evening)\b",
                        "evening",
                    ),
                ):
                    for mention in re.finditer(pattern, lowered):
                        before = lowered[max(0, mention.start() - 18):mention.start()]
                        after = lowered[mention.end():mention.end() + 28]
                        negated = bool(
                            re.search(r"\b(?:nicht|kein|keine|not)\s*$", before)
                            or (re.search(r"\bno\s*$", before) and mention[0] in {"morning", "afternoon", "evening"})
                            or re.match(
                                r"\s*(?:geht|passt|funktioniert)\s+(?:bei\s+mir\s+)?nicht\b",
                                after,
                            )
                        )
                        if not negated:
                            time_mentions.append((mention.start(), canonical))
                if time_mentions:
                    _, canonical = max(time_mentions)
                    self.remember("preferred_time_of_day", canonical)
                    self.preferred_time_of_day_set = True
                    self.preferred_time = ""
            if "nächste woche" in lowered or "naechste woche" in lowered:
                self.remember("preferred_week", "next_week")
            elif "diese woche" in lowered:
                self.remember("preferred_week", "this_week")
            weekday = re.search(
                r"\b(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b",
                lowered,
            )
            if weekday:
                self.remember("preferred_day", weekday.group(1))
            date_match = re.search(r"\b(\d{1,2}\.\s*(?:\d{1,2}\.|[a-zäöü]+))\b", lowered)
            if date_match:
                self.remember("preferred_date", date_match.group(1))
                if "woche" not in lowered:
                    self.preferred_week = ""
                if not weekday:
                    self.preferred_day = ""
            if any(word in lowered for word in ("erstgespräch", "erstgespraech", "vorgespräch")):
                self.remember("appointment_type", "Kostenloses Erstgespräch")
            clock = spoken_clock(lowered, self.preferred_time_of_day)
            if not clock and self._ambiguous_clock and time_mentions:
                clock = spoken_clock(self._ambiguous_clock, self.preferred_time_of_day)
            if clock:
                self.preferred_time, self.clarification_question = clock
                self.preferred_time_approximate = bool(re.search(r"\bgegen\b", lowered))
                self.time_clarification_required = bool(self.clarification_question)
                self._ambiguous_clock = lowered if self.time_clarification_required else ""
            elif re.fullmatch(r"no\s+später[.! ]*", lowered):
                self.time_clarification_required = True
                self.clarification_question = "Meinen Sie später am selben Tag oder an einem anderen Tag?"

    def remember_calendar_details(self, details: dict[str, Any]) -> None:
        name = _clean(details.get("name"), 160)
        if name:
            self.remember("customer_name", name, confirmed=True, authoritative=False)
        for field_name in ("email", "phone"):
            if details.get(field_name):
                self.remember(field_name, details[field_name], authoritative=False)
        if details.get("reason"):
            self.remember("request_topic", details["reason"], authoritative=False)
        if details.get("start"):
            self.selected_slot = {
                "start": _clean(details["start"]),
                "end": _clean(details.get("end")),
            }

    def contact_ready(self, details: dict[str, Any]) -> bool:
        self.remember_calendar_details(details)
        channels = [field_name for field_name in ("email", "phone") if details.get(field_name)]
        return bool(
            self.customer_name
            and channels
            and all(self.is_confirmed(field_name, details[field_name]) for field_name in channels)
            and (
                self.is_confirmed("booking_consent")
                or (
                    channels == ["email"]
                    and self._confirmed_revisions.get("booking_email") == self._revisions.get("email", 0)
                )
            )
        )

    def enrich_handoff(self, arguments: dict[str, Any], transcript: str) -> dict[str, Any]:
        """Fill only missing handoff fields from the same call's established state."""
        self.ingest_transcript(transcript)
        enriched = dict(arguments)
        supplied_name = _clean(" ".join(filter(None, (
            _clean(enriched.get("first_name"), 80),
            _clean(enriched.get("last_name"), 80),
        ))), 160)
        if supplied_name:
            self.remember(
                "customer_name", supplied_name, confirmed=True, authoritative=False,
            )
        if self.customer_name:
            if not _clean(enriched.get("first_name")):
                enriched["first_name"] = self.first_name
            if not _clean(enriched.get("last_name")):
                enriched["last_name"] = self.last_name
        for field_name in ("email", "phone"):
            supplied = _clean(enriched.get(field_name))
            if supplied:
                self.remember(field_name, supplied, authoritative=False)
            if getattr(self, field_name):
                enriched[field_name] = getattr(self, field_name)
        if not _clean(enriched.get("preferred_channel")) and self.preferred_contact_method:
            enriched["preferred_channel"] = self.preferred_contact_method
        if not _clean(enriched.get("conversation_summary")) and self.request_topic:
            enriched["conversation_summary"] = self.request_topic
        if self.is_confirmed("email"):
            enriched["email_confirmed"] = True
        return enriched

    def snapshot(self) -> dict[str, Any]:
        """Return call context for the model without exposing internal implementation details."""
        return {
            "customer_name": self.customer_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "preferred_contact_method": self.preferred_contact_method,
            "appointment_type": self.appointment_type,
            "preferred_day": self.preferred_day,
            "preferred_date": self.preferred_date,
            "preferred_week": self.preferred_week,
            "preferred_time_of_day": self.preferred_time_of_day,
            "preferred_time": self.preferred_time,
            "preferred_time_approximate": self.preferred_time_approximate,
            "appointment_request": self.appointment_request,
            "availability_request": self.availability_request,
            "short_appointment_requested": self.short_appointment_requested,
            "time_clarification_required": self.time_clarification_required,
            "clarification_question": self.clarification_question,
            "excluded_periods": [dict(period) for period in self.excluded_periods],
            "selected_slot": self.selected_slot,
            "offered_slots": self.offered_slots,
            "request_topic": self.request_topic,
            "name_confirmed": self.is_confirmed("name"),
            "email_confirmed": self.is_confirmed("email"),
            "phone_confirmed": self.is_confirmed("phone"),
            "appointment_confirmed": self.appointment_confirmed,
            "lang": self.lang,
        }

    def clear(self) -> None:
        """Erase all call-scoped personal data when the call ends."""
        fresh = type(self)()
        self.__dict__.clear()
        self.__dict__.update(fresh.__dict__)
