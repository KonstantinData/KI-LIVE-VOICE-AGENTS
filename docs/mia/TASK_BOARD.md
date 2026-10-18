# Task board and dependency plan
Status 2026-10-18: Phase 0 evidence and proposed runtime contracts remain the
baseline. The approved content cleanup separates shared MKX policy, KEA
reception and offline MIA prompt builders; it does not activate MIA or implement
planning/session/rendering engines. The former tentative 2026-10-16 meeting is
historical context, not a current delivery deadline.

Current user requirements take precedence over older rows/timeboxes: max120s
initial dialogue including both speakers/pauses/interaction; no room, window,
door or connection questions before the first raster draft, including optional
exceptions; prepared layouts with bounded changes; separate appliance
preferences; no spoken recap; first concept/refinement before optional contact.
See [current requirements](PRODUCT_REQUIREMENTS.md), [conversation design](CONVERSATION_DESIGN.md)
and [raster-first flow](RASTER_FIRST_DRAFT_DE.md). Rendering wait and total first
result time are measured separately. Long uninterrupted speech and 10x10 m
scene labels remain unresolved, not defaults.

Historical 2026-10-15 workshop: MIA-P04 produced the earlier measured-room-first
draft for discussion. Raster-first supersedes that entry flow. The proposed
generic-furniture demo/separate article sample and catalog dependencies remain
separate scope decisions; content cleanup does not approve catalog adoption.

| ID | Priority / owner | Goal and result | Depends on | Tests / docs | Status / risk |
|---|---|---|---|---|---|
| MIA-P01 | P1 A | approved journey and demo/MVP split | inventory | MIA-01..19; PRD | proposed; timing unmeasured |
| MIA-P04 | P1 coordinator + seven senior product roles | integrated first customer-experience draft and cross-role critique | P01 + current user requirements | TEAM_WORKSHOP_BRIEF, TEAM_WORKSHOP_RESULTS, EXPERIENCE_DRAFT_DE; independent document review | workshop conducted; first draft for user discussion; not a working demo or accepted new implementation scope |
| MIA-P03 | P1 coordinator + A/B/C/F/H | freeze identity/brief/job/catalog/intake DTOs and error states | P01 + specialist reviews | JSON schemas/fixtures + consumer contract tests; INTERFACES | proposed; required before interface implementation |
| MIA-R01 | P1 B + foundation owner | immutable tenant/agent/session/project binding | P01, interface freeze | spoof/switch/isolation/KEA default; architecture/schema | open; release blocker |
| MIA-D01 | P1 D | 12-20 visually verified GL variants, separate XL identity | supplied PDFs | exact page/region/hash + 100% independent subset review | source sampled; full subset not curated |
| MIA-D02 | P1 D/J/H | reuse located catalog core; central neutral service/MIA consumer feasibility | existing core + source classification/grants | lifecycle gates/rights/consumer isolation; ADR | local CARAT DB and exact source hashes verified; no active versions or MIA grant; no relocation authorized |
| MIA-C01 | P1 C | structured brief/version/edit/export | R01,D01 | unknown geometry/conflict/concurrency/5 edits; interfaces | open |
| MIA-E01 | P1 E | isolated explicit entry + concept UI/text path | R01,C01 schemas | mobile/keyboard/instance collision/DE-EN; UX | open; dirty website must be isolated |
| MIA-E02 | P1 E | integrated production-MVP voice/media/upload/resume/contact/booking UI | E01,R02,C02,F02,G02,H01 | complete browser/mobile/a11y + error journey; product copy | open; live provider evidence required |
| MIA-R02 | P1 B | natural voice/text discovery + structured capture | R01,C01 | interruption/PII/fallback/live Realtime; profile docs | open; server observation contract needed |
| MIA-J01 | P1 J/H | local test environment, durable jobs/budgets/flags | job identity/schema | restart/reservation/limits/cancel; ops | proposed; monetary budget absent |
| MIA-C02 | P1 C | real bounded generation + reference edits/private media | C01,J01,approved budget | actual provider benchmark/drift/usage; model decision | not run |
| MIA-F01 | P1 F | current CRM bridge/auth/idempotency | verified receiver | replay/parallel/timeouts/PII; release docs | separate chat active, not completed |
| MIA-F02 | P1 F | MIA plan/media/history + usage projection | F01,C01 schemas | real test CRM receipt/display; interfaces | blocked by F01 contract |
| MIA-G01 | P1 G | approved provider/calendar/test binding | owner decision, R01,F01 | rights/slot/consent; decision | unresolved; Anna/Zeeg not interchangeable |
| MIA-G02 | P1 G | book/recheck/reconcile/change/cancel | G01 + secure contact | concurrent slot/DST/unknown result/live test | open |
| MIA-H01 | P1 H | MIME/quarantine, resume, retention/PII safeguards | R01,C01,J01 | adversarial/ownership/deletion/crossworker | release blockers remain |
| MIA-H02 | P1 H | independent combined-state release security/privacy review | E02,F02,G02,J02,H01 | all negative authorization/PII/secret/log checks; SECURITY_REVIEW | not run; no activation approval |
| MIA-P02 | P2 A/I | pilot metrics/style/function/needs/spatial/satisfaction | working concept/provider | frozen scenarios >=3 runs, real-user pilot | open; no match claims |
| MIA-I01 | P1 I | combined independent integration/KEA/Anna regression | all demo packages | API/browser/provider/phone evidence levels | baseline only |
| MIA-J02 | P1 J | load/alerts/restore/rollback/release manifest | combined system | synthetic restore + kill switch + peak load | not run |
| MIA-I02 | P1 I | acceptance no open P0/P1 + release review | I01,J02,H review | acceptance report and release hash | not accepted |
| MIA-K01 | P2 K | neutral conceptual JSON/brief export | C01 | source/version/unknown fields | proposal |
| MIA-K02 | P3 K | vendor verified CARAT feasibility/import | docs/license/test tenant | actual target import | not verified; not demo dependency |

## Parallel waves
- Phase 0: A; B/runtime; E/F/G website; C/D/K; H/J; independent I ran independently and returned centrally.
- Contract precursor: P03 freezes versioned DTOs/fixtures and responsibilities before shared interfaces are independently implemented.
- Wave 1 after P03: R01 foundation; D01 subset; F01 separate CRM bridge; G01 authority research; A test scenarios. C01 planning/version implementation starts once R01 is available. No shared-file writes.
- Wave 2 after R01 + C01 availability: B prompt/extraction; C job/provider adapter; E concept UI; F CRM projection; H negative tests; J environment/CI. E02 follows its integrated dependencies; H02 reviews the combined release candidate.
- Wave 3: combined integration + independent I; resolve failures with owning agent; rerun affected tests/dependencies.
- Wave 4: real-provider/test CRM/calendar/human evaluation, operational proof and concrete production release authorization.

## Historical demonstrator timebox (not a current commitment)
Day 1: freeze bounded contracts, validate one GL subset, implement text brief + deterministic schematic + version UI with synthetic adapters.
Day 2: voice fallback, five changes, protected form/handoff preview, provider test only after bounded budget, independent rehearsal and failure paths.
Do not promise this schedule as delivery evidence. If real provider/calendar/CRM prerequisites remain absent, disclose demo simulation; production MVP stays open. Neutral catalog extraction should not block one authorized verified subset.
