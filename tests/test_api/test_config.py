"""Tests for production configuration guardrails."""

import pytest
from pydantic import ValidationError

from src.api.config import Settings


def test_production_rejects_demo_login():
    """Production settings reject local demo login mode."""
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            allow_demo_login=True,
            cors_origins=["https://example.com"],
        )
