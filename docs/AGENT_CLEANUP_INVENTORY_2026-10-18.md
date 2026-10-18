# MKX agent content inventory and proposed cleanup

Date: 2026-10-18. Active area: mein-kuechenexperte.de / MKX.
Status: inventory completed and cleanup scope approved by the user on 2026-10-18.
The findings/proposal below record the approval baseline. See the separate
[implementation receipt](AGENT_CLEANUP_IMPLEMENTATION_2026-10-18.md) for delivery.

## Scope and evidence baseline

- Working directory: `C:/Users/konst/.codex/worktrees/mia-phase-zero/KI-LIVE-VOICE-AGENTS`.
- Branch: `codex/mia-phase-zero-20261014`.
- HEAD: `c0b1c85bcd0b96cdd3697dd975a1efd22bb679e4`.
- The earlier, uncommitted Lisa-to-KEA migration is part of the inspected working
  tree. It is a structural change, not accepted semantic cleanup.
- Compare the original `HEAD:src/agents/lisa` package with the current
  `src/agents/mein_kuechenexperte/kea` package and its call sites.
- The user's pre-existing edit in `docs/mia/README.md` must be preserved.
- This inventory changes no executable source, registry profile, existing
  document, database or deployment. This report is the only added artifact.

The user identifies Lisa/MIA content reuse as the original problem. Names in
the current snapshot or the absence of a separately named MIA folder cannot
settle the historical ownership of reused prose. The classification below uses
actual tasks, instructions and execution paths. It distinguishes reusable
conversation instructions from a working planning implementation.

## Confirmed agent ownership

| Agent | Tenant | Responsibility | Inspected source |
| --- | --- | --- | --- |
| KEA | MKX | Website reception, service questions, project orientation, upload/contact handoff | `src/agents/mein_kuechenexperte/kea`, `src/api/services/kea_text_flow*.py` |
| MIA | MKX | Planning assistant: wish-driven kitchen concept, bounded refinement, later actual-room adaptation | `docs/mia`, including the latest raster-first requirements and diagram; no separately dispatched planning path was found in the inspected runtime |
| Anna | MKX | Telephone assistance with her own phone profile, knowledge and allowed tools | `src/agents/anna`, `src/telephony`, tenant phone profile |

MIA and Anna are independent of KEA. Sharing MKX ownership does not share agent
authority, visitor session ownership, calendar grants or mutable project state.

## Content inventory of the four original prompt files

References below use their current migrated paths under
`src/agents/mein_kuechenexperte/kea/prompts`.

| File and source | Role-specific material | Reusable material | Required disposition after approval |
| --- | --- | --- | --- |
| `identity.py:3-25` | Reception, project phase, services, consultation/upload/contact; no binding professional planning | Truthful identity and limits | Keep reception identity in KEA. Give MIA an explicit planning-assistant identity. Distinguish an illustrative AI concept from commissioned professional planning. Do not transfer KEA's blanket anti-planning wording into MIA. |
| `conversation_contract.py:5-50` | Guided intake slots and handoff destination | One question, concise channel-appropriate answers, no repetition or invented claims | Split neutral conversation policy from KEA's intake flow. MIA receives a separate wish-to-concept-to-refinement contract. |
| `conversation_contract.py:53-76` | MKX service, pricing and professional-consultation explanation, mixed with KEA's next-question routing | MKX business facts may be relevant to both agents | Keep authoritative business facts in tenant knowledge; leave KEA routing in KEA. MIA must not inherit a contact-first gate or substitute a paid-consultation explanation for the first AI concept. |
| `rules.py:5-42` | Project orientation, documents, contact escalation, closing recap | Uncertainty, no fabricated facts, short answers, protected identifiers | Separate general rules from per-agent objectives. Preserve KEA's handoff behavior; MIA skips repeated spoken summaries and retains structured wishes internally. |
| `rules.py:45-54` | KEA has no local lead/calendar/mail tools; secure widget handoff | Data minimization and purpose-limited handling | Keep tool authority agent-specific. MIA does not inherit Anna's calendar access or gain tools from prompt text. |
| `tonality.py:5-41` | Reception examples, handoff-focused goal, fixed Sie address, KEA name | Warmth, proportionate empathy, concise natural language, no exaggerated promises | Extract only role-neutral style. Keep examples, objective, agent name and address handling explicitly assigned. MIA's planning conversation must not be pulled back to reception on every turn. |

