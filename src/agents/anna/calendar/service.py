"""ANNA-only calendar workflow; candidate identifiers never expose Graph IDs.

Only ANNA-owned events are mutable. Production requires explicitly configured
weekly hours, fixed duration and minimum gap. Test defaults are weekdays
09:00–17:00 Europe/Berlin. Writes require call-bound prepared confirmation.
"""

import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import CalendarConfig, CalendarError
from .holidays import public_holidays
from .store import CalendarStore


class CalendarService:
    def __init__(self, config, graph, notifier):
        self.config, self.graph, self.notifier = config, graph, notifier
        self.store = CalendarStore(config.data_dir, config.encryption_key)
        self.zone = ZoneInfo(config.timezone)
        self.closed = set()

    def _policy(self):
        # Support lightweight test configurations without weakening production.
        return CalendarConfig(
            mode=self.config.mode,
            **{field: getattr(self.config, field, "") for field in (
                "weekly_hours", "duration_minutes", "buffer_minutes",
            )},
        ).scheduling_policy()

    def _earliest_start(self):
        hours = CalendarConfig(minimum_notice_hours=getattr(self.config, "minimum_notice_hours", "24")).notice_hours()
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    def _bookable(self, start, end):
        if start.astimezone(timezone.utc) < self._earliest_start():
            raise CalendarError("slot_unavailable")
        hours, duration, _ = self._policy()
        local, finish = start.astimezone(self.zone), end.astimezone(self.zone)
        if local.date() in public_holidays(local.year) or finish.date() in public_holidays(finish.year):
            raise CalendarError("public_holiday")
        elapsed = end - start
        if not timedelta(minutes=15) <= elapsed <= timedelta(hours=4):
            raise CalendarError("invalid_duration")
        if duration is not None and elapsed != timedelta(minutes=duration):
            raise CalendarError("invalid_duration")
        start_minute = local.hour * 60 + local.minute + local.second / 60 + local.microsecond / 60000000
        end_minute = finish.hour * 60 + finish.minute + finish.second / 60 + finish.microsecond / 60000000
        if local.date() != finish.date() or not any(start_minute >= opening and end_minute <= closing for opening, closing in hours.get(local.weekday(), ())):
            raise CalendarError("outside_business_hours")

    def close_session(self, session_id):
        self.closed.add(session_id)
        self.store._put("closed_session", session_id, {"closed": True})

    def _date(self, value):
        try:
            result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if result.tzinfo is None:
                raise ValueError
            # Explicit offsets must describe an actual Berlin wall time.
            local = result.astimezone(self.zone)
            if result.utcoffset() != timedelta(0) and (local.replace(tzinfo=None) != result.replace(tzinfo=None) or local.utcoffset() != result.utcoffset()):
                raise ValueError
            return result
        except (ValueError, TypeError):
            raise CalendarError("invalid_datetime") from None

    def _range(self, data, future=False):
        start, end = self._date(data["start"]), self._date(data["end"])
        if end <= start or end - start > timedelta(days=31):
            raise CalendarError("invalid_range")
        if future and start <= datetime.now(timezone.utc):
            raise CalendarError("past_appointment")
        return start, end

    def _contact(self, data):
        email = str(data.get("email", "")).strip()
        phone = "".join(c for c in str(data.get("phone", "")) if c.isdigit())
        if data.get("consent") is not True or data.get("contact_confirmed") is not True or not str(data.get("name", "")).strip() or not ("@" in email or len(phone) >= 7):
            raise CalendarError("contact_and_consent_required")

    def _identity(self, supplied, stored):
        same_name = supplied.get("name", "").strip().casefold() == stored.get("name", "").strip().casefold()
        same_email = bool(supplied.get("email")) and supplied["email"].strip().casefold() == stored.get("email", "").strip().casefold()
        def phone(value):
            return "".join(c for c in str(value) if c.isdigit())
        same_phone = len(phone(supplied.get("phone", ""))) >= 7 and phone(supplied["phone"]) == phone(stored.get("phone", ""))
        return same_name and (same_email or same_phone)

    def _stamp(self, event, field):
        value = event[field]
        if isinstance(value, str):
            return self._date(value)
        raw = datetime.fromisoformat(value["dateTime"].replace("Z", "+00:00"))
        if raw.tzinfo is None:
            zone = value.get("timeZone", "UTC")
            raw = raw.replace(tzinfo=ZoneInfo("Europe/Berlin" if zone == "W. Europe Standard Time" else zone))
        return raw

    def _busy(self, event):
        return not event.get("isCancelled", False) and event.get("showAs", "busy") != "free"

    async def _available(self, start, end, exclude=None):
        buffer = timedelta(minutes=self._policy()[2])
        window_start, window_end = start - buffer, end + buffer
        events = await self.graph.list_events(window_start.isoformat(), window_end.isoformat())
        return not any(self._busy(e) and e.get("id") != exclude and self._stamp(e, "start") < window_end and self._stamp(e, "end") > window_start for e in events)

    async def execute(self, action, arguments, session_id):
        try:
            if session_id in self.closed or await self.store.get("closed_session", session_id):
                raise CalendarError("session_closed")
            async with self.store.locked():
                if session_id in self.closed or await self.store.get("closed_session", session_id):
                    raise CalendarError("session_closed")
                return await self._execute(action, arguments, session_id)
        except CalendarError as exc:
            return {"success": False, "error": getattr(exc, "code", "calendar_error")}
        except (KeyError, ValueError, TypeError):
            return {"success": False, "error": "invalid_arguments"}
        except Exception:
            return {"success": False, "error": "calendar_unavailable"}

    async def _execute(self, action, args, session):
        if self.config.mode not in {"test", "production"}:
            raise CalendarError("calendar_disabled")
        self._policy()
        self._earliest_start()
        if action == "get_booking_policy":
            hours, duration, buffer = self._policy()
            def clock(minutes):
                return f"{minutes // 60:02d}:{minutes % 60:02d}"
            return {"success": True, "mode": self.config.mode,
                    "timezone": self.config.timezone,
                    "public_holidays_excluded": True, "holiday_region": "DE-BW",
                    "current_time": datetime.now(self.zone).isoformat(),
                    "appointment_type": "Kostenloses Erstgespräch",
                    "weekly_hours": {str(day): [[clock(start), clock(end)] for start, end in intervals] for day, intervals in hours.items()},
                    "duration_minutes": duration, "buffer_minutes": buffer}
        if action in {"get_calendar_events", "check_availability"}:
            start, end = self._range(args, action == "check_availability")
            if action == "check_availability":
                self._bookable(start, end)
            return {"success": True, "available": await self._available(start, end), "start": start.isoformat(), "end": end.isoformat()}
        if action == "find_free_slots":
            start, end = self._range(args)
            start = max(start.astimezone(timezone.utc), self._earliest_start())
            minutes = int(args.get("duration_minutes", 60))
            time_of_day = str(args.get("time_of_day", ""))
            if time_of_day not in {"", "morning", "afternoon", "early_evening", "evening"}:
                raise CalendarError("invalid_time_of_day")
            preferred_clock = str(args.get("preferred_clock", ""))
            if preferred_clock and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", preferred_clock):
                raise CalendarError("invalid_preferred_clock")
            requested_weekday = args.get("requested_weekday")
            if requested_weekday is not None and (type(requested_weekday) is not int or not 0 <= requested_weekday <= 6):
                raise CalendarError("invalid_requested_weekday")
            tolerance = args.get("clock_tolerance_minutes", 0)
            if type(tolerance) is not int or tolerance not in {0, 30}:
                raise CalendarError("invalid_clock_tolerance")
            excluded_intervals = []
            raw_exclusions = args.get("excluded_intervals", [])
            if not isinstance(raw_exclusions, list) or len(raw_exclusions) > 14:
                raise CalendarError("invalid_excluded_intervals")
            for exclusion in raw_exclusions:
                if not isinstance(exclusion, dict):
                    raise CalendarError("invalid_excluded_intervals")
                excluded_intervals.append(self._range(exclusion))
            if not 15 <= minutes <= 240:
                raise CalendarError("invalid_duration")
            _, duration, buffer_minutes = self._policy()
            if duration is not None and minutes != duration:
                raise CalendarError("invalid_duration")
            if start + timedelta(minutes=minutes) > end:
                return {"success": True, "slots": []}
            buffer = timedelta(minutes=buffer_minutes)
            events = await self.graph.list_events((start - buffer).isoformat(), (end + buffer).isoformat())
            preferred_slots = []
            fallback_slots = []
            local_cursor = start.astimezone(self.zone)
            cursor = local_cursor.replace(second=0, microsecond=0)
            if local_cursor.second or local_cursor.microsecond or cursor.minute % 15:
                cursor += timedelta(minutes=15 - cursor.minute % 15)
            cursor = cursor.astimezone(timezone.utc)
            while cursor + timedelta(minutes=minutes) <= end:
                finish = cursor + timedelta(minutes=minutes)
                local, local_end = cursor.astimezone(self.zone), finish.astimezone(self.zone)
                local_minute = local.hour * 60 + local.minute
                local_end_minute = local_end.hour * 60 + local_end.minute
                matches_time_of_day = {
                    "": True,
                    "morning": local_minute < 12 * 60 and local_end_minute <= 12 * 60,
                    "afternoon": local_minute > 12 * 60 and local_end_minute <= 18 * 60,
                    "early_evening": 18 * 60 <= local_minute < 20 * 60,
                    "evening": local_minute >= 18 * 60,
                }[time_of_day]
                if preferred_clock:
                    hour, minute = map(int, preferred_clock.split(":"))
                    matches_time_of_day = matches_time_of_day and abs(local_minute - hour * 60 - minute) <= tolerance
                if requested_weekday is not None:
                    matches_time_of_day = matches_time_of_day and local.weekday() == requested_weekday
                if any(cursor < excluded_end and finish > excluded_start for excluded_start, excluded_end in excluded_intervals):
                    matches_time_of_day = False
                try:
                    self._bookable(cursor, finish)
                    bookable = True
                except CalendarError:
                    bookable = False
                if matches_time_of_day and bookable and not any(self._busy(e) and self._stamp(e, "start") < finish + buffer and self._stamp(e, "end") > cursor - buffer for e in events):
                    slot = (cursor, {"start": local.isoformat(), "end": local_end.isoformat()})
                    if local.minute in {0, 30}:
                        preferred_slots.append(slot)
                    else:
                        fallback_slots.append(slot)
                cursor += timedelta(minutes=15)
            selected = preferred_slots[:3]
            selected.extend(fallback_slots[:3 - len(selected)])
            selected.sort(key=lambda item: item[0])
            return {"success": True, "slots": [slot for _, slot in selected]}
        if action == "find_customer_appointment":
            self._contact(args)
            original = self._date(args["original_start"])
            events = await self.graph.list_events(original.isoformat(), (original + timedelta(days=1)).isoformat())
            matches = []
            for event in events:
                owned = await self.store.get("event", event["id"])
                if owned and self._identity(args, owned) and self._stamp(event, "start") == original and not event.get("isCancelled"):
                    if self.config.mode == "test" and not event.get("subject", "").startswith("ANNA TEST "):
                        continue
                    token = secrets.token_urlsafe(24)
                    await self.store.put("candidate", token, {"session": session, "expires": datetime.now(timezone.utc).timestamp() + 300, "event": event, "contact": owned})
                    matches.append({"candidate_id": token, "start": self._stamp(event, "start").isoformat(), "end": self._stamp(event, "end").isoformat()})
            if len(matches) > 1:
                for item in matches:
                    await self.store.put("candidate", item["candidate_id"], {})
                return {"success": False, "error": "ambiguous_appointment", "candidates": []}
            return {"success": True, "candidates": matches, "ambiguous": len(matches) != 1}
        if action == "prepare_appointment":
            details = dict(args.get("details", {}))
            # Provider identifiers are resolved only from an owned candidate.
            details.pop("event_id", None)
            operation = args.get("action")
            if operation not in {"create", "reschedule", "cancel"}:
                raise CalendarError("invalid_action")
            self._contact(details)
            original = None
            if operation != "create":
                candidate = await self.store.get("candidate", details.get("candidate_id", ""))
                self._valid_token(candidate, session)
                if not self._identity(details, candidate["contact"]):
                    raise CalendarError("identity_mismatch")
                original = candidate["event"]
                details["event_id"] = original["id"]
            if operation != "cancel":
                start, end = self._range(details, True)
                self._bookable(start, end)
                if not await self._available(start, end, details.get("event_id")):
                    raise CalendarError("slot_unavailable")
            else:
                details.update(start=self._stamp(original, "start").isoformat(), end=self._stamp(original, "end").isoformat())
            token = secrets.token_urlsafe(32)
            record = {"session": session, "expires": datetime.now(timezone.utc).timestamp() + 300, "action": operation, "details": details, "original": original}
            await self.store.put("confirmation", token, record)
            local = self._date(details["start"]).astimezone(self.zone)
            label = {"create": "anlegen", "reschedule": "verschieben", "cancel": "absagen"}[operation]
            return {"success": True, "confirmation_token": token, "confirmation_action": operation, "summary": f"Termin am {local:%d.%m.%Y um %H:%M} Uhr {label}. Bitte ausdrücklich bestätigen."}
        mapping = {"create_appointment": "create", "reschedule_appointment": "reschedule", "cancel_appointment": "cancel"}
        if action not in mapping:
            raise CalendarError("unknown_action")
        if self.config.mode == "disabled":
            raise CalendarError("calendar_disabled")
        record = await self.store.get("confirmation", args.get("confirmation_token", ""))
        self._valid_token(record, session)
        operation = mapping[action]
        if args.get("confirmed") is not True or args.get("confirmation_action") != operation or record["action"] != operation:
            raise CalendarError("explicit_confirmation_required")
        details = record["details"]
        self._contact(details)
        canonical = {k: details.get(k) for k in ("name", "email", "phone", "start", "end", "event_id")}
        canonical.update(action=operation, mode=self.config.mode)
        canonical["name"], canonical["email"] = canonical["name"].strip().casefold(), (canonical["email"] or "").strip().casefold()
        canonical["phone"] = "".join(c for c in str(canonical["phone"] or "") if c.isdigit())
        for field in ("start", "end"):
            canonical[field] = self._date(canonical[field]).astimezone(timezone.utc).isoformat()
        txid = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
        existing = await self.store.get("operation", txid)
        if existing:
            if existing["status"] == "uncertain":
                return {"success": False, "error": "write_uncertain", "requires_manual_review": True}
            return self._result(existing)
        original = record["original"]
        if original:
            current = await self.graph.get_event(original["id"])
            if not current or current.get("@odata.etag") != original.get("@odata.etag") or not current.get("@odata.etag"):
                raise CalendarError("appointment_changed")
            if self.config.mode == "test" and not current.get("subject", "").startswith("ANNA TEST "):
                raise CalendarError("test_record_required")
        if operation != "cancel":
            start, end = self._range(details, True)
            self._bookable(start, end)
            if not await self._available(start, end, details.get("event_id")):
                raise CalendarError("slot_unavailable")
        if session in self.closed or await self.store.get("closed_session", session):
            raise CalendarError("session_closed")
        if operation != "cancel":
            self._bookable(start, end)
        state = {"status": "uncertain", "action": operation, "details": details, "original": original, "transaction_id": txid, "calendar_changed": False, "created_at": datetime.now(timezone.utc).isoformat()}
        await self.store.put("operation", txid, state)
        try:
            if operation == "create":
                event = await self.graph.find_transaction(txid)
                if not event:
                    content = "Quelle: ANNA\n" + "\n".join(f"{key}: {str(details.get(key, ''))[:1600]}" for key in ("name", "email", "phone", "summary"))
                    event = await self.graph.create_event({"subject": ("ANNA TEST " if self.config.mode == "test" else "ANNA ") + "Kostenloses Erstgespräch", "transactionId": txid, "showAs": "busy", "start": self._graph_time(details["start"]), "end": self._graph_time(details["end"]), "body": {"contentType": "Text", "content": content}})
                await self.store.put("event", event["id"], {"name": details["name"], "email": details.get("email", ""), "phone": details.get("phone", "")})
            elif operation == "reschedule":
                import html
                body = original.get("body", {"contentType": "Text", "content": ""}).copy()
                history = f"\nANNA rescheduled at {datetime.now(timezone.utc).isoformat()}: {self._stamp(original, 'start').isoformat()} – {self._stamp(original, 'end').isoformat()} -> {details['start']} – {details['end']}. Reason: {details.get('reason', 'customer request')}"
                body["content"] = body.get("content", "") + ("<p>" + html.escape(history) + "</p>" if body.get("contentType", "").lower() == "html" else history)
                await self.graph.update_event(original["id"], {"start": self._graph_time(details["start"]), "end": self._graph_time(details["end"]), "body": body}, original["@odata.etag"])
            else:
                await self.graph.delete_event(original["id"], original["@odata.etag"])
        except Exception:
            return {"success": False, "error": "write_uncertain", "requires_manual_review": True}
        state.update(status="notification_pending", calendar_changed=True)
        await self.store.put("operation", txid, state)
        await self._notify(txid, state)
        return self._result(state)

    def _graph_time(self, value):
        return {"dateTime": self._date(value).astimezone(timezone.utc).replace(tzinfo=None).isoformat(), "timeZone": "UTC"}

    def _valid_token(self, record, session):
        if not record or record["session"] != session or record["expires"] < datetime.now(timezone.utc).timestamp():
            raise CalendarError("confirmation_invalid_or_expired")

    def _result(self, state):
        return {"success": state["status"] == "complete", "calendar_changed": state["calendar_changed"], "notification_accepted": state["status"] == "complete", "status": state["status"]}

    async def _notify(self, txid, state):
        try:
            accepted = await self.notifier(state)
        except Exception:
            accepted = False
        state["status"] = "complete" if accepted else "notification_failed"
        await self.store.put("operation", txid, state)

    async def retry_notifications(self):
        count = 0
        async with self.store.locked():
            for txid, state in await self.store.all("operation"):
                if state["status"] in {"notification_pending", "notification_failed"}:
                    await self._notify(txid, state)
                    count += state["status"] == "complete"
        return {"success": True, "notifications_accepted": count}
