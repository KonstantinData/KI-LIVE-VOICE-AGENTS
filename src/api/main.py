"""
FastAPI Application Entry Point
================================
What:    Main FastAPI application with voice/widget runtime routes and WebSocket endpoints.
Does:    Sets up CORS, tenant isolation, rate limiting; registers runtime API routes; handles WebSocket chat.
Why:     Central entry point for voice and widget communication without owning CRM screens.
Who:     Uvicorn server, website widget, and CRM handoff integrations.
Depends: fastapi, structlog, uvicorn, src.api.{config, middleware, routes, services, websocket}
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_settings
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.tenant import TenantMiddleware
from src.api.routes import health
from src.api.routes import uploads, voice, widget_config
from src.api.services.scheduler import setup_scheduler, shutdown_scheduler
from src.api.websocket.chat_handler import handle_chat

log = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup und Shutdown Handler."""
    log.info("app.startup", env=settings.app_env, port=settings.app_port)
    setup_scheduler()
    yield
    log.info("app.shutdown")
    shutdown_scheduler()


app = FastAPI(
    title="KI-LIVE-VOICE-AGENTS API",
    description="Backend für das KI-Agenten-Team für Küchen- und Möbelgeschäfte",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware
app.add_middleware(TenantMiddleware)
app.add_middleware(RateLimitMiddleware)

# Runtime routes
app.include_router(health.router)
app.include_router(voice.router)
app.include_router(uploads.router)
app.include_router(widget_config.router)


# WebSocket Chat-Endpoint
@app.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    studio: str = "default",
    visitor: str = "anonymous",
    consent: str = "0",
) -> None:
    """WebSocket-Endpoint für den Chat. ?studio={slug}&visitor={visitor_id}"""
    await handle_chat(
        websocket,
        studio_slug=studio,
        visitor_id=visitor,
        consent_given=consent in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
