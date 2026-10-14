# Decisions and unresolved inputs
| ID | State | Decision / rationale / alternative |
|---|---|---|
| ADR-MIA-001 | mandatory | Runtime owns planning execution; W owns CRM. Reject CRM duplication in R. |
| ADR-MIA-002 | recommended | Indexed immutable agent/session/project identity; presentation labels insufficient. Metadata-only bootstrap rejected as long-term concurrent/resume contract. |
| ADR-MIA-003 | recommended | Separate authoritative concept geometry from illustrative render_scene and image. Unknown dimensions stay null. |
| ADR-MIA-004 | recommended | Existing PostgreSQL/private storage + bounded durable worker; no new server/volume/broker without evidence. |
| ADR-MIA-005 | mandatory | Keep original dirty checkouts unchanged; isolated implementation branches/worktrees and PR integration. W fetch corruption is outside automatic destructive repair scope. |
| ADR-MIA-006 | recommended | First demonstration uses one certified small GL subset; XL remains independent. Full catalogs/CARAT do not block demo. |
| ADR-MIA-007 | unresolved | Current CRM receiver/database authority must be verified. Separate user-created CRM bridge chat owns implementation. No blind dual writes. |
| ADR-MIA-008 | unresolved | Choose real provider/calendar/service/test destination; do not widen Anna-only grant or infer Zeeg API availability. |
| ADR-MIA-009 | recommended | Image provider adapter and benchmark configurable current models. No paid call absent concrete approved budget. |
| ADR-MIA-010 | user proposal | Central tenant/project-neutral manufacturer catalog: one update pipeline, scoped read consumers and independent tenant overlays. DKH/MKE remain isolated. No relocation implemented/authorized. |
| ADR-MIA-011 | mandatory | Neutral export is preparation, not working CARAT import. Actual vendor contract/license/test import required. |
| ADR-MIA-012 | recommended | Anonymous demo retention 7d; optional resume 30d; separate approved production/CRM purposes. These are proposals, not legal deadlines. |
| ADR-MIA-013 | mandatory | No product/fixed-price/stock/licensing assumptions from manufacturer PDFs or image-source docs. |

## User inputs
- 2026-10-14: meeting not agreed, possibly in two days; target 2026-10-16 remains tentative.
- No budget approved yet.
- Exact Ballerina GL/XL sales manual 2026 sources supplied, hashes in inventory.
- Existing Ballerina server database thought to be via SCAS/DKH. Neither service location nor consumer rights verified.
- DKH expressly has no connection to MKE.
- User proposes central neutral catalog maintenance; architecture discussion, not a data-migration mandate.
- New CRM bridge chat explicitly requested and created.

## Open decisions and owners
| Input | Owner / unblock evidence |
|---|---|
| Provider total/call benchmark budget + model/account entitlement | Konstantin; bounded approved amount; J/C cost plan |
| Test calendar/service and permitted actor/actions | calendar owner + G; synthetic destination and grant evidence |
| Authoritative CRM route/revision/database | F/H; service mapping + synthetic receipt displayed |
| Neutral catalog service source/deployment location | D/J; actual service reference, read-only metadata |
| Catalog reusable rights and fields | source owner/H; approved consumer grant/media/price rights |
| 12-20 GL records/front mappings | D + independent I; full subset visual verification |
| Production retention, privacy notices and resume proof | A/H + owner; approved purpose/expiry/deletion implementation |
| Pilot sample and success thresholds | A/I + owner; preregistered real-user evaluation |
| Production release | user; exact manifest + QA/security/rollback proof |

No unresolved fact is silently replaced by a software default or a simulated-success label.
