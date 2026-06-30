"""
Authentication Routes
=====================
What:    Dashboard login route issuing JWT bearer tokens.
Does:    Verifies an environment-configured admin password hash and embeds tenant scope.
Why:     Removes hard-coded production credentials while keeping explicit dev bootstrap support.
Who:     Dashboard frontend and protected API routes.
Depends: bcrypt, fastapi, jose, pydantic, src.api.config
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel

from src.api.config import get_settings

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()


class LoginRequest(BaseModel):
    """Login-Anfrage mit Benutzername und Passwort."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT-Token-Antwort."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


def _hash_password(password: str) -> bytes:
    """Erzeugt einen bcrypt-Hash für das gegebene Passwort."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def _verify_password(password: str, hashed: bytes) -> bool:
    """Vergleicht ein Passwort mit einem bcrypt-Hash."""
    return bcrypt.checkpw(password.encode(), hashed)


def _get_admin_hash() -> bytes | None:
    """
    Returns the configured admin password hash.

    Production must set ADMIN_PASSWORD_HASH. The legacy admin/secret login is
    only available when ALLOW_DEMO_LOGIN=true and APP_ENV is not production.
    """
    if settings.admin_password_hash:
        return settings.admin_password_hash.encode()
    if settings.allow_demo_login and settings.app_env != "production":
        return _hash_password("secret")
    return None


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Authentifiziert einen Benutzer und gibt einen JWT-Token zurück.

    In production, set ADMIN_USERNAME and ADMIN_PASSWORD_HASH.
    """
    hashed = _get_admin_hash() if request.username == settings.admin_username else None
    if not hashed or not _verify_password(request.password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Anmeldedaten",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    token = jwt.encode(
        {
            "sub": request.username,
            "studio_slug": settings.admin_studio_slug,
            "exp": expire,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )
