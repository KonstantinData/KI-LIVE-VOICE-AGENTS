"""Scheduling policy is enforced by the service, independently of the model."""

from dataclasses import replace
from datetime import datetime, timezone
import json

from cryptography.fernet import Fernet
import pytest

from src.agents.anna.calendar.config import CalendarConfig, CalendarError
from src.agents.anna.calendar.service import CalendarService


def policy(**changes):
    return replace(CalendarConfig(
        mode="production", weekly_hours=json.dumps({str(day): [["09:30", "17:30"]] for day in range(5)}),
        duration_minutes="60", buffer_minutes="15",
    ), **changes)


@pytest.mark.parametrize("field,value", [
    ("weekly_hours", ""), ("weekly_hours", "{}"), ("weekly_hours", "[]"),
    ("duration_minutes", ""), ("buffer_minutes", ""),
    ("weekly_hours", '{"7":[["09:00","17:00"]]}'),
    ("weekly_hours", '{"0":[["9:00","17:00"]]}'),
    ("weekly_hours", '{"0":[["09:00","24:00"]]}'),
    ("weekly_hours", '{"0":[["18:00","17:00"]]}'),
    ("weekly_hours", '{"0":[["09:00","12:00"],["11:00","17:00"]]}'),
    ("duration_minutes", "14"),
    ("duration_minutes", "241"), ("buffer_minutes", "-1"),
    ("buffer_minutes", "121"), ("buffer_minutes", "nan"),
])
def test_production_policy_rejects_missing_or_invalid(field, value):
    with pytest.raises(CalendarError):
        policy(**{field: value}).validate_policy()


def test_test_mode_preserves_defaults():
    assert CalendarConfig(mode="test").scheduling_policy() == (
        {day: ((540, 1020),) for day in range(5)}, None, 0,
    )


class Graph:
    def __init__(self):
        self.events = []
        self.ranges = []
        self.writes = 0

    async def list_events(self, start, end):
        self.ranges.append((start, end))
        return self.events

    async def find_transaction(self, transaction_id):
        return None

    async def get_event(self, event_id):
        return next(event for event in self.events if event["id"] == event_id)

    async def create_event(self, payload):
        self.writes += 1
        return dict(payload, id="owned")


@pytest.fixture
def service(tmp_path):
    async def notify(state):
        return True
    return CalendarService(policy(data_dir=tmp_path, encryption_key=Fernet.generate_key()), Graph(), notify)


def details(start="2030-01-07T10:00:00+01:00", end="2030-01-07T11:00:00+01:00", **extra):
    return dict(name="Test Customer", email="test@example.invalid", consent=True,
                contact_confirmed=True, start=start, end=end, **extra)


async def prepare(service, data=None):
    return await service.execute("prepare_appointment", {"action": "create", "details": data or details()}, "call")


async def commit(service, proposal):
    return await service.execute("create_appointment", {
        "confirmation_token": proposal["confirmation_token"],
        "confirmed": True, "confirmation_action": "create",
    }, "call")


@pytest.mark.asyncio
async def test_clock_constraint_filters_before_slot_limit(service):
    service.config = replace(service.config, weekly_hours=json.dumps({str(day): [["09:00", "19:00"]] for day in range(5)}), duration_minutes="30")
    result = await service.execute("find_free_slots", {
        "start": "2030-01-07T09:00:00+01:00", "end": "2030-01-12T19:00:00+01:00",
        "duration_minutes": 30, "preferred_clock": "17:45", "time_of_day": "",
    }, "dialect")
    assert len(result["slots"]) == 3
    assert all(datetime.fromisoformat(slot["start"]).strftime("%H:%M") == "17:45" for slot in result["slots"])


