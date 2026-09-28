"""Bounded Graph calendar transport; never retry ambiguous writes blindly."""

from urllib.parse import quote, urlsplit

import httpx

from .config import CalendarError
from .oauth import OAuthManager

BASE = "https://graph.microsoft.com/v1.0/me"
PREFER = 'outlook.timezone="UTC", IdType="ImmutableId"'


class GraphCalendar:
    def __init__(self, oauth: OAuthManager, http: httpx.AsyncClient | None = None):
        self.oauth = oauth
        self.http = http

    async def _request(self, method, url, *, payload=None, etag=None, params=None):
        headers = {"Authorization": f"Bearer {await self.oauth.access_token()}", "Prefer": PREFER}
        if etag:
            headers["If-Match"] = etag
        kwargs = {"headers": headers, "params": params, "follow_redirects": False}
        if payload is not None:
            kwargs["json"] = payload
        write = method != "GET"
        try:
            if self.http is not None:
                response = await self.http.request(method, url, **kwargs)
            else:
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.request(method, url, **kwargs)
        except httpx.HTTPError:
            raise CalendarError("graph_write_uncertain" if write else "graph_unavailable") from None
        if response.status_code == 412:
            raise CalendarError("graph_conflict")
        if response.status_code == 404:
            raise CalendarError("graph_not_found")
        if response.status_code >= 500 and write:
            raise CalendarError("graph_write_uncertain")
        if not 200 <= response.status_code < 300:
            raise CalendarError("graph_rejected")
        if response.status_code == 204:
            return {}
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError
            return data
        except ValueError:
            raise CalendarError("graph_write_uncertain" if write else "graph_response_invalid") from None

    async def _pages(self, path, params):
        url = BASE + path
        expected_path = urlsplit(url).path
        seen, events = set(), []
        for _ in range(100):
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or parsed.netloc != "graph.microsoft.com"
                or parsed.path != expected_path or parsed.fragment or url in seen):
                raise CalendarError("graph_pagination_invalid")
            seen.add(url)
            result = await self._request("GET", url, params=params)
            values = result.get("value")
            if not isinstance(values, list) or any(not isinstance(v, dict) for v in values):
                raise CalendarError("graph_response_invalid")
            events.extend(values)
            next_url = result.get("@odata.nextLink")
            if not next_url:
                return events
            if not isinstance(next_url, str):
                raise CalendarError("graph_pagination_invalid")
            url, params = next_url, None
        raise CalendarError("graph_pagination_limit")

    async def list_events(self, start: str, end: str) -> list[dict]:
        return await self._pages("/calendarView", {
            "startDateTime": start, "endDateTime": end, "$top": "1000",
        })

    async def get_event(self, event_id: str) -> dict:
        return await self._request("GET", self._event_url(event_id))

    @staticmethod
    def _event_url(event_id):
        if not event_id or len(event_id) > 2048:
            raise CalendarError("graph_event_id_invalid")
        return BASE + "/events/" + quote(event_id, safe="")

    async def create_event(self, payload: dict) -> dict:
        if not payload.get("transactionId"):
            raise CalendarError("graph_transaction_required")
        return await self._request("POST", BASE + "/events", payload=payload)

    async def update_event(self, event_id: str, payload: dict, etag: str) -> dict:
        if not etag or etag == "*":
            raise CalendarError("graph_etag_required")
        return await self._request("PATCH", self._event_url(event_id), payload=payload, etag=etag)

    async def delete_event(self, event_id: str, etag: str) -> dict:
        if not etag or etag == "*":
            raise CalendarError("graph_etag_required")
        return await self._request("DELETE", self._event_url(event_id), etag=etag)

    async def find_transaction(self, transaction_id: str) -> dict | None:
        if not transaction_id:
            raise CalendarError("graph_transaction_required")
        # transactionId filtering is not supported consistently by Graph. Scan a
        # bounded, fully paginated collection and fail closed if it is incomplete.
        events = await self._pages("/events", {"$top": "1000"})
        matches = [e for e in events if e.get("transactionId") == transaction_id]
        if len(matches) > 1:
            raise CalendarError("graph_transaction_ambiguous")
        return matches[0] if matches else None
