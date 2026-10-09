# Olivia de Jong deployment, 2026-10-09

## Approved source and unchanged identity

The approved profile is recorded in the owning runtime repository at
`docs/olivia-de-jong-profile.md`, from attachment
`72aee51c-c3cf-4dde-a11e-198b36f18c1a/Eingefügter Text.txt`.
Source SHA-256:
`3ce4e70430301dd17044c378b7e8805a486ea2b2640df97e6bc79b4838bc5eec`.

Canonical scope remains `tenant_id=liquisto`, `agent_id=liquisto-assistant`,
`audience=internal-authenticated`. No second agent or memory namespace exists.
The profile email `olivia@liquisto.claud` is preserved exactly as approved;
this release does not provision or attest a mailbox.

The persona describes internal ERP/process/data-governance/task support and
channel-specific style. Existing `inform-and-prepare`, `draft-only`,
`not-executable` and navigation-only boundaries remain authoritative. Illustrative
task-completion examples grant no Todoist, Slack, email or ERP write authority.

## Runtime target and exact preservation

- Runtime host: `scas-runtime-prod`, `178.105.62.169`.
- Container: `liquisto-assistant-liquisto-local-assistant-1`.
- Initial memory-enabled base:
  `sha256:6f91a8f7680eab7411dc8defeb799fb3ba93a052c8e6ecde4e9af0821013d36b`.
- First persona image:
  `sha256:f112dbb2dac7365cd06723d304a94ab5eda2bd66094a58b82737fc6779ee8069`.
- Persona JSON-contract image:
  `sha256:2252ffc6b9aff36231bd1d1c326f2b8fe14569eb81f3fb4a985af77677f74e6e`.
- Provider fence-normalization intermediate image:
  `sha256:a6311419c7e46df930a6fd6d2524422aefc093cffc18a5237ff67bf2a1f26c68`.
- Provider JSON-mode intermediate image:
  `sha256:b54cf894133e89e7b589a7e19c1ac3204b71c60d82541bf7888b8e390e0d515b`.
- Full-schema intermediate image:
  `sha256:f5defd505744b02ca2c0c8b06b963124f85667659340d49738c6d8d7549c87d5`.
- Compatible-generation intermediate image:
  `sha256:359d9bea70e1f1bc4166470161b86fd69dfa2fd3b1aafa02791a823d2e37f485`.
- Final image with no-source draft restriction:
  `sha256:62d21cbfa33540e72de32a1e986d650f30ff8056ba27a2fc34ee31b0846e6636`.
- Tag: `liquisto-assistant-liquisto-local-assistant:olivia-de-jong-20261009`.
- Shared prompt SHA-256:
  `f2cf4c95a77ef4b0ab863c30df4f7d38a3e81a58ec0408a89c8c5a75a9e21beb`.
- Liquisto registry SHA-256:
  `a0a3cb1d5270c17ab004e81fe44f5ca6f7f047129e2b06b33b12a1c1519da5d2`.

The first real model answer contained the new identity but used a Markdown JSON
fence, which the existing API correctly rejected (`json_invalid`, HTTP 502).
The final shared prompt strengthens the existing text JSON contract: first/last
characters must delimit a JSON object, no fences or surrounding text, and an
explicit no-action self-introduction example. Prompt instructions alone did not
reliably stop the local model's fences or occasional plain-text replies.
JSON-object mode eliminated formatting errors but a real response still failed
the action contract with `literal_error`. The final provider adapter requests
`response_format.type=json_schema`, using `ProviderDraft.model_json_schema()`
directly from the authoritative existing route contract. Its deferred import
avoids an import-time cycle. The installed Ollama 0.32.1 rejects the complete
schema as an invalid generation grammar (HTTP 400). A bounded synthetic probe
proved that removing only `minLength`, `maxLength`, `minItems`, `maxItems` from
a fresh generation-schema copy restores HTTP 200. Patterns, date-time formats,
required fields, references, literals/enums and `additionalProperties=false`
remain in constrained generation. The full independent `ProviderDraft`
validation retains every size bound, source subset, timezone and uniqueness
check; no response field is filled, coerced or silently accepted.
The adapter also removes only
one complete `json` Markdown fence; surrounding prose, multiple fences, malformed
JSON, unexpected fields and invalid actions remain rejected. The existing
`ProviderDraft` schema and source/authority validation are unchanged.

