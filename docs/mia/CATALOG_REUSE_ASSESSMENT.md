# Existing Ballerina catalog reuse assessment

Date: 2026-10-14. Scope: read-only manufacturer-catalog discovery authorized by the user's CARAT planning/floorplan-agent hint. No tenant/customer context, migration, import, gate mutation or activation is authorized by this inspection.

## Located and verified

The catalog implementation is in the separate CARAT-AUTOPLAN-AGENT repository, inspected clean at commit `8fd93101a05914a9fa29dce74f3d216982d51f28`:
- `docs/CATALOG_DATABASE.md`: source-backed manufacturer catalog database and validation boundary.
- `docs/adr/0001-local-postgresql-catalog-knowledge-base.md`: accepted local PostgreSQL architecture.
- `catalog_knowledge/`: models, imports, parser profiles, lifecycle, read-only runtime resolution and CLI.
- `alembic/versions/`: catalog/source/lifecycle/business-readiness migrations.

The actual configured connection was successfully queried: local `127.0.0.1:5432`, database `carat_room_planning`, schema `catalog_knowledge`, PostgreSQL 18.4. This is a local service on the user's machine, not evidence of a SCAS/Hetzner catalog deployment. A separate remote copy has not been established.

Connection credentials were loaded privately and never printed. PostgreSQL enforced `default_transaction_read_only=on`; direct lifecycle/metadata inspection ended with rollback. The non-sensitive aggregate CLI status executed only SELECTs. No schema/data/gates/pointers changed.

## Exact sources and lifecycle state

| Series | Edition / source match | Current lifecycle | Business readiness | Active pointer |
|---|---|---|---|---|
| Ballerina GL, handleless, kitchen_furniture, DE/de | 2026; exact hash matches user GL PDF | staged | pending | none |
| Ballerina XL, handled, kitchen_furniture, DE/de | 2026; exact hash matches user XL PDF | remediating | blocked | none |

GL source SHA256: `ca4be5ad6ba4f7391d925977543b28dd93d07fa6bc65199a1b21667fc47f9e2d`.
XL source SHA256: `aa4ad3a72fdc9c1991d2ac22bf99875f7334c4a60cc2c325138f52740c5e799d`.

The local schema currently contains 1,816 source pages, 833 article candidates, 1,749 execution-code records and 5,004 catalog-price records. A separate exact-source query confirmed 775 stored GL pages and 1,041 stored XL pages, matching each source document's declared page count. Price values were not queried or disclosed. Count/extraction completion does not establish semantic correctness, valid commercial prices, dealer authorization or production readiness.

Article validation: 67 candidate and 766 machine_checked; no verified article items in the aggregate result. Most front variants/codes are also machine_checked. Sixty verified front records do not certify the complete series.

GL has no persisted lifecycle operations/gate reports/activation event in the returned series status. Its missing business evidence is not a passing or failed gate.
XL's latest authoritative report fails all six required business gates:
- catalog.semantic-coverage;
- catalog.entity-certification;
- catalog.commercial-semantics;
- catalog.planning-policy;
- catalog.runtime-consumer;
- catalog.end-to-end-planning.

XL has a historical activation followed by a readiness-reconciliation event. The current pointer is empty and business status blocked; historical publication is not current active readiness.

## Reuse feasibility and boundaries

The inspected catalog ORM/schema is already organized around manufacturer, complete series identity, immutable edition/source versions, articles/fronts/prices/rules and provenance. No dedicated tenant/customer/project entity columns or tables were found in the inspected catalog model/schema; source text and JSONB payload contents were not audited. This finding is restricted to schema shape; it does not authorize sharing an entire database or unrelated CARAT records.

The implementation and operation are still owned by the CARAT project and local configuration. `RUNTIME_CONSUMER_BINDINGS` currently registers only `carat-furniture-planning`; this registration is readiness/probe evidence, not an authorization grant. The productive resolver has no caller/principal parameter. No MIA consumer, shared hosted API, consumer-specific access grant or network service was found. A neutral data model alone is not a proven multi-tenant access boundary. Read-only mode enforced for this diagnostic transaction is not proof of permanent least-privilege production roles.

The schema retains private local source locators and raw supplier page text. A future service must project allowlisted DTOs, omitting local paths/raw source content/price fields by default and granting source/media/commercial access separately. Schema inspection does not establish that every free-text value is free of personal or tenant information.

Recommended path:
1. Reuse the existing versioned catalog core and source evidence; avoid a duplicate GL/XL re-import or independent maintenance pipeline.
2. Define a project-neutral catalog package/service ownership contract, preserving CARAT's existing local consumer and accepted operation until a deliberate replacement is tested.
3. Implement authenticated consumer authorization separately from readiness registration, then register and validate MIA with narrowly scoped series/version/field access. Do not inherit CARAT permissions or access Das Küchenhaus customer/tenant data.
4. Resolve source-bound semantic/entity/planning and applicable commercial gates before treating records as autonomous constraints. Source text or numerical catalog values cannot bypass failed readiness.
5. If centralized hosting is selected, migrate only the classified catalog scope through a verified backup/restore and read-compatibility rehearsal. Do not move the whole existing database by assumption. Existing server capacity and privacy/rights/access/backup/recovery review precede a concrete production release request.
6. Keep tenant assortment, prices/discounts, credentials and planning/customer/project state in independent tenant-owned stores/overlays. Consumers pin an exact approved catalog version; one central update creates an immutable successor, not silent mutation of existing plans.

No new server, permanent database engine or physical relocation is established as necessary. A schema/service on an approved existing PostgreSQL engine may suffice; local-versus-hosted operation is an explicit architecture decision.

## Safe next actions

GL: technical and business validation of the exact staged source/version through the catalog lifecycle owner.
XL: remediation of its authoritative failed business gates through the assigned semantic-certification/runtime-readiness owners, preserving the failed report and pointer history.
Central service: define consumer grants and a bounded extraction/migration proposal. No import, validation, remediation or publish action was executed during this read-only task.

The MIA demonstrator may use an independently source-verified subset under its bounded unverified-concept contract; this does not activate either complete catalog or certify commercial/order use. The subset needs explicit provenance and independent checking. The existing productive CatalogPlanningRuntime requires the full verified front/article/commercial-price/planning-rule bundle; it must not be used to skip failed gates or fall back to staged/newest records. An evidence-limited conceptual DTO would be a separately approved contract, not a weakening of that runtime.

The existing end_to_end_planning gate/probe proves read-only catalog-bundle resolution only, not CARAT UI article insertion, a saved plan, or a calculated commercial result.

## Verification limits

Actual local connection, PostgreSQL read-only mode, exact source-hash matches, aggregate counts, lifecycle metadata and catalog table names were verified. No raw prices, supplier document text, customer records or CARAT UI state were read. Repository changes are limited to MIA planning documentation. Existing CARAT process was already running and remained untouched; no CARAT session/test was started by this inspection.

Independent QA inspected the catalog models/runtime/migrations and rechecked this corrected assessment. Documentation reuse findings were accepted after distinguishing schema shape, content classification, readiness registration and actual authorization. All 13 local Markdown links/JSON examples passed checks; git diff --check passed. No parser/runtime implementation tests were required or rerun for this documentation-only change.

