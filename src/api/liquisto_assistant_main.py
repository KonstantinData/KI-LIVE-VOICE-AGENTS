"""Liquisto-only FastAPI entry point for the internal assistant service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import assistant, liquisto_mail, liquisto_mail_openai
from src.api.services.liquisto_navigation_sideband import navigation_sideband_manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Closes provider monitoring tasks without persisting audio or transcripts."""

    yield
    await navigation_sideband_manager.close()


app = FastAPI(
    title="Liquisto Assistant Runtime",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.include_router(assistant.health_router)
app.include_router(assistant.router)
app.include_router(liquisto_mail.router)
app.include_router(liquisto_mail_openai.router)