A subsequent valid JSON reply failed the existing source-subset validation:
the model invented a draft/source for a self-introduction with empty request
context. The final generation schema additionally sets `prepared_actions.maxItems=0`
only for the server-built empty context suffix. It recognizes an optional
complete native untrusted-memory envelope, validates its JSON shape and never
reads memory as authority. The exact pinned hook escapes memory delimiters.
Tests include empty/nonempty contexts, an earlier fake user marker and complete
or malformed memory envelopes. Nonempty source contexts retain draft generation;
all downstream source/permission validations remain unchanged.

Provider adapter SHA-256:
`1d348ae123d2b16945f7aa15e91a57d71693b0f1e6dc6820ed8ddb6fe587a6f4`.
Its dedicated one-file overlay preserves the exact persona image and all native
memory hooks. Its separate guard checks this fixed baseline and the adapter pin.
The structured-output parameter is supported by the provider's
[official OpenAI compatibility contract](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx).
It grants no tool or business capability; downstream schema/source checks remain
the authority. Synthetic tests reject surrounding prose, multiple fences,
unexpected fields and incomplete actions and assert the exact authoritative
compatible generation schema request. Semantic source IDs, timestamps and permissions still undergo
the existing independent route validation.

Each persona overlay copies only `src/agents/liquisto_assistant/prompt.py` and
`registry/tenants/liquisto/tenant.json`. Registry changes are limited to display
names and greeting. The guard checks exact image/file pins, permitted layers,
registry semantic delta, current hashes and post-switch configuration equality.

Unchanged installed file hashes:

| File | SHA-256 |
| --- | --- |
| `src/api/routes/assistant.py` | `8b58a96b58957f73e8b88c71cf0dd4e476a76984654af97ce67f5cea42e240a6` |
| `src/api/services/identity_memory.py` | `c46d665f3be69f30ae101ddea20331c0a36c6b89de66649b80945e7a1e2c5c1b` |
| `src/api/liquisto_assistant_main.py` | `08930fba12e9e0fdaf56282c7728de61e6b31715e525078b7057cc29ff31cbc3` |

The previous containers remain stopped for rollback. Runtime environment values,
mounts, credentials, HostConfig, ports, four private networks and routing were
preserved. CRM, Workbench and the local model were not replaced. The historical
memory-installation guard remains unchanged; the persona guard has a closed
selection of the two inspected baselines rather than an arbitrary base override.

## Append-only Identity Core

The memory host remains `ki-team-prod-nbg1-01`, `46.225.221.42`, service release
`20261008-mvp02`. No memory-service restart or database migration was necessary.
The operator inspected revision **1** and appended **2** using
`PostgresMemoryStore.register_identity()` and protected owner credentials in a
one-off operator container. Ordinary API/worker containers received no owner
credentials. No UPDATE/DELETE, forget, reset or namespace migration was used.

Only name, role, self-description, style, values, source reference and revision
changed. Technical Core fields were copied from the live version. The sealed
SCAS authorization profile and its expiry `2027-01-06` remain unchanged.

A private logical backup completed before writing. Private before/after receipts
compare every scoped episode, assertion, evidence record, reflection batch,
retired event/batch and prior identity version. They confirmed exact preservation.
The scope contained zero active episodes/assertions, three retired events and
two retired batches before the update; no existing user data was removed.

## Verification levels

The existing native acceptance check passed after deployment: fresh SCAS authority,
sealed binding, signed memory reads, actual text/Voice hooks, unchanged tools,
wrong-digest/foreign-subject rejection and the guarded synthetic
capture/recall/forget/replay lifecycle. Existing and concurrent personal-context
guards remain unchanged; only the test's synthetic preference was cleaned up.

