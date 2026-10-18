# MIA project control
Status 2026-10-18: Phase 0 findings and proposed runtime contracts remain open.
The approved agent-content cleanup adds separate offline MIA prompt builders;
these are not a planning engine, registered agent or production activation.

Current flow: at most 120 seconds of initial dialogue including both speakers,
pauses and interaction; no room/window/door/connection questions before the first
draft; wishes drive bounded prepared-layout changes in a raster scene for every
visitor. Actual-room adaptation follows. Preserve separate appliance choices,
unknown dimensions and retained devices; no spoken answer recap. The visitor
sees and can refine the concept before optional contact. See [raster-first](RASTER_FIRST_DRAFT_DE.md)
and [current conversation design](CONVERSATION_DESIGN.md). Rendering wait and
total first-result time are measured separately; timing is not validated.
Uninterrupted long speech and the diagram's 10x10 m scene remain open decisions.

Active area: mein-kuechenexperte.de. Runtime and website/CRM repositories are explicitly in scope. The supplied Ballerina manufacturer PDFs are authorized external sources for this project; Das Küchenhaus remains an unrelated tenant.

## Deliverables
- [Inventory](SOURCE_INVENTORY.md): current sources, repository states and actual integration gaps.
- [Catalog reuse assessment](CATALOG_REUSE_ASSESSMENT.md): located local CARAT catalog database, exact source matches, unresolved readiness and neutral-service proposal.
- [Product requirements](PRODUCT_REQUIREMENTS.md): demonstrator, production MVP, acceptance IDs.
- [Conversation design](CONVERSATION_DESIGN.md): fluid dialogue, contextual empathy/humor and selective visual support, without spoken recaps.
- [Architecture](ARCHITECTURE.md): ownership, session identity, jobs, versioning, media and shared catalog proposal.
- [Interfaces](INTERFACES.md): proposed versioned contracts and state machines.
- [Assignments](AGENT_ASSIGNMENTS.md): all eleven specialist roles and file ownership.
- [Task board](TASK_BOARD.md): dependencies, priority, evidence and parallel work.
- [Decisions](DECISIONS.md): accepted constraints, recommendations, unresolved inputs.
- [Security review](SECURITY_REVIEW.md): release blockers and safeguards.
- [Test plan](TEST_PLAN.md): independent acceptance and hypothesis evaluation.
- [Acceptance report](ACCEPTANCE_REPORT.md): executed baseline checks and remaining proof.
- [Operations](OPERATIONS_RUNBOOK.md): isolated environment, resource limits, release/rollback gates.

## Runtime critical path (separate from approved content cleanup)
1. Freeze session, planning, catalog and intake contracts; agree accountable CRM and calendar destinations.
2. Build isolated demonstrator using one visually verified Ballerina subset and synthetic CRM/calendar adapters.
3. Prove text discovery, voice-fixture integration, versioned schematic concept and five revisions without unsupported product claims.
4. Authorize a bounded provider benchmark budget before actual live voice/image calls, then independently prove natural conversation and generated/editable images.
5. Integrate the real test CRM/calendar, independently validate, then prepare a concrete release for explicit production approval.

The formerly tentative 2026-10-16 meeting and two-day demonstrator schedule are
historical planning context, not current deadlines or delivery evidence. No API
spending budget has been approved by this content cleanup. Earlier acceptance
receipts remain unchanged in ACCEPTANCE_REPORT.md; they prove only their stated scope.

Local source layout: `src/agents/mein_kuechenexperte/shared` contains selected
role-neutral MKX policy/business context; `kea` owns reception/text flow and its
text/voice composition; `mia` owns planning prompt sections and offline builders.
MIA runtime/project/session bindings, registry activation, rendering, CRM and
calendar integration remain separate implementation work. Anna's independent
phone/calendar package is now `src/agents/mein_kuechenexperte/anna`; the move
does not change her phone/tool authority.

A separate user-created chat owns the CRM bridge:
`01a13869-aecc-7c60-bb78-8b4bf6fd7747` — Website-Kontakte an aktuelle CRM-App anbinden.
This is an external dependency, not completed work. Do not edit that chat's files concurrently.

## Authority
The user supplied the full MIA master prompt on 2026-10-14. Production changes, deployments, customer-data changes, security-critical configuration and material new spending require explicit release-specific authorization. Ordinary isolated development is in scope; missing factual calendar/catalog/CRM authority cannot be invented.
