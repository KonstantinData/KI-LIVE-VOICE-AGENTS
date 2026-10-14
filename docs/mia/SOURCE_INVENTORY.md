# Phase 0 source inventory
Inspected 2026-10-14. Evidence below distinguishes source, offline tests and current host process observations.

## Repositories and isolation
R = D:/Git-GitHub/Repositories/condata/KI-LIVE-VOICE-AGENTS.
W = D:/Git-GitHub/Repositories/02_mein_kuechenexperte/mein-kuechenexperte.
C = C:/Users/konst/.codex/worktrees/mia-phase-zero/KI-LIVE-VOICE-AGENTS.

R original HEAD: 155512f67230b1ea52f1c41ee038adf7789a0554, branch codex/olivia-de-jong-20261009, existing tracked/untracked Anna changes. Preserve them.
C planning branch: codex/mia-phase-zero-20261014, based on fetched origin/main 9c280f309a6e09a65ac1bc0fa98435d802707069. Original feature branch was not copied.
W HEAD: b22427b7874afdbde651c7c5a050b6eaec65345a, main, extensive existing website/SEO/CSS/image changes.
W fetch failed on an internal refs/codex/turn-diffs/checkpoints object. Remote freshness is unresolved; do not delete unknown refs or repair unrelated work. A clean isolated checkout must precede W implementation.

R AGENTS.md restricts runtime to voice/chat/upload/profile/audit/handoff. CRM UI, schemas and business records belong to W. No additional W AGENTS.md was found. Supplied global instructions apply.

## Verified source map
| Capability | Evidence | MIA consequence |
|---|---|---|
| KEA public + Anna phone profiles | R registry/tenants/mein-kuechenexperte/tenant.json:35,80 | No MIA profile exists |
| Text dispatch | R src/api/websocket/chat_handler.py:118,153; src/api/main.py:71 | MKE hard-dispatches KEA; no text agent selector |
| Widget label | R frontends/widget/src/lib/config.ts:83 | data-agent is presentation, not executable authority |
| Voice profile gate | R src/api/services/voice_sessions.py:40,53,138 | Public enabled voice only; add MIA without exposing Anna |
| Conversation ownership | R src/db/models/conversation.py:17; services/voice_sessions.py:84 | Tenant/visitor ownership lacks agent binding and secure resume proof |
| Unknown follow-up agent | R src/api/routes/voice.py:231,595 | Unknown explicit profile can fall back to default handoff routing |
| Private uploads | R src/api/routes/uploads.py:134,335; services/project_upload_runtime.py:91 | Reuse after agent/session binding and file validation hardening |
| PDF interpretation | R src/api/services/project_uploads.py:113,186 | Prose summary, not validated room geometry; page pixels may contain PII |
| Runtime storage | R src/db/models; src/db/alembic/versions | No MIA plan/revision/media/job/outbox persistence |
| Calendar | R src/telephony/calendar_tools.py:28; src/agents/anna/calendar/service.py:270 | Anna-only grants; reusable mechanisms, separate MIA authority required |
| Browser tools | R src/api/routes/voice.py:442 | Browser voice tools currently 410; structured capture/execution path must be designed |
| Website | W www/index.php:344; includes/stylesheets.php:24 | PHP + shared includes + vanilla JS |
| KEA embed | W www/includes/_shared/footer.php:217; assets/js/kea-consent-launcher.js:8 | Single root assumptions; two unchanged loaders would collide |
| Current visual style | W www/assets/css/editorial-design.css:2 | Warm canvas, green actions, Source Sans/Serif; older design docs drift |
| Legacy contact | W www/agent-lead-webhook.php:57,75; includes/crm/secure_contact_capture.php:65 | Requires legacy offer flag; drops MIA fields |
| Contact persistence | W www/includes/crm/contact_capture_repository.php:18,240 | Random capture IDs; retry is not atomic delivery deduplication |
| Usage persistence | W database/migrations/003_create_crm_ai_usage_events.sql:28; www/agent-usage-webhook.php:54 | Unique event constraint exists but replay can produce 503 |
| New CRM | W apps/mke-crm; services/mke-crm-api; deploy/mke-crm | Next frontend, independent Python API/PostgreSQL |
| CRM bridge gap | W docs/crm-template-adoption.md:116,139 | New CRM deployed; old website intake explicitly not connected |
| CRM documentation drift | W services/mke-crm-api/README.md:7 | Template/undeployed claim conflicts with later deployment record |
| Public booking | W www/quick_check_termin.php:196,233 | Zeeg embed is not verified backend availability/book/cancel integration |
| CRM appointments | W services/mke-crm-api/migrations/0002_overview_workspace.sql:120 | Displayable records do not prove provider booking |
| Cost accounting | R src/api/services/crm_handoff.py:23,89 | Stale rate snapshot, missing image-output accounting/agent attribution |

