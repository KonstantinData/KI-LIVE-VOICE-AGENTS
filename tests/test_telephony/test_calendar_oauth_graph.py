"""Security and transport checks without Microsoft credentials or real events."""

import asyncio
import base64
import hashlib
import time
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet

from src.agents.anna.calendar.config import MASTER_CALENDAR, CalendarConfig, CalendarError
from src.agents.anna.calendar.graph import BASE, GraphCalendar
from src.agents.anna.calendar.oauth import OAuthManager


@pytest.fixture
def config(tmp_path):
    return CalendarConfig(tenant_id="test-tenant", client_id="test-client",
        client_secret="private-client-secret", redirect_uri="https://anna.example/auth/microsoft/callback",
        encryption_key=Fernet.generate_key().decode(), data_dir=tmp_path / "calendar", mode="test")


def token_response(**updates):
    return {"access_token": "private-access", "refresh_token": "private-refresh",
            "expires_in": 3600, "scope": "Calendars.ReadWrite User.Read", **updates}


@pytest.mark.asyncio
async def test_pkce_one_use_state_account_and_encrypted_storage(config):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=token_response())
        return httpx.Response(200, json={"id": "master-id", "mail": MASTER_CALENDAR,
                                         "userPrincipalName": MASTER_CALENDAR})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        oauth = OAuthManager(config, http)
        query = parse_qs(urlsplit(await oauth.start("n" * 40)).query)
        assert query["code_challenge_method"] == ["S256"]
        assert "client_secret" not in query
        assert "Mail.Send" not in query["scope"][0]
        await oauth.finish("auth-code", query["state"][0], "n" * 40)
        grant = parse_qs(calls[0].content.decode())
        digest = hashlib.sha256(grant["code_verifier"][0].encode()).digest()
        assert query["code_challenge"] == [base64.urlsafe_b64encode(digest).rstrip(b"=").decode()]
        assert await oauth.access_token() == "private-access"
        assert oauth.status()["connected"]
        with pytest.raises(CalendarError, match="oauth_state_invalid"):
            await oauth.finish("auth-code", query["state"][0], "n" * 40)
        contents = b"".join(p.read_bytes() for p in config.data_dir.iterdir() if p.is_file())
        for value in (b"private-access", b"private-refresh", b"private-client-secret", b"master-id"):
            assert value not in contents


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["nonce", "state", "expired", "account", "scope", "guest"])
async def test_oauth_fails_closed(config, failure):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json=token_response(scope="User.Read" if failure == "scope"
                else "User.Read Calendars.ReadWrite"))
        return httpx.Response(200, json={"id": "id",
            "mail": MASTER_CALENDAR if failure == "guest" else "wrong@example.test",
            "userPrincipalName": "kontakt_konstantinmilonas.de#EXT#@example.onmicrosoft.com"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        oauth = OAuthManager(config, http)
        state = parse_qs(urlsplit(await oauth.start("n" * 40)).query)["state"][0]
        if failure == "expired":
            async with oauth._transaction() as conn:
                value = oauth._read(conn, "pending")
                value["expires_at"] = time.time() - 1
                oauth._write(conn, "pending", value)
        with pytest.raises(CalendarError):
            await oauth.finish("code", "bad" if failure == "state" else state,
                               "bad" if failure == "nonce" else "n" * 40)
        assert not oauth.status()["connected"]
        if failure in {"nonce", "state", "expired"}:
            assert not calls
        else:
            with pytest.raises(CalendarError, match="oauth_state_invalid"):
                await oauth.finish("code", state, "n" * 40)


@pytest.mark.asyncio
async def test_refresh_rotation_serialized_across_managers(config):
    refresh_count = 0

    async def handler(request):
        nonlocal refresh_count
        if request.url.path.endswith("/token"):
            refresh_count += 1
            await asyncio.sleep(0.1)
            assert parse_qs(request.content.decode())["refresh_token"] == ["old-refresh"]
            return httpx.Response(200, json=token_response(refresh_token="rotated-refresh"))
        return httpx.Response(200, json={"id": "master-id", "userPrincipalName": MASTER_CALENDAR})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        first, second = OAuthManager(config, http), OAuthManager(config, http)
        async with first._transaction() as conn:
            first._write(conn, "tokens", {"access_token": "expired", "refresh_token": "old-refresh",
                "expires_at": 0, "account_id": "master-id", "binding": first._binding()})
        assert await asyncio.gather(first.access_token(), second.access_token()) == ["private-access"] * 2
        assert refresh_count == 1
        async with first._transaction() as conn:
            assert first._read(conn, "tokens")["refresh_token"] == "rotated-refresh"
            assert first._read(conn, "tokens")["binding"] == first._binding()


@pytest.mark.asyncio
async def test_disabled_and_wrong_master_are_inert(config):
    assert OAuthManager(CalendarConfig()).status() == {"connected": False, "mode": "disabled"}
    for bad in [replace(config, mode="disabled"), replace(config, calendar_user="other@example.test"),
                replace(config, tenant_id="common"), replace(config, encryption_key="invalid")]:
        with pytest.raises(CalendarError):
            await OAuthManager(bad).start("n" * 40)


@pytest.mark.asyncio
@pytest.mark.parametrize("authority", ["common", "consumers", "organizations", "other-tenant"])
async def test_non_business_or_wrong_tenant_authority_is_rejected(config, authority):
    manager = OAuthManager(replace(config, authority_tenant=authority))
    with pytest.raises(CalendarError, match="calendar_not_configured"):
        await manager.start("n" * 40)
    assert not manager.status()["connected"]


@pytest.mark.asyncio
@pytest.mark.parametrize("binding_change", ["legacy", "authority_tenant", "client_id", "calendar_user"])
@pytest.mark.parametrize("expired", [False, True])
async def test_tokens_from_previous_identity_configuration_fail_closed(config, binding_change, expired):
    def unexpected_request(request):
        pytest.fail("Mismatched tokens must never reach Microsoft or refresh")

    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected_request)) as http:
        manager = OAuthManager(config, http)
        value = {"access_token": "old-access", "refresh_token": "old-refresh",
                 "account_id": "same-email-personal-account", "expires_at": 0 if expired else time.time() + 3600}
        if binding_change != "legacy":
            value["binding"] = {**manager._binding(), binding_change: "different"}
        async with manager._transaction() as conn:
            manager._write(conn, "tokens", value)
        assert not manager.status()["connected"]
        with pytest.raises(CalendarError, match="oauth_login_required"):
            await manager.access_token()


