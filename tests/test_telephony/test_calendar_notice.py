"""Internal booking notice is measured in elapsed UTC hours at every stage."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest
from cryptography.fernet import Fernet

from src.agents.anna.calendar.config import CalendarConfig, CalendarError
from src.agents.anna.calendar.service import CalendarService
from tests.test_telephony.test_calendar_policy import Graph, policy, details, prepare, commit


@pytest.fixture
def service(tmp_path):
    async def notify(state):
        return True
    return CalendarService(policy(data_dir=tmp_path, encryption_key=Fernet.generate_key()), Graph(), notify)


@pytest.fixture
def clock(monkeypatch):
    class Clock(datetime):
        current = datetime(2030, 1, 6, 9, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls.current.astimezone(tz)

    monkeypatch.setattr("src.agents.anna.calendar.service.datetime", Clock)
    return Clock


@pytest.mark.parametrize("value", ["", "0", "23", "24.5", "-1", "nan", "745"])
def test_notice_cannot_disable_minimum(value):
    with pytest.raises(CalendarError):
        CalendarConfig(minimum_notice_hours=value).validate_policy()


@pytest.mark.asyncio
async def test_exact_threshold_and_one_microsecond_before(service, clock):
    args = details()
    assert (await service.execute("check_availability", args, "call"))["available"]
    clock.current += timedelta(microseconds=1)
    assert (await service.execute("check_availability", args, "call"))["error"] == "slot_unavailable"
    assert (await prepare(service))["error"] == "slot_unavailable"
    assert service.graph.writes == 0


@pytest.mark.asyncio
async def test_final_write_rechecks_elapsed_time(service, clock):
    proposal = await prepare(service)
    clock.current += timedelta(seconds=1)
    assert (await commit(service, proposal))["error"] == "slot_unavailable"
    assert service.graph.writes == 0
    assert await service.store.all("operation") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["reschedule", "cancel"])
async def test_reschedule_enforces_notice_but_cancellation_remains_allowed(service, clock, operation):
    event = {"id": "owned", "@odata.etag": "v1", "start": "2030-01-06T12:00:00+01:00", "end": "2030-01-06T13:00:00+01:00"}
    service.graph.events.append(event)
    await service.store.put("candidate", "candidate", {
        "session": "call", "expires": clock.current.timestamp() + 300,
        "event": event, "contact": details(),
    })
    proposal = await service.execute("prepare_appointment", {
        "action": operation, "details": details(candidate_id="candidate"),
    }, "call")
    assert proposal["success"]
    clock.current += timedelta(seconds=1)

    async def delete(event_id, etag):
        service.graph.writes += 1

    service.graph.delete_event = delete
    result = await service.execute(operation + "_appointment", {
        "confirmation_token": proposal["confirmation_token"],
        "confirmed": True, "confirmation_action": operation,
    }, "call")
    if operation == "cancel":
        assert result["success"] and service.graph.writes == 1
    else:
        assert result["error"] == "slot_unavailable" and service.graph.writes == 0


@pytest.mark.asyncio
async def test_search_clamps_broad_range_and_returns_empty_short_range(service, clock):
    result = await service.execute("find_free_slots", {
        "start": "2030-01-06T00:00:00+01:00", "end": "2030-01-07T12:00:00+01:00",
    }, "call")
    assert result["success"]
    assert result["slots"][0]["start"] == "2030-01-07T10:00:00+01:00"
    result = await service.execute("find_free_slots", {
        "start": "2030-01-06T00:00:00+01:00", "end": "2030-01-07T09:59:00+01:00",
    }, "call")
    assert result == {"success": True, "slots": []}


@pytest.mark.asyncio
@pytest.mark.parametrize("now,start", [
    ("2030-03-30T10:00:00+01:00", "2030-03-31T11:00:00+02:00"),
    ("2030-10-26T10:00:00+02:00", "2030-10-27T09:00:00+01:00"),
])
async def test_dst_uses_elapsed_hours(service, clock, now, start):
    service.config = replace(service.config, weekly_hours=json.dumps({str(day): [["00:00", "23:59"]] for day in range(7)}))
    clock.current = datetime.fromisoformat(now)
    end = (datetime.fromisoformat(start) + timedelta(hours=1)).isoformat()
    args = details(start, end)
    assert (await service.execute("check_availability", args, "call"))["available"]
    clock.current += timedelta(microseconds=1)
    assert (await prepare(service, args))["error"] == "slot_unavailable"
