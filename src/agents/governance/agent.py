"""
DataGovernance Agent — Main Entry Point
=========================================
What:    Orchestrates all compliance rule checks and generates reports.
Does:    Discovers files, runs all rule modules, aggregates findings, writes JSON + Markdown reports.
Why:     Single executable for DSGVO / EU AI Act compliance scanning of the entire codebase.
Who:     Called via CLI: python -m src.agents.governance.agent --scan-all
         Also usable as a library: run_scan(config) → GovernanceReport
Depends: argparse, pathlib, all rules modules, report.py, scanner.py, models.py, config.py
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog

from src.agents.governance.config import GovernanceConfig
from src.agents.governance.models import GovernanceReport, ScanSummary
from src.agents.governance.report import write_json_report, write_markdown_report
from src.agents.governance.rules.documentation import check_required_documents
from src.agents.governance.rules.dsgvo import (
    check_consent_mechanism,
    check_cookie_consent,
    check_gdpr_endpoints,
    check_retention_policy,
)
from src.agents.governance.rules.eu_ai_act import (
    check_ai_disclosure,
    check_human_oversight,
    check_score_bias,
)
from src.agents.governance.rules.multi_tenant import (
    check_knowledge_vector_isolation,
    check_studio_id_filters,
)
from src.agents.governance.rules.security import (
    check_input_validation,
    check_pii_in_logs,
    check_secrets_in_code,
)
from src.agents.governance.scanner import FileScanner

log = structlog.get_logger()


def run_scan(config: GovernanceConfig) -> GovernanceReport:
    """
    Execute all governance rule checks and return a complete report.

    Args:
        config: GovernanceConfig with repo_root and rule settings.

    Returns:
        GovernanceReport with all findings and summary statistics.
    """
    scanner = FileScanner(config)
    all_source_files = scanner.find_all_source_files()
    scanned_count = len(all_source_files)

    # Shared mutable counter for sequential finding IDs
    # NOTE: Using a list so all rule functions can mutate the same counter by reference
    counter = [0]
    findings = []

    log.info("governance.scan.start", repo=str(config.repo_root), files=scanned_count)

    # ── Priority 1: Documentation (fastest — just file existence) ──────────
    findings += check_required_documents(scanner, config, counter)
    log.info("governance.rules.documentation", count=len(findings))

    # ── Priority 2: Secrets ─────────────────────────────────────────────────
    n = len(findings)
    findings += check_secrets_in_code(scanner, config, counter)
    log.info("governance.rules.secrets", new=len(findings) - n)

    # ── Priority 3: Multi-tenant isolation ──────────────────────────────────
    n = len(findings)
    findings += check_studio_id_filters(scanner, config, counter)
    findings += check_knowledge_vector_isolation(scanner, config, counter)
    log.info("governance.rules.multi_tenant", new=len(findings) - n)

    # ── Priority 4: DSGVO ───────────────────────────────────────────────────
    n = len(findings)
    findings += check_consent_mechanism(scanner, config, counter)
    findings += check_gdpr_endpoints(scanner, config, counter)
    findings += check_retention_policy(scanner, config, counter)
    findings += check_cookie_consent(scanner, config, counter)
    log.info("governance.rules.dsgvo", new=len(findings) - n)

    # ── Priority 5: EU AI Act ───────────────────────────────────────────────
    n = len(findings)
    findings += check_ai_disclosure(scanner, config, counter)
    findings += check_human_oversight(scanner, config, counter)
    findings += check_score_bias(scanner, config, counter)
    log.info("governance.rules.eu_ai_act", new=len(findings) - n)

    # ── Priority 6: Security ────────────────────────────────────────────────
    n = len(findings)
    findings += check_pii_in_logs(scanner, config, counter)
    findings += check_input_validation(scanner, config, counter)
    log.info("governance.rules.security", new=len(findings) - n)

    summary = ScanSummary.from_findings(findings, scanned_count)
    report = GovernanceReport(
        report_id=f"GOV-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}",
        repo_root=str(config.repo_root),
        summary=summary,
        findings=findings,
        metadata={"scanner_version": "1.0.0"},
    )

    log.info(
        "governance.scan.complete",
        total=summary.total_findings,
        kritisch=summary.kritisch,
        hoch=summary.hoch,
    )
    return report


def _print_summary(report: GovernanceReport) -> None:
    """Print a compact summary to stdout after a scan."""
    s = report.summary
    print("\n" + "=" * 60)
    print(f"COMPLIANCE SCAN — {report.generated_at[:10]}")
    print("=" * 60)
    print(f"Geprüfte Dateien : {s.scanned_files}")
    print(f"Findings gesamt  : {s.total_findings}")
    print(f"  🔴 KRITISCH    : {s.kritisch}")
    print(f"  🟠 HOCH        : {s.hoch}")
    print(f"  🟡 MITTEL      : {s.mittel}")
    print(f"  🔵 NIEDRIG     : {s.niedrig}")
    print(f"  ⚪ HINWEIS     : {s.hinweis}")
    print(f"  Auto-fixable   : {s.auto_fixable}")
    print("=" * 60)
    if s.kritisch > 0:
        print("⛔ KRITISCHE FINDINGS — Bitte sofort beheben!")
    elif s.hoch > 0:
        print("⚠️  HOHE FINDINGS — Vor Go-Live beheben.")
    else:
        print("✅ Keine kritischen oder hohen Findings.")
    print()


def main() -> None:
    """CLI entry point for the governance agent."""
    parser = argparse.ArgumentParser(
        description="DataGovernance Agent — DSGVO + EU AI Act Compliance Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  python -m src.agents.governance.agent --scan-all\n"
            "  python -m src.agents.governance.agent --scan-all --report\n"
            "  python -m src.agents.governance.agent --category dsgvo\n"
        ),
    )
    parser.add_argument(
        "--scan-all",
        action="store_true",
        help="Scan all files in the repository",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write JSON + Markdown reports to compliance/",
    )
    parser.add_argument(
        "--category",
        choices=["dsgvo", "eu_ai_act", "security", "multi_tenant", "documentation"],
        help="Scan only a specific category",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=".",
        help="Path to the repository root (default: current directory)",
    )
    args = parser.parse_args()

    if not args.scan_all and not args.category:
        parser.print_help()
        sys.exit(0)

    repo_root = Path(args.repo_root).resolve()
    config = GovernanceConfig.default(repo_root)

    if args.category:
        config.enabled_categories = [args.category]

    report = run_scan(config)
    _print_summary(report)

    if args.report:
        output_dir = repo_root / config.output_dir
        json_path = write_json_report(report, output_dir)
        md_path = write_markdown_report(report, output_dir)
        print(f"📄 JSON-Report: {json_path}")
        print(f"📄 Markdown-Report: {md_path}")

    # Exit with non-zero code if critical findings exist (useful for CI)
    if report.summary.kritisch > 0:
        sys.exit(2)
    elif report.summary.hoch > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
