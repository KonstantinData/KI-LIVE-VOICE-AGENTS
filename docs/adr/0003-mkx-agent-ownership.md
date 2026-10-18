# ADR 0003: Explicit MKX Agent Ownership

## Status

Local content separation approved and implemented on 2026-10-18 following the
structural migration and content inventory. Combined verification passed; see
the [implementation receipt](../AGENT_CLEANUP_IMPLEMENTATION_2026-10-18.md).
Deployment and MIA runtime activation are separate steps.

Follow-up approved on 2026-10-18: relocate Anna's entire source package,
including `calendar`, to `src/agents/mein_kuechenexperte/anna`; update imports
and start assets without changing behavior, public IDs or authority. This
supersedes only the earlier decision to preserve Anna's source location.
Migration verification is separate from the earlier content-cleanup results.

## Context

The inspected `src/agents/lisa` snapshot used KEA-facing prompt text while its
class, constants, imports and summary speaker labels still used Lisa's name.
It also contained obsolete example studio facts behind a knowledge fallback.
These observations establish naming inconsistency, not exclusive functional
ownership. The user clarified that Lisa and MIA responsibilities were mixed in
the reused files. The requested cleanup therefore requires content-level
separation; moving the entire package under KEA did not complete that task.

MKX (Mein Kuechenexperte) owns distinct agents with different responsibilities:

| Agent | Responsibility | Current source |
| --- | --- | --- |
| KEA | Website reception, project intake and secure handoff | `src/agents/mein_kuechenexperte/kea` |
| MIA | Planning assistant for developing and refining kitchen concepts | `docs/mia` requirements; `src/agents/mein_kuechenexperte/mia` offline prompts/builders only, no activated runtime/profile |
| Anna | Telephone assistant | `src/agents/mein_kuechenexperte/anna` including calendar; shared transport in `src/telephony` |

MIA belongs to MKX and is independent of KEA. Anna's existing telephone
implementation also remains independent. A shared tenant does not make one
agent a submodule of another or grant access to its sessions or capabilities.

## Decision

- Move KEA into the explicit tenant package `src/agents/mein_kuechenexperte/kea`.
  Use `KeaAgent`, `build_kea_system_prompt`, `build_kea_voice_prompt` and `KEA_*`.
  Remove the old Lisa package instead of maintaining parallel implementations.
- Preserve the four prompt-section filenames and the current intake behavior.
  Text and voice continue to share KEA's conversation contract.
- Resolve KEA's identity from the existing `kea-project-intake` tenant profile.
  KEA builders reject other tenants, missing profiles and a mismatched prompt
  profile. No MIA profile or runtime is activated by this migration.
- Use registry-backed MKX knowledge. Remove the obsolete Python studio sample:
  its fictitious address, prices, brands and delivery/montage claims conflict
  with the configured independent-consulting knowledge. Missing knowledge
  produces a configuration error rather than reintroducing those sample facts.
- Public WebSocket chat and voice creation require a registered profile.
  Unregistered database studios no longer receive KEA through a legacy fallback.
  Explicit unknown voice agent IDs remain rejected. Ending a legacy conversation
  may close it, but does not invoke KEA's tenant-specific summarizer.
- Separate role-neutral MKX conversation policy and selected business context in
  `src/agents/mein_kuechenexperte/shared`. Keep reception objectives, examples,
  contact authority and deterministic text flow in `kea`. MIA has independent
  planning prompt sections and offline text/voice builders in `mia`; it does not
  import KEA's intake template or inherit Anna's tools. Shared transport/LLM/
  storage mechanics remain in the common runtime.
- Preserve Anna's telephone/calendar behavior; the approved follow-up relocates
  her package as described above. Reconcile
  current MIA requirements while retaining clearly labelled historical drafts
  and immutable acceptance receipts. MIA first uses wish-driven prepared layouts
  with bounded changes in a raster scene for every visitor. Initial dialogue is
  capped at 120 seconds including both speakers, pauses and interaction. Ask no
  room/window/door/connection questions before the draft, including optional
  exceptions; retain unsolicited room data for later. Actual-room adaptation
  follows the visible draft. Keep per-device appliance preferences, no spoken
  recaps and first-concept/refinement before optional contact.
- Keep rendering wait and total first-result timing separate from dialogue.
  Long uninterrupted speech handling and the diagram's 10x10 m scene remain
  unresolved; no audio cut or scene constant is inferred by this cleanup.
- Anna remains an independent MKX agent. Move all prompt, knowledge and calendar
  modules under `src/agents/mein_kuechenexperte/anna`; retain `src/telephony` and
  `deploy/anna` / `deploy/anna-server`. Keep agent/profile IDs, tool/calendar
  grants, endpoints, environment names, service identities and persisted data
  unchanged. KEA/MIA gain no permission through this shared directory. Earlier
  inventory and implementation receipts retain their historical source paths.

## Consequences

Internal Python imports must use the new package. Public KEA agent IDs,
prompt-profile IDs, HTTP paths, webhook contracts and tenant registry data do
not change. No database migration, executable MIA planning engine, registry
activation or deployment is included. Offline MIA builders produce prompt
artifacts; they do not select furniture, generate images, book appointments or
establish agent-bound session/project access.

Full immutable tenant/agent/session/project binding for MIA remains a separate
implementation requirement; a package rename does not provide that isolation.
Historical ADRs, consent versions and negative legacy-name test fixtures retain
their original evidence. Current templates and knowledge instructions use KEA.

## Historical structural-migration validation

- `python -B -m ruff check src tests`: passed.
- `python -B -m pytest -p no:cacheprovider tests/test_core
  tests/test_api/test_kea_text_flow.py tests/test_api/test_kea_chat_identity.py
  tests/test_api/test_runtime_routes.py tests/test_api/test_voice_routes.py
  tests/test_api/test_crm_handoff.py tests/test_api/test_liquisto_assistant.py
  tests/test_api/test_liquisto_navigation_sideband.py tests/test_telephony -q`:
  597 passed; one Starlette/httpx deprecation warning.
- Independent combined-state source review: no blocking findings.
- No live provider calls, browser/telephone acceptance or deployment performed.

The validation above is historical evidence for the structural migration and
tested runtime paths. It predates the approved content separation and is not
its acceptance. Combined-state role/prompt checks and KEA/Anna regression
results must be reported separately; no prior green result proves MIA planning
functionality, live operation or semantic acceptance.

## Approved content-cleanup validation

The final combined state passed Ruff and 630 selected offline tests, including
separate role/context checks and the KEA WebSocket transport with persisted
test messages. Independent source review found no blocking issues. The
implementation receipt records the exact command and limits: no model behavior,
120-second performance, rendering, real call or provider acceptance is claimed.
