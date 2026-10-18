"""Resolve KEA's tenant-owned runtime identity without selecting other agents."""

from src.db.models.studio import Studio
from src.tenants.models import LiveVoiceAgentProfile
from src.tenants.registry import get_tenant_profile_for_studio


def get_kea_profile(studio: Studio) -> LiveVoiceAgentProfile:
    """Reject missing or unrelated profiles before using MKX-specific behavior."""
    if studio.slug != "mein-kuechenexperte":
        raise ValueError("KEA is only available for the mein-kuechenexperte tenant.")
    profile = get_tenant_profile_for_studio(studio.slug)
    if profile is None or profile.tenant_id != "mein-kuechenexperte":
        raise ValueError("KEA tenant profile is not available.")
    agent = profile.live_voice_agent("kea-project-intake")
    if agent.prompt_profile != "mein-kuechenexperte-project-intake":
        raise ValueError("KEA prompt profile is not available.")
    return agent
