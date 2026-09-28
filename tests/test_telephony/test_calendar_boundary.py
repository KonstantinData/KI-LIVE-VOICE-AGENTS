import asyncio
from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from src.agents.anna.calendar.app import create_app
from src.agents.anna.calendar.config import CalendarConfig, CalendarError
from src.telephony.calendar_tools import PhoneCalendarTools, calendar_enabled
from src.telephony.mail import send_calendar_notification


def test_calendar_gate_never_grants_kea(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    assert calendar_enabled("mein-kuechenexperte", "anna-phone-assistant")
    assert not calendar_enabled("mein-kuechenexperte", "kea")
    assert not calendar_enabled("other", "anna-phone-assistant")


@pytest.mark.parametrize("reference", ["Der Letztere.", "Den Letzteren.", "Der letzte."])
def test_latter_reference_selects_last_offered_slot(reference):
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")
    client.state.offered_slots = [
        {"start": "2026-10-05T15:00:00+02:00"},
        {"start": "2026-10-05T16:00:00+02:00"},
    ]
    assert client._relative_slot_from_transcript("Anrufer: " + reference) == client.state.offered_slots[-1]


@pytest.mark.parametrize("purpose,ready", [("booking", True), ("other", False), (None, False)])
def test_booking_email_needs_one_correctness_confirmation(monkeypatch, purpose, ready):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")
    requests = []

    async def request(path, payload):
        requests.append(payload)
        return {"success": True, "confirmation_token": "opaque", "calendar_changed": True}

    client._request = request

    async def scenario():
        transcript = "Anna: Ihre E-Mail ist test@example.com, richtig?\nAnrufer: Ja."
        arguments = {"field": "email", "value": "test@example.com"}
        if purpose:
            arguments["purpose"] = purpose
        assert (await client.execute("confirm_calendar_detail", arguments, transcript))["success"]
        details = {"name": "Test Person", "email": "test@example.com"}
        prepared = await client.execute("prepare_appointment", {"action": "create", "details": details}, transcript)
        assert prepared["success"] is ready
        if not ready:
            return
        write = {"confirmation_token": "opaque", "confirmed": True, "confirmation_action": "create"}
        assert not (await client.execute("create_appointment", write, transcript))["success"]
        assert not (await client.execute("create_appointment", write, transcript + "\nAnrufer: Der Letztere."))["success"]
        transcript += "\nAnna: Dann buche ich den Termin. Ist das richtig?\nAnrufer: Ja."
        assert (await client.execute("create_appointment", write, transcript))["success"]
        assert not (await client.execute("create_appointment", write, transcript))["success"]
        assert len(requests) == 2

    asyncio.run(scenario())


def test_new_caller_confirmation_required(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")
    calls = []

    async def request(path, payload):
        calls.append(payload)
        return {"success": True, "confirmation_token": "opaque"}

    client._request = request

    async def scenario():
        client._prepared["opaque"] = 1
        args = {"confirmation_token": "opaque", "confirmed": True}
        assert not (await client.execute("cancel_appointment", args, "Anrufer: Ja"))["success"]
        assert not (await client.execute("cancel_appointment", args, "Anrufer: Ja\nAnrufer: Nein"))["success"]
        assert (await client.execute("cancel_appointment", args, "Anrufer: Ja\nAnrufer: Ja bitte"))["success"]
        await client.close()
        assert not (await client.execute("check_availability", {}, ""))["success"]

    asyncio.run(scenario())
    assert len(calls) == 2


@pytest.mark.parametrize("confirmation,accepted", [
    ("Yes", True),
    ("Yes, please.", True),
    ("I confirm that.", True),
    ("Yes, go ahead!", True),
    ("Agreed", True),
    ("No", False),
    ("Maybe", False),
    ("Yes, but don't book", False),
    ("Yes, please, but not yet", False),
    ("I do not confirm", False),
    ("Please cancel instead", False),
])
@pytest.mark.parametrize("action", [
    "create_appointment", "reschedule_appointment", "cancel_appointment",
])
def test_english_calendar_confirmation_requires_new_unqualified_turn(
    monkeypatch, confirmation, accepted, action,
):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")
    requests = []

    async def request(path, payload):
        requests.append(payload)
        return {"success": True, "confirmation_token": "opaque"}

    client._request = request

    async def scenario():
        transcript = f"Anrufer: {confirmation}"
        client._prepared["opaque"] = 1
        arguments = {"confirmation_token": "opaque", "confirmed": True}
        stale = await client.execute(action, arguments, transcript)
        assert stale["error"] == "new_explicit_caller_confirmation_required"
        result = await client.execute(action, arguments, transcript + f"\nAnrufer: {confirmation}")
        assert result["success"] is accepted
        if not accepted:
            assert result["error"] == "new_explicit_caller_confirmation_required"

    asyncio.run(scenario())
    assert len(requests) == (1 if accepted else 0)


@pytest.mark.parametrize("confirmation,requested_action", [
    ("Please book", "create_appointment"),
    ("Bitte buchen", "create_appointment"),
    ("Ja, buchen Sie", "create_appointment"),
    ("Please reschedule", "reschedule_appointment"),
    ("Bitte verschieben", "reschedule_appointment"),
    ("Ja, verschieben Sie", "reschedule_appointment"),
    ("Please cancel", "cancel_appointment"),
    ("Bitte absagen", "cancel_appointment"),
    ("Ja, sagen Sie ab", "cancel_appointment"),
])
@pytest.mark.parametrize("action", [
    "create_appointment", "reschedule_appointment", "cancel_appointment",
])
def test_action_specific_confirmation_cannot_authorize_another_action(
    monkeypatch, confirmation, requested_action, action,
):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")
    requests = []

    async def request(path, payload):
        requests.append(payload)
        return {"success": True, "confirmation_token": "opaque"}

    client._request = request

    async def scenario():
        client._prepared["opaque"] = 1
        result = await client.execute(
            action, {"confirmation_token": "opaque", "confirmed": True},
            f"Anrufer: Prepare it\nAnrufer: {confirmation}",
        )
        assert result["success"] is (action == requested_action)
        if action != requested_action:
            assert result["error"] == "new_explicit_caller_confirmation_required"

    asyncio.run(scenario())
    assert len(requests) == (1 if action == requested_action else 0)


def test_calendar_contact_fields_require_separate_confirmations(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")
    requests = []

    async def request(path, payload):
        requests.append(payload)
        return {"success": True, "confirmation_token": "opaque"}

    client._request = request

    async def scenario():
        transcript = "Anrufer: Ich bin Konstantin Milonas und meine Nummer ist 017623785746."
        details = {"name": "Konstantin Milonas", "phone": "0176 23785746"}
        result = await client.execute(
            "prepare_appointment", {"action": "create", "details": details}, transcript,
        )
        assert result["error"] == "separate_contact_confirmations_required"

        transcript += "\nAnna: Ihre Telefonnummer ist 0176 23785746, richtig?\nAnrufer: Ja."
        assert (await client.execute(
            "confirm_calendar_detail", {"field": "phone", "value": "0176 23785746"}, transcript,
        ))["success"]
        transcript += "\nAnna: Darf ich diese Daten für die Terminbuchung verwenden?\nAnrufer: Ja."
        assert (await client.execute(
            "confirm_calendar_detail", {"field": "booking_consent", "value": ""}, transcript,
        ))["success"]

        result = await client.execute(
            "prepare_appointment", {"action": "create", "details": details}, transcript,
        )
        assert result["success"]
        assert requests[0]["arguments"]["details"]["contact_confirmed"] is True
        assert requests[0]["arguments"]["details"]["consent"] is True

    asyncio.run(scenario())


def test_calendar_contact_correction_invalidates_old_confirmation(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")

    async def scenario():
        transcript = "Anna: Ist Ihre Telefonnummer 0176 23785764?\nAnrufer: Ja."
        await client.execute(
            "confirm_calendar_detail", {"field": "phone", "value": "0176 23785764"}, transcript,
        )
        transcript += "\nAnna: Darf ich die Daten für den Termin verwenden?\nAnrufer: Ja."
        await client.execute(
            "confirm_calendar_detail", {"field": "booking_consent", "value": ""}, transcript,
        )
        transcript += "\nAnrufer: Meine Telefonnummer ist 0176 23785746."
        result = await client.execute(
            "prepare_appointment",
            {"action": "create", "details": {
                "name": "Konstantin Milonas", "phone": "0176 23785746",
            }},
            transcript,
        )
        assert result["error"] == "separate_contact_confirmations_required"

    asyncio.run(scenario())


def test_contact_confirmation_is_idempotent_and_shared_with_fallback(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")

    async def scenario():
        transcript = (
            "Anrufer: Mein Name ist Konstantin Milonas und ich möchte einen Termin.\n"
            "Anna: Ich habe info@condata.io verstanden. Ist das richtig?\n"
            "Anrufer: Ja, das ist korrekt."
        )
        first = await client.execute("confirm_calendar_detail", {
            "field": "email", "value": "info@condata.io",
        }, transcript)
        second = await client.execute("confirm_calendar_detail", {
            "field": "email", "value": "info@condata.io",
        }, transcript)
        assert first["success"] is True
        assert second == {
            "success": True, "confirmed_field": "email", "already_confirmed": True,
        }

        enriched = client.enrich_contact_handoff({
            "first_name": "", "last_name": "", "email": "", "phone": "",
            "preferred_channel": "",
        }, transcript + "\nAnrufer: Bitte per E-Mail.")
        assert enriched["first_name"] == "Konstantin"
        assert enriched["last_name"] == "Milonas"
        assert enriched["email"] == "info@condata.io"
        assert enriched["email_confirmed"] is True
        assert enriched["preferred_channel"] == "email"

    asyncio.run(scenario())


def test_afternoon_preference_is_forwarded_to_slot_search(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")
    requests = []

    async def request(path, payload):
        requests.append(payload)
        return {"success": True, "slots": []}

    client._request = request

    async def scenario():
        await client.execute("find_free_slots", {
            "start": "2030-01-07T09:00:00+01:00",
            "end": "2030-01-12T18:00:00+01:00",
            "duration_minutes": 30,
        }, "Anrufer: Ich suche einen Termin am Nachmittag.")

    asyncio.run(scenario())
    assert requests[0]["arguments"]["time_of_day"] == "afternoon"


def test_latest_caller_time_preference_overrides_stale_tool_argument(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")
    requests = []

    async def request(path, payload):
        requests.append(payload)
        return {"success": True, "slots": []}

    client._request = request

    async def scenario():
        await client.execute("find_free_slots", {
            "start": "2030-01-07T09:00:00+01:00",
            "end": "2030-01-12T20:00:00+01:00",
            "duration_minutes": 30,
            "time_of_day": "morning",
        }, "Anrufer: Nicht vormittags, lieber nachmittags.")
        await client.execute("find_free_slots", {
            "start": "2030-01-07T09:00:00+01:00",
            "end": "2030-01-12T20:00:00+01:00",
            "duration_minutes": 30,
            "time_of_day": "afternoon",
        }, "Anrufer: Nachmittags geht nicht, lieber abends.")
        await client.execute("find_free_slots", {
            "start": "2030-01-07T09:00:00+01:00",
            "end": "2030-01-12T20:00:00+01:00",
            "duration_minutes": 30,
            "time_of_day": "evening",
        }, "Anrufer: Die Tageszeit ist mir jetzt egal.")

    asyncio.run(scenario())
    assert [request["arguments"]["time_of_day"] for request in requests] == [
        "afternoon", "evening", "",
    ]


def test_relative_last_slot_is_bound_to_last_recent_option(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")

    async def request(path, payload):
        if payload["action"] == "find_free_slots":
            return {"success": True, "slots": [
                {"start": "2026-10-05T09:00:00+02:00", "end": "2026-10-05T09:30:00+02:00"},
                {"start": "2026-10-05T09:30:00+02:00", "end": "2026-10-05T10:00:00+02:00"},
                {"start": "2026-10-05T10:00:00+02:00", "end": "2026-10-05T10:30:00+02:00"},
            ]}
        return {"success": True, "confirmation_token": "opaque"}

    client._request = request

    async def scenario():
        await client.execute("find_free_slots", {
            "start": "2026-10-05T08:00:00+02:00",
            "end": "2026-10-05T12:00:00+02:00",
            "duration_minutes": 30,
        }, "")
        result = await client.execute(
            "resolve_calendar_slot_reference", {"reference": "last"},
            "Anrufer: Dann der letzte Termin.",
        )
        assert result["slot"]["start"] == "2026-10-05T10:00:00+02:00"

        transcript = "Anna: Ist Ihre Telefonnummer 0176 23785746?\nAnrufer: Ja."
        await client.execute("confirm_calendar_detail", {
            "field": "phone", "value": "0176 23785746",
        }, transcript)
        transcript += "\nAnna: Darf ich die Daten für den Termin verwenden?\nAnrufer: Ja."
        await client.execute("confirm_calendar_detail", {
            "field": "booking_consent", "value": "",
        }, transcript)
        transcript = "Anrufer: Dann der letzte Termin.\n" + transcript
        wrong = await client.execute("prepare_appointment", {
            "action": "create", "details": {
                "name": "Konstantin Milonas", "phone": "0176 23785746",
                "start": "2026-10-05T09:30:00+02:00", "end": "2026-10-05T10:00:00+02:00",
            },
        }, transcript)
        assert wrong["error"] == "selected_slot_mismatch"
        assert wrong["slot"]["start"] == "2026-10-05T10:00:00+02:00"

    asyncio.run(scenario())


def test_relative_reference_uses_exact_spoken_subset_and_middle(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    client = PhoneCalendarTools("mein-kuechenexperte", "anna-phone-assistant", "call")

    async def request(path, payload):
        return {"success": True, "slots": [
            {"start": "2026-10-05T09:00:00+02:00", "end": "2026-10-05T09:30:00+02:00"},
            {"start": "2026-10-05T09:30:00+02:00", "end": "2026-10-05T10:00:00+02:00"},
            {"start": "2026-10-05T10:00:00+02:00", "end": "2026-10-05T10:30:00+02:00"},
        ]}

    client._request = request

    async def scenario():
        await client.execute("find_free_slots", {
            "start": "2026-10-05T08:00:00+02:00",
            "end": "2026-10-05T12:00:00+02:00",
            "duration_minutes": 30,
        }, "Anrufer: Montagvormittag.")
        remembered = await client.execute("remember_offered_calendar_slots", {
            "starts": [
                "2026-10-05T10:00:00+02:00",
                "2026-10-05T09:30:00+02:00",
                "2026-10-05T09:00:00+02:00",
            ],
        }, "")
        assert remembered == {"success": True, "offered_count": 3}
        middle = await client.execute(
            "resolve_calendar_slot_reference", {"reference": "middle"}, "",
        )
        last = await client.execute(
            "resolve_calendar_slot_reference", {"reference": "last"}, "",
        )
        assert middle["slot"]["start"] == "2026-10-05T09:30:00+02:00"
        assert last["slot"]["start"] == "2026-10-05T09:00:00+02:00"

        await client.execute("remember_offered_calendar_slots", {
            "starts": [
                "2026-10-05T09:00:00+02:00",
                "2026-10-05T10:00:00+02:00",
            ],
        }, "")
        ambiguous = await client.execute(
            "resolve_calendar_slot_reference", {"reference": "middle"}, "",
        )
        assert ambiguous["error"] == "slot_reference_ambiguous"

    asyncio.run(scenario())


def test_internal_auth_and_disabled_mode():
    config = CalendarConfig(api_token="operator", mode="disabled")
    with TestClient(create_app(config)) as client:
        assert client.post("/internal/execute", json={}).status_code == 401
        response = client.post("/internal/execute", headers={"Authorization": "Bearer operator"}, json={})
        assert response.json()["error"] == "calendar_disabled"
        assert client.get("/health").json()["mode"] == "disabled"
    with TestClient(create_app(replace(config, mode="disabled"))) as client:
        response = client.get("/auth/microsoft/start")
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "Secure" in response.headers["set-cookie"]
        assert client.post("/auth/microsoft/start", data={"token": "operator"}).status_code == 401


def test_production_startup_requires_complete_configuration():
    with pytest.raises(CalendarError):
        with TestClient(create_app(CalendarConfig(api_token="operator", mode="production"))):
            pass


def test_production_http_requires_policy_and_authentication():
    class Service:
        def __init__(self):
            self.calls = 0

        async def execute(self, action, arguments, session):
            self.calls += 1
            return {"success": True, "action": action}

    service = Service()
    config = CalendarConfig(api_token="operator", mode="production")
    body = {"action": "get_booking_policy", "arguments": {}, "session_id": "call"}
    with TestClient(create_app(config, service=service)) as client:
        assert client.post("/internal/execute", json=body).status_code == 401
        result = client.post("/internal/execute", json=body,
                             headers={"Authorization": "Bearer operator"}).json()
        assert result["error"] == "calendar_policy_required"
    assert service.calls == 0
    config = replace(config, weekly_hours='{"0": [["09:00", "19:00"]]}',
                     duration_minutes="30", buffer_minutes="15")
    with TestClient(create_app(config, service=service)) as client:
        result = client.post("/internal/execute", json=body,
                             headers={"Authorization": "Bearer operator"}).json()
        assert result["success"] is True
    assert service.calls == 1


def test_calendar_mail_fixed_recipient_and_snapshot(monkeypatch):
    captured = []

    def deliver(message, recipient):
        captured.append((message, recipient))
        return True

    monkeypatch.setattr("src.telephony.mail._deliver", deliver)
    operation = {"action": "cancel", "calendar_changed": True, "transaction_id": "a" * 64,
                 "details": {"name": "ANNA TEST", "email": "test@example.invalid", "start": "2030-01-01"},
                 "original": {"start": {"dateTime": "2030-01-01"}}, "created_at": "2026-09-27"}
    assert asyncio.run(send_calendar_notification(operation))
    message, recipient = captured[0]
    assert recipient == "kontakt@mein-kuechenexperte.de"
    assert "2030-01-01" in message.get_content()
    assert "ANNA TEST" in message.get_content()
