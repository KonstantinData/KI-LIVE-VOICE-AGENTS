"""
Governance Rules — Documentation Requirements
================================================
What:    Checks that all legally required compliance documents exist in the repo.
Does:    Verifies presence and non-emptiness of DPIA, PROCESSING_REGISTER, etc.
Why:     Missing documents are direct DSGVO/EU AI Act violations with audit risk.
Who:     agent.py orchestrates; findings go into GovernanceReport.
Depends: src.agents.governance.{scanner, models, config}
"""

from __future__ import annotations

from src.agents.governance.config import GovernanceConfig
from src.agents.governance.models import Category, Finding, Severity
from src.agents.governance.scanner import FileScanner

# Document metadata: rel_path → (subcategory, regulation, deadline)
_REQUIRED_DOCS: list[tuple[str, str, str, str]] = [
    (
        "compliance/DPIA.md",
        "6.8_DPIA",
        "Art. 35 DSGVO",
        "Vor Go-Live — DPIA ist bei Profiling-Verarbeitung Pflicht",
    ),
    (
        "compliance/PROCESSING_REGISTER.md",
        "6.11_VERARBEITUNGSVERZEICHNIS",
        "Art. 30 DSGVO",
        "Sofort — Verarbeitungsverzeichnis ist ab erstem Einsatz Pflicht",
    ),
    (
        "compliance/AI_RISK_CLASSIFICATION.md",
        "3.1_RISIKOKLASSIFIZIERUNG",
        "Art. 6 EU AI Act",
        "Vor Go-Live — Risikoklassifizierung ist Pflicht ab 02.08.2026",
    ),
    (
        "compliance/TECHNICAL_DOCUMENTATION.md",
        "3.3_TECHNISCHE_DOKUMENTATION",
        "Art. 11 + Annex IV EU AI Act",
        "Vor Go-Live — Technische Dokumentation Pflicht ab 02.08.2026",
    ),
    (
        "compliance/INCIDENT_RESPONSE.md",
        "6.7_DATENPANNE",
        "Art. 33, 34 DSGVO",
        "Sofort — Meldeprozess muss jederzeit aktivierbar sein",
    ),
    (
        "compliance/DATA_RETENTION.md",
        "1.3_SPEICHERBEGRENZUNG",
        "Art. 5 Abs. 1 lit. e DSGVO",
        "Vor Go-Live — Löschfristen müssen vor erster Datenerhebung definiert sein",
    ),
    (
        "compliance/THIRD_PARTY_PROCESSORS.md",
        "1.6_AUFTRAGSVERARBEITUNG",
        "Art. 28 DSGVO",
        "Vor Go-Live — AVVs müssen vor Einsatz externer Dienste abgeschlossen sein",
    ),
    (
        "compliance/CONSENT_VERSIONS.md",
        "6.6_EINWILLIGUNGSAUFBEWAHRUNG",
        "Art. 7 DSGVO",
        "Vor Go-Live — Einwilligungstext muss versioniert sein",
    ),
]


def check_required_documents(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that all required compliance documents exist and are non-empty.

    Args:
        scanner: Initialised FileScanner.
        config: GovernanceConfig with repo_root.
        counter: Mutable counter list [n] for generating sequential finding IDs.

    Returns:
        List of findings for missing or empty documents.
    """
    findings: list[Finding] = []

    for rel_path, subcategory, regulation, deadline in _REQUIRED_DOCS:
        if not scanner.document_exists(rel_path):
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.HOCH,
                category=Category.DOCUMENTATION,
                subcategory=subcategory,
                regulation=regulation,
                file=rel_path,
                line=None,
                finding=f"Pflichtdokument fehlt: '{rel_path}' existiert nicht oder ist leer.",
                must_be=(
                    f"Die Datei '{rel_path}' muss existieren und vollständig ausgefüllt sein. "
                    "Eine Vorlage ist in der DATA_GOVERNANCE_AGENT.md beschrieben."
                ),
                fix_example=None,
                deadline=deadline,
                auto_fixable=False,
                references=[regulation],
            ))

    return findings