@pytest.mark.asyncio
async def test_excluded_afternoon_is_date_bound_and_precedes_slot_limit(service):
    result = await service.execute("find_free_slots", {
        "start": "2030-01-07T12:00:00+01:00", "end": "2030-01-09T18:00:00+01:00",
        "duration_minutes": 60, "time_of_day": "afternoon",
        "excluded_intervals": [{"start": "2030-01-07T12:00:00+01:00", "end": "2030-01-07T18:00:00+01:00"}],
    }, "dialect")
    assert len(result["slots"]) == 3
    assert all(slot["start"].startswith("2030-01-08") for slot in result["slots"])


@pytest.mark.asyncio
@pytest.mark.parametrize("start,end,error", [
    ("2030-01-07T09:00:00+01:00", "2030-01-07T10:00:00+01:00", "outside_business_hours"),
    ("2030-01-07T17:00:00+01:00", "2030-01-07T18:00:00+01:00", "outside_business_hours"),
    ("2030-01-12T10:00:00+01:00", "2030-01-12T11:00:00+01:00", "outside_business_hours"),
    ("2030-01-07T10:00:00+01:00", "2030-01-07T10:30:00+01:00", "invalid_duration"),
    ("2020-01-06T10:00:00+01:00", "2020-01-06T11:00:00+01:00", "past_appointment"),
])
async def test_prepare_and_availability_enforce_policy(service, start, end, error):
    assert (await prepare(service, details(start, end)))["error"] == error
    assert (await service.execute("check_availability", {"start": start, "end": end}, "call"))["error"] == error
    assert service.graph.writes == 0


@pytest.mark.asyncio
async def test_final_write_revalidates_policy(service):
    proposal = await prepare(service)
    service.config = replace(service.config, weekly_hours='{"0":[["11:00","17:00"]]}')
    assert (await commit(service, proposal))["error"] == "outside_business_hours"
    assert service.graph.writes == 0


@pytest.mark.asyncio
async def test_final_write_rechecks_buffer_and_cannot_exclude_foreign_event(service):
    proposal = await prepare(service)
    service.graph.events = [{"id": "foreign", "start": "2030-01-07T11:10:00+01:00", "end": "2030-01-07T12:00:00+01:00"}]
    assert (await commit(service, proposal))["error"] == "slot_unavailable"
    assert (await prepare(service, details(event_id="foreign")))["error"] == "slot_unavailable"
    assert service.graph.ranges[-1] == ("2030-01-07T09:45:00+01:00", "2030-01-07T11:15:00+01:00")
    assert service.graph.writes == 0


@pytest.mark.asyncio
async def test_reschedule_rechecks_policy_at_prepare_and_commit(service):
    event = {"id": "owned", "@odata.etag": "v1", "start": "2030-01-07T14:00:00+01:00", "end": "2030-01-07T15:00:00+01:00"}
    service.graph.events = [event]
    await service.store.put("candidate", "candidate", {
        "session": "call", "expires": datetime.now(timezone.utc).timestamp() + 300,
        "event": event, "contact": details(),
    })
    invalid = details("2030-01-07T17:00:00+01:00", "2030-01-07T18:00:00+01:00", candidate_id="candidate")
    assert (await service.execute("prepare_appointment", {"action": "reschedule", "details": invalid}, "call"))["error"] == "outside_business_hours"
    proposal = await service.execute("prepare_appointment", {"action": "reschedule", "details": details(candidate_id="candidate")}, "call")
    service.config = replace(service.config, weekly_hours='{"0":[["11:00","17:00"]]}')
    result = await service.execute("reschedule_appointment", {
        "confirmation_token": proposal["confirmation_token"], "confirmed": True,
        "confirmation_action": "reschedule",
    }, "call")
    assert result["error"] == "outside_business_hours"
    assert service.graph.writes == 0


@pytest.mark.asyncio
async def test_buffer_before_candidate_blocks_booking(service):
    service.graph.events = [{"id": "foreign", "start": "2030-01-07T09:00:00+01:00", "end": "2030-01-07T09:50:00+01:00"}]
    assert (await prepare(service))["error"] == "slot_unavailable"


