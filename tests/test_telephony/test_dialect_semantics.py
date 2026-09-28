"""Swabian scheduling normalization preserves tool and identity boundaries."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.telephony.calendar_tools import PhoneCalendarTools
from src.telephony.conversation_state import PhoneConversationState


@pytest.mark.parametrize("utterance,expected", [
    ("I hätt gern nächste Woch am Middag en Termin.", {
        "appointment_request": True, "preferred_week": "next_week", "preferred_time_of_day": "afternoon"}),
    ("Könnet Se mol gucka, ob am Donnerstag no was frei isch?", {
        "preferred_day": "donnerstag", "availability_request": True}),
    ("No nächste Woch wär besser.", {"preferred_week": "next_week"}),
    ("I brauch bloß en kurzen Termin.", {"appointment_request": True, "short_appointment_requested": True}),
    ("No am Obed wär’s besser.", {"preferred_time_of_day": "evening"}),
])
def test_appointment_semantics(utterance, expected):
    state = PhoneConversationState()
    state.ingest_transcript("Anrufer: " + utterance)
    assert {key: state.snapshot()[key] for key in expected} == expected


@pytest.mark.parametrize("utterance,clock", [
    ("Am Fünfe wär guat.", "17:00"),
    ("Dreiviertel sechse wär besser.", "17:45"),
    ("Halb sechse passt.", "17:30"),
    ("Viertel sechse passt.", "17:15"),
    ("Am Fünfe, also um 17 Uhr.", "17:00"),
    ("Um 05:30 Uhr.", "05:30"),
    ("Um 05:30.", "05:30"),
    ("Um Mittag.", "12:00"),
    ("Um 12 Uhr mittags.", "12:00"),
])
def test_contextual_clock_and_replay(utterance, clock):
    state = PhoneConversationState()
    transcript = "Anrufer: Am frühen Abend.\nAnrufer: " + utterance
    state.ingest_transcript(transcript)
    state.ingest_transcript(transcript)
    assert state.preferred_time == clock
    assert not state.time_clarification_required


def test_ambiguous_clock_requires_clarification_until_resolved_or_withdrawn():
    state = PhoneConversationState()
    transcript = "Anrufer: Halb sechse passt."
    state.ingest_transcript(transcript)
    assert state.time_clarification_required and not state.preferred_time
    state.ingest_transcript(transcript + "\nAnrufer: Am frühen Abend.")
    assert state.preferred_time == "17:30" and not state.time_clarification_required
    state.ingest_transcript("Anrufer: No später.")
    assert state.time_clarification_required
    state.ingest_transcript("Anrufer: Egal wann.")
    assert not state.time_clarification_required and not state.preferred_time


def test_exclusion_is_date_bound_retractable_and_not_global_preference():
    state = PhoneConversationState()
    transcript = "Anrufer: Morga Mittag geht bei mir net."
    state.ingest_transcript(transcript)
    assert state.excluded_periods == [{"relative_day": "tomorrow", "time_of_day": "afternoon"}]
    assert not state.preferred_time_of_day and not state.preferred_date
    state.ingest_transcript(transcript + "\nAnrufer: Morgen Nachmittag geht doch.")
    assert state.excluded_periods == []


def test_explicit_date_correction_clears_old_week_and_weekday():
    state = PhoneConversationState()
    state.ingest_transcript("Anrufer: Nächste Woche Donnerstag.\nAnrufer: Lieber am 20. Oktober.")
    assert state.preferred_date == "20. oktober"
    assert not state.preferred_week and not state.preferred_day


@pytest.mark.asyncio
async def test_spoken_email_uses_existing_confirmation_without_dialect_rewriting(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "dialect")
    transcript = "Anrufer: Die Mail isch info at Condata Punkt io, Condata mit C."
    client.state.ingest_transcript(transcript)
    assert not client.state.is_confirmed("email")
    transcript += "\nAnna: info@condata.io, ist das richtig?\nAnrufer: Ja."
    args = {"field": "email", "value": "info@condata.io", "purpose": "booking"}
    assert (await client.execute("confirm_calendar_detail", args, transcript))["success"]
    assert (await client.execute("confirm_calendar_detail", args, transcript))["already_confirmed"]
    assert client.state.email == "info@condata.io"
    assert client.state.contact_ready({"name": "Test Person", "email": "info@condata.io"})


@pytest.mark.asyncio
async def test_phone_passes_constraints_without_changing_duration_or_week_range(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "dialect")
    requests = []

    async def request(path, payload):
        requests.append(payload)
        return {"success": True, "slots": []}

    client._request = request
    today = datetime.now(ZoneInfo("Europe/Berlin"))
    monday = (today + timedelta(days=7 - today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start, end = monday + timedelta(days=3, hours=9), monday + timedelta(days=3, hours=20)
    transcript = ("Anrufer: Nächschte Woch Donnerstag am frühen Abend.\n"
                  "Anrufer: Dreiviertel sechse wär besser.\nAnrufer: Bloß en kurzen Termin.")
    args = {"start": start.isoformat(), "end": end.isoformat(), "duration_minutes": 30, "time_of_day": "evening"}
    await client.execute("find_free_slots", args, transcript)
    forwarded = requests[-1]["arguments"]
    assert forwarded["preferred_clock"] == "17:45" and forwarded["time_of_day"] == ""
    assert forwarded["requested_weekday"] == 3
    assert forwarded["duration_minutes"] == 30
    assert forwarded["start"] == start.isoformat() and forwarded["end"] == end.isoformat()


@pytest.mark.asyncio
async def test_ambiguous_clock_cannot_dispatch_and_wrong_clock_cannot_prepare(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "dialect")
    args = {"start": "2030-01-07T09:00:00+01:00", "end": "2030-01-07T19:00:00+01:00", "duration_minutes": 30}
    result = await client.execute("find_free_slots", args, "Anrufer: Halb sechse passt.")
    assert result["error"] == "time_clarification_required"
    result = await client.execute("prepare_appointment", {"action": "create", "details": args}, "Anrufer: Also um 17:30 Uhr.")
    assert result["error"] == "caller_time_constraint_mismatch"