Additional content conflicts to resolve:

- KEA's voice template permits up to two questions (`kea/voice_prompt.py:71`),
  while the shared KEA contract allows one main question
  (`kea/prompts/conversation_contract.py:16`). Use one consistent per-turn rule.
- KEA's text tone fixes Sie (`kea/prompts/tonality.py:5`), whereas voice supports
  an explicit Du/Sie choice (`kea/voice_prompt.py:39-44,77-78`). Make this an
  explicit channel/profile input rather than contradictory shared wording.
- An internal staff summary is distinct from repeatedly reciting the visitor's
  answers. Preserve useful internal context without importing spoken recap
  instructions into MIA.
- `knowledge/chunks.json` mixes MKX business facts with KEA-specific chunks such
  as `project-intake-scope` and `secure-contact-handoff`. Reusing every chunk
  unfiltered would carry reception behavior into MIA. Use an explicit content
  selection, not a second copy of the entire knowledge file.

## Executable behavior outside those four files

| Source | Current behavior | Consequence |
| --- | --- | --- |
| `src/api/websocket/chat_handler.py:108-109,151-158,199-211` | Admitted MKX chat always uses `KeaTextFlow`; the alternative LLM text branch is unreachable under the current gate | Editing only the four prompt sections would not clean up the actual website text conversation. |
| `src/api/services/kea_text_flow.py:25-76` and `kea_text_flow_nodes.py` | Deterministic reception choices, service knowledge, uploads/contact and summary | This is KEA-owned content and should live with KEA, with API code handling transport. |
| `kea/system_prompt.py:19-28,32-73` | Combines tenant knowledge, visitor context and role/style/rule sections | Replace indiscriminate composition with explicit KEA sections and shared role-neutral policy. |
| `kea/voice_prompt.py:90-98,100-131` | Intake job, contact/upload flow, consent handling and a second copy of conversation rules | Give KEA one authoritative contract plus channel-specific voice rules. MIA must not import this intake-oriented voice template. |
| `kea/agent.py:60-67,112-171` | Empty tool registry and conversation finalization with a staff summary | No furniture selection, scene generation or revision engine can be recovered merely by renaming this class. Reused prose may still need separation. |
| `registry/tenants/mein-kuechenexperte/tenant.json:25-40,80-115` | KEA public widget/live-voice profile and independent Anna phone profile | No MIA profile is currently selected by this registry. |

## MIA requirements and conflicting documentation

The latest user-directed flow is recorded in
`docs/mia/PRODUCT_REQUIREMENTS.md:74-80`,
`RASTER_FIRST_WORKSHOP.md:7-18` and `RASTER_FIRST_DRAFT_DE.md:9-35,69-95`:

1. MIA is the planning assistant. Initial discovery covers cooking use, desired
   improvement, atmosphere and must-haves; known answers are not asked again.
2. Initial conversation is at most 120 seconds including both speakers, pauses
   and interaction. Rendering wait and total time to visible result are measured
   separately; neither is a proven runtime performance claim.
3. The first concept uses a neutral raster scene for every visitor. Before the
   first draft MIA asks no questions about room measurements, windows, doors or
   connections, including optional measuring questions. Unsolicited room data
   may be retained for later actual-room adaptation.
4. Wishes select a prepared layout and bounded allowed adjustments. This is not
   arbitrary free CAD planning.
