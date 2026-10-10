# Liquisto Internal Assistant Deployment

This deployment target runs only the authenticated Liquisto assistant API for
text responses and internal WebRTC call brokering. It does not expose public
widget, WebSocket, upload, CRM-write, or tool routes.

The internal WebRTC session advertises exactly one provider function,
`open_liquisto_destination`. It carries only the semantic Navigation Contract
v1.2 documented in `docs/liquisto-assistant-runtime.md`; it is not an HTTP tool
route and cannot resolve URLs or mutate data.

## Boundary

- Entrypoint: `src.api.liquisto_assistant_main:app`
- Runtime service: `liquisto-local-assistant:8080`
- Local LLM service: `liquisto-assistant-llm:11434`
- Production provider base URL: exactly
  `http://liquisto-assistant-llm:11434/v1`
- Assistant network: pre-created isolated Docker network `liquisto-assistant`
- CRM attestation network: pre-created external Docker network with the fixed
  name `liquisto-crm`
- Voice egress: dedicated `liquisto-voice-egress` bridge; host firewall should
  allow only required HTTPS provider traffic.
- Runtime-to-CRM attestation: exactly
  `http://liquisto-crm-service:8080/internal/v1/assistant/navigation/attestations`
  on the shared internal network; no redirects or alternate hosts.
- Public host port: none

Create the isolated Assistant network once on the runtime host:

```bash
docker network create --internal liquisto-assistant
```

The local OpenAI-compatible provider must join `liquisto-assistant`. The SCAS
deployment must create and own the external `liquisto-crm` network and attach
`liquisto-crm-service` to it before this compose project starts. The Runtime is
attached to that network under its existing service identity; the network name
is not configurable and cannot redirect attestations to another tenant or
service. Do not attach this service to a public reverse proxy. When Voice is
enabled, restrict the egress network at the host firewall or egress proxy to
`api.openai.com:443`; it grants no inbound publication by itself.

## Required secrets and configuration

Provide these values through the deployment secret store, never repository
files or command history:

- `LIQUISTO_ASSISTANT_SERVICE_TOKEN`: shared SCAS-to-runtime Bearer token.
- `LIQUISTO_ASSISTANT_LLM_MODEL`: model identifier served by the local provider.
- `LIQUISTO_ASSISTANT_VOICE_ENABLED`: independent Voice kill switch; default false.
- `LIQUISTO_NAVIGATION_SIDEBAND_ENABLED`: provider monitoring kill switch;
  default false and required for Voice readiness.
- `LIQUISTO_OLIVIA_NAVIGATION_RUNTIME_TOKEN`: dedicated Runtime-to-CRM Bearer
  token with at least 32 bytes. It must differ from every Voice, Workbench, and
  provider token.
- `OPENAI_API_KEY`: required only when the internal Voice kill switch is enabled.

The compose file fixes `LIQUISTO_ASSISTANT_LLM_BASE_URL` to the only production
host accepted by runtime validation. `OPENAI_API_KEY` is used only by the
server-side internal Voice broker and is never returned to SCAS or the browser.
The Runtime token is sent only to the fixed tenant-local CRM attestation
endpoint and is never returned, logged, or exposed through readiness.

The production provider timeout is 60 seconds. This covers bounded Cockpit
requests on the approved CPU-only host, where prompt evaluation can exceed 20
seconds even while the local model is already resident. Provider failures still
fail closed and never activate a remote or cross-tenant fallback.

## Separate OpenAI mail candidate

The disabled synthetic mail pilot is documented in
[`docs/olivia-openai-mail-candidate.md`](../../docs/olivia-openai-mail-candidate.md).
It uses a separate key and signed purpose; this Compose file does not bind or
activate it. Existing local text, Voice, and Memory deployments are not changed
by preparing that candidate.

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
{"contract_version":"2.0","status":"ready","tenant_id":"liquisto","agent_id":"liquisto-assistant"}
```

Repository changes do not deploy themselves. Release this service only through
the controlled Runtime and SCAS gates below.

Do not deploy the navigation slice until the SCAS counterpart is verified with
the same byte-exact v1.2 schema, provider-authenticated sideband handling,
server-bound Voice session and principal, CRM read-capability gate, local route
allowlist, durable attestation/decision ledger, atomic idempotent completion,
and joint allow/deny/replay smoke tests. A real DataChannel plus sideband plus
CRM E2E is mandatory. Keep the existing production version running when any
gate is missing or any contract field differs.

The SCAS runtime endpoint is exactly:

`http://liquisto-local-assistant:8080/assistant/respond`

The employee-authenticated SCAS BFF creates Olivia WebRTC calls through
`http://liquisto-local-assistant:8080/assistant/voice/calls`. Keep
`LIQUISTO_ASSISTANT_VOICE_ENABLED=false` until that BFF is deployed and set
`OPENAI_API_KEY` only in this server-side service environment. The public widget
must not call this endpoint and must never receive either secret.

When Voice is enabled, SCAS verifies the dedicated readiness contract:

```bash
curl --fail \
  -H "Authorization: Bearer $LIQUISTO_ASSISTANT_SERVICE_TOKEN" \
  http://liquisto-local-assistant:8080/assistant/voice/readyz
```

Expected exact body:

```json
{"contract_version":"2.0","status":"ready","tenant_id":"liquisto","agent_id":"liquisto-assistant","channel":"voice","navigation_contract_version":"1.2","navigation_destinations":["workbench.cockpit","crm.overview","crm.tasks"],"voice_enabled":true}
```

This authenticated response is an exact release attestation. SCAS keeps Voice
navigation hidden when any key, value, or destination order differs.

Before enabling the two kill switches, verify that the externally managed
`liquisto-crm` network exists and that `liquisto-crm-service` is attached to it,
inject the same new Runtime token into both services through the approved secret
store, apply the SCAS durable-ledger migration, and prove that the CRM service
accepts the twelve-key attestation only from Runtime. These are external
deployment steps; this repository does not create the network, secret, or SCAS
database ledger.
