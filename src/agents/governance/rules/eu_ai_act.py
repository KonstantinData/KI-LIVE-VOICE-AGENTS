"""
Governance Rules — EU AI Act Checks
======================================
What:    Checks for EU AI Act compliance: AI disclosure, human oversight, risk classification.
Does:    Scans system prompts, widget code, and config for transparency and oversight mechanisms.
Why:     EU AI Act Art. 50 (transparency) and Art. 14 (human oversight) apply from Aug 2026.
Who:     agent.py; findings go into GovernanceReport.
Depends: src.agents.governance.{scanner, models, config}, re
"""

from __future__ import annotations

import re

from src.agents.governance.config import GovernanceConfig
from src.agents.governance.models import Category, Finding, Severity
from src.agents.governance.scanner import FileScanner


def check_ai_disclosure(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that Lisa explicitly identifies itself as AI in the system prompt and widget.

    EU AI Act Art. 50 requires that users are informed they are interacting with AI
    before or at the start of the interaction.

    Returns:
        Findings if AI identity is not clearly disclosed.
    """
    findings: list[Finding] = []

    # Check identity prompt
    identity_paths = list(
        (config.repo_root / "src" / "agents").rglob("identity.py")
    )
    for path in identity_paths:
        rel = scanner.rel(path)
        content = scanner.read_file(path)
        if content is None:
            continue
        has_ai_disclosure = bool(re.search(
            r"KI|KI-Assistent|Künstliche Intelligenz|AI|artificial intelligence|ich bin.*KI|"
            r"KI-Mitarbeiter|digitale.*Assistentin",
            content, re.IGNORECASE
        ))
        if not has_ai_disclosure:
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.HOCH,
                category=Category.EU_AI_ACT,
                subcategory="2.1_KI_OFFENLEGUNG",
                regulation="Art. 50 Abs. 1 EU AI Act",
                file=rel,
                line=None,
                finding=(
                    "System-Prompt enthält keine klare KI-Offenlegung. "
                    "Nutzer müssen BEVOR sie chatten wissen, dass sie mit einer KI sprechen."
                ),
                must_be=(
                    "Die erste Antwort von Lisa muss klar machen, dass es sich um eine KI handelt. "
                    'Beispiel: "Ich bin Lisa, die KI-Assistentin von [Studio]. '
                    'Ich bin ein automatisiertes System, kein Mensch."'
                ),
                fix_example=(
                    'LISA_IDENTITY = """\n'
                    "Du bist Lisa, die KI-Assistentin von {studio_name}.\n"
                    "WICHTIG: Du bist eine Künstliche Intelligenz (KI), kein Mensch.\n"
                    "Weise dich in deiner ersten Antwort als KI-Assistentin aus.\n"
                    '"""'
                ),
                deadline="Vor Go-Live — Pflicht ab 02.08.2026",
                auto_fixable=False,
                references=["Art. 50 Abs. 1 EU AI Act"],
            ))

    # Check widget for AI disclosure in UI
    widget_src = config.repo_root / "frontends" / "widget" / "src"
    if widget_src.exists():
        all_widget = ""
        for p in widget_src.rglob("*.tsx"):
            c = scanner.read_file(p)
            if c:
                all_widget += c

        if all_widget and not re.search(
            r"KI|Künstlich|AI|Assistent|Bot", all_widget, re.IGNORECASE
        ):
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.MITTEL,
                category=Category.EU_AI_ACT,
                subcategory="2.1_KI_OFFENLEGUNG",
                regulation="Art. 50 Abs. 1 EU AI Act",
                file="frontends/widget/src/",
                line=None,
                finding=(
                    "Widget-UI enthält keinen erkennbaren Hinweis auf KI-Natur des Chat-Partners."
                ),
                must_be=(
                    "Widget-Header oder Consent-Banner muss 'KI-Assistent' oder 'AI' enthalten. "
                    "Nutzer müssen vor dem ersten Senden wissen, dass sie mit einer KI chatten."
                ),
                fix_example="<header>Lisa — KI-Assistentin von {studioName}</header>",
                deadline="Vor Go-Live",
                auto_fixable=False,
                references=["Art. 50 Abs. 1 EU AI Act"],
            ))

    return findings


