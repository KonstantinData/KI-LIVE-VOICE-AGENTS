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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Server
    app_env: str = "development"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    log_level: str = "DEBUG"

    # Datenbank
    database_url: str = (
        "postgresql+asyncpg://ki_team:passwort@localhost:5432/ki_mitarbeiter"
    )
    crm_contact_handoff_endpoint: str = ""
    crm_contact_handoff_secret: str = ""
    crm_usage_handoff_endpoint: str = ""
    crm_usage_handoff_secret: str = ""
    crm_upload_access_secret: str = ""

    # OpenAI
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    openai_chat_max_tokens: int = 1024
    openai_realtime_model: str = "gpt-realtime-2.1"
    openai_realtime_voice: str = "marin"
    enable_voice_sessions: bool = False
    max_voice_session_seconds: int = 900
    max_voice_sdp_chars: int = 200_000

    # Liquisto internal assistant. These settings never fall back to OpenAI cloud.
    liquisto_assistant_service_token: str = ""
    liquisto_assistant_llm_base_url: str = ""
    liquisto_assistant_llm_model: str = ""
    liquisto_assistant_llm_timeout_seconds: float = 20.0
    liquisto_assistant_llm_max_output_tokens: int = 1200
    liquisto_assistant_voice_enabled: bool = False

    # Runtime safety
    max_chat_message_chars: int = 4000
    retention_conversation_days: int = 180
    retention_upload_days: int = 180
    retention_event_days: int = 1095

    # Customer project uploads
    upload_storage_dir: str = "uploads/project-files"
    max_upload_file_bytes: int = 10_485_760
    max_upload_files_per_selection: int = 10
    max_uploads_per_visitor_hour: int = 10
    max_uploads_per_conversation: int = 30
    enable_upload_ai_analysis: bool = True

    # Encryption
    encryption_key: str = ""

    # URLs
    api_url: str = "http://localhost:8000"
    ws_url: str = "ws://localhost:8000"
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
        if self.enable_voice_sessions and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when ENABLE_VOICE_SESSIONS=true"
            )
        if self.liquisto_assistant_voice_enabled and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when "
                "LIQUISTO_ASSISTANT_VOICE_ENABLED=true"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Gibt eine gecachte Settings-Instanz zurück."""
    return Settings()
