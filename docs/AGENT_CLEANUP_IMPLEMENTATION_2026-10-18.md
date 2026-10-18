# MKX content cleanup implementation receipt

Date: 2026-10-18. Active area: mein-kuechenexperte.de / MKX.
State: approved cleanup implemented and verified locally; uncommitted, not deployed.
Approval baseline: [inventory and proposed scope](AGENT_CLEANUP_INVENTORY_2026-10-18.md).
Architecture: [ADR 0003](adr/0003-mkx-agent-ownership.md).

## Delivered ownership

| Package | Content and behavior |
| --- | --- |
| `src/agents/mein_kuechenexperte/shared` | Role-neutral conversation style and an explicit allowlist of ten MKX business-knowledge chunks. New/agent-specific chunks are not automatically shared. No tool grants or session state. |
| `src/agents/mein_kuechenexperte/kea` | Website reception identity, contract, limits and tone; one text/voice role composition; own moved deterministic text flow and nodes; staff summary. |
| `src/agents/mein_kuechenexperte/mia` | Independent planning identity, conversation contract, limits and tone; offline text/voice prompt composition only. No `MiaAgent`, public endpoint, profile activation or planner engine. |
| Existing `src/agents/anna` and `src/telephony` | Independent MKX telephone implementation, unchanged. |

KEA's intake, secure-contact and KEA-specific values chunks are excluded from
MIA's business context. Shared conversation policy does not assign a handoff,
planning job or calendar authority. Pricing/service facts come from curated
tenant knowledge rather than duplicated offer text in prompt/API modules.

KEA text and voice now share the reception contract and a single-question rule.
Explicit Du/Sie input also selects matching quoted voice examples. MIA has its
own contract and channel rules; her concept label follows the selected address.

MIA's offline instructions express raster-first discovery for every visitor,
at most 120 seconds initial conversation, no pre-draft room/window/door/
connection questioning, prepared layouts with bounded changes, separate device
integration preferences and unknown widths, and first visible concept/refinement
before optional contact. They preserve structured unknowns/corrections without
treating supplied context as action authority or a success receipt.

The current MIA documents were reconciled with those requirements. Older
measured-room-first drafts are explicitly historical. Dialogue duration,
render wait and total visible-result duration are distinct. The diagram's
10x10 m scene and uninterrupted long-speech handling remain unresolved.

## Runtime changes

- KEA's deterministic text flow and nodes moved from API services into its own
  package. The transport calls that flow directly; unreachable alternate LLM
  message/finalization branches were removed. Independent AST comparison found
  the moved flow executable bodies unchanged apart from imports/docstrings.
- API voice configuration selects the profile and calls the KEA builder rather
  than duplicating role/domain/offer prompt text.
- The approved prior tenant/profile checks and missing-knowledge errors remain.
  The obsolete example studio facts and legacy cross-tenant KEA fallback remain
  removed. Public HTTP paths, registry IDs and webhook contracts are unchanged.

## Verification

Interpreter: `D:/Git-GitHub/Repositories/condata/KI-LIVE-VOICE-AGENTS/venv/Scripts/python.exe`.
Working directory: the `mia-phase-zero` worktree. All checks are offline.

```text
python -B -m ruff check src tests
python -B -m pytest -p no:cacheprovider tests/test_core tests/test_api/test_kea_text_flow.py tests/test_api/test_kea_chat_identity.py tests/test_api/test_runtime_routes.py tests/test_api/test_voice_routes.py tests/test_api/test_crm_handoff.py tests/test_api/test_upload_routes.py tests/test_api/test_upload_validation_retention.py tests/test_api/test_liquisto_assistant.py tests/test_api/test_liquisto_navigation_sideband.py tests/test_telephony -q
```

- Ruff: passed.
- Selected combined tests: **630 passed**, one Starlette/httpx deprecation warning.
- Independent combined-state source review: no blocking findings.
- KEA WebSocket regression exercises the moved flow, response serialization,
  actual SQLite test messages and closure without an LLM call.
- Tests cover role/context separation, explicit knowledge selection, unknown
  and corrected device data, address/channel consistency and unavailable MIA.
- Anna/telephony, tenant registry, source knowledge JSON, database/schema,
  frontend, historical MIA acceptance report and drawio diagram are unchanged.
  Registry content was also checked by SHA-256 against the approval baseline.
- The exact pre-existing user-edited inventory line in `docs/mia/README.md` was
  preserved while reconciling the surrounding documentation.

## Limits and remaining work

Prompt composition tests establish supplied content and routing, not actual
model behavior. No claim is made for measured timing, natural conversation,
furniture selection, rendering, refinement execution, room fit or live operation.
No paid provider call, real telephone/browser acceptance, migration, commit,
push or deployment was performed.

A working MIA planner still requires its own approved implementation: immutable
agent/session/project ownership, planning state and prepared layouts, actual
rendering/refinement, protected uploads/media, browser entry, purpose-specific
handoff/calendar authority and end-to-end acceptance. Adding this prompt package
does not activate those capabilities or inherit Anna's permissions.
