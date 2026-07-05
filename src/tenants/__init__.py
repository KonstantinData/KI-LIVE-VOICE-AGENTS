"""Tenant registry helpers for live voice runtime composition."""

from src.tenants.registry import (
    agent_display_name,
    get_tenant_profile,
    get_tenant_profile_for_studio,
)

__all__ = [
    "agent_display_name",
    "get_tenant_profile",
    "get_tenant_profile_for_studio",
]