5. Appliance integration is recorded separately per device. Mixed answers are
   valid; a device type does not establish exact width. Retained devices remain
   explicit requirements; unresolved dimensions stay unknown.
6. The visitor sees and can refine the personal concept before optional contact.
   Actual-room adaptation follows the initial visible draft.
7. Natural concise conversation, selective visuals and contextual empathy are
   compatible with internal structured state. Repeated spoken answer recaps are
   not part of MIA's discovery (`CONVERSATION_DESIGN.md:7-19,41-64`).

| Document | Required reconciliation |
| --- | --- |
| `docs/mia/CONVERSATION_DESIGN.md:68-76` | Replace active-looking 150-second/room-feasibility guidance with the latest first-stage requirements. Label the former 2-3-minute approach as historical; do not confuse conversation time with total visible-result time. |
| `docs/mia/PRODUCT_REQUIREMENTS.md:26,68,74-80` | Integrate later corrections into a coherent current specification instead of appending incompatible active-looking rules. |
| `docs/mia/DECISIONS.md:19` | Record the later user-directed raster-first/appliance corrections and distinguish them from team recommendations. |
| `docs/mia/TEST_PLAN.md:39-43` | Separate first raster-scene checks from later measured-room checks; add 120-second, no pre-draft room/measurement questions, no pre-draft contact gate and per-appliance scenarios. |
| `docs/mia/EXPERIENCE_DRAFT_DE.md` | Clearly label the older measured-room-first journey as historical; preserve it as design history. |
| `docs/mia/TASK_BOARD.md`, `README.md` | Align navigation and status with the current requirements, preserving the existing user edit and historical acceptance receipts. |
| `docs/mia/diagrams/FIRST_CONVERSATION.drawio` | Preserve the current adaptive/appliance flow. Treat its 10x10 m scene labels as an unconfirmed design assumption, not an adopted requirement. Its scope ends before generation. |

Two product details remain open and are not silently resolved by cleanup:
handling uninterrupted visitor speech at the 120-second limit, and whether
10x10 m is an intended scene constant. Neither blocks inactive prompt separation;
both need a decision before implementing the corresponding runtime behavior.

## Anna boundary

Anna's independent MKX phone ownership is explicit in
`registry/tenants/mein-kuechenexperte/tenant.json:82-92`,
`src/agents/anna/prompt.py:339-350` and `src/agents/anna/knowledge.py:9-19`.
Her phone data/consent policy differs from the widget: her profile allows voice
contact capture, whereas KEA's widget policy does not. These rules must not be
flattened into a universal common prompt. The cleanup does not relocate Anna's
implementation or change her telephone/calendar behavior.

## Current session boundary: required before MIA activation

`src/db/models/conversation.py:17-27` stores studio, visitor, channel and state,
without a dedicated persisted agent owner. Chat, voice and upload lookup paths
use studio/visitor/conversation identity rather than immutable agent identity
(`chat_handler.py:119-133`, `voice_sessions.py:83-109`,
`project_upload_runtime.py:91-128`). Voice closure chooses the MKX summarizer by
tenant (`voice.py:762-767`). Provider tracing is not persisted session ownership.

Consequently, adding MIA's name/profile to MKX now would not establish safe
coexistence. Explicit agent-bound session lookup, transcript/end, upload,
handoff and browser selection belong to a separate MIA runtime implementation.
Until that work is approved and verified, MIA remains unregistered/inactive.

## Earlier local changes that are more than a rename

The pending working tree already contains these behavior changes:

1. `kea/profile.py:8-18`: MKX/KEA profile checks.
2. `kea/system_prompt.py:19-24`: missing knowledge raises instead of using
   placeholder studio facts/minimal fallback.
3. `voice_sessions.py:53-66,124-130`: missing registry profile disables voice
   creation and removes generic configuration fallbacks.
