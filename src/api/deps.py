"""
FastAPI Dependencies
====================
What:    Shared dependency functions for DB sessions, JWT auth, and tenant context.
Does:    Verifies bearer tokens and resolves the active studio from token/header/query data.
Why:     Keeps route handlers small while enforcing tenant isolation in one place.
Who:     All API route modules.
Depends: fastapi, jose, sqlalchemy, src.api.config, src.db.database, src.db.models.studio
"""

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.db.database import get_session
from src.db.models.studio import Studio

settings = get_settings()
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: Gibt eine Datenbank-Session zurück."""
    async for session in get_session():
        yield session


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    """
    Dependency: Prüft JWT-Token und gibt den aktuellen User zurück.

    Wirft 401 wenn der Token fehlt oder ungültig ist.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht authentifiziert",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültiger Token",
            )
        return {"user_id": user_id, "payload": payload}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_studio(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
) -> Studio:
    """
    Resolves the current studio and verifies that it is active.

    Resolution order:
    1. X-Studio-ID header or studio_id query parameter.
    2. X-Studio-Slug header or studio_slug query parameter.
    3. studio_id / studio_slug JWT claims.
    4. APP admin_studio_slug setting for single-studio dashboard deployments.
    """
    payload = user["payload"]
    studio_id = (
        request.headers.get("X-Studio-ID")
        or request.query_params.get("studio_id")
        or payload.get("studio_id")
    )
    studio_slug = (
        request.headers.get("X-Studio-Slug")
        or request.query_params.get("studio_slug")
        or payload.get("studio_slug")
        or settings.admin_studio_slug
    )

    statement = select(Studio)
    if studio_id:
        try:
            statement = statement.where(Studio.id == UUID(str(studio_id)))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid studio_id",
            ) from exc
    else:
        statement = statement.where(Studio.slug == studio_slug)

    result = await session.execute(statement)
    studio = result.scalar_one_or_none()
    if studio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Studio not found")
    if not studio.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Studio is inactive")
    return studio


# Typen für Dependency Injection
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentStudio = Annotated[Studio, Depends(get_current_studio)]