@pytest.mark.asyncio
@pytest.mark.parametrize("binding_change", ["legacy", "authority_tenant", "client_id", "calendar_user"])
async def test_pending_authorization_cannot_cross_configuration(config, binding_change):
    def unexpected_request(request):
        pytest.fail("Mismatched authorization must not redeem a code")

    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected_request)) as http:
        manager = OAuthManager(config, http)
        url = await manager.start("n" * 40)
        assert urlsplit(url).path == "/test-tenant/oauth2/v2.0/authorize"
        state = parse_qs(urlsplit(url).query)["state"][0]
        async with manager._transaction() as conn:
            value = manager._read(conn, "pending")
            if binding_change == "legacy":
                value.pop("binding")
            else:
                value["binding"][binding_change] = "different"
            manager._write(conn, "pending", value)
        with pytest.raises(CalendarError, match="oauth_state_invalid"):
            await manager.finish("code", state, "n" * 40)
        assert not manager.status()["connected"]


class FakeOAuth:
    async def access_token(self):
        return "bearer-private"


@pytest.mark.asyncio
async def test_calendar_view_paging_and_conditional_writes():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer bearer-private"
        assert 'IdType="ImmutableId"' in request.headers["prefer"]
        assert 'outlook.timezone="UTC"' in request.headers["prefer"]
        if request.method == "GET":
            if "$skiptoken" in request.url.params:
                return httpx.Response(200, json={"value": [{"id": "second"}]})
            return httpx.Response(200, json={"value": [{"id": "first"}],
                "@odata.nextLink": BASE + "/calendarView?$skiptoken=next"})
        if request.method in {"PATCH", "DELETE"}:
            assert request.headers["if-match"] == 'W/"version1"'
        return httpx.Response(204) if request.method == "DELETE" else httpx.Response(200, json={"id": "event"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        graph = GraphCalendar(FakeOAuth(), http)
        events = await graph.list_events("2026-10-01T10:00:00Z", "2026-10-02T10:00:00Z")
        assert [e["id"] for e in events] == ["first", "second"]
        assert requests[0].url.params["startDateTime"] == "2026-10-01T10:00:00Z"
        await graph.create_event({"transactionId": "unique"})
        await graph.update_event("event", {"subject": "new"}, 'W/"version1"')
        await graph.delete_event("event", 'W/"version1"')


@pytest.mark.asyncio
@pytest.mark.parametrize("next_url", ["https://evil.example/token", BASE + "/events?$skip=1",
                                      "http://graph.microsoft.com/v1.0/me/calendarView"])
async def test_pagination_never_sends_token_to_foreign_location(next_url):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"value": [], "@odata.nextLink": next_url})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(CalendarError, match="graph_pagination_invalid"):
            await GraphCalendar(FakeOAuth(), http).list_events("start", "end")
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["create", "update", "delete"])
async def test_write_timeout_is_ambiguous_and_not_retried(method):
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret provider content")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        graph = GraphCalendar(FakeOAuth(), http)
        with pytest.raises(CalendarError, match="^graph_write_uncertain$"):
            if method == "create":
                await graph.create_event({"transactionId": "id"})
            elif method == "update":
                await graph.update_event("event", {}, 'W/"v"')
            else:
                await graph.delete_event("event", 'W/"v"')
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_graph_conflict_and_missing_concurrency_guard():
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(412, json={"secret": "not exposed"}))) as http:
        graph = GraphCalendar(FakeOAuth(), http)
        with pytest.raises(CalendarError, match="graph_conflict"):
            await graph.update_event("id", {}, 'W/"v"')
        with pytest.raises(CalendarError, match="graph_etag_required"):
            await graph.delete_event("id", "*")
        with pytest.raises(CalendarError, match="graph_transaction_required"):
            await graph.create_event({})


@pytest.mark.asyncio
async def test_partial_pagination_failure_never_looks_like_free_calendar():
    def handler(request):
        if "$skiptoken" in request.url.params:
            return httpx.Response(503, json={"error": "provider detail"})
        return httpx.Response(200, json={"value": [],
            "@odata.nextLink": BASE + "/calendarView?$skiptoken=next"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(CalendarError, match="graph_rejected"):
            await GraphCalendar(FakeOAuth(), http).list_events("start", "end")


@pytest.mark.asyncio
async def test_transaction_recovery_reads_every_page():
    def handler(request):
        if "$skiptoken" in request.url.params:
            return httpx.Response(200, json={"value": [{"id": "found", "transactionId": "operation"}]})
        return httpx.Response(200, json={"value": [{"id": "unrelated"}],
            "@odata.nextLink": BASE + "/events?$skiptoken=next"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        graph = GraphCalendar(FakeOAuth(), http)
        assert (await graph.find_transaction("operation"))["id"] == "found"
        assert await graph.find_transaction("absent") is None
