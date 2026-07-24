"""Liquisto-only FastAPI entry point for the internal assistant service."""

from fastapi import FastAPI

from src.api.routes import assistant


app = FastAPI(
    title="Liquisto Assistant Runtime",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(assistant.health_router)
app.include_router(assistant.router)
