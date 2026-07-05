# ADR 0002: Tenant Runtime Profiles For Live Voice Agents

## Status

Accepted

## Context

The product is no longer a hard-coded "Lisa" assistant. `KEA` is the public
widget name for the `mein-kuechenexperte` tenant only. The backend needs a
tenant-aware structure that can select a Live Voice Agent profile, policies,
tools, knowledge scopes, upload rules, and widget copy per tenant.

The reference implementation in `skill-centric-agent-system` uses tenant
registries, role-derived runtime modules, immutable runtime profiles, policies,
and validators. This repository does not need the full control plane yet, but
it needs the same boundary: tenant configuration grants runtime authority, not
free-form prompt text.

OpenAI Realtime client secrets are short-lived credentials created by the
server with session configuration. The browser must not receive the standard
API key. The OpenAI Agents SDK also treats tools and guardrails as runtime
surfaces that can be enabled and validated through context. JSON Schema Draft
2020-12 is the matching contract format used by the reference repository.

## Decision

Add a small local tenant registry:

- `registry/tenants/<tenant>/tenant.json` is the authoritative tenant profile.
- `registry/modules/tenants/<tenant>/skills/<skill>/skill-pack.json` documents
  tenant-specific skill packs and required audit evidence.
- `schemas/tenant-live-voice-profile.schema.json` defines the profile contract.
- `src/tenants` loads and validates profiles into typed runtime objects.

Runtime code reads the tenant profile to determine:

- public widget name and welcome copy,
- Live Voice Agent display name,
- voice enablement and model/voice defaults,
- selected skills, tools, scopes, policies, and validators,
- upload and secure contact-handoff policy.

`KEA` remains tenant data for `mein-kuechenexperte`. The technical agent type is
`live-voice`.

## Consequences

The existing database `studios.config` remains for operational and historical
compatibility, but the tenant registry overrides public widget identity and
Live Voice Agent identity when a registry profile exists.

Future tenants can add a new `registry/tenants/<tenant>/tenant.json` and a
matching tenant skill pack without adding a new hard-coded agent package.

Sources checked:

- OpenAI Realtime client secrets and WebRTC guidance:
  https://developers.openai.com/api/reference/resources/realtime/subresources/client_secrets/methods/create/
- OpenAI Realtime guide:
  https://developers.openai.com/api/docs/guides/realtime
- OpenAI Agents SDK tools and guardrails:
  https://openai.github.io/openai-agents-python/tools/
- JSON Schema Draft 2020-12:
  https://json-schema.org/draft/2020-12
