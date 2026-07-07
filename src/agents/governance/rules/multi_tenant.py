"""
Governance Rules — Multi-Tenant Isolation
============================================
What:    Verifies that every database query filters by studio_id.
Does:    Scans Python ORM queries for missing studio_id WHERE clauses.
Why:     Without tenant isolation, one studio could read another's data — DSGVO violation.
Who:     agent.py; findings go into GovernanceReport.
Depends: src.agents.governance.{scanner, models, config}, re
"""

from __future__ import annotations

import re

from src.agents.governance.config import GovernanceConfig
from src.agents.governance.models import Category, Finding, Severity
from src.agents.governance.scanner import FileScanner

# SQLAlchemy models that store tenant-owned or tenant-derived data.
_TENANT_MODELS = {
    "Conversation",
    "Event",
    "KnowledgeChunk",
    "Message",
}

_SELECT_PATTERN = r"select\s*\("

# Files/directories where cross-studio queries are intentionally allowed
_ADMIN_PATHS = ["seed.py", "migration", "alembic", "test_", "conftest"]


def check_studio_id_filters(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that all ORM queries in business-logic files filter by studio_id.

    Heuristic: any select() call that does not contain 'studio_id' within
    the next 5 lines is flagged for manual review.

    Args:
        scanner: Initialised FileScanner.
        config: Governance config.
        counter: Mutable counter for finding IDs.

    Returns:
        List of HOCH findings for queries without visible studio_id filter.
    """
    findings: list[Finding] = []

    for path in scanner.find_python_files():
        rel = scanner.rel(path)

        # Skip admin/seed/test files — cross-studio access is intentional there
        if any(x in rel for x in _ADMIN_PATHS):
            continue

        # Only check files in business logic paths
        if not any(rel.startswith(p) for p in ["src/api", "src/agents", "src/core"]):
            continue

        content = scanner.read_file(path)
        if content is None:
            continue

        lines = content.splitlines()
        matches = scanner.grep(path, _SELECT_PATTERN)
        for lineno, _ in matches:
            # Check the surrounding query block. Legitimate statements often span
            # several lines before the tenant filter is added.
            window_end = min(lineno + 20, len(lines))
            window = "\n".join(lines[lineno - 1:window_end])

            selected_tenant_model = any(
                re.search(rf"\b{model}\b", window) for model in _TENANT_MODELS
            )
            if not selected_tenant_model:
                continue

            if "studio_id" not in window:
                counter[0] += 1
                findings.append(Finding(
                    id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                    severity=Severity.HOCH,
                    category=Category.MULTI_TENANT,
                    subcategory="5.1_DATEN_ISOLATION",
                    regulation="Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung",
                    file=rel,
                    line=lineno,
                    finding=(
                        f"DB-Query in Zeile {lineno} ohne erkennbaren studio_id-Filter. "
                        "Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden."
                    ),
                    must_be=(
                        "Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS "
                        ".where(<Model>.studio_id == studio_id) enthalten."
                    ),
                    fix_example=(
                        "# VORHER (VERSTOSS):\n"
                        "result = await session.execute(select(Conversation))\n\n"
                        "# NACHHER (COMPLIANT):\n"
                        "result = await session.execute(\n"
                        "    select(Conversation).where(Conversation.studio_id == studio_id)\n"
                        ")"
                    ),
                    deadline="Vor Go-Live — Datenlecks zwischen Studios verhindern",
                    auto_fixable=False,
                    references=["Art. 5 Abs. 1 lit. b DSGVO", "Art. 32 DSGVO"],
                ))

    # Deduplicate by (file, line) — same query might match multiple patterns
    seen: set[tuple[str, int | None]] = set()
    deduped: list[Finding] = []
    for f in findings:
        key = (f.file or "", f.line)
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    return deduped


def check_knowledge_vector_isolation(
    scanner: FileScanner,
    config: GovernanceConfig,
    counter: list[int],
) -> list[Finding]:
    """
    Check that pgvector similarity searches always include a studio_id filter.

    Returns:
        Findings for vector searches without tenant isolation.
    """
    findings: list[Finding] = []

    knowledge_paths = list((config.repo_root / "src" / "core").rglob("knowledge*.py"))
    for path in knowledge_paths:
        rel = scanner.rel(path)
        content = scanner.read_file(path)
        if content is None:
            continue

        # Look for cosine_distance / l2_distance calls
        if re.search(r"cosine_distance|l2_distance|<->|<#>|<=>", content):
            if "studio_id" not in content:
                counter[0] += 1
                findings.append(Finding(
                    id=f"{config.finding_id_prefix}-2026-{counter[0]:04d}",
                    severity=Severity.KRITISCH,
                    category=Category.MULTI_TENANT,
                    subcategory="5.2_VEKTOR_ISOLATION",
                    regulation="Art. 5 Abs. 1 lit. b DSGVO",
                    file=rel,
                    line=None,
                    finding=(
                        "Vektorsuche in knowledge.py ohne studio_id-Filter. "
                        "Ähnlichkeitssuche könnte Wissensbasis-Einträge anderer Studios liefern."
                    ),
                    must_be=(
                        "Jede Vektorsuche muss studio_id als Pflicht-WHERE-Bedingung haben: "
                        ".where(KnowledgeChunk.studio_id == studio_id)"
                    ),
                    fix_example=(
                        "result = await session.execute(\n"
                        "    select(KnowledgeChunk)\n"
                        "    .where(KnowledgeChunk.studio_id == studio_id)  # PFLICHT\n"
                        "    .order_by(KnowledgeChunk.embedding.cosine_distance(query_vec))\n"
                        "    .limit(5)\n"
                        ")"
                    ),
                    deadline="Sofort — Datenleck zwischen Studios",
                    auto_fixable=False,
                    references=["Art. 5 Abs. 1 lit. b DSGVO"],
                ))

    return findings