4. `chat_handler.py:108-109`: missing registry profile rejects chat.
5. `voice.py:762-767`: an unregistered legacy conversation may close but no
   longer invokes KEA's summary generator.
6. `kea/voice_prompt.py:34-38`: supplied display name must match KEA's profile.

Recommendation: retain these explicit tenant/knowledge boundaries as part of the
reviewed cleanup, rather than silently restoring the placeholder or cross-tenant
KEA fallbacks. Their inclusion is part of the approval request, not implicit
acceptance based on the previous rename.

## Proposed implementation after approval

```text
src/agents/mein_kuechenexperte/
  shared/                 # MKX role-neutral style and explicit business context
  kea/
    prompts/              # Reception identity, contract and rules
    text_flow.py          # Moved from api/services
    text_flow_nodes.py    # Moved from api/services
    system_prompt.py
    voice_prompt.py
    agent.py
    profile.py
  mia/
    prompts/              # Separate planning identity, contract, rules and tone
    system_prompt.py      # Offline prompt composition; no endpoint activation
    voice_prompt.py       # Own channel rules; no import of KEA's intake template
```

1. Establish the content ownership map above. Extract only genuinely neutral
   conversation policy and selected MKX business context; keep goals, examples,
   recap policy and tool/contact authority per agent. Anna does not inherit the
   new shared prompt automatically.
2. Clean KEA's four sections and text/voice composition. Keep one consistent
   question/address policy. Move the deterministic flow and its copy into KEA's
   package; update imports/tests. Remove the unreachable alternate WebSocket
   text branch while preserving KEA's supported website behavior.
3. Give MIA her own explicit prompt package and offline builders using the
   existing requirements and relevant reusable conversation content. These are
   prompt artifacts, not a recovered or completed planning engine. Do not add a
   runtime `MiaAgent`, registry activation or pretend generation/booking tools.
   Unsupported outcomes must not be reported as completed.
4. Reconcile the identified documents and annotate unresolved design assumptions.
   Correct completion claims in ADR 0003/package documentation.
5. Verify the combined result and report role separation, runtime state and
   remaining MIA implementation work separately.

## Acceptance for this cleanup

- KEA prompts and deterministic flow express reception/orientation only.
- MIA's own prompt package expresses planning, raster-first discovery and
  refinement, without KEA's blanket anti-planning/contact-first/recap rules.
- MIA asks no pre-draft questions about room measurements, windows, doors or
  connections; optionally volunteered room facts are retained for later only.
- Shared content contains no agent-specific task destination, automatic grant
  or mutable session/project state. Business facts are not copied wholesale
  from KEA's knowledge into MIA.
- Representative prompt-context checks distinguish the two roles, retain
  unknowns and corrections, and preserve the first-concept-before-contact rule.
- Existing KEA chat, voice, handoff, upload and Anna telephone regression suites
  pass; no new MIA entry becomes reachable. Run Ruff and the affected tests.
- Documents distinguish user requirements, recommendations, historical drafts,
  local code and activation. A prompt package is never reported as a working
  kitchen planner.

New scene/rendering/selection engines, project persistence, catalog adoption,
CRM business logic, calendar authority, database migration, frontend planning
surface, paid provider calls and production deployment are not included in this
cleanup proposal. The implementation of a working MIA planner needs its own
concrete scope after the ownership cleanup.

## Inventory verification

- Two independent read-only reviews covered runtime dispatch/session boundaries
  and MIA/Anna requirements respectively; their findings were reconciled against
  the source references above.
- Previous migration evidence: 597 selected tests and Ruff passed before this
  inventory. Those results do not prove semantic ownership or MIA functionality.
- No tests/provider calls were run for this read-only inventory. Hashes of the
  eight inspected KEA implementation/prompt files and the pre-existing user edit
  are unchanged; Git status is unchanged apart from this new report.
- Approval gate: wait for the user's explicit approval of this proposal before
  editing executable source or reconciling existing documents.
