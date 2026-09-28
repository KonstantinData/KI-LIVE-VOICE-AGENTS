"""Isolated ANNA calendar HTTP boundary; never mount in the widget API."""

import logging
import secrets
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .config import CalendarConfig, CalendarError
from .graph import GraphCalendar
from .oauth import OAuthManager
from .service import CalendarService

LOGGER = logging.getLogger("anna.calendar")

def create_app(config=None, service=None, oauth=None):
    config = config or CalendarConfig.from_env()
    oauth = oauth or OAuthManager(config)

    @asynccontextmanager
    async def lifespan(app):
        if app.state.service is None and config.mode in {"test", "production"}:
            from src.telephony.mail import send_calendar_notification
            config.validate()
            app.state.service = CalendarService(config, GraphCalendar(oauth), send_calendar_notification)
        yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.service = service

    def authorize(request):
        supplied = request.headers.get("authorization", "")
        if not config.api_token or not secrets.compare_digest(supplied, "Bearer " + config.api_token):
            raise HTTPException(401, "unauthorized")

    async def body(request):
        raw = await request.body()
        if len(raw) > 16384:
            raise HTTPException(413, "request_too_large")
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError
            return data
        except ValueError:
            raise HTTPException(400, "invalid_request") from None

    @app.get("/health")
    async def health():
        return {"service": "anna-calendar", "mode": config.mode}

    @app.post("/internal/execute")
    async def execute(request: Request):
        authorize(request)
        data = await body(request)
        if config.mode not in {"test", "production"} or app.state.service is None:
            return {"success": False, "error": "calendar_disabled"}
        if config.mode == "production":
            try:
                config.validate_policy()
            except CalendarError:
                return {"success": False, "error": "calendar_policy_required"}
        session = data.get("session_id")
        if not isinstance(session, str) or not 1 <= len(session) <= 128 or not isinstance(data.get("arguments"), dict):
            raise HTTPException(400, "invalid_request")
        return await app.state.service.execute(data.get("action"), data["arguments"], session)

    @app.post("/internal/close-session")
    async def close_session(request: Request):
        authorize(request)
        data = await body(request)
        if app.state.service and isinstance(data.get("session_id"), str):
            app.state.service.close_session(data["session_id"])
        return {"success": True}

    @app.post("/internal/retry-notifications")
    async def retry(request: Request):
        authorize(request)
        if app.state.service is None:
            return {"success": False, "error": "calendar_disabled"}
        return await app.state.service.retry_notifications()

    @app.get("/internal/status")
    async def status(request: Request):
        authorize(request)
        counts = {}
        if app.state.service:
            for _, operation in await app.state.service.store.all("operation"):
                key = operation.get("status", "unknown")
                counts[key] = counts.get(key, 0) + 1
        return {**oauth.status(), "operation_counts": counts}

    @app.get("/auth/microsoft/start")
    async def start_form():
        response = HTMLResponse('<form method="post"><label>ANNA Einrichtungsschlüssel <input type="password" name="token" autocomplete="off" required></label><button>An Microsoft anmelden</button></form>')
        response.set_cookie("anna_oauth_nonce", secrets.token_urlsafe(32), secure=True, httponly=True, samesite="lax", max_age=600)
        response.headers["Cache-Control"] = "no-store"
        # Some embedded browsers reject a same-origin form submission under
        # form-action despite the literal self target. The server still requires
        # the HttpOnly setup cookie and a constant-time validated setup token.
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    @app.post("/auth/microsoft/start")
    async def start(request: Request):
        raw = await request.body()
        if len(raw) > 4096:
            raise HTTPException(413, "request_too_large")
        supplied = parse_qs(raw.decode(errors="replace")).get("token", [""])[0]
        nonce = request.cookies.get("anna_oauth_nonce", "")
        if not config.api_token or not secrets.compare_digest(supplied, config.api_token) or len(nonce) < 32:
            raise HTTPException(401, "unauthorized")
        try:
            return RedirectResponse(await oauth.start(nonce), status_code=303, headers={"Cache-Control": "no-store"})
        except CalendarError:
            raise HTTPException(503, "oauth_not_ready") from None

    @app.get("/auth/microsoft/callback")
    async def callback(request: Request):
        try:
            await oauth.finish(request.query_params.get("code", ""), request.query_params.get("state", ""), request.cookies.get("anna_oauth_nonce", ""))
            response = HTMLResponse("Microsoft-Anmeldung abgeschlossen. Die Verfügbarkeit für ANNA hängt von der freigegebenen Betriebskonfiguration ab.")
        except CalendarError as exc:
            # The provider code, state and token response remain confidential.
            LOGGER.warning("oauth_callback_failed code=%s", exc.code)
            response = HTMLResponse("Anmeldung nicht abgeschlossen. Bitte Einrichtung erneut starten.", status_code=400)
        response.delete_cookie("anna_oauth_nonce", secure=True, httponly=True, samesite="lax")
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return app


app = create_app()