def check_human_oversight(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check for human oversight mechanisms: kill-switch, autonomy levels, escalation.

    Art. 14 EU AI Act requires that humans can intervene, override, and shut down the AI.

    Returns:
        Findings for missing oversight mechanisms.
    """
    findings: list[Finding] = []

    # Check Studio model for is_active / kill-switch
    studio_model_path = config.repo_root / "src" / "db" / "models" / "studio.py"
    if studio_model_path.exists():
        content = scanner.read_file(studio_model_path)
        if content and "is_active" not in content:
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.HOCH,
                category=Category.EU_AI_ACT,
                subcategory="2.4_MENSCHLICHE_AUFSICHT",
                regulation="Art. 14 EU AI Act — Human Oversight",
                file=scanner.rel(studio_model_path),
                line=None,
                finding=(
                    "Studio-Model hat kein is_active-Flag. "
                    "Es gibt keinen Kill-Switch um Lisa für ein Studio sofort zu deaktivieren."
                ),
                must_be=(
                    "Studio-Model braucht: is_active: bool = True. "
                    "Der WebSocket-Handler muss prüfen: if not studio.is_active: reject connection."
                ),
                fix_example=(
                    "# In src/db/models/studio.py:\n"
                    "is_active: Mapped[bool] = mapped_column(Boolean, default=True)\n\n"
                    "# In chat_handler.py:\n"
                    "if not studio.is_active:\n"
                    '    await websocket.send_json({"type": "error", '
                    '"message": "Service vorübergehend nicht verfügbar"})\n'
                    "    await websocket.close()\n"
                    "    return"
                ),
                deadline="Vor Go-Live — Pflicht ab 02.08.2026",
                auto_fixable=False,
                references=["Art. 14 EU AI Act"],
            ))

    # Check FollowUp model for autonomy_level (manual/auto)
    followup_model_path = config.repo_root / "src" / "db" / "models" / "followup.py"
    if followup_model_path.exists():
        content = scanner.read_file(followup_model_path)
        if content and "autonomy_level" not in content:
            counter[0] += 1
            findings.append(Finding(
                id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                severity=Severity.MITTEL,
                category=Category.EU_AI_ACT,
                subcategory="2.4_MENSCHLICHE_AUFSICHT",
                regulation="Art. 14 EU AI Act",
                file=scanner.rel(followup_model_path),
                line=None,
                finding=(
                    "FollowUp-Model hat kein autonomy_level-Feld. "
                    "Ohne Autonomie-Stufen können automatisierte Aktionen nicht von "
                    "manuell freigegebenen unterschieden werden."
                ),
                must_be=(
                    "autonomy_level: Mapped[str] — Werte: 'manual', 'suggested', 'auto'. "
                    "Nur 'auto'-Aktionen dürfen ohne Human-Freigabe ausgeführt werden."
                ),
                fix_example=(
                    'autonomy_level: Mapped[str] = mapped_column(\n'
                    '    String(50), default="manual", nullable=False\n'
                    ")"
                ),
                deadline="Innerhalb von 30 Tagen",
                auto_fixable=False,
                references=["Art. 14 EU AI Act"],
            ))

    return findings


def check_score_bias(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that the lead scoring algorithm does not use discriminatory inputs (name, language).

    Art. 5 EU AI Act forbids AI that exploits vulnerabilities of persons. Discriminatory
    scoring based on name origin or language is a potential EU AI Act + DSGVO Art. 22 issue.

    Returns:
        Findings if name or language fields are used as scoring inputs.
    """
    findings: list[Finding] = []

    extract_tool_paths = list(
        (config.repo_root / "src" / "agents").rglob("extract_lead_data.py")
    )
    for path in extract_tool_paths:
        rel = scanner.rel(path)
        content = scanner.read_file(path)
        if content is None:
            continue

        # NOTE: Scoring should only be based on objective criteria (budget, timeline, style)
        # NOT on subjective/demographic fields (name, language, origin)
        score_func_match = re.search(
            r"def _calculate_score.*?(?=\ndef |\nclass |\Z)",
            content, re.DOTALL
        )
        if score_func_match:
            score_code = score_func_match.group(0)
            # Check if name is used as scoring input (it should only be used for identification)
            if re.search(r'score.*name|name.*score|"name".*\+|name.*points', score_code):
                counter[0] += 1
                findings.append(Finding(
                    id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                    severity=Severity.HOCH,
                    category=Category.EU_AI_ACT,
                    subcategory="3.4_BIAS_FAIRNESS",
                    regulation="Art. 5 EU AI Act + Art. 22 DSGVO",
                    file=rel,
                    line=None,
                    finding=(
                        "Lead-Score-Berechnung verwendet möglicherweise den Namen als Input. "
                        "Scoring nach demographischen Merkmalen ist diskriminierend."
                    ),
                    must_be=(
                        "Score nur nach sachlichen Kriterien: Budget, Zeitrahmen, Küchenstil, "
                        "Raumgröße, Konkretheit der Anfrage. "
                        "NICHT nach: Name, Sprache, Herkunft, Adresse."
                    ),
                    fix_example=(
                        "# COMPLIANT score factors:\n"
                        "# budget_range: +20, timeline: +15, kitchen_style: +10\n"
                        "# room_size: +5, email: +20, phone: +15\n"
                        "# NOT: name origin, language detected, address"
                    ),
                    deadline="Vor Go-Live",
                    auto_fixable=False,
                    references=["Art. 5 EU AI Act", "Art. 22 DSGVO"],
                ))

    return findings
