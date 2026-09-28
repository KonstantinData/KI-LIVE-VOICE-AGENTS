import asyncio
import json
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from src.agents.anna.calendar.service import CalendarService


class Graph:
    def __init__(self):
        self.events = {}
        self.writes = 0
        self.fail = False

    async def list_events(self, start, end):
        return list(self.events.values())

    async def find_transaction(self, tx):
        return next((v for v in self.events.values() if v.get("transactionId") == tx), None)

    async def create_event(self, payload):
        self.writes += 1
        if self.fail:
            raise TimeoutError
        event = dict(payload, id=str(self.writes), **{"@odata.etag": "v1"})
        self.events[event["id"]] = event
        return event

    async def get_event(self, event_id):
        return self.events.get(event_id)

    async def update_event(self, event_id, payload, etag):
        self.writes += 1
        self.events[event_id].update(payload)

    async def delete_event(self, event_id, etag):
        self.writes += 1
        del self.events[event_id]


@pytest.fixture
def setup(tmp_path):
    graph = Graph()
    async def notify(operation):
        return False
    config = SimpleNamespace(data_dir=tmp_path, encryption_key=Fernet.generate_key(), timezone="Europe/Berlin", mode="test")
    return CalendarService(config, graph, notify), graph


def details(**kwargs):
    return dict(name="Test Customer", email="test@example.com", consent=True, contact_confirmed=True, start="2030-01-07T10:00:00+01:00", end="2030-01-07T11:00:00+01:00", **kwargs)


async def prepare(service, action="create", data=None, session="call"):
    return await service.execute("prepare_appointment", {"action": action, "details": data or details()}, session)


async def commit(service, token, action="create", session="call"):
    return await service.execute(action + "_appointment", {"confirmation_token": token, "confirmed": True, "confirmation_action": action}, session)


@pytest.mark.asyncio
async def test_outbox_retries_without_calendar_write(setup):
    service, graph = setup
    proposal = await prepare(service)
    result = await commit(service, proposal["confirmation_token"])
    assert result == {"success": False, "calendar_changed": True, "notification_accepted": False, "status": "notification_failed"}
    assert (await commit(service, proposal["confirmation_token"])) == result
    async def accepted(operation):
        return True
    service.notifier = accepted
    assert (await service.retry_notifications())["notifications_accepted"] == 1
    assert graph.writes == 1
    assert b"test@example.com" not in service.store.path.read_bytes()


@pytest.mark.asyncio
async def test_uncertain_write_never_blindly_repeated(setup):
    service, graph = setup
    proposal = await prepare(service)
    graph.fail = True
    assert (await commit(service, proposal["confirmation_token"]))["error"] == "write_uncertain"
    assert (await commit(service, proposal["confirmation_token"]))["error"] == "write_uncertain"
    assert graph.writes == 1


@pytest.mark.asyncio
async def test_concurrent_bookings_recheck_availability(setup):
    service, graph = setup
    a = await prepare(service)
    other = details()
    other["email"] = "other@example.com"
    b = await prepare(service, data=other)
    results = await asyncio.gather(commit(service, a["confirmation_token"]), commit(service, b["confirmation_token"]))
    assert sum(r.get("calendar_changed", False) for r in results) == 1
    assert graph.writes == 1


@pytest.mark.asyncio
async def test_session_binding_closure_and_missing_contact(setup):
    service, graph = setup
    proposal = await prepare(service)
    assert (await commit(service, proposal["confirmation_token"], session="other"))["error"] == "confirmation_invalid_or_expired"
    service.close_session("call")
    assert (await commit(service, proposal["confirmation_token"]))["error"] == "session_closed"
    data = details()
    data.pop("email")
    assert (await prepare(service, data=data, session="new"))["error"] == "contact_and_consent_required"
    data["phone"] = "+49 123 4567890"
    assert (await prepare(service, data=data, session="new"))["success"]
    assert graph.writes == 0


