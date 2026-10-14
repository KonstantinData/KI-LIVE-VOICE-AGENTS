# Proposed MIA interfaces
Status: design contract proposal v0.1; endpoints below do not yet exist.

## Rules
JSON schemas reject unknown privileged fields; bounded collections/text; server derives tenant/agent ownership and permissions. Schema/fixtures/tests change together. Exactly one contract owner modifies shared DTOs; consumers implement after freeze.
Times: ISO8601 UTC for persistence, Europe/Berlin for display and action review. Units: mm, explicit currency and customer-budget vs commercial-price distinction.
All error responses carry stable error_code + retryable + request_id; no credentials/provider payload/customer transcript.

## Public API proposal
| Endpoint | Request | Success / authority |
|---|---|---|
| POST /mia/sessions | selected public agent, consent versions, locale | session/project ID, scoped capability, allowed limits |
| GET /mia/projects/{id} | authenticated ownership | reviewed brief + revisions + authoritative states |
| PUT /mia/projects/{id}/brief | expected_version, allowlisted validated changes | new immutable brief revision |
| POST /mia/projects/{id}/generations | base_revision_id, idempotency_key | 202 job_id, never generated success before completion |
| POST /mia/projects/{id}/revisions | base_revision_id, semantic changes, idempotency_key | 202 job / optimistic conflict |
| GET /mia/jobs/{id} | owner capability | state, safe progress, last known receipt |
| POST /mia/jobs/{id}/cancel | owner, same request key | cancellation state; last complete revision retained |
| GET /mia/media/{id}/content | owner or short-lived bound grant | private streamed media, no-store/nosniff |
| POST /mia/contacts | protected form + specific consent + selected revision | durable intake receipt, delivery pending separately |
| POST /mia/bookings/prepare | approved service + contact_ref + candidate slot | immutable expiring action review |
| POST /mia/bookings/confirm | preparation_id + explicit confirmation + idempotency_key | confirmed only with provider event receipt |
| POST /mia/resume/exchange | approved protected capability/verified owner flow | rotated access, never ID-only ownership |
| POST /mia/projects/{id}/delete | current ownership + defined policy | deletion/revocation receipt |

Existing /ws/chat, voice broker and upload endpoints get backward-compatible server-bound profile/session support. Their existing names need not be duplicated.

## Kitchen concept
```json
{
  "schema_version": "mia.kitchen-concept/1.0",
  "tenant_id": "mein-kuechenexperte",
  "agent_id": "mia-kitchen-design",
  "project_id": "opaque-project-id",
  "revision_id": "opaque-revision-id",
  "revision_number": 0,
  "parent_revision_id": null,
  "dealer_profile_version": "mke-demo/1",
  "catalog_version_refs": [],
  "stage": "concept_unverified",
  "room": {
    "units": "mm",
    "coordinate_system": "local_cartesian",
    "height": {"value": null, "evidence_status": "unknown", "source_refs": []},
    "walls": [], "openings": [], "connections": []
  },
  "preferences": {},
  "budget_intent": {"currency": "EUR", "lower": null, "upper": null},
  "components": [], "materials": [], "appliance_requirements": [],
  "assumptions": [], "unresolved_questions": [],
  "validation": {"geometry": "not_evaluable", "technical": "not_verified"}
}
```
Evidence states: unknown/customer_reported/document_extracted/assumed/professionally_verified. Extraction records source hash/page/region/extractor/confidence; verification records reviewer/time. Render assumptions live separately.

## Revisions and jobs
Patch includes base_revision_id + expected_revision_number + stable request key + allowlisted semantic changes. Server computes changed/dependent fields, preserves unrelated authoritative fields and revalidates catalog constraints.
One initial image + five successful revisions proposed. Failed generation attempts have their own attempts and billable usage, not successful customer revisions.
Job states: queued/running/retry_wait/succeeded/failed/cancel_requested/cancelled/outcome_unknown.
Lease loss and provider timeout after request submission require reconciliation, not unbounded retry. Request hash reuse mismatch is 409.

## Catalog API proposal
Read-only version-qualified query: manufacturer + complete series identity + exact version + eligible component/material filters. Response includes stable record IDs, dimensions/restrictions, source refs, verification state and freshness.
No tenant customer/project content in common catalog. Consumer identity/grant resolves allowed catalog/edition/fields. Tenant commercial overlays are separately authorized and never returned to another tenant.
Unsupported GL/XL combinations, expired/discontinued entries, unknown constraints or uncertified semantics fail closed for article selection.
Media/price fields require distinct permitted use. No direct browser database access; secrets server-side.

## CRM handoff
```json
{
  "schema_version": "mia.crm-handoff/1.0",
  "event_id": "stable-event-id",
  "payload_hash": "canonical-payload-sha256",
  "tenant_id": "mein-kuechenexperte",
  "agent_id": "mia-kitchen-design",
  "session_id": "opaque-session-id",
  "conversation_id": "opaque-conversation-id",
  "project_id": "opaque-project-id",
  "selected_revision_id": "opaque-revision-id",
  "occurred_at": "2026-10-14T12:00:00Z",
  "locale": "de-DE",
  "contact": {"secure_form_reference": "opaque-reference"},
  "consent": {"purpose": "adviser_followup", "version": "approved-version"},
  "planning_snapshot": {"summary": "", "unknowns": [], "source_refs": []},
  "media_refs": [],
  "booking": null
}
```
Actual minimal contact fields are supplied server-side from the approved protected form; no trust in client contact_ref without owner lookup. No raw audio/full transcript.
Unique receiver key (tenant_id, agent_id, event_id), canonical payload hash, transactionally stored original acknowledgment. Identical replay -> same 2xx receipt; changed payload -> conflict. Durable intake success, CRM delivery and mail success are separate states.
Receiver returns event_id + capture/lead/project refs + intake_state + delivery_state. Notification intent is idempotent. Limited authenticated service ingress; no operator impersonation.
Separate CRM bridge chat owns actual target schema and migration; freeze before runtime handoff implementation.

## Usage and booking
Usage envelope: server-assigned agent/function/session/project/revision/job/attempt, provider/model/version, timestamp, billable unit categories including image output, pricing snapshot/currency/known-or-unknown cost. Missing usage cannot bypass reserved quotas.
Booking states: proposed/prepared/confirmation_required/submitting/confirmed/conflict/outcome_unknown/failed/cancelled. Store preparation/action hash, provider/calendar ref, exact UTC start/end, display timezone, confirmation, request key, provider event ID. Replay returns original receipt. New slot or reschedule requires fresh confirmation. Provider write and notifications are separate outcomes.
