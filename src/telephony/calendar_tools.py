"""Opt-in ANNA calendar tool client; no Graph credentials enter voice sessions."""

from __future__ import annotations

import os
import re
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .conversation_state import PhoneConversationState


CALENDAR_ACTIONS = frozenset({
    "get_conversation_context", "get_booking_policy",
    "get_calendar_events", "check_availability", "find_free_slots",
    "remember_offered_calendar_slots", "resolve_calendar_slot_reference",
    "confirm_calendar_detail",
    "find_customer_appointment", "prepare_appointment", "create_appointment",
    "reschedule_appointment", "cancel_appointment",
})
WRITE_ACTIONS = frozenset({"create_appointment", "reschedule_appointment", "cancel_appointment"})


def calendar_enabled(tenant_id: str, agent_id: str) -> bool:
    """Calendar authority is restricted to this phone identity and explicit opt-in."""
    return (
        tenant_id == "mein-kuechenexperte"
        and agent_id == "anna-phone-assistant"
        and os.getenv("ANNA_CALENDAR_TOOLS_ENABLED", "").lower() == "true"
    )


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "name": name, "description": description,
            "parameters": {"type": "object", "additionalProperties": False,
                           "properties": properties, "required": required}}


def calendar_tool_definitions() -> list[dict]:
    """Only bounded domain arguments are exposed; no mailbox IDs or Graph payloads."""
    stamp = {"type": "string", "description": "ISO-8601 mit UTC-Offset, z.B. 2026-10-14T15:00:00+02:00"}
    text = {"type": "string", "maxLength": 160}
    contact = {"name": text, "email": text, "phone": text}
    interval = {"start": stamp, "end": stamp}
    result = [
        _tool("get_conversation_context", "Liefert den bereits erfassten Gesprächskontext und Bestätigungsstatus. Intern verwenden, um bekannte Angaben nicht erneut abzufragen.", {}, []),
        _tool("get_booking_policy", "Liefert interne Buchungsregeln, Betriebsmodus und aktuelle Zeit. Vor der Terminsuche aufrufen. Diese Daten niemals dem Anrufer nennen.", {}, []),
        _tool("get_calendar_events", "Liefert ausschließlich belegte Zeitfenster, keine Kundendetails.", interval, ["start", "end"]),
        _tool("check_availability", "Prüft einen Zeitraum, ohne eine Reservierung vorzunehmen.", interval, ["start", "end"]),
        _tool("find_free_slots", "Sucht freie Termine innerhalb der internen Buchungszeiten und der bekannten Tageszeitpräferenz. Dem Anrufer ausschließlich konkrete freie Termine nennen, niemals die zugrunde liegenden Regeln.",
              {**interval, "duration_minutes": {"type": "integer", "minimum": 15, "maximum": 240},
               "time_of_day": {"type": "string", "enum": ["morning", "afternoon", "early_evening", "evening"]}},
              ["start", "end", "duration_minutes"]),
        _tool(
            "remember_offered_calendar_slots",
            "Speichert unmittelbar vor dem Vorlesen exakt die tatsächlich genannten Terminoptionen in derselben Reihenfolge. Nur Startwerte aus der letzten Suche verwenden.",
            {"starts": {"type": "array", "minItems": 1, "maxItems": 3,
                        "items": stamp, "uniqueItems": True}},
            ["starts"],
        ),
        _tool(
            "resolve_calendar_slot_reference",
            "Löst einen relativen Verweis des Anrufers exakt gegen die zuletzt gefundenen Terminoptionen auf. Unmittelbar bei Aussagen wie 'der erste', 'der zweite' oder 'der letzte' aufrufen, bevor du Datum oder Uhrzeit bestätigst.",
            {"reference": {"type": "string", "enum": [
                "first", "second", "third", "middle", "last", "earlier", "later",
            ]}},
            ["reference"],
        ),
        _tool(
            "confirm_calendar_detail",
            "Nach einmaligem Vorlesen einer E-Mail-Adresse oder Telefonnummer und ausdrücklichem Ja intern bestätigen. Wenn die E-Mail ausdrücklich für diese Terminaktion genannt wurde, purpose=booking setzen: keine zusätzliche Verwendungsfrage. Bei Angaben für Rückruf, Zusammenfassung oder andere Zwecke purpose=other; nicht als Buchungszustimmung behandeln. booking_consent nur nach ausdrücklicher Erlaubnis zur anderweitig erfassten Datenverwendung. Nicht erwähnen.",
            {
                "field": {"type": "string", "enum": ["email", "phone", "booking_consent"]},
                "value": {"type": "string", "maxLength": 254},
                "purpose": {"type": "string", "enum": ["booking", "other"]},
            },
            ["field", "value"],
        ),
        _tool("find_customer_appointment", "Identifiziert einen eigenen Termin anhand bestätigter Kontaktdaten und ursprünglicher Startzeit. Niemals nur nach Name suchen.",
              {**contact, "original_start": stamp}, ["name", "original_start"]),
        _tool("prepare_appointment", "Bereitet eine Änderung vor, schreibt noch nichts. Lies die Zusammenfassung vor und frage danach ausdrücklich nach Bestätigung.",
              {"action": {"type": "string", "enum": ["create", "reschedule", "cancel"]},
               "details": {"type": "object", "additionalProperties": False,
                           "properties": {**contact, **interval, "candidate_id": text,
                                          "reason": {"type": "string", "maxLength": 800},
                                          "summary": {"type": "string", "maxLength": 1600}},
                           "required": ["name"]}}, ["action", "details"]),
    ]
    for action in sorted(WRITE_ACTIONS):
        result.append(_tool(action, "Erst nach Vorlesen und einer NEUEN ausdrücklichen Bestätigung des Anrufers aufrufen. Niemals automatisch wiederholen.",
                            {"confirmation_token": {"type": "string"}, "confirmed": {"type": "boolean"},
                             "confirmation_action": {"type": "string", "enum": [action.split('_')[0]]}},
                            ["confirmation_token", "confirmed", "confirmation_action"]))
    return result