@pytest.mark.asyncio
async def test_exact_buffer_gap_allows_booking(service):
    service.graph.events = [{"id": "foreign", "start": "2030-01-07T11:15:00+01:00", "end": "2030-01-07T12:00:00+01:00"}]
    proposal = await prepare(service)
    assert (await commit(service, proposal))["calendar_changed"]
    assert service.graph.writes == 1


@pytest.mark.asyncio
async def test_slot_search_uses_hours_duration_and_buffer(service):
    service.graph.events = [{"id": "foreign", "start": "2030-01-07T09:00:00+01:00", "end": "2030-01-07T10:00:00+01:00"}]
    args = {"start": "2030-01-07T08:00:00+01:00", "end": "2030-01-07T18:00:00+01:00", "duration_minutes": 60}
    result = await service.execute("find_free_slots", args, "call")
    assert [slot["start"] for slot in result["slots"]] == [
        "2030-01-07T10:30:00+01:00",
        "2030-01-07T11:00:00+01:00",
        "2030-01-07T11:30:00+01:00",
    ]
    args["duration_minutes"] = 30
    assert (await service.execute("find_free_slots", args, "call"))["error"] == "invalid_duration"


@pytest.mark.asyncio
async def test_slot_search_returns_at_most_three_memorable_starts(service):
    args = {"start": "2030-01-07T09:37:00+01:00", "end": "2030-01-07T17:30:00+01:00", "duration_minutes": 60}
    result = await service.execute("find_free_slots", args, "call")
    assert [slot["start"] for slot in result["slots"]] == [
        "2030-01-07T10:00:00+01:00",
        "2030-01-07T10:30:00+01:00",
        "2030-01-07T11:00:00+01:00",
    ]


@pytest.mark.asyncio
async def test_direct_availability_keeps_customer_requested_quarter_hour(service):
    result = await service.execute("check_availability", {
        "start": "2030-01-07T10:15:00+01:00",
        "end": "2030-01-07T11:15:00+01:00",
    }, "call")
    assert result["success"] is True
    assert result["available"] is True
    assert result["start"] == "2030-01-07T10:15:00+01:00"


@pytest.mark.asyncio
async def test_slot_search_uses_quarter_hour_fallback_only_when_needed(service):
    service.config = replace(
        service.config,
        weekly_hours='{"0":[["09:15","10:30"]]}',
        duration_minutes="30",
    )
    args = {"start": "2030-01-07T09:00:00+01:00", "end": "2030-01-07T10:30:00+01:00", "duration_minutes": 30}
    result = await service.execute("find_free_slots", args, "call")
    assert [slot["start"] for slot in result["slots"]] == [
        "2030-01-07T09:15:00+01:00",
        "2030-01-07T09:30:00+01:00",
        "2030-01-07T10:00:00+01:00",
    ]
    assert "2030-01-07T09:45:00+01:00" not in {slot["start"] for slot in result["slots"]}


@pytest.mark.asyncio
async def test_slot_search_keeps_buffer_and_split_windows(service):
    service.config = replace(
        service.config,
        weekly_hours=json.dumps(APPROVED_HOURS),
        duration_minutes="30",
    )
    service.graph.events = [{
        "id": "foreign",
        "start": "2030-01-08T08:45:00+01:00",
        "end": "2030-01-08T12:45:00+01:00",
    }]
    args = {"start": "2030-01-08T08:00:00+01:00", "end": "2030-01-08T20:00:00+01:00", "duration_minutes": 30}
    result = await service.execute("find_free_slots", args, "call")
    assert result["slots"] == [{
        "start": "2030-01-08T18:30:00+01:00",
        "end": "2030-01-08T19:00:00+01:00",
    }]


@pytest.mark.asyncio
async def test_service_itself_rejects_missing_production_policy(service):
    service.config = replace(service.config, buffer_minutes="")
    assert (await prepare(service))["error"] == "calendar_policy_required"
    assert (await service.execute("get_booking_policy", {}, "call"))["error"] == "calendar_policy_required"
    assert not service.graph.ranges


