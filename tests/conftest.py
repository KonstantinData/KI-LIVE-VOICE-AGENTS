"""Pytest Fixtures für alle Tests."""

# ruff: noqa: E402

import os

# Muss vor allen src-Importen gesetzt werden, damit database.py SQLite nutzt
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.main import app
from src.db.database import get_session
from src.db.models.base import Base


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Erstellt eine Test-Datenbank-Engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # SQLite unterstützt kein pgvector — KnowledgeChunk-Embedding überspringen
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Returns an isolated database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client():
    """HTTP-Test-Client für FastAPI."""
    app.dependency_overrides.clear()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_client(db_session: AsyncSession):
    """HTTP-Test-Client mit DB-Dependency-Override auf dieselbe Test-Session."""

    async def override_db():
        yield db_session

    app.dependency_overrides[get_session] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