@pytest.mark.asyncio
async def test_identity_history_and_cancellation(setup):
    service, graph = setup
    token = (await prepare(service))["confirmation_token"]
    await commit(service, token)
    query = dict(name="Test Customer", email="test@example.com", consent=True, contact_confirmed=True, original_start=details()["start"])
    candidate = (await service.execute("find_customer_appointment", query, "call"))["candidates"][0]
    data = details(candidate_id=candidate["candidate_id"], reason="<unsafe>")
    data.update(start="2030-01-08T10:00:00+01:00", end="2030-01-08T11:00:00+01:00")
    graph.events["1"]["body"] = {"contentType": "HTML", "content": "<b>Original</b>"}
    # Candidate was captured before body update; refresh the candidate.
    candidate = (await service.execute("find_customer_appointment", query, "call"))["candidates"][0]
    data["candidate_id"] = candidate["candidate_id"]
    proposal = await prepare(service, "reschedule", data)
    await commit(service, proposal["confirmation_token"], "reschedule")
    assert "<b>Original</b>" in graph.events["1"]["body"]["content"]
    assert "&lt;unsafe&gt;" in graph.events["1"]["body"]["content"]
    query["original_start"] = data["start"]
    candidate = (await service.execute("find_customer_appointment", query, "call"))["candidates"][0]
    data["candidate_id"] = candidate["candidate_id"]
    proposal = await prepare(service, "cancel", data)
    assert (await commit(service, proposal["confirmation_token"], "cancel"))["calendar_changed"]
    assert not graph.events


@pytest.mark.asyncio
async def test_dst_and_foreign_identity_are_fail_closed(setup):
    service, graph = setup
    result = await service.execute("check_availability", {"start": "2030-03-31T02:30:00+01:00", "end": "2030-03-31T04:00:00+02:00"}, "call")
    assert result["error"] == "invalid_datetime"
    query = dict(name="Test Customer", email="test@example.com", consent=True, contact_confirmed=True, original_start=details()["start"])
    graph.events["foreign"] = {"id": "foreign", "start": details()["start"], "end": details()["end"], "subject": "Private event"}
    assert (await service.execute("find_customer_appointment", query, "call"))["candidates"] == []


@pytest.mark.asyncio
async def test_holiday_check_search_and_prepare_rejected_even_with_open_hours(setup):
    service, graph = setup
    service.config.weekly_hours = json.dumps({str(day): [["09:00", "17:00"]] for day in range(7)})
    holiday = {"start": "2030-10-03T10:00:00+02:00", "end": "2030-10-03T11:00:00+02:00"}
    assert await service.execute("check_availability", holiday, "call") == {"success": False, "error": "public_holiday"}
    assert await service.execute("find_free_slots", holiday, "call") == {"success": True, "slots": []}
    assert (await prepare(service, data=details() | holiday))["error"] == "public_holiday"
    ordinary = {"start": "2030-10-04T10:00:00+02:00", "end": "2030-10-04T11:00:00+02:00"}
    assert (await service.execute("check_availability", ordinary, "call"))["available"]
    assert graph.writes == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["create", "reschedule"])
async def test_final_write_rechecks_holiday_for_preexisting_confirmation(setup, operation):
    service, graph = setup
    data = details()
    if operation == "reschedule":
        await commit(service, (await prepare(service))["confirmation_token"])
        query = data | {"original_start": data["start"]}
        candidate = (await service.execute("find_customer_appointment", query, "call"))["candidates"][0]
        data = data | {"candidate_id": candidate["candidate_id"], "start": "2030-01-08T10:00:00+01:00", "end": "2030-01-08T11:00:00+01:00"}
        assert (await prepare(service, operation, data | {"start": "2030-10-03T10:00:00+02:00", "end": "2030-10-03T11:00:00+02:00"}))["error"] == "public_holiday"
    proposal = await prepare(service, operation, data)
    token = proposal["confirmation_token"]
    record = await service.store.get("confirmation", token)
    # Model a confirmation prepared by the previous deployment before enforcement.
    record["details"].update(start="2030-10-03T10:00:00+02:00", end="2030-10-03T11:00:00+02:00")
    await service.store.put("confirmation", token, record)
    writes_before = graph.writes
    assert (await commit(service, token, operation))["error"] == "public_holiday"
    assert graph.writes == writes_before


@pytest.mark.asyncio
async def test_existing_holiday_event_can_be_cancelled(setup):
    service, graph = setup
    await commit(service, (await prepare(service))["confirmation_token"])
    graph.events["1"].update(start="2030-10-03T10:00:00+02:00", end="2030-10-03T11:00:00+02:00")
    query = details() | {"original_start": graph.events["1"]["start"]}
    candidate = (await service.execute("find_customer_appointment", query, "call"))["candidates"][0]
    proposal = await prepare(service, "cancel", details(candidate_id=candidate["candidate_id"]))
    assert (await commit(service, proposal["confirmation_token"], "cancel"))["calendar_changed"]
    assert not graph.events
