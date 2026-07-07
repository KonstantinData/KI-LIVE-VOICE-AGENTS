"""
Governance Rules — DSGVO (GDPR) Checks
=========================================
What:    Checks for DSGVO compliance: consent, retention, GDPR endpoints, data minimisation.
Does:    Scans Python routes + TypeScript widget for consent mechanisms, deletion endpoints, etc.
Why:     DSGVO violations carry fines up to 20M EUR or 4% of global annual turnover.
Who:     agent.py; findings go into GovernanceReport.
Depends: src.agents.governance.{scanner, models, config}, re
"""

from __future__ import annotations

import re

from src.agents.governance.config import GovernanceConfig
from src.agents.governance.models import Category, Finding, Severity
from src.agents.governance.scanner import FileScanner


def check_gdpr_endpoints(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that GDPR data-subject rights endpoints exist (Art. 15-22 DSGVO).

    Looks for /gdpr/export and /gdpr/delete routes in the routes directory.

    Returns:
        Findings for missing endpoints.
    """
    findings: list[Finding] = []
    routes_dir = config.repo_root / "src" / "api" / "routes"

    all_route_content = ""
    for path in routes_dir.rglob("*.py"):
        content = scanner.read_file(path)
        if content:
            all_route_content += content

    checks = [
        (
            r"gdpr.*export|export.*gdpr|data.*export",
            "GET /gdpr/export",
            "Art. 15 + Art. 20 DSGVO — Auskunft + Datenportabilität",
            "Endpoint fehlt: Kunden können ihre Daten nicht abrufen (Art. 15/20 DSGVO).",
        ),
        (
            r"gdpr.*delete|delete.*gdpr|data.*delete|right.*erasure",
            "DELETE /gdpr/delete",
            "Art. 17 DSGVO — Recht auf Löschung",
            "Endpoint fehlt: Kunden können ihre Daten nicht löschen lassen (Art. 17 DSGVO).",
        ),
    ]

    for pattern, endpoint_name, regulation, finding_text in checks:
        if not re.search(pattern, all_route_content, re.IGNORECASE):
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.KRITISCH,
                category=Category.DSGVO,
                subcategory="1.4_RECHTE_DER_BETROFFENEN",
                regulation=regulation,
                file="src/api/routes/",
                line=None,
                finding=finding_text,
                must_be=(
                    f"Implementiere {endpoint_name} mit vollständiger Funktion: "
                    "Datenexport als JSON über Runtime-Daten (conversations, messages, "
                    "upload metadata, events) gefiltert nach visitor_id. "
                    "CRM-Daten müssen im externen CRM-Repository behandelt werden."
                ),
                fix_example=(
                    "@router.get('/gdpr/export')\n"
                    "async def gdpr_export(visitor_id: str, session=Depends(get_session)):\n"
                    "    # Load runtime data for this visitor\n"
                    "    return {'conversations': [...], 'messages': [...], 'uploads': [...]}\n\n"
                    "@router.delete('/gdpr/delete')\n"
                    "async def gdpr_delete(visitor_id: str, session=Depends(get_session)):\n"
                    "    # Delete or anonymise runtime data; CRM erasure is external\n"
                    "    await anonymise_runtime_visitor(visitor_id, session)"
                ),
                deadline="Vor Go-Live — Betroffenenrechte müssen implementiert sein",
                auto_fixable=False,
                references=[regulation],
            ))

    return findings


def check_consent_mechanism(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that the widget implements a consent dialog before starting the chat.

    Returns:
        Findings for missing consent in TypeScript widget code.
    """
    findings: list[Finding] = []
    widget_src = config.repo_root / "frontends" / "widget" / "src"

    if not widget_src.exists():
        return findings

    all_widget_content = ""
    for path in widget_src.rglob("*.tsx"):
        content = scanner.read_file(path)
        if content:
            all_widget_content += content
    for path in widget_src.rglob("*.ts"):
        content = scanner.read_file(path)
        if content:
            all_widget_content += content

    has_consent = bool(re.search(
        r"consent|datenschutz|einwilligung|privacy|gdpr",
        all_widget_content, re.IGNORECASE
    ))
    has_ws_guard = bool(re.search(
        r"consentGiven|consent_given|isConsented|hasConsent",
        all_widget_content, re.IGNORECASE
    ))

    if not has_consent:
        counter[0] += 1
        findings.append(Finding(
            id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
            severity=Severity.KRITISCH,
            category=Category.DSGVO,
            subcategory="1.5_EINWILLIGUNG",
            regulation="Art. 6 Abs. 1 + Art. 7 DSGVO + TTDSG § 25",
            file="frontends/widget/src/",
            line=None,
            finding=(
                "Das Widget enthält keinen erkennbaren Consent-Mechanismus. "
                "Der Chat darf erst nach expliziter Einwilligung gestartet werden."
            ),
            must_be=(
                "Vor dem ersten Chat-Start muss ein Consent-Banner erscheinen mit: "
                "(1) Hinweis auf KI-Verarbeitung, "
                "(2) Welche Daten erhoben werden, "
                "(3) Speicherdauer, "
                "(4) Widerrufsrecht, "
                "(5) Link zur Datenschutzerklärung. "
                "Der WebSocket-Connect darf NUR nach Zustimmung erfolgen."
            ),
            fix_example=(
                "const [consentGiven, setConsentGiven] = useState(false);\n\n"
                "// Block WebSocket until consent\n"
                "useEffect(() => {\n"
                "  if (consentGiven) connectWebSocket();\n"
                "}, [consentGiven]);\n\n"
                "if (!consentGiven) return <ConsentBanner onAccept={() => setConsentGiven(true)} />;"
            ),
            deadline="Sofort — Muss VOR Go-Live implementiert sein",
            auto_fixable=False,
            references=["Art. 6 DSGVO", "Art. 7 DSGVO", "TTDSG § 25"],
        ))
    elif not has_ws_guard:
        counter[0] += 1
        findings.append(Finding(
            id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
            severity=Severity.HOCH,
            category=Category.DSGVO,
            subcategory="1.5_EINWILLIGUNG",
            regulation="Art. 7 DSGVO",
            file="frontends/widget/src/",
            line=None,
            finding=(
                "Consent-Text vorhanden, aber WebSocket-Connect-Guard fehlt. "
                "Consent muss die WS-Verbindung tatsächlich blockieren."
            ),
            must_be="WebSocket-Verbindung muss durch consentGiven-State blockiert sein.",
            fix_example=(
                "useEffect(() => {\n"
                "  if (consentGiven) connectWebSocket();\n"
                "}, [consentGiven]);"
            ),
            deadline="Vor Go-Live beheben",
            auto_fixable=False,
            references=["Art. 7 DSGVO"],
        ))

    return findings


def check_retention_policy(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that a data retention / deletion mechanism exists in the codebase.

    Returns:
        Findings if no retention policy or scheduler job is found.
    """
    findings: list[Finding] = []

    # Check for retention-related code in scheduler or services
    scheduler_paths = list((config.repo_root / "src").rglob("scheduler*.py"))
    service_paths = list((config.repo_root / "src").rglob("retention*.py"))
    all_paths = scheduler_paths + service_paths

    has_retention = False
    for path in all_paths:
        content = scanner.read_file(path)
        if content and re.search(
            r"delete|retention|expire|cleanup|purge|anonymis",
            content, re.IGNORECASE
        ):
            has_retention = True
            break

    if not has_retention:
        counter[0] += 1
        findings.append(Finding(
            id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
            severity=Severity.HOCH,
            category=Category.DSGVO,
            subcategory="1.3_SPEICHERBEGRENZUNG",
            regulation="Art. 5 Abs. 1 lit. e DSGVO",
            file="src/api/services/scheduler.py",
            line=None,
            finding=(
                "Kein Retention/Lösch-Mechanismus im Scheduler gefunden. "
                "Personenbezogene Daten werden unbegrenzt gespeichert."
            ),
            must_be=(
                "Implementiere automatische Lösch-Jobs im Scheduler:\n"
                "- Konversations-Rohdaten: nach Runtime-Retention löschen\n"
                "- Upload-Dateien: nach Runtime-Retention löschen\n"
                "- Events/Audit-Trail: nach Audit-Retention archivieren/löschen\n"
                "- CRM-Leads/Kontakte: im externen CRM-Repository behandeln"
            ),
            fix_example=(
                "@scheduler.scheduled_job('cron', hour=2)\n"
                "async def run_retention_cleanup():\n"
                "    cutoff = datetime.now(UTC) - timedelta(days=180)\n"
                "    await delete_old_conversations(cutoff)\n"
                "    await delete_expired_upload_files(cutoff)"
            ),
            deadline="Vor Go-Live implementieren",
            auto_fixable=False,
            references=["Art. 5 Abs. 1 lit. e DSGVO"],
        ))

    return findings


def check_cookie_consent(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check how visitor_id is generated — session-only vs persistent cookie.

    Returns:
        Finding if visitor_id appears to be stored as a persistent cookie.
    """
    findings: list[Finding] = []
    widget_src = config.repo_root / "frontends" / "widget" / "src"

    if not widget_src.exists():
        return findings

    for path in widget_src.rglob("*.ts*"):
        rel = scanner.rel(path)
        for lineno, line in scanner.grep(path, r"localStorage|cookie.*visitor|visitor.*cookie"):
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.HOCH,
                category=Category.DSGVO,
                subcategory="6.1_COOKIE_CONSENT",
                regulation="TTDSG § 25 + Art. 6 DSGVO",
                file=rel,
                line=lineno,
                finding=(
                    f"visitor_id wird möglicherweise als persistentes Cookie/localStorage gespeichert "
                    f"(Zeile {lineno}). Das erfordert eine explizite Cookie-Einwilligung."
                ),
                must_be=(
                    "visitor_id entweder als Session-Only (kein Cookie) generieren "
                    "ODER explizite Cookie-Einwilligung einholen bevor localStorage genutzt wird."
                ),
                fix_example=(
                    "// Session-Only (kein Cookie, kein Consent nötig):\n"
                    "const visitorId = crypto.randomUUID(); // Nur im RAM\n\n"
                    "// ODER mit Consent:\n"
                    "if (cookieConsentGiven) localStorage.setItem('visitor_id', id);"
                ),
                deadline="Vor Go-Live — TTDSG-Verstoß vermeiden",
                auto_fixable=False,
                references=["TTDSG § 25", "Art. 6 Abs. 1 DSGVO"],
            ))

    return findings
