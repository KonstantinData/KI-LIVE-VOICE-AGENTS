"""
Governance Agent — Data Models
================================
What:    Pydantic models for compliance findings, reports, and severity levels.
Does:    Defines the data structures used across all governance agent modules.
Why:     Single source of truth for finding structure; enables JSON serialization.
Who:     All rules modules, scanner.py, report.py, agent.py.
Depends: pydantic v2
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity level of a compliance finding."""
    KRITISCH = "KRITISCH"   # Must be fixed before go-live; potential fines
    HOCH = "HOCH"           # Must be fixed before go-live; high legal risk
    MITTEL = "MITTEL"       # Fix within 30 days
    NIEDRIG = "NIEDRIG"     # Fix within 90 days
    HINWEIS = "HINWEIS"     # Best practice; no legal deadline


class Category(str, Enum):
    """Top-level compliance category."""
    DSGVO = "DSGVO"
    EU_AI_ACT = "EU_AI_ACT"
    SECURITY = "SECURITY"
    MULTI_TENANT = "MULTI_TENANT"
    DOCUMENTATION = "DOCUMENTATION"


class Finding(BaseModel):
    """
    A single compliance finding produced by the governance scanner.

    Args:
        id: Unique ID in format GOV-YYYY-NNNN.
        timestamp: UTC timestamp of the finding.
        severity: How urgent this finding is.
        category: Which legal/technical area this belongs to.
        subcategory: Fine-grained rule reference (e.g. "1.5_EINWILLIGUNG").
        regulation: Exact legal article (e.g. "Art. 6 Abs. 1 DSGVO").
        file: Relative path to the file with the issue (None for missing docs).
        line: Line number in the file (None if not file-specific).
        finding: Human-readable description of what is wrong.
        must_be: What compliant code/config/doc must look like.
        fix_example: Optional code snippet showing the fix.
        deadline: When this must be fixed by (human-readable).
        auto_fixable: Whether the agent can apply this fix automatically.
        references: List of legal references for this finding.

    Returns:
        A serializable finding ready for JSON/Markdown report output.
    """
    id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    severity: Severity
    category: Category
    subcategory: str
    regulation: str
    file: str | None = None
    line: int | None = None
    finding: str
    must_be: str
    fix_example: str | None = None
    deadline: str
    auto_fixable: bool = False
    references: list[str] = Field(default_factory=list)


class ScanSummary(BaseModel):
    """Aggregate statistics for a governance scan run."""
    scanned_files: int = 0
    total_findings: int = 0
    kritisch: int = 0
    hoch: int = 0
    mittel: int = 0
    niedrig: int = 0
    hinweis: int = 0
    auto_fixable: int = 0

    @classmethod
    def from_findings(cls, findings: list[Finding], scanned_files: int) -> ScanSummary:
        """Build summary statistics from a list of findings."""
        return cls(
            scanned_files=scanned_files,
            total_findings=len(findings),
            kritisch=sum(1 for f in findings if f.severity == Severity.KRITISCH),
            hoch=sum(1 for f in findings if f.severity == Severity.HOCH),
            mittel=sum(1 for f in findings if f.severity == Severity.MITTEL),
            niedrig=sum(1 for f in findings if f.severity == Severity.NIEDRIG),
            hinweis=sum(1 for f in findings if f.severity == Severity.HINWEIS),
            auto_fixable=sum(1 for f in findings if f.auto_fixable),
        )


class GovernanceReport(BaseModel):
    """Complete governance scan report."""
    report_id: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    repo_root: str
    summary: ScanSummary
    findings: list[Finding]
    metadata: dict[str, Any] = Field(default_factory=dict)
