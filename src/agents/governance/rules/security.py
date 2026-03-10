"""
Governance Rules — Security Checks
=====================================
What:    Detects hardcoded secrets, missing auth, unvalidated input, and PII in logs.
Does:    Scans Python and TypeScript source for security anti-patterns.
Why:     Security failures are DSGVO Art. 32 violations and create KRITISCH risk.
Who:     agent.py; findings go into GovernanceReport.
Depends: src.agents.governance.{scanner, models, config}, re
"""

from __future__ import annotations

import re

from src.agents.governance.config import GovernanceConfig
from src.agents.governance.models import Category, Finding, Severity
from src.agents.governance.scanner import FileScanner

# PII patterns that must not appear in plain-text log statements
_PII_LOG_PATTERNS = [
    (r'log\.\w+\([^)]*email[^)]*\)', "email address"),
    (r'log\.\w+\([^)]*phone[^)]*\)', "phone number"),
    (r'log\.\w+\([^)]*password[^)]*\)', "password"),
    (r'log\.\w+\([^)]*name\s*=\s*[^)]*\)', "customer name"),
]


def check_secrets_in_code(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Scan all source files for hardcoded secrets and API keys.

    Args:
        scanner: Initialised FileScanner.
        config: GovernanceConfig with secret_patterns.
        counter: Mutable counter for finding ID generation.

    Returns:
        List of KRITISCH findings for each detected secret.
    """
    findings: list[Finding] = []

    for pattern in config.secret_patterns:
        for path, lineno, line in scanner.grep_all(pattern, "all", re.IGNORECASE):
            # Skip .env files and test fixtures — those are expected
            rel = scanner.rel(path)
            if any(x in rel for x in [".env", "test_", "conftest", ".example"]):
                continue

            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.KRITISCH,
                category=Category.SECURITY,
                subcategory="4.5_SECRETS_MANAGEMENT",
                regulation="Art. 32 DSGVO — Sicherheit der Verarbeitung",
                file=rel,
                line=lineno,
                finding=(
                    f"Möglicher hardcodierter Secret/API-Key in Zeile {lineno}: "
                    f"{line.strip()[:80]}"
                ),
                must_be=(
                    "Secrets dürfen NIEMALS im Quellcode stehen. "
                    "Alle Secrets müssen in .env gespeichert und über Settings geladen werden. "
                    "Den betroffenen Key sofort rotieren und aus der Git-History entfernen: "
                    "git filter-repo --path <file> --invert-paths"
                ),
                fix_example=(
                    "# VORHER (VERSTOSS):\n"
                    'api_key = "sk-ant-abc123"\n\n'
                    "# NACHHER (COMPLIANT):\n"
                    "from src.api.config import get_settings\n"
                    "api_key = get_settings().anthropic_api_key"
                ),
                deadline="Sofort — Key rotieren und aus Git-History entfernen",
                auto_fixable=False,
                references=["Art. 32 DSGVO", "BDSG § 64"],
            ))

    return findings


def check_pii_in_logs(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that log statements do not emit PII (names, emails, phones) in plain text.

    Args:
        scanner: Initialised FileScanner.
        config: Governance config.
        counter: Mutable counter for finding IDs.

    Returns:
        List of MITTEL findings for PII leakage in logs.
    """
    findings: list[Finding] = []

    for pattern, data_type in _PII_LOG_PATTERNS:
        for path, lineno, line in scanner.grep_all(pattern, "python", re.IGNORECASE):
            rel = scanner.rel(path)
            if "test_" in rel or "conftest" in rel:
                continue
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.MITTEL,
                category=Category.SECURITY,
                subcategory="4.4_LOGGING_MONITORING",
                regulation="Art. 32 DSGVO + Art. 12 EU AI Act",
                file=rel,
                line=lineno,
                finding=(
                    f"Log-Statement könnte {data_type} im Klartext ausgeben: "
                    f"{line.strip()[:80]}"
                ),
                must_be=(
                    "Personenbezogene Daten (Name, E-Mail, Telefon) dürfen NICHT im Klartext "
                    "in Logs erscheinen. Nur IDs und anonymisierte Werte loggen."
                ),
                fix_example=(
                    "# VORHER (VERSTOSS):\n"
                    'log.info("lead.created", email=lead.email)\n\n'
                    "# NACHHER (COMPLIANT):\n"
                    'log.info("lead.created", lead_id=str(lead.id))'
                ),
                deadline="Innerhalb von 30 Tagen beheben",
                auto_fixable=False,
                references=["Art. 32 DSGVO", "Art. 12 EU AI Act"],
            ))

    return findings


def check_input_validation(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that user input is validated and message length is capped.

    Returns:
        Findings for missing input length limits in the chat handler.
    """
    findings: list[Finding] = []

    # Check WebSocket handler for max-length validation
    chat_handler_paths = list(
        (config.repo_root / "src" / "api" / "websocket").rglob("*.py")
    )
    for path in chat_handler_paths:
        rel = scanner.rel(path)
        content = scanner.read_file(path)
        if content is None:
            continue
        # NOTE: We check for any length/size guard — exact pattern may vary
        has_length_check = bool(
            re.search(r"len\s*\(|max.*length|max_length|2000|MAX_", content, re.IGNORECASE)
        )
        if not has_length_check:
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.HOCH,
                category=Category.SECURITY,
                subcategory="4.3_INPUT_VALIDATION",
                regulation="Art. 32 DSGVO + OWASP Top 10 A03",
                file=rel,
                line=None,
                finding=(
                    "Keine erkennbare Längenbegrenzung für User-Input im Chat-Handler. "
                    "Unbegrenzte Eingaben ermöglichen Prompt-Injection und DoS."
                ),
                must_be=(
                    "Maximale Nachrichtenlänge von 2.000 Zeichen erzwingen. "
                    "User-Input in <user_message> Tags wrappen für Prompt-Isolation."
                ),
                fix_example=(
                    "MAX_MESSAGE_LENGTH = 2000\n\n"
                    "if len(user_message) > MAX_MESSAGE_LENGTH:\n"
                    "    await websocket.send_json({'type': 'error', "
                    "'message': 'Nachricht zu lang'})\n"
                    "    return\n\n"
                    "# Wrap user input to prevent prompt injection\n"
                    'safe_input = f"<user_message>{user_message}</user_message>"'
                ),
                deadline="Vor Go-Live beheben",
                auto_fixable=False,
                references=["Art. 32 DSGVO", "OWASP A03:2021"],
            ))

    return findings
