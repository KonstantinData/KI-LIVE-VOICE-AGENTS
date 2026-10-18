# Decisions and unresolved inputs
| ID | State | Decision / rationale / alternative |
|---|---|---|
| ADR-MIA-001 | mandatory | Runtime owns planning execution; W owns CRM. Reject CRM duplication in R. |
| ADR-MIA-002 | recommended | Indexed immutable agent/session/project identity; presentation labels insufficient. Metadata-only bootstrap rejected as long-term concurrent/resume contract. |
| ADR-MIA-003 | recommended | Separate authoritative concept geometry from illustrative render_scene and image. Unknown dimensions stay null. |
| ADR-MIA-004 | recommended | Existing PostgreSQL/private storage + bounded durable worker; no new server/volume/broker without evidence. |
| ADR-MIA-005 | mandatory | Keep original dirty checkouts unchanged; isolated implementation branches/worktrees and PR integration. W fetch corruption is outside automatic destructive repair scope. |
| ADR-MIA-006 | earlier recommendation; revision proposed in ADR-MIA-016 | First demonstration uses one certified small GL subset; XL remains independent. Full catalogs/CARAT do not block demo. The workshop proposes decoupling the general furniture experience from that source-verified article sample; await user discussion before treating the dependency as waived. |
| ADR-MIA-007 | unresolved | Current CRM receiver/database authority must be verified. Separate user-created CRM bridge chat owns implementation. No blind dual writes. |
| ADR-MIA-008 | unresolved | Choose real provider/calendar/service/test destination; do not widen Anna-only grant or infer Zeeg API availability. |
| ADR-MIA-009 | recommended | Image provider adapter and benchmark configurable current models. No paid call absent concrete approved budget. |
| ADR-MIA-010 | user proposal | Central tenant/project-neutral manufacturer catalog: one update pipeline, scoped read consumers and independent tenant overlays. DKH/MKE remain isolated. No relocation implemented/authorized. |
| ADR-MIA-011 | mandatory | Neutral export is preparation, not working CARAT import. Actual vendor contract/license/test import required. |
| ADR-MIA-012 | recommended | Anonymous demo retention 7d; optional resume 30d; separate approved production/CRM purposes. These are proposals, not legal deadlines. |
| ADR-MIA-013 | mandatory | No product/fixed-price/stock/licensing assumptions from manufacturer PDFs or image-source docs. |
| ADR-MIA-014 | user requirement, 2026-10-15 | Fluid personal dialogue without spoken answer recaps; brief contextual empathy and optional appropriate humor/laughter. Images appear selectively. Internal structured state and explicit contact/booking consent remain required. See CONVERSATION_DESIGN.md. |
| ADR-MIA-015 | user requirement, 2026-10-15 | Deliver a real visible personalized concept before optional postcode/contact capture. Communicate this value at entry. Sales qualification cannot replace the concept; contact, email verification and booking remain separate voluntary steps with truthful receipt states. |
| ADR-MIA-016 | workshop recommendation for user discussion, 2026-10-15 | Measure 2-3 minutes from conversation start through first personal furnished result, including planning/rendering. Prefer consistent model-based 3D and 6-8 curated template variants initially. Propose generic fixed-size demo furniture plus a separate source-verified Ballerina article sample instead of blocking the whole experience on a catalog subset. These scope/implementation proposals are not approved by the workshop itself; source/tenant/readiness gates remain unchanged. See TEAM_WORKSHOP_RESULTS.md and EXPERIENCE_DRAFT_DE.md. |
| ADR-MIA-017 | later user requirement, 2026-10-15; reconciled 2026-10-18 | Every visitor starts with a wish-driven draft in a neutral raster scene, using prepared layouts and bounded changes, not free planning. Initial dialogue is capped at 120 seconds including both speakers, pauses and interaction. Ask no room/window/door/connection questions before the draft, including optional exceptions; retain unsolicited room data for later. Actual-room adaptation follows. Earlier measured-room-first and 150-second instructions are superseded; render wait and total first-result time are separately measured. See RASTER_FIRST_WORKSHOP.md and RASTER_FIRST_DRAFT_DE.md. |
| ADR-MIA-018 | later user correction, 2026-10-15 | Appliance integration is a per-device preference, with mixed answers allowed. Keep type/integration/width separate, preserve retained devices and known answers, and leave unresolved dimensions unknown. No universal fully-integrated default or mandatory detail questionnaire. |
| ADR-MIA-019 | approved local content cleanup, 2026-10-18 | Separate MKX role-neutral policy in shared/, KEA reception in kea/ and MIA planning prompts with offline builders in mia/. This does not activate MIA, implement a planner or grant Anna's tools/calendar authority. Runtime/project binding and release remain separate work. |

## User inputs
- 2026-10-14: meeting not agreed, possibly in two days; target 2026-10-16 remains tentative.
- No budget approved yet.
- Exact Ballerina GL/XL sales manual 2026 sources supplied, hashes in inventory.
- Initial Ballerina database attribution to SCAS/DKH was unconfirmed. User's later CARAT hint led to actual local PostgreSQL/catalog_knowledge discovery and matching GL/XL hashes. No active business-ready catalog or MIA consumer grant exists; a separate server copy remains unverified.
- DKH expressly has no connection to MKE.
- User proposes central neutral catalog maintenance; architecture discussion, not a data-migration mandate.
- New CRM bridge chat explicitly requested and created.

## Open decisions and owners
| Input | Owner / unblock evidence |
|---|---|
| Provider total/call benchmark budget + model/account entitlement | Konstantin; bounded approved amount; J/C cost plan |
| Test calendar/service and permitted actor/actions | calendar owner + G; synthetic destination and grant evidence |
| Authoritative CRM route/revision/database | F/H; service mapping + synthetic receipt displayed |
| Neutral catalog package/hosted service and MIA consumer | D/J/H; existing local core located, extraction/hosting/grant contract and tested consumer still required |
| Catalog reusable rights and fields | source owner/H; approved consumer grant/media/price rights |
| 12-20 GL records/front mappings | D + independent I; full subset visual verification |
| Production retention, privacy notices and resume proof | A/H + owner; approved purpose/expiry/deletion implementation |
| Pilot sample and success thresholds | A/I + owner; preregistered real-user evaluation |
| Uninterrupted visitor speech beyond the 120-second dialogue cap | product owner; explicit transition/interruption policy before runtime implementation; no hard audio cut inferred |
| Diagram's 10x10 m presentation scene | product owner; confirm scene constant or illustrative assumption; never treat it as customer-room measurement |
| Production release | user; exact manifest + QA/security/rollback proof |

No unresolved fact is silently replaced by a software default or a simulated-success label.
