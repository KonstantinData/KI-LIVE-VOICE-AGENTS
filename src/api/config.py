"""
Application Configuration
=========================
What:    Pydantic settings model for all environment variables.
Does:    Loads and validates configuration from .env file; provides type-safe access to settings.
Why:     Centralizes configuration; ensures required variables are present; prevents runtime errors.
Who:     All modules that need configuration (API, agents, services).
Depends: pydantic, pydantic-settings
"""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Lädt alle Umgebungsvariablen aus .env mit Validierung.
    Wenn eine Pflicht-Variable fehlt, crasht die App sofort
    mit einer klaren Fehlermeldung.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    app_env: str = "development"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    log_level: str = "DEBUG"

    # Datenbank
    database_url: str = "postgresql+asyncpg://ki_team:passwort@localhost:5432/ki_mitarbeiter"

    # Anthropic Claude
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 1024

    # OpenAI Embeddings
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    # Resend E-Mail
    resend_api_key: str = ""
    resend_from_email: str = "noreply@example.com"
    resend_from_name: str = "KI-Assistent"
    enable_email_sending: bool = False

    # Google Calendar OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    enable_calendar_sync: bool = False

    # Auth (Dashboard)
    admin_username: str = "admin"
    admin_password_hash: str = ""
    admin_studio_slug: str = "mein-kuechenexperte"
    allow_demo_login: bool = False
    jwt_secret: str = "dev-secret-min-32-chars-placeholder!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080

    # Runtime safety
    max_chat_message_chars: int = 4000
    retention_conversation_days: int = 180
    retention_unconverted_lead_days: int = 365
    retention_feedback_days: int = 730
    retention_event_days: int = 1095

    # Encryption
    encryption_key: str = ""

    # URLs
    api_url: str = "http://localhost:8000"
    ws_url: str = "ws://localhost:8000"
    dashboard_url: str = "http://localhost:5173"
    widget_url: str = "http://localhost:5174"
    website_url: str = "https://www.mein-kuechenexperte.de"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> list[str]:
        """Parst CORS_ORIGINS aus JSON-String oder Liste."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Fail fast when production security settings are incomplete."""
        if self.app_env == "production":
            if self.jwt_secret == "dev-secret-min-32-chars-placeholder!":
                raise ValueError("JWT_SECRET must be set in production")
            if not self.admin_password_hash:
                raise ValueError("ADMIN_PASSWORD_HASH must be set in production")
            if self.allow_demo_login:
                raise ValueError("ALLOW_DEMO_LOGIN must be false in production")
        if self.enable_email_sending and not self.resend_api_key:
            raise ValueError("RESEND_API_KEY is required when ENABLE_EMAIL_SENDING=true")
        if self.enable_calendar_sync and (
            not self.google_client_id or not self.google_client_secret
        ):
            raise ValueError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required when ENABLE_CALENDAR_SYNC=true"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Gibt eine gecachte Settings-Instanz zurück."""
    return Settings()
