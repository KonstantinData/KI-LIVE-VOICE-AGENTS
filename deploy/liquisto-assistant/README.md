# Liquisto Internal Assistant Deployment

This deployment target runs only the authenticated Liquisto text-assistant API.
It does not expose widget, WebSocket, Voice, upload, CRM-write, or tool routes.

## Boundary

- Entrypoint: `src.api.liquisto_assistant_main:app`
- Runtime service: `liquisto-local-assistant:8080`
- Local LLM service: `liquisto-assistant-llm:11434`
- Production provider base URL: exactly
  `http://liquisto-assistant-llm:11434/v1`
- Network: pre-created isolated Docker network `liquisto-assistant`
- Public host port: none

Create the isolated network once on the runtime host:

```bash
docker network create --internal liquisto-assistant
```

The SCAS backend and the local OpenAI-compatible provider must join that same
network. Do not attach this service to a public reverse proxy.

## Required secrets and configuration

Provide these values through the deployment secret store, never repository
files or command history:

- `LIQUISTO_ASSISTANT_SERVICE_TOKEN`: shared SCAS-to-runtime Bearer token.
- `LIQUISTO_ASSISTANT_LLM_MODEL`: model identifier served by the local provider.

The compose file fixes `LIQUISTO_ASSISTANT_LLM_BASE_URL` to the only production
host accepted by runtime validation. `OPENAI_API_KEY` is neither required nor
used by this service.

The production provider timeout is 60 seconds. This covers bounded Cockpit
requests on the approved CPU-only host, where prompt evaluation can exceed 20
seconds even while the local model is already resident. Provider failures still
fail closed and never activate a remote or cross-tenant fallback.

## Verification

Liveness is intentionally unauthenticated and contains no configuration:

```bash
curl --fail http://liquisto-local-assistant:8080/healthz
```

Expected exact body:

```json
{"status":"ok"}
```

Readiness is authenticated and verifies that the configured model is visible
on the local provider:

```bash
curl --fail \
  -H "Authorization: Bearer $LIQUISTO_ASSISTANT_SERVICE_TOKEN" \
  http://liquisto-local-assistant:8080/readyz
```

Expected exact body:

```json
{"contract_version":"1.0","status":"ready","tenant_id":"liquisto","agent_id":"liquisto-lotse"}
```

This repository change intentionally does not perform a live deployment.

The SCAS runtime endpoint is exactly:

`http://liquisto-local-assistant:8080/assistant/respond`
