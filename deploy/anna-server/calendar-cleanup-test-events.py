"""Remove only incomplete synthetic ANNA TEST events after a failed test run."""

import asyncio
from datetime import datetime, timedelta, timezone

from src.agents.anna.calendar.config import CalendarConfig
from src.agents.anna.calendar.graph import GraphCalendar
from src.agents.anna.calendar.oauth import OAuthManager


async def main():
    config = CalendarConfig.from_env()
    if config.mode != "test":
        raise SystemExit("Refused: explicit test mode required.")
    config.validate()
    graph = GraphCalendar(OAuthManager(config))
    now = datetime.now(timezone.utc)
    events = await graph.list_events((now - timedelta(days=1)).isoformat(), (now + timedelta(days=31)).isoformat())
    deleted = 0
    for event in events:
        if event.get("subject") != "ANNA TEST Beratung":
            continue
        current = await graph.get_event(event["id"])
        body = str((current.get("body") or {}).get("content", "")) if current else ""
        if "Synthetic integration test; no real customer appointment." not in body:
            continue
        etag = current.get("@odata.etag")
        if not etag:
            raise SystemExit("Test event has no ETag; manual review required.")
        await graph.delete_event(current["id"], etag)
        deleted += 1
    print(f"Deleted synthetic ANNA TEST events: {deleted}")


if __name__ == "__main__":
    asyncio.run(main())