class PhoneCalendarTools:
    """Bind opaque confirmations to the actual call and a subsequent caller turn."""

    def __init__(
        self, tenant_id: str, agent_id: str, session_id: str,
        state: PhoneConversationState | None = None,
    ):
        self.enabled = calendar_enabled(tenant_id, agent_id)
        self.session_id = session_id
        self.state = state or PhoneConversationState()
        self._prepared: dict[str, int] = {}
        self._last_free_slots: list[dict[str, str]] = []
        self._selected_slot: dict[str, str] | None = None
        self._closed = False

    @staticmethod
    def _caller_turns(transcript: str) -> list[str]:
        return [line[8:].strip() for line in transcript.splitlines() if line.startswith("Anrufer:")]

    @staticmethod
    def _neutral_confirmation(text: str) -> bool:
        normalized = " ".join(text.lower().replace(",", " ").split()).strip(".!? ")
        if re.search(r"\b(?:nein|nicht|aber|no|not|don't|do not)\b", normalized):
            return False
        return (
            normalized.startswith(("ja", "yes"))
            or normalized in {
                "ich bestätige", "ich bestätige das", "genau", "stimmt", "das stimmt",
                "korrekt", "das ist korrekt", "richtig", "das ist richtig", "passt",
                "einverstanden", "i confirm", "i confirm that", "correct", "agreed",
            }
        )

    @staticmethod
    def _normalize_detail(field: str, value: str) -> str:
        value = value.strip().casefold()
        if field == "email":
            return re.sub(r"\s+", "", value)
        if field == "phone":
            return "".join(character for character in value if character.isdigit())
        return " ".join(value.split())

    def enrich_contact_handoff(self, arguments: dict, transcript: str) -> dict:
        """Reuse call-scoped contact state across calendar and fallback handoff."""
        return self.state.enrich_handoff(arguments, transcript)

    def _confirm_detail(self, arguments: dict, transcript: str) -> dict[str, Any]:
        field = str(arguments.get("field", ""))
        value = str(arguments.get("value", ""))
        if field not in {"email", "phone", "booking_consent"}:
            return {"success": False, "error": "invalid_confirmation_field"}
        if field != "booking_consent" and not self._normalize_detail(field, value):
            return {"success": False, "error": "confirmation_value_required"}
        caller_turns = self._caller_turns(transcript)
        if not caller_turns or not self._neutral_confirmation(caller_turns[-1]):
            return {"success": False, "error": "separate_caller_confirmation_required"}
        normalized = "confirmed" if field == "booking_consent" else self._normalize_detail(field, value)
        if self.state.is_confirmed(field, None if field == "booking_consent" else value):
            if field == "email" and arguments.get("purpose") == "booking":
                self.state.confirm_booking_email(value)
            return {"success": True, "confirmed_field": field, "already_confirmed": True}
        if not self.state.confirm(field, value if field != "booking_consent" else normalized):
            return {"success": False, "error": "confirmation_value_required"}
        if field == "email" and arguments.get("purpose") == "booking":
            self.state.confirm_booking_email(value)
        return {"success": True, "confirmed_field": field}

    def _resolve_slot_reference(self, reference: str) -> dict[str, Any]:
        offered = self.state.offered_slots or self._last_free_slots
        if not offered:
            return {"success": False, "error": "no_recent_slot_options"}
        positions = {
            "first": 0, "earlier": 0, "second": 1, "third": 2,
            "last": len(offered) - 1,
            "later": len(offered) - 1,
        }
        if reference == "middle":
            if len(offered) % 2 == 0:
                return {"success": False, "error": "slot_reference_ambiguous"}
            positions[reference] = len(offered) // 2
        index = positions.get(reference)
        if index is None or index >= len(offered):
            return {"success": False, "error": "slot_reference_out_of_range"}
        self._selected_slot = offered[index]
        self.state.selected_slot = dict(self._selected_slot)
        return {"success": True, "slot": self._selected_slot}

    def _remember_offered_slots(self, starts: Any) -> dict[str, Any]:
        if not isinstance(starts, list) or not 1 <= len(starts) <= 3:
            return {"success": False, "error": "invalid_offered_slots"}
        offered = []
        for start in starts:
            match = next((slot for slot in self._last_free_slots if self._same_instant(
                str(start), str(slot.get("start", "")),
            )), None)
            if match is None or match in offered:
                return {"success": False, "error": "offered_slot_not_in_latest_search"}
            offered.append(match)
        self.state.offered_slots = [dict(slot) for slot in offered]
        self.state.selected_slot = None
        self._selected_slot = None
        return {"success": True, "offered_count": len(offered)}

    def _relative_slot_from_transcript(self, transcript: str) -> dict[str, str] | None:
        patterns = (
            (r"\b(?:der|den)\s+letzt(?:e|ere)(?:n)?(?:\s+termin)?\b", "last"),
            (r"\b(?:der|den)\s+erste(?:n)?(?:\s+termin)?\b", "first"),
            (r"\b(?:der|den)\s+zweite(?:n)?(?:\s+termin)?\b", "second"),
            (r"\b(?:der|den)\s+dritte(?:n)?(?:\s+termin)?\b", "third"),
            (r"\b(?:der|den)\s+mittlere(?:n)?(?:\s+termin)?\b", "middle"),
            (r"\b(?:der|den)\s+frühere(?:n)?(?:\s+termin)?\b", "earlier"),
            (r"\b(?:der|den)\s+spätere(?:n)?(?:\s+termin)?\b", "later"),
        )
        for turn in reversed(self._caller_turns(transcript)):
            for pattern, reference in patterns:
                if re.search(pattern, turn, flags=re.IGNORECASE):
                    result = self._resolve_slot_reference(reference)
                    return result.get("slot") if result.get("success") else None
        return None

    @staticmethod
    def _same_instant(left: str, right: str) -> bool:
        from datetime import datetime

        try:
            return datetime.fromisoformat(left) == datetime.fromisoformat(right)
        except (TypeError, ValueError):
            return False

    def _contact_is_confirmed(self, details: dict, transcript: str) -> bool:
        self.state.ingest_transcript(transcript)
        return self.state.contact_ready(details)

    def _search_constraints(self, arguments: dict) -> dict:
        """Bind semantic preferences to the search, before the service's slot limit."""
        args = dict(arguments)
        zone = ZoneInfo("Europe/Berlin")
        today = datetime.now(zone).date()
        if self.state.preferred_week:
            monday = today - timedelta(days=today.weekday())
            if self.state.preferred_week == "next_week":
                monday += timedelta(days=7)
            week_start = datetime.combine(monday, time.min, zone)
            week_end = datetime.combine(monday + timedelta(days=7), time.min, zone)
            try:
                args["start"] = max(datetime.fromisoformat(str(args["start"])), week_start).isoformat()
                args["end"] = min(datetime.fromisoformat(str(args["end"])), week_end).isoformat()
            except (ValueError, TypeError, KeyError):
                pass  # The calendar service rejects invalid timestamps.
        if self.state.preferred_time_of_day_set:
            args["time_of_day"] = self.state.preferred_time_of_day
        if self.state.preferred_time:
            # A contextual 17:00 must not be removed by the generic evening >=18 rule.
            args["time_of_day"] = ""
            args["preferred_clock"] = self.state.preferred_time
            args["clock_tolerance_minutes"] = 30 if self.state.preferred_time_approximate else 0
        weekdays = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"]
        if self.state.preferred_day in weekdays:
            args["requested_weekday"] = weekdays.index(self.state.preferred_day)
        if self.state.excluded_periods:
            tomorrow = today + timedelta(days=1)
            args["excluded_intervals"] = [{
                "start": datetime.combine(tomorrow, time(12), zone).isoformat(),
                "end": datetime.combine(tomorrow, time(18), zone).isoformat(),
            } for period in self.state.excluded_periods
                if period == {"relative_day": "tomorrow", "time_of_day": "afternoon"}]
        return args

    def _matches_constraints(self, details: dict) -> bool:
        """Prevent preparation/checks from bypassing normalized caller constraints."""
        if not (self.state.preferred_week or self.state.preferred_day or self.state.preferred_time
                or self.state.excluded_periods):
            return True  # Base timestamp validation remains owned by the service.
        try:
            start = datetime.fromisoformat(str(details["start"]))
            end = datetime.fromisoformat(str(details["end"]))
            if start.tzinfo is None or end.tzinfo is None:
                return False
            constrained = self._search_constraints(details)
            local = start.astimezone(ZoneInfo("Europe/Berlin"))
            if self.state.preferred_week and not (
                datetime.fromisoformat(constrained["start"]) <= start
                and end <= datetime.fromisoformat(constrained["end"])
            ):
                return False
            if "requested_weekday" in constrained and local.weekday() != constrained["requested_weekday"]:
                return False
            if "preferred_clock" in constrained:
                hour, minute = map(int, constrained["preferred_clock"].split(":"))
                if abs(local.hour * 60 + local.minute - hour * 60 - minute) > constrained["clock_tolerance_minutes"]:
                    return False
            return not any(start < datetime.fromisoformat(period["end"]) and end > datetime.fromisoformat(period["start"])
                           for period in constrained.get("excluded_intervals", []))
        except (KeyError, ValueError, TypeError):
            return False

    async def _request(self, path: str, payload: dict) -> dict[str, Any]:
        endpoint = os.getenv("ANNA_CALENDAR_SERVICE_URL", "http://anna-calendar:8735").rstrip("/")
        token = os.getenv("ANNA_CALENDAR_API_TOKEN", "")
        if not token or endpoint not in {"http://anna-calendar:8735", "http://127.0.0.1:8735"}:
            return {"success": False, "error": "calendar_not_configured"}
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
                response = await client.post(endpoint + path, json=payload,
                                             headers={"Authorization": "Bearer " + token})
            if response.status_code != 200:
                return {"success": False, "error": "calendar_service_unavailable"}
            result = response.json()
            return result if isinstance(result, dict) else {"success": False, "error": "calendar_invalid_response"}
        except (httpx.HTTPError, ValueError):
            # A timed-out write may already have committed; never claim failure means no change.
            return {"success": False, "error": "calendar_result_unknown", "retry_automatically": False}

    async def execute(self, name: str, arguments: dict, transcript: str) -> dict:
        if not self.enabled or self._closed or name not in CALENDAR_ACTIONS:
            return {"success": False, "error": "calendar_not_authorized"}
        self.state.ingest_transcript(transcript)
        caller_turns = self._caller_turns(transcript)
        if name == "get_conversation_context":
            return {"success": True, "context": self.state.snapshot()}
        if name == "remember_offered_calendar_slots":
            return self._remember_offered_slots(arguments.get("starts"))
        if name == "resolve_calendar_slot_reference":
            return self._resolve_slot_reference(str(arguments.get("reference", "")))
        if name == "confirm_calendar_detail":
            return self._confirm_detail(arguments, transcript)
        if name in {"find_free_slots", "check_availability", "prepare_appointment"} and (
            self.state.time_clarification_required
            and not (name == "prepare_appointment" and arguments.get("action") == "cancel")
        ):
            return {"success": False, "error": "time_clarification_required",
                    "question": self.state.clarification_question}
        if name == "find_free_slots":
            arguments = self._search_constraints(arguments)
            try:
                if datetime.fromisoformat(arguments["start"]) >= datetime.fromisoformat(arguments["end"]):
                    return {"success": True, "slots": [], "context": self.state.snapshot()}
            except (ValueError, TypeError, KeyError):
                pass
        if name == "check_availability" or (
            name == "prepare_appointment" and arguments.get("action") in {"create", "reschedule"}
        ):
            details = arguments if name == "check_availability" else arguments.get("details", {})
            if not self._matches_constraints(details):
                return {"success": False, "error": "caller_time_constraint_mismatch",
                        "context": self.state.snapshot()}
        if name in {"find_customer_appointment", "prepare_appointment"}:
            details = arguments.get("details", {}) if name == "prepare_appointment" else arguments
            if not isinstance(details, dict):
                return {"success": False, "error": "separate_contact_confirmations_required"}
            if name == "prepare_appointment":
                selected = self._selected_slot or self._relative_slot_from_transcript(transcript)
                if selected and not self._same_instant(
                    str(details.get("start", "")), str(selected.get("start", "")),
                ):
                    return {"success": False, "error": "selected_slot_mismatch", "slot": selected}
            if not self._contact_is_confirmed(details, transcript):
                return {"success": False, "error": "separate_contact_confirmations_required"}
            details["contact_confirmed"] = True
            details["consent"] = True
        if name in WRITE_ACTIONS:
            token = str(arguments.get("confirmation_token", ""))
            prepared_at = self._prepared.get(token)
            latest = caller_turns[-1].lower() if caller_turns else ""
            neutral_confirmation = self._neutral_confirmation(latest) and not re.search(
                r"\b(?:buch(?:en|e)|verschieb(?:en|e)|absagen|sag(?:e|en)\s+.*\bab|"
                r"book|reschedule|cancel)\b", latest,
            )
            action_confirmations = {
                "create_appointment": r"(?:ja[, ]+buchen sie|bitte buchen|please book)",
                "reschedule_appointment": r"(?:ja[, ]+verschieben sie|bitte verschieben|please reschedule)",
                "cancel_appointment": r"(?:ja[, ]+sagen sie ab|bitte absagen|please cancel)",
            }
            affirmative = neutral_confirmation or re.fullmatch(
                action_confirmations[name] + r"[.! ]*", latest,
            )
            if prepared_at is None or len(caller_turns) <= prepared_at or not affirmative:
                return {"success": False, "error": "new_explicit_caller_confirmation_required"}
            # Consume before dispatch: a timed-out write may already have committed.
            self._prepared.pop(token, None)
        result = await self._request("/internal/execute", {
            "action": name, "arguments": arguments, "session_id": self.session_id,
        })
        if name == "find_free_slots" and result.get("success"):
            slots = result.get("slots")
            self._last_free_slots = [slot for slot in slots if isinstance(slot, dict)] if isinstance(slots, list) else []
            self._selected_slot = None
            self.state.selected_slot = None
            self.state.offered_slots = [dict(slot) for slot in self._last_free_slots]
        if name == "prepare_appointment" and result.get("confirmation_token"):
            self._prepared[str(result["confirmation_token"])] = len(caller_turns)
        if name in WRITE_ACTIONS and result.get("calendar_changed") is True:
            self.state.appointment_confirmed = True
        if name == "create_appointment" and result.get("calendar_changed") is True:
            booking_email = self.state.booking_email
            if booking_email:
                from .mail import send_appointment_confirmation
                result_details = result.get("details") or {}
                appt_name = self.state.customer_name or result_details.get("name", "")
                appt_type = self.state.appointment_type or result_details.get("appointment_type", "Kostenloses Erstgespräch")
                try:
                    await send_appointment_confirmation(
                        name=appt_name,
                        start=str(result_details.get("start", "")),
                        end=str(result_details.get("end", "")),
                        appointment_type=appt_type,
                        email=booking_email,
                        session_id=self.session_id,
                        lang=self.state.lang,
                    )
                    result["customer_confirmation_sent"] = True
                except Exception:
                    result["customer_confirmation_sent"] = False
        return result

    async def close(self) -> None:
        self._closed = True
        self._prepared.clear()
        self._last_free_slots.clear()
        self._selected_slot = None
        self.state.clear()
        if self.enabled:
            await self._request("/internal/close-session", {"session_id": self.session_id})
