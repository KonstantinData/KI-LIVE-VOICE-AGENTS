# Agent assignments and bounded ownership
Coordinator owns shared requirements/contracts/reconciliation/acceptance. Independent QA reports directly to coordinator.
Phase 0 used six actual subagent contexts: runtime_voice, website_crm_calendar, planning_dealer_carat, security_operations, product_ux, independent_qa. Additional scas_catalog_reuse investigated catalog location only.
These are real isolated agent contexts, not eleven separate sidebar chats. No specialist implemented code or had an implementation branch. Future implementing agents each require their own branch/worktree.

| Role | Task IDs | Expected output | Proposed implementation boundary | Prerequisites |
|---|---|---|---|---|
| A Product/UX + coordinator | MIA-P01,P02,P03 | journeys, copy, conversion, acceptance rubric and frozen shared contracts | docs/mia/PRODUCT_REQUIREMENTS.md, INTERFACES.md; versioned schema/fixture package | current service positioning, date/budget; specialist contract review |
| B Voice/conversation | MIA-R01,R02 | MIA profile, natural extraction/corrections/text fallback | R src/agents/mia, registry MKE profile; dedicated runtime tests | identity/profile/brief contracts |
| C Planning/media | MIA-C01,C02 | validated plan/version/job/edit generation | R proposed src/api/services/mia_planning, mia_generation; runtime-only DB migrations | plan/catalog/job schema; budget |
| D Dealer/catalog | MIA-D01,D02 | verified Ballerina subset, catalog/overlay policy | proposed scoped catalog adapter + MKE demo profile fixtures | exact source/version; rights; catalog location |
| E Frontend/site | MIA-E01,E02 | independent KEA/MIA entries, responsive concept UI | R frontends/widget; W dedicated MIA PHP entry/CSS/JS | instance/session/event schemas; dirty design reconciliation |
| F CRM | MIA-F01,F02 | authoritative idempotent intake + project/media display | W services/mke-crm-api, migrations, apps/mke-crm; legacy intake compatibility | CRM authority, handoff freeze; separate chat |
| G Calendar | MIA-G01,G02 | provider-confirmed safe booking/change/cancel | approved MIA adapter; W confirmed CRM projection | owner/provider/test calendar, secure contact/confirmation |
| H Security/privacy | MIA-H01,H02 | threat review, upload/resume/grants/retention proof | independent tests/review; bounded hardening via owning agent | all frozen contracts |
| I Independent QA | MIA-I01,I02 | scenario suites, regressions, hypothesis evaluation, final report | tests/browser fixtures; docs/mia/ACCEPTANCE_REPORT.md | combined commits/test environment |
| J DevOps | MIA-J01,J02 | isolated env, quotas/worker/CI/monitoring/rollback | R deploy/CI/runtime ops; W approved release manifests | resource/budget policy, tested migrations |
| K CARAT | MIA-K01,K02 | neutral export + verified vendor feasibility | R export schema/adapter; no unrelated CARAT repo work | plan schema; vendor docs/license/test installation |

## Shared-file ownership
One coordinator-approved runtime foundation owner changes Conversation migration, profile/schema/config, common resolver and dispatch routes. B/C/E/F/G consume released DTOs; they do not independently rewrite shared files.
One CRM integration owner in the separate chat changes webhook/API/migrations; no parallel legacy/new CRM dual writing.
Shared manufacturer catalog extraction/relocation is a separate architecture work package, never implicit DKH tenant access.

## Required handoff
Every package returns: implemented behavior; exact files; executed commands/results and tested SHA; risks/limits; dependencies; documentation; PR URL. NOT RUN/BLOCKED are honest states. Implementer completion is not QA acceptance.
Integration: reviewed PRs, coordinator integration branch, combined verification, independent QA, then release proposal. No default-branch repair commits or destructive cleanup.
