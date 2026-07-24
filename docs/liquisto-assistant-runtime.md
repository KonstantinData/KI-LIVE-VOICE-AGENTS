# Olivia internal runtime

## Purpose and authority

Olivia (`liquisto-assistant`) is Liquisto's internal assistant and secretary.
She informs employees and prepares visible drafts. Internal Voice has exactly
one navigation function; neither channel has business-write authority. The
runtime has no external web fallback, contact/lead handoff, generic browser
control, or cross-tenant fallback.

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
`internal-authenticated` audience, the exact singleton navigation tool, no
handoff, and `public_widget.voice_enabled=false`. The provider session uses
`tool_choice: auto` so Olivia can either answer normally or emit the single
allowlisted navigation function. SCAS must never expose the service token to
the browser.

### Navigation wire contract v1.1

The only Realtime function is `open_liquisto_destination`. The provider emits
it through `response.function_call_arguments.done`. Its arguments are one exact
JSON object with no additional root or parameter properties:

```json
{
  "contract_version": "1.1",
  "request_id": "req-voice-123",
  "tenant_id": "liquisto",
  "agent_id": "liquisto-assistant",
  "source": "voice",
  "intent": "navigate",
  "destination_id": "crm.tasks",
  "parameters": {}
}
```

`destination_id` is exactly one of `workbench.cockpit`, `crm.overview`, or
`crm.tasks`. No principal, URL, href, path, browser command, shell command,
mutation, export, or create argument exists. Unknown or additional fields fail
closed. The authenticated SCAS Workbench server derives `principal_id` from its
employee session; model output is never identity authority.

The eight model-controlled argument keys deliberately omit `call_id`. SCAS
accepts only the provider event `response.function_call_arguments.done`,
validates its event-level `call_id`, parses the exact tool arguments, and then
constructs the same-origin transport envelope by adding that provider value:

```json
{
  "contract_version": "1.1",
  "request_id": "req-voice-123",
  "call_id": "call-provider-123",
  "tenant_id": "liquisto",
  "agent_id": "liquisto-assistant",
  "source": "voice",
  "intent": "navigate",
  "destination_id": "crm.tasks",
  "parameters": {}
}
```

Olivia cannot select, echo, or overwrite `call_id`.

After an allowed destination resolves through the browser's local route map,
the internal completion request has exactly six keys:

```json
{
  "contract_version": "1.1",
  "request_id": "req-voice-123",
  "call_id": "call-provider-123",
  "decision_id": "decision-123",
  "destination_id": "crm.tasks",
  "parameters": {}
}
```

It contains no URL, principal, or model-controlled receipt value.

The Workbench DataChannel handler forwards the semantic intent same-origin to
SCAS `POST /api/assistant/navigation`. SCAS revalidates contract, Tenant, Agent,
session, Origin, employee capability, and its explicit three-entry route
allowlist. The browser never consumes a URL from Olivia and navigates only when
an allowed `destination_id` resolves in its local map.

SCAS returns the following exact object as `function_call_output`:

```json
{
  "contract_version": "1.1",
  "request_id": "req-voice-123",
  "call_id": "call-provider-123",
  "decision_id": "decision-123",
  "tenant_id": "liquisto",
  "agent_id": "liquisto-assistant",
  "source": "voice",
  "intent": "navigate",
  "status": "allow",
  "destination_id": "crm.tasks",
  "parameters": {},
  "reason_code": "allowed",
  "decision_time": "2026-07-24T09:00:00Z",
  "message": "Ich öffne die aktuellen Aufgaben."
}
```

`status` is `allow` or `deny`. `reason_code` is one of `allowed`,
`request-invalid`, `tenant-denied`, `agent-denied`, `destination-denied`,
`session-denied`, `capability-denied`, or `authority-unavailable`. The Runtime
defines and tests this type for contract alignment, but does not pretend to
receive DataChannel events: SCAS is the decision, execution, and durable audit
authority. Structurally unreadable JSON may return `problem+json` because
request/call correlation is then unavailable.

For every parseable navigation decision SCAS evidence must contain Tenant,
server-bound principal, source, intent, destination ID, decision status and
UTC decision time, plus request/call/decision correlation and reason code. Raw
audio, transcripts, SDP, prompts, context content, secrets, and free URLs must
not be persisted. The Runtime call log records only safe session metadata and
`raw_audio_stored=false`; it does not claim that browser navigation occurred.

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
  "voice_enabled": true,
  "navigation_contract_version": "1.1",
  "navigation_destinations": [
    "workbench.cockpit",
    "crm.overview",
    "crm.tasks"
  ]
}
```

The authenticated response has exactly these keys and the destination order is
canonical. SCAS must hide Voice navigation when the attestation is absent or
different. The endpoint remains service-token protected and is not a public
readiness surface.

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
Authenticated `GET /readyz` validates the Olivia registry contract, the exact
singleton navigation tool, local configuration, and model availability before
returning contract v2.

## Navigation release gate

Do not deploy this slice until the compatible SCAS DataChannel handler,
same-origin navigation endpoint, server-bound employee principal, CRM read
capability check, local three-entry route map, exact decision/audit contract,
durable evidence retention, and joint runbook smoke tests are verified. A
provider session alone is not a navigation implementation.
