"""
Governance Agent — Configuration
==================================
What:    Configuration dataclass for the governance scanner.
Does:    Defines which paths to scan, which rules to enable, where to write output.
Why:     Centralises all tunable parameters so rules stay environment-agnostic.
Who:     agent.py, all rule modules.
Depends: pathlib, dataclasses
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GovernanceConfig:
    """
    Runtime configuration for a governance scan.

    Args:
        repo_root: Absolute path to the repository root.
        scan_python_paths: Subdirectories to scan for Python files.
        scan_ts_paths: Subdirectories to scan for TypeScript/JS files.
        exclude_dirs: Directory names to skip entirely.
        compliance_dir: Where compliance/*.md documents should live.
        output_dir: Where governance_log.json and governance_report.md are written.
        enabled_categories: Which rule categories to run (all if empty).
        finding_id_prefix: Prefix for generated finding IDs.
    """
    repo_root: Path
    scan_python_paths: list[str] = field(
        default_factory=lambda: ["src", "tests"]
    )
    scan_ts_paths: list[str] = field(
        default_factory=lambda: ["frontends/widget/src", "frontends/dashboard/src"]
    )
    exclude_dirs: list[str] = field(
        default_factory=lambda: [
            "venv", "__pycache__", ".git", "node_modules",
            "dist", "build", ".mypy_cache", ".ruff_cache",
        ]
    )
    compliance_dir: str = "compliance"
    output_dir: str = "compliance"
    enabled_categories: list[str] = field(default_factory=list)  # empty = all
    finding_id_prefix: str = "GOV"

    # Required compliance documents that must exist
    required_documents: list[str] = field(default_factory=lambda: [
        "compliance/DPIA.md",
        "compliance/PROCESSING_REGISTER.md",
        "compliance/AI_RISK_CLASSIFICATION.md",
        "compliance/TECHNICAL_DOCUMENTATION.md",
        "compliance/INCIDENT_RESPONSE.md",
        "compliance/DATA_RETENTION.md",
        "compliance/THIRD_PARTY_PROCESSORS.md",
        "compliance/CONSENT_VERSIONS.md",
    ])

    # Known public endpoints that do NOT require auth (explicit allow-list)
    public_endpoints: list[str] = field(default_factory=lambda: [
        "/health",
        "/ws/chat",
        "/widget-config",
        "/google-calendar/callback",  # OAuth callback — secured via state param
    ])

    # Patterns that indicate a secret/API key in code
    secret_patterns: list[str] = field(default_factory=lambda: [
        r"sk-[a-zA-Z0-9]{48}",               # OpenAI key
        r"re_[a-zA-Z0-9]{32,}",              # Resend key
        r"GOCSPX-[a-zA-Z0-9\-_]{28,}",      # Google OAuth secret
        r"ghp_[a-zA-Z0-9]{36}",             # GitHub PAT
        r"(?i)password\s*=\s*['\"][^'\"]{8,}['\"]",  # Hardcoded password
    ])

    @classmethod
    def default(cls, repo_root: Path | str) -> GovernanceConfig:
        """Create default configuration for the standard repo layout."""
        return cls(repo_root=Path(repo_root))
