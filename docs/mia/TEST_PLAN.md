# Independent test and acceptance plan
QA I is independent of implementers and reports directly to coordinator. A package is accepted only after combined-state tests, security/docs review and coordinator confirmation.

Current requirements were reconciled on 2026-10-18. Offline MIA prompt checks
can verify role/wording separation only; the product acceptance below remains
open until corresponding runtime behavior is implemented and demonstrated.

## Evidence levels
1. Static/DTO/schema checks.
2. Offline fake-provider tests and isolated test database.
3. Local integrated browser/failure/restart tests.
4. Real authorized image/Realtime/CRM/calendar tests with synthetic participants.
5. Real mobile/keyboard/screen reader/phone regressions.
6. Human kitchen-planning and customer perceived-match assessment.
Mock evidence never closes a higher-level real system gate.

Every result records requirement IDs, runtime+website+catalog SHAs/versions, environment, fixture, actor/tenant/agent, expected/observed, command/artifact, tester/date and PASS/FAIL/BLOCKED/NOT RUN.

## Acceptance matrix
| Requirements | Required tests |
|---|---|
| MIA-01,14,16 | all-transport profile selection; unknown/disabled/foreign/Anna denied; same visitor KEA/MIA separation; mid-session spoof; actual KEA/Anna regression |
| MIA-02,03,04 | live voice interruption/corrections, microphone refusal text continuation; extraction provenance/unknown/conflicts; no spoken answer recap or repeated answered question; contextual empathy/humor and conditional visual aids; no room/window/door/connection question before first draft, including optional exceptions; unsolicited room data retained for later; separate mixed appliance preferences and unknown widths |
| MIA-05,06 | real first-image and five edits; immutable snapshots, optimistic conflicts, requested-change fulfilment and unrelated visual drift review |
| MIA-07,14 | malformed/polyglot/upload decode/page/pixel limits/quarantine; tenant/agent quota races; signed media expiry; PII/injection |
| MIA-08 | token theft/foreign project/expiry/revocation/restart/mobile cookie behavior; IDs alone denied |
| MIA-09,10 | first personalized concept/refinement without postcode/contact; no lead gate or stock-picture substitute; declined contact consent no PII; protected form never spoken; sequential/20-way replay one receipt/record/mail intent; payload mismatch conflict; correct CRM UI; email sent/verified only on separate authoritative evidence |
| MIA-11,12 | actual test calendar; consent bound to exact slot; concurrent booking; DST; timeout-after-write reconcile; provider success/mail failure; change/cancel authority |
| MIA-12,15 | restart during provider job/outbox, cancelled run, ambiguous paid outcome, durable quotas and zero automatic duplicate dispatch |
| MIA-13 | desktop + actual smartphone; 320 CSS px/keyboard/zoom/reflow/screen-reader focus/labels/reduced motion |
| MIA-15,19 | crossworker quota stress, spend reconciliation, 30min load/alerts, MIA kill switch with KEA/Anna intact, synthetic restore/rollback |
| MIA-17 | neutral export schema/source/version/unknowns; CARAT import explicitly NOT RUN absent vendor test |
| MIA-18 | frozen scenarios >=3 technical runs, objective dimensions separate from real customer rating |

Catalog subset must be independently 100% checked against page/table-region evidence. Include GL/XL mismatch, invalid width/front, unknown dimension and discontinued choice. No catalog count is semantic readiness proof.

## Hypothesis evaluation
Freeze the 12 synthetic product scenarios in PRD before comparing models. Capture configuration, prompts, input hashes, accepted brief, output/version, durations, attempts, usage/cost and errors. Run each scenario >=3 times, retain failures/variability rather than selecting best image.
Separate:
- Style: blinded 0-4 material/color/style rating.
- Function: weighted predeclared priorities, satisfied/partial/absent/unknown.
- Explicit wishes: must-have/must-avoid checklist; forbidden product/needs violation is hard failure.
- First raster scene: coherent furniture sizes, bounded layout selection and genuine functional/wish fidelity; scene extent is presentation data, not inferred customer geometry. Every visitor takes this first path without a measurement/contact gate.
- Later actual-room adaptation: independent planner checks supplied geometry, doors, circulation and collisions; unknown facts remain unevaluable. Do not require these measurements before the first draft or claim actual-room fit from raster-scene checks.
- Subjective satisfaction: actual participants' 0-100 perceived match and 5-point satisfaction, reasons.
Do not average unrelated metrics into “78% match”. Report first/final concept, median/distribution, fraction >=70, sample/denominator and missing outputs. Human sample and thresholds must be approved before pilot.

Timing: measure the at-most-120-second initial dialogue including both speakers,
pauses and interaction, rendering wait and full start-to-first-visible-personal
furnished-result interval separately. Report p50/p95, failures and voice/text
differences; a phase label must not hide continued discovery or an unlimited
render wait. The older 2-3-minute total-result hypothesis is historical guidance,
not the current dialogue limit or an achieved result. No spoken summary is a
prerequisite. Timing and 70-80% match remain unproven. Long uninterrupted speech
and the diagram's 10x10 m scene need explicit decisions before corresponding
runtime tests can be frozen; do not invent a hard audio cutoff or scene constant.

Workshop discussion demonstrator: the proposed model-based furnished 3D path can demonstrate geometry/plan/unit-list consistency and functional revisions without a photorealistic provider. This does not close later real-provider/voice acceptance gates. The generic furniture path and separate source-verified article sample remain scope recommendations for user discussion; see TEAM_WORKSHOP_RESULTS.md.

## Existing commands
R: python -m ruff check src tests; python -m pytest tests -q; pnpm --filter ki-team-widget lint; pnpm --filter ki-team-widget build.
W: Python CRM API tests; Node CRM isolation/PDF; selected PHP security/CRM; DE/EN parity; local website security/schema/head/offer checks.
Avoid W qa:deploy-ready in the original dirty checkout without review: it includes sitemap generation. No live route writes/bookings/emails/provider spend during baseline.

MIA CI must add runtime/widget/CRM and browser acceptance gates; existing narrow runtime CI and website PHP CI do not cover the combined journey.
