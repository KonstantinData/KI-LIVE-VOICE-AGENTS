# AGENTS.md - KI-LIVE-VOICE-AGENTS

This repository contains the tenant-scoped live voice and chat runtime for AI
agents embedded on customer websites.

## Current Repository Scope

This repo owns:

- FastAPI runtime for widget chat, WebSocket chat, Live Voice sessions, uploads,
  tenant config, and audit events.
- The embeddable widget in `frontends/widget`.
- Tenant registry and tenant-specific runtime profiles.
- Upload storage, upload analysis, upload retention, and signed upload access
  endpoints for authorized CRM users.
- Handoff clients that send sanitized contact, usage, and upload metadata to
  the CRM owned by the tenant website repository.

This repo does **not** own:

- CRM screens, dashboards, lead/contact/activity UI, cost reports, or CRM
  workspace navigation.
- CRM database schemas or CRM record derivation.
- external CRM implementation details beyond handoff contracts.

For `mein-kuechenexperte`, CRM code and CRM UI live in the separate
`mein-kuechenexperte` repository. This runtime may only communicate with that
CRM through explicit, configured handoff endpoints and signed upload access.

## Allowed CRM Boundary

The only CRM-related code allowed in this repository is integration code for:

- `CRM_CONTACT_HANDOFF_ENDPOINT` / `CRM_CONTACT_HANDOFF_SECRET`
- `CRM_USAGE_HANDOFF_ENDPOINT` / `CRM_USAGE_HANDOFF_SECRET`
- `CRM_UPLOAD_ACCESS_SECRET` or the configured contact handoff secret fallback
- webhook payload normalization and tests
- tenant-safe signed upload content streaming for authenticated CRM flows

Do not add CRM pages, lead CRUD routes, dashboard frontends, CRM migrations, or
tenant CRM business logic here.

## Runtime Structure

```text
KI-LIVE-VOICE-AGENTS/
├── src/
│   ├── agents/        # Runtime agent implementations
│   ├── api/           # Voice, upload, widget, WebSocket, handoff runtime
│   ├── core/          # Shared LLM, memory, knowledge, and tool interfaces
│   ├── db/            # Runtime-only models and migrations
│   └── tenants/       # Tenant profile loading
├── frontends/widget/  # Embeddable widget bundle
├── registry/          # Tenant registry and skill packs
├── schemas/           # Tenant/runtime contracts
├── tests/             # Runtime and handoff tests
└── deploy/            # Backend deployment assets and runbooks
```

## Development Rules

- Keep code, identifiers, docstrings, comments, commit messages, and technical
  docs in English.
- Keep German only for German end-user widget copy, prompts, and customer-facing
  text.
- Use `rg` for search.
- Use `apply_patch` for manual edits.
- Do not revert user changes.
- Do not store secrets in the repo.
- Tenant-scoped reads and writes must remain tenant-scoped.
- Handoff payloads must stay sanitized and purpose-limited.
- Uploaded files must not become public assets; CRM access must use signed,
  short-lived, tenant-checked links.

## Verification

Before marking repository changes complete, run the relevant subset of:

```bash
python -m ruff check src tests
python -m pytest tests -q
pnpm --filter ki-team-widget lint
pnpm --filter ki-team-widget build
```

For production deployment, use `deploy/RUNBOOK.md`.
