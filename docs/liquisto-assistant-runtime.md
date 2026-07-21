# Liquisto Lotse Internal Runtime

## Purpose

`Liquisto Lotse` is an internal, tenant-scoped text assistant for the Liquisto
Cockpit, CRM, Trade, and Control surfaces. It is not a browser widget and it is
not a Live Voice Agent. The only integration path is an authenticated
service-to-service HTTP request.

The runtime is analysis-only:

- no runtime tools;
- no CRM, Trade, Control, or other writes;
- no external web access;
- no fallback to the generic OpenAI settings or cloud endpoint;
- no storage of prompts or raw request-context snapshots;
- no cross-tenant registry, prompt, knowledge, identity, or consent fallback.

## Request contract

`POST /assistant/respond` requires
`Authorization: Bearer <LIQUISTO_ASSISTANT_SERVICE_TOKEN>` and this exact body:

```json
{
  "contract_version": "1.0",
  "tenant_id": "liquisto",
  "area_id": "liquisto",
  "agent_id": "liquisto-lotse",
  "request_id": "req-123",
  "principal_id": "user-123",
  "conversation_id": null,
  "prompt": "Welche Abweichung soll ich zuerst prüfen?",
  "surface": "cockpit",
  "mode": "analysis-only",
  "context": [
    {
      "source_id": "source-a",
      "label": "Betriebslage",
      "content": "Lieferstatus weicht vom bestätigten Termin ab."
    }
  ]
}
```

`surface` is one of `cockpit`, `crm`, `trade`, or `control`. Context is bounded
to 12 entries, 4,000 characters per entry, and 20,000 aggregate content characters. Identifiers are
limited to 200 characters and source identifiers must be unique. Unknown fields and contract,
tenant, area, agent, mode, or surface mismatches fail closed.

The normalized prompt must contain 2 to 1,200 characters.

## Response contract

```json
{
  "contract_version": "1.0",
  "request_id": "req-123",
  "response_id": "resp_...",
  "conversation_id": "conv_...",
  "mode": "analysis-only",
  "answer": "...",
  "sources": [
    {"source_id": "source-a", "label": "Betriebslage"}
  ]
}
```

If `conversation_id` is supplied, it is echoed. Otherwise the stateless runtime
creates an identifier for response correlation. It does not persist a
conversation or raw request context.

Answers are limited to 6,000 characters. Oversized provider output fails closed
and is never silently truncated.

## Local provider policy

The runtime uses a minimal OpenAI-compatible `/chat/completions` adapter. It
does not instantiate the repository's cloud `LLMClient`.

Required environment variables:

- `LIQUISTO_ASSISTANT_SERVICE_TOKEN`
- `LIQUISTO_ASSISTANT_LLM_BASE_URL`
- `LIQUISTO_ASSISTANT_LLM_MODEL`

Production accepts only
`http://liquisto-assistant-llm:11434/v1`. Development and tests accept only
`http://localhost:<port>/v1`, `http://127.0.0.1:<port>/v1`, or the IPv6 loopback
equivalent. Credentials, query strings, fragments, HTTPS cloud hosts, other
service names, and paths other than `/v1` are rejected.

The service token must be non-empty and must not contain whitespace. It is
compared exactly and is never trimmed.

Only request identifiers, response identifiers, surface, and source count are
logged. Prompt text and context contents are not logged or persisted.

## Health contracts

- Unauthenticated `GET /healthz`: exact body `{"status":"ok"}`.
- Bearer-authenticated `GET /readyz`: validates configuration and local model
  availability, then returns the exact contract documented in the deployment
  runbook.

The production container uses `src.api.liquisto_assistant_main:app`, which
registers only these health endpoints and `/assistant/respond`.

SCAS reaches the runtime only over the isolated external Docker network
`liquisto-assistant`, using the exact endpoint
`http://liquisto-local-assistant:8080/assistant/respond`.
