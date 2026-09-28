"""Explicit test-mode Graph/SMTP acceptance; creates only ANNA TEST events."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from src.agents.anna.calendar.config import CalendarConfig
from src.agents.anna.calendar.graph import GraphCalendar
from src.agents.anna.calendar.oauth import OAuthManager
from src.agents.anna.calendar.service import CalendarService
from src.telephony.mail import send_calendar_notification


async def main():
    config = CalendarConfig.from_env()
    if config.mode != "test":
        raise SystemExit("Refused: explicit test mode required.")
    config.validate()
    oauth = OAuthManager(config)
    if not oauth.status()["connected"]:
        raise SystemExit("Owner OAuth login required; no changes made.")
    service = CalendarService(config, GraphCalendar(oauth), send_calendar_notification)
    session = "test-" + str(uuid.uuid4())
    contact = {"name": "ANNA TEST Integration", "email": f"anna-test-{uuid.uuid4().hex}@example.invalid",
               "consent": True, "contact_confirmed": True}

    async def checked(action, arguments):
        result = await service.execute(action, arguments, session)
        if not result.get("success"):
            print("STOP", action, result.get("error") or result.get("status"),
                  "calendar_changed=", result.get("calendar_changed", False))
            raise SystemExit("Review the encrypted operation ledger; do not blindly rerun.")
        return result

    async def change(action, details):
        prepared = await checked("prepare_appointment", {"action": action, "details": details})
        await checked(action + "_appointment", {"confirmation_token": prepared["confirmation_token"],
                      "confirmation_action": action, "confirmed": True})
        print(action, "calendar confirmed; owner SMTP accepted")

    try:
        start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        result = await checked("find_free_slots", {"start": start.isoformat(),
                               "end": (start + timedelta(days=10)).isoformat(), "duration_minutes": 30})
        slots = result["slots"]
        original = slots[0] if slots else None
        moved = next((s for s in slots if original and s["start"] >= original["end"]), None)
        if not original or not moved:
            raise SystemExit("Not enough free test slots; no changes made.")
        await change("create", {**contact, **original, "summary": "Synthetic integration test; no real customer appointment."})
        found = await checked("find_customer_appointment", {**contact, "original_start": original["start"]})
        if len(found["candidates"]) != 1:
            raise SystemExit("Test appointment ambiguous; manual review required.")
        await change("reschedule", {**contact, **moved, "candidate_id": found["candidates"][0]["candidate_id"], "reason": "ANNA TEST reschedule"})
        found = await checked("find_customer_appointment", {**contact, "original_start": moved["start"]})
        if len(found["candidates"]) != 1:
            raise SystemExit("Moved test appointment ambiguous; manual review required.")
        candidate = await service.store.get("candidate", found["candidates"][0]["candidate_id"])
        content = candidate["event"].get("body", {}).get("content", "")
        if "ANNA TEST reschedule" not in content or "Synthetic integration test" not in content:
            raise SystemExit("History verification failed; test event retained for review.")
        print("Original body and appended history verified")
        await change("cancel", {**contact, "candidate_id": found["candidates"][0]["candidate_id"], "reason": "ANNA TEST cleanup"})
        print("Test sequence completed. Verify all three messages in owner Inbox/Spam.")
    finally:
        service.close_session(session)


if __name__ == "__main__":
    asyncio.run(main())