Local verification counts are recorded with the final verification below. PostgreSQL verification
passed 17 tests against isolated `cim_acceptance`, including append-only identity
and restricted runtime/operator rights. Ruff passed the changed owning-runtime
surface and the complete memory repository.

The native check stops before provider transport. Voice instruction construction
and memory inclusion are backend initialization evidence, not an audio call.
Browser-to-BFF and actual end-user Voice acceptance remain open: Chrome discovery
failed to start its Codex app-server (`os error 3`), and no authenticated browser
session was available. The real native text request is reported separately below.

### Final observed evidence

| Surface | Observed result |
| --- | --- |
| Real native text | HTTP 200 through `/assistant/respond`, actual local model, fresh SCAS authorization and signed memory attestation; answer includes Olivia de Jong, zero prepared actions |
| Ordinary text memory | Exact context equality before/after the real request; no preference capture |
| Native text/Voice backend | Existing `native_olivia_acceptance.py --execute` passed after the final image: signed reads, capture/recall/forget/replay checks, cleanup, fresh authority and unchanged tools |
| Voice initialization | New shared persona and memory included in the native Voice-init instructions; no real provider/audio conversation |
| Productive Identity Core | Protected operator inspection confirms revision 2, Olivia de Jong and unchanged technical core |
| Owning runtime local tests | 143 passed; changed-surface Ruff passed |
| Memory README/CI local tests | 209 passed, 41 subtests passed; 17 PostgreSQL tests skipped locally and separately passed against isolated server database `cim_acceptance`; full repository Ruff passed |
| Browser/Voice end-user acceptance | Not performed; browser discovery app-server failed with `os error 3`; authenticated browser session unavailable |

The final productive scope still has zero active episodes/assertions/evidence/
reflection batches. Retired event count grew from 3 to 8 only through the
guarded acceptance tests' own synthetic cleanup; retired batches remain 2.
The append's private before/after receipt already proved preservation of all
pre-existing rows and identity history. No user record was deleted to prepare
an acceptance test. Current revision remains 2; the inspection's suggested next
revision 3 was not written.

The final image pin is installed in the existing server Compose memory override.
The final deployment guard reports identical configuration and preserved persona,
registry and native memory-hook hashes. Previous stopped containers remain for
rollback. No new tools, executable actions, memory principals or permissions were
introduced.

## Repeatable procedure and future recreation

Build `integrations/olivia-persona-overlay.Dockerfile` from a local tag pinned to
the reviewed memory-enabled image; do not replace the deployed runtime with a
plain repository image that omits memory hooks. Run
`scripts/recreate_olivia_persona_safely.py --inspect` with exact new image/prompt/
registry pins, then the same arguments with `--recreate`. `--baseline persona-v1`
is only for the recorded JSON-contract follow-up image.
The final provider-format overlay uses the separately fixed
`scripts/recreate_olivia_provider_format_safely.py`; it permits no persona,
registry, memory-hook or permission change. Its closed `provider-json-v1`
baseline selects only the recorded JSON-object image and adapter for the final
schema follow-up. `provider-schema-v1` selects only the recorded full-schema
image/adapter for the compatible-generation follow-up. `provider-grammar-v1`
selects the recorded compatible-generation image/adapter for the no-source
draft follow-up.

The server's existing memory override is pinned to the final immutable image
for subsequent Compose recreation. Keep its private network, protected memory
env file, relay host entry and binding mount. Rollback must retain those settings
and use a reviewed persona compatible with Identity Core revision 2; do not
delete identity history or user memories to restore a prior display name.

`scripts/update_olivia_identity.py --mode inspect|append|verify` keeps the technical
core fixed and requires an explicit expected revision for append. Receipts stay
in the protected operator directory. Ordinary chat/Voice remain read-only and
capture/forget remain the existing closed authenticated preference operations.
