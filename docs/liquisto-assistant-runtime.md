# Olivia internal runtime

## Purpose and authority

Olivia (`liquisto-assistant`) is Liquisto's internal assistant and secretary.
She informs employees and prepares visible drafts, but has no execution or
business-write authority. The runtime has no tools, no external web fallback,
no contact/lead handoff, and no cross-tenant fallback.

SCAS owns employee authentication and permission-filtered retrieval from
Liquisto systems. It passes only bounded, request-local source items. This
runtime validates the exact v2 contract, treats context as data, calls only the
configured local provider, and never persists raw request context.

## Request contract v2

`POST /assistant/respond` requires
`Authorization: Bearer <LIQUISTO_ASSISTANT_SERVICE_TOKEN>`:

```json
{
  "contract_version": "2.0",
  "tenant_id": "liquisto",
  "area_id": "liquisto",
  "agent_id": "liquisto-assistant",
  "request_id": "req-123",
  "principal_id": "user-123",
  "conversation_id": null,
  "prompt": "Bereite eine kurze Aufgabenliste vor.",
  "surface": "cockpit",
  "mode": "inform-and-prepare",
  "context": [{
    "source_id": "crm-open-tasks",
    "label": "Liquisto CRM: offene Aufgaben",
    "system": "liquisto-crm",
    "permission": "crm:read",
    "observed_at": "2026-07-24T08:00:00+02:00",
    "classification": "internal",
    "content": "Lieferstatus weicht vom bestätigten Termin ab."
  }]
}
```

Surfaces are `cockpit`, `crm`, `trade`, or `control`. Context is limited to 12
items, 4,000 characters per item, and 20,000 aggregate content characters.
Source identifiers must be unique, timestamps timezone-aware, and unknown fields
fail closed.

## Response and prepared actions

The response uses mode `inform-and-prepare` and answer mode `analysis-only`.
`prepared_actions` contains zero to eight ephemeral drafts. Each draft is
strictly `authority_mode: draft-only` and `execution_status: not-executable`,
must reference only source IDs supplied in the request, and includes its full
preview, target system, expected effect, risks, and missing information.

There is deliberately no apply, approve, command, or execution endpoint.

## Internal Voice broker

Olivia has a dedicated Live Voice prompt with no foreign tenant persona,
end-customer intake, handoff, or public-site legal script. The public widget
remains disabled. SCAS uses the service-token-authenticated
`POST /assistant/voice/calls` v2 broker and passes the authenticated employee's
`principal_id`, surface, address mode, bounded authorized context, and browser
SDP. The runtime returns only the SDP answer and safe call metadata; the OpenAI
API key remains server-side.

`LIQUISTO_ASSISTANT_VOICE_ENABLED` is an independent kill switch and defaults
to `false`. When enabled, readiness of the internal profile still requires an
`internal-authenticated` audience, no tools, no handoff, and
`public_widget.voice_enabled=false`. The provider session fixes `tools: []` and
`tool_choice: none`. SCAS must never expose the service token to the browser.

SCAS checks Voice readiness through authenticated
`GET /assistant/voice/readyz`. The endpoint fails closed when the service token
is missing or invalid, the Voice kill switch is off, the server-side OpenAI key
is missing, or the immutable internal Voice registry profile is invalid. A
successful response is exactly:

```json
{
  "contract_version": "2.0",
  "status": "ready",
  "tenant_id": "liquisto",
  "agent_id": "liquisto-assistant",
  "channel": "voice",
  "voice_enabled": true
}
```

## Knowledge and systems

The registry contains a small, reviewed baseline used by both Olivia text and
Voice prompts. Complete architecture,
platform content, processes, and internal-system data stay in their authoritative
systems. SCAS must retrieve them read-only, apply the signed-in employee's
permissions and purpose, and attach system, permission, classification, source,
and observation metadata. Missing or unknown authorization fails closed.

The runtime additionally validates every text and Voice context item against
the tenant registry. A source is usable only when its `source_id` is active and
its `system`, `required_permission`, classification, tenant, and read-only
access mode match exactly. The active v2 allowlist is:

- `liquisto-business-purpose`: `liquisto-tenant-registry`, `tenant:read`, public;
- `crm-companies`: `liquisto-crm`, `crm:read`, internal;
- `crm-deals`: `liquisto-crm`, `crm:read`, internal;
- `crm-open-tasks`: `liquisto-crm`, `crm:read`, internal.

Architecture, platform content, processes, website, Trade, Control, Documents,
and Integrations sources are registered as `planned`. They fail closed until a
separate review activates their exact source contract. A prompt or SCAS payload
cannot activate a planned or unknown source.

The public widget Voice path additionally requires an agent audience of
`public`. Olivia is `internal-authenticated`, so changing a widget feature flag
cannot expose her through the public Voice routes.

## Local provider and readiness

Production accepts only `http://liquisto-assistant-llm:11434/v1`. Development
and tests accept loopback `/v1` URLs. Cloud/provider fallback is rejected.
Authenticated `GET /readyz` validates the Olivia registry contract, empty tool
set, local configuration, and model availability before returning contract v2.
