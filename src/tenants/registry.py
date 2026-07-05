"""
Tenant Registry Loader
======================
What:    Loads local tenant runtime profiles from registry/tenants.
Does:    Provides cached typed access to widget, voice, upload, and policy data.
Why:     Tenant config must be the authority for public agent names and runtime
         grants; prompts alone must not grant capabilities.
Who:     API routes and runtime services.
Depends: json, pathlib, pydantic, src.tenants.models
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from src.tenants.models import TenantProfile

REPO_ROOT = Path(__file__).resolve().parents[2]
TENANT_REGISTRY_DIR = REPO_ROOT / "registry" / "tenants"


class TenantRegistryError(ValueError):
    """Raised when a tenant registry profile is missing or invalid."""


@lru_cache(maxsize=128)
def get_tenant_profile(tenant_id: str) -> TenantProfile:
    """Loads one tenant profile by tenant id."""
    path = TENANT_REGISTRY_DIR / tenant_id / "tenant.json"
    if not path.exists():
        raise TenantRegistryError(f"Tenant profile not found: {tenant_id}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        profile = TenantProfile.model_validate(data)
    except Exception as exc:
        raise TenantRegistryError(f"Tenant profile is invalid: {tenant_id}") from exc
    if not profile.is_active:
        raise TenantRegistryError(f"Tenant profile is not active: {tenant_id}")
    return profile


@lru_cache(maxsize=128)
def get_tenant_profile_for_studio(studio_slug: str) -> TenantProfile | None:
    """Returns the tenant profile matching a studio slug, if one exists."""
    direct_path = TENANT_REGISTRY_DIR / studio_slug / "tenant.json"
    if direct_path.exists():
        return get_tenant_profile(studio_slug)

    for path in sorted(TENANT_REGISTRY_DIR.glob("*/tenant.json")):
        try:
            profile = get_tenant_profile(path.parent.name)
        except TenantRegistryError:
            continue
        if profile.studio_slug == studio_slug:
            return profile
    return None


def agent_display_name(studio_slug: str, fallback: str = "Live Voice Agent") -> str:
    """Returns the tenant-selected public agent name."""
    profile = get_tenant_profile_for_studio(studio_slug)
    if profile is None:
        return fallback
    return profile.public_widget.agent_name


def widget_config_from_profile(
    studio_slug: str,
    studio_name: str,
    db_config: dict[str, Any],
) -> dict[str, Any]:
    """Builds public widget config with tenant registry authority when present."""
    profile = get_tenant_profile_for_studio(studio_slug)
    if profile is None:
        return {
            "studio": studio_slug,
            "studio_name": studio_name,
            "primary_color": db_config.get("primary_color", "#2563eb"),
            "agent_name": db_config.get("agent_name", "Live Voice Agent"),
            "agent_subtitle": db_config.get("agent_subtitle", "Live Voice Agent"),
            "welcome_message": db_config.get(
                "welcome_message",
                "Hallo! Wie kann ich Ihnen bei Ihrem Projekt helfen?",
            ),
            "privacy_url": db_config.get("privacy_url", "/datenschutz"),
            "retention_days": int(db_config.get("retention_days", 90)),
            "voice_enabled": bool(db_config.get("voice_enabled", False)),
            "upload_enabled": bool(db_config.get("upload_enabled", False)),
        }

    widget = profile.public_widget
    return {
        "studio": profile.studio_slug,
        "studio_name": profile.display_name,
        "primary_color": db_config.get("primary_color", "#2563eb"),
        "agent_name": widget.agent_name,
        "agent_subtitle": widget.agent_subtitle,
        "welcome_message": widget.welcome_message,
        "privacy_url": widget.privacy_url,
        "retention_days": widget.retention_days,
        "voice_enabled": widget.voice_enabled,
        "upload_enabled": widget.upload_enabled,
    }
