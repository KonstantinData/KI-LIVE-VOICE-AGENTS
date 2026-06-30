"""Tests for production configuration guardrails."""

import pytest
from pydantic import ValidationError

from src.api.config import Settings


def test_production_requires_real_jwt_secret_and_admin_hash():
    """Production settings reject insecure bootstrap defaults."""
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="dev-secret-min-32-chars-placeholder!",
            admin_password_hash="",
            cors_origins=["https://example.com"],
        )


def test_enabled_email_requires_resend_key():
    """Email feature flag must not be enabled without provider credentials."""
    with pytest.raises(ValidationError):
        Settings(enable_email_sending=True, resend_api_key="")


def test_enabled_calendar_requires_oauth_credentials():
    """Calendar feature flag must not be enabled without OAuth credentials."""
    with pytest.raises(ValidationError):
        Settings(enable_calendar_sync=True, google_client_id="", google_client_secret="")
