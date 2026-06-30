"""DataGovernance Agent — DSGVO + EU AI Act compliance scanner for the KI-Mitarbeiter platform."""

from src.agents.governance.agent import run_scan
from src.agents.governance.config import GovernanceConfig
from src.agents.governance.models import GovernanceReport

__all__ = ["run_scan", "GovernanceConfig", "GovernanceReport"]
