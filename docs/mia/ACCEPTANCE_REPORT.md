# Acceptance report
Date: 2026-10-14. Scope: Phase 0 reconnaissance and planning. Independent QA accepted the 12 planning documents after correction. MIA implementation, demonstrator, MVP and production are NOT ACCEPTED.

## Executed independent baseline
| Environment / revision | Check | Result |
|---|---|---|
| Clean C 19d86e517c03896b55795a515a7492b6ded33aa0 | selected tenant/KEA/runtime/voice/handoff/upload/Anna/calendar offline suites | 250 passed, one Starlette/httpx deprecation warning |
| Clean C 9c280f309a6e09a65ac1bc0fa98435d802707069 | affected tenant registry subset rerun after main advanced | 6 passed; previous 250 stays attributed to older SHA |
| W b22427b dirty checkout, selected unchanged CRM source | Python CRM API template | 8 passed |
| W same, selected unchanged CRM source | Node isolation/PDF, visual outputs disabled | 15 passed |
| W same, dirty critical.css involved | cookie contract | 5 passed, contaminated baseline |
| W same | selected PHP contact/upload/derivation/dashboard/detail/usage/Anna | 45 tests, 160 assertions, 1 existing failure |

PHP failure: CrmAiUsageTest.php:95 fixes occurred_at to 2026-07-07; ai_usage_repository.php:147 filters using actual now minus30days. Expected2, observed0 at test line45. Time-determinism defect remains open; no unrelated fix made in this planning branch.

C means the isolated worktree C:/Users/konst/.codex/worktrees/mia-phase-zero/KI-LIVE-VOICE-AGENTS; R in inventory is the original dirty checkout. These baselines were not executed in original R.

### Executed commands
Runtime interpreter: D:/Git-GitHub/Repositories/condata/KI-LIVE-VOICE-AGENTS/venv/Scripts/python.exe. Working directory C. The selected 250-test invocation was executed at 19d86e5:
```powershell
python -B -m pytest -p no:cacheprovider --basetemp 'C:/Users/konst/AppData/Local/Temp/mia-independent-qa-20261014' tests/test_core/test_tenant_registry.py tests/test_api/test_kea_text_flow.py tests/test_api/test_runtime_routes.py tests/test_api/test_voice_routes.py tests/test_api/test_crm_handoff.py tests/test_api/test_upload_routes.py tests/test_api/test_upload_validation_retention.py tests/test_telephony/test_profiles.py tests/test_telephony/test_calendar_service.py tests/test_telephony/test_calendar_policy.py tests/test_telephony/test_calendar_boundary.py tests/test_telephony/test_calendar_oauth_graph.py -q
```
Affected registry repeated at 9c280f3:
```powershell
python -B -m pytest -p no:cacheprovider tests/test_core/test_tenant_registry.py -q
```
Website working directory W, except the Node CRM command runs in W/apps/mke-crm:
```powershell
python -B -m unittest discover -s services/mke-crm-api/tests -p test_template.py -v
$env:PDF_VISUAL_ARTIFACTS='0'
node --test tests/isolation.test.mjs tests/pdf.test.mjs
node --test tests/js/cookie-banner-contract.test.cjs
php vendor/bin/phpunit --do-not-cache-result --no-coverage --filter 'SecureContactCaptureTest|CrmVoiceUploadAccessTest|CrmCoreDerivationTest|CrmDashboardTest|CrmRecordDetailTest|CrmAiUsageTest|AnnaVoiceHandoffTest' tests/Security
```
The cookie/PHP commands run in W, not W/apps/mke-crm. These are recorded receipts, not instructions to execute real providers.

No real provider/CRM/calendar write occurred. Runtime subset uses fake clients/MockTransport and SQLite/temp synthetic files. Full suites, Ruff/widget build, actual browser/phone/device/live providers and backup/restore were NOT RUN for Phase 0.

## Preliminary requirement status
All MIA-01..19: NOT RUN / NOT IMPLEMENTED. Existing baselines are reusable regression evidence, not MIA acceptance.
Source discovery: complete for decision-relevant surfaces. Independent QA reviewed all 12 planning documents and rechecked the corrected budget/proof order, isolated baseline identities, shared-catalog scope and reproducible command receipts. No substantive Phase 0 document blocker remained. Automated Markdown-link, fenced-JSON and assignment/task-ID checks passed; git diff --cached --check passed. Phase 1 executable contract freeze remains open.
Ballerina: exact source/edition/sample inspection complete. Read-only CARAT follow-up confirmed actual local DB, exact GL/XL PDF hashes and lifecycle states: GL staged/pending, XL remediating/business blocked, neither active. Full subset/certification, rights/current availability and MIA consumer/hosted service remain NOT VERIFIED; see CATALOG_REUSE_ASSESSMENT.md.
Server: current process/capacity snapshot measured; peak MIA load and integration NOT VERIFIED.
CARAT: vendor product feasibility only; no arbitrary MIA interface/license/practical import VERIFIED.
CRM bridge: separate chat active; no completion or real-receipt proof yet.

## Blockers
- Immutable same-tenant agent/session/project identity and protected resume.
- Current CRM authority/bridge contract and reliable replay.
- MIA calendar/service/test grant.
- Budget + provider benchmark, image usage enforcement.
- Validated source-bound dealer subset. Existing local catalog location is now verified; business-readiness, shared-service rights and MIA consumer grants remain central-service prerequisites, not a reason to block an independently verified PDF-subset demonstrator.
- Upload/retention/quota safeguards and private media lifecycle.
- Integrated human/browser/provider/CRM/calendar/phone tests.
- Operational restore/rollback/load/alerts and explicit release authorization.

## Closure rule
No package or project is complete because an agent reports code written. Coordinator checks combined functionality, security, tests, documentation, evidence and outstanding scope deviations. Production requires concrete release-specific authorization.

## Conversation and value-first follow-up, 2026-10-15
Product/UX independently accepted the updated requirements and scripted conversation sketch after correction: no spoken answer recaps, relevant follow-up questions, contextual empathy/humor, selective visuals, and a visible personalized concept before optional postcode/contact capture. The conversation guide is the fourteenth planning document. These are requirement/preview changes, not implemented runtime behavior.

Local browser checks exercised family/frustration/humor examples, already-answered household/material questions, null storage for unknown opening and room dimensions, schematic fallback labels, unchanged window capture, the contact preview's validation feedback, absence of contact identifiers in widget state, and 320px reflow. No JavaScript page errors were observed. Markdown links/JSON examples and staged diff checks passed. The preview makes no backend submission; no real email, provider, CRM or calendar operation was executed. Actual voice/laughter and the personalized concept-generation function remain NOT RUN / NOT IMPLEMENTED.