## Host evidence
Security specialist performed one bounded read-only KI-TEAM SSH inspection with existing host-key verification.
- Load 0.15/0.16/0.11; RAM 7,745 MiB total / 6,131 MiB available.
- Root 150G total / 101G used / 44G available (71%).
- Existing additional volumes have free capacity; their ownership/purpose was not established and they must not be repurposed.
- ki-team-api active; MKE CRM frontend/API/DB, website staging and Anna/calendar containers running; MKE database reported healthy.
This proves process/capacity snapshot only. It does not prove public ingress, deployed source revision, voice interaction, booking, correct CRM receipt, backup recovery or MIA peak concurrency.

## Ballerina sources
User explicitly supplied manufacturer PDFs from an unrelated business folder. No customer/tenant data is authorized for reuse.
- GL 2026: 775 pages, 285579629 bytes, SHA256 CA4BE5AD6BA4F7391D925977543B28DD93D07FA6BC65199A1B21667FC47F9E2D.
- XL 2026: 1041 pages, 490511312 bytes, SHA256 AA4AD3A72FDC9C1991D2AC22BF99875F7334C4A60CC2C325138F52740C5E799D.
Covers/index/sample geometry and component pages visually inspected; printed validity starts 2026-01-01. Older PDF metadata is not edition authority. Native text is usable; dense tables/symbols need coordinate and visual validation.
GL and XL differ in article/front/geometry semantics. Never merge by supplier/year or interpret order-number tokens as physical dimensions. Some printed phase-out deadlines are already past; edition membership does not prove current availability.
No full import, price extraction or technical catalog certification was performed. Do not copy PDFs/catalog artwork into Git or public assets.

## SCAS catalog uncertainty
Read-only SCAS code inspection found no catalog_knowledge service, database config or catalog deployment in the inspected checkout/local origin/main. The catalog lifecycle skill describes GL parsing and XL complete-source-layer capability, but not live business readiness.
Catalog service location, server DB identity, source-hash match, active pointer, business gates and consumer binding remain not_available.
Bounded read-only host follow-up found the existing kuechenberater API/worker/PostgreSQL/Redis stack under /opt/ki-kuechenberater. The exact catalog_knowledge module and CATALOG_DATABASE.md paths were absent there and in the running API container; importlib discovery returned false. This does not rule out a separate catalog service/database. No DB/customer records, env/config values or logs were inspected.
User suggests central tenant/project-neutral catalog maintenance. This is a proposed architecture, not an authorized relocation or existing verified shared service. Das Küchenhaus and MKE remain isolated.

## Scope limits
Decision-relevant code, schemas, docs, tests, CI and deployment surfaces in both repos were inventoried by six independent read-only specialists. No claim is made that every binary/document in either repository was semantically reviewed. Area-scoped memory query was unavailable (local ledger connection refused); conclusions rely on current sources. No MIA provider call, customer-data write or deployment occurred.
