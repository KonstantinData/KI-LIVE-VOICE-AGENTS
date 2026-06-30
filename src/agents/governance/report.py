"""
Governance Agent — Report Generator
======================================
What:    Generates compliance reports in JSON and Markdown format.
Does:    Takes a GovernanceReport and writes governance_log.json + governance_report.md.
Why:     Separates report rendering from scan logic; reports must be human-readable.
Who:     agent.py calls this after all rules have run.
Depends: json, pathlib, src.agents.governance.models
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.agents.governance.models import GovernanceReport, Severity

_SEVERITY_EMOJI = {
    Severity.KRITISCH: "🔴",
    Severity.HOCH: "🟠",
    Severity.MITTEL: "🟡",
    Severity.NIEDRIG: "🔵",
    Severity.HINWEIS: "⚪",
}


def write_json_report(report: GovernanceReport, output_dir: Path) -> Path:
    """
    Write the full report as a machine-readable JSON file.

    Args:
        report: Completed GovernanceReport.
        output_dir: Directory where governance_log.json will be written.

    Returns:
        Path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "governance_log.json"
    data = report.model_dump(mode="json")
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def write_markdown_report(report: GovernanceReport, output_dir: Path) -> Path:
    """
    Write a human-readable Markdown compliance report.

    Args:
        report: Completed GovernanceReport.
        output_dir: Directory where governance_report.md will be written.

    Returns:
        Path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "governance_report.md"
    lines: list[str] = []

    s = report.summary
    generated = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    lines += [
        f"# Compliance-Report — {generated}",
        "",
        "## Zusammenfassung",
        "",
        "| Kennzahl | Wert |",
        "| --- | --- |",
        f"| Geprüfte Dateien | {s.scanned_files} |",
        f"| Findings gesamt | {s.total_findings} |",
        f"| 🔴 KRITISCH | {s.kritisch} |",
        f"| 🟠 HOCH | {s.hoch} |",
        f"| 🟡 MITTEL | {s.mittel} |",
        f"| 🔵 NIEDRIG | {s.niedrig} |",
        f"| ⚪ HINWEIS | {s.hinweis} |",
        f"| Auto-fixable | {s.auto_fixable} von {s.total_findings} |",
        "",
    ]

    if s.total_findings == 0:
        lines += ["## ✅ Keine Findings — alle geprüften Regeln bestanden.", ""]
    else:
        # Group by severity
        for severity in [
            Severity.KRITISCH, Severity.HOCH, Severity.MITTEL,
            Severity.NIEDRIG, Severity.HINWEIS
        ]:
            group = [f for f in report.findings if f.severity == severity]
            if not group:
                continue

            emoji = _SEVERITY_EMOJI[severity]
            lines += [
                f"## {emoji} {severity.value} ({len(group)} Finding{'s' if len(group) != 1 else ''})",
                "",
            ]

            for finding in group:
                location = ""
                if finding.file:
                    location = f"`{finding.file}`"
                    if finding.line:
                        location += f" Zeile {finding.line}"

                lines += [
                    f"### {finding.id} — {finding.subcategory}",
                    "",
                    f"**Rechtsgrundlage:** {finding.regulation}",
                    f"**Fundort:** {location}" if location else "",
                    f"**Deadline:** {finding.deadline}",
                    f"**Auto-fixable:** {'Ja' if finding.auto_fixable else 'Nein'}",
                    "",
                    "**Problem:**",
                    f"{finding.finding}",
                    "",
                    "**So muss es sein:**",
                    f"{finding.must_be}",
                    "",
                ]

                if finding.fix_example:
                    lines += [
                        "**Fix-Beispiel:**",
                        "",
                        "```python",
                        finding.fix_example,
                        "```",
                        "",
                    ]

                if finding.references:
                    lines += [
                        f"**Referenzen:** {', '.join(finding.references)}",
                        "",
                        "---",
                        "",
                    ]
                else:
                    lines += ["---", ""]

    lines += [
        "## Nächste Schritte",
        "",
        "1. Alle KRITISCH-Findings sofort beheben (vor Go-Live Pflicht)",
        "2. HOCH-Findings vor Go-Live abschließen",
        "3. MITTEL-Findings innerhalb von 30 Tagen",
        "4. `make compliance` nach jeder Änderung erneut ausführen",
        "",
        f"*Generiert von DataGovernanceAgent am {generated}*",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