APPROVED_HOURS = {
    "0": [["09:00", "19:00"]],
    **{str(day): [["09:00", "12:30"], ["18:30", "19:00"]] for day in range(1, 5)},
    "5": [["15:00", "17:00"]],
}


@pytest.mark.asyncio
@pytest.mark.parametrize(("start", "end", "expected_starts"), [
    (
        "2030-01-07T12:00:00+01:00",
        "2030-01-07T18:00:00+01:00",
        [
            "2030-01-07T12:30:00+01:00",
            "2030-01-07T13:00:00+01:00",
            "2030-01-07T13:30:00+01:00",
        ],
    ),
    (
        "2030-01-12T12:00:00+01:00",
        "2030-01-12T18:00:00+01:00",
        [
            "2030-01-12T15:00:00+01:00",
            "2030-01-12T15:30:00+01:00",
            "2030-01-12T16:00:00+01:00",
        ],
    ),
    (
        "2030-01-08T12:00:00+01:00",
        "2030-01-08T20:00:00+01:00",
        [],
    ),
])
async def test_afternoon_search_honors_each_weekdays_actual_windows(
    service, start, end, expected_starts,
):
    service.config = replace(
        service.config,
        weekly_hours=json.dumps(APPROVED_HOURS),
        duration_minutes="30",
    )
    result = await service.execute("find_free_slots", {
        "start": start,
        "end": end,
        "duration_minutes": 30,
        "time_of_day": "afternoon",
    }, "call")

    assert result["success"] is True
    assert [slot["start"] for slot in result["slots"]] == expected_starts


@pytest.mark.asyncio
async def test_slot_search_rejects_unknown_time_of_day(service):
    result = await service.execute("find_free_slots", {
        "start": "2030-01-07T09:00:00+01:00",
        "end": "2030-01-07T19:00:00+01:00",
        "duration_minutes": 60,
        "time_of_day": "late_afternoon",
    }, "call")

    assert result["success"] is False
    assert result["error"] == "invalid_time_of_day"


@pytest.mark.asyncio
@pytest.mark.parametrize("start,end,allowed", [
    ("2030-01-07T18:30:00+01:00", "2030-01-07T19:00:00+01:00", True),
    ("2030-01-07T18:45:00+01:00", "2030-01-07T19:15:00+01:00", False),
    ("2030-01-08T12:00:00+01:00", "2030-01-08T12:30:00+01:00", True),
    ("2030-01-08T12:15:00+01:00", "2030-01-08T12:45:00+01:00", False),
    ("2030-01-08T15:00:00+01:00", "2030-01-08T15:30:00+01:00", False),
    ("2030-01-08T18:30:00+01:00", "2030-01-08T19:00:00+01:00", True),
    ("2030-01-12T16:30:00+01:00", "2030-01-12T17:00:00+01:00", True),
    ("2030-01-13T15:00:00+01:00", "2030-01-13T15:30:00+01:00", False),
])
async def test_approved_split_hours_and_boundary_slots(service, start, end, allowed):
    service.config = replace(service.config, weekly_hours=json.dumps(APPROVED_HOURS), duration_minutes="30")
    result = await prepare(service, details(start, end))
    assert result["success"] is allowed
    if not allowed:
        assert result["error"] == "outside_business_hours"


@pytest.mark.asyncio
async def test_booking_policy_discloses_only_scheduling_rules(service):
    service.config = replace(service.config, weekly_hours=json.dumps(APPROVED_HOURS), duration_minutes="30")
    result = await service.execute("get_booking_policy", {}, "call")
    assert result["weekly_hours"] == APPROVED_HOURS
    assert result["duration_minutes"] == 30
    assert result["buffer_minutes"] == 15
    assert result["timezone"] == "Europe/Berlin"
    assert result["appointment_type"] == "Kostenloses Erstgespräch"
    assert result["current_time"]
    assert "email" not in result
    service.config = replace(service.config, mode="disabled")
    assert (await service.execute("get_booking_policy", {}, "call"))["error"] == "calendar_disabled"
