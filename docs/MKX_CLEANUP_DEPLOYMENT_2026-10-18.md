# MKX cleanup deployment — 2026-10-18

## Release

Source commit: `d3d51a4195f2290f48119e04d1e0c49bd7b57a4e`
(`refactor(mkx): separate agent content and namespace Anna`).
Branch: `codex/mia-phase-zero-20261014`.

The API, Anna phone worker, and Anna calendar service were deployed on
`ki-team-prod-nbg1-01`. MIA remains an offline planning package and was not
activated. No frontend, dependency, database schema, tenant ID, agent ID,
telephone number, calendar grant, or conversation-policy change was deployed.

## Production source preservation

The API checkout remains based on `18d0fdd1e7ec806180e54d56eef300e3e0f3f014`.
This release applied an explicit 31-file source overlay, not a complete Git
checkout update. Existing production CIM additions in voice sessions, the KEA
text flow, and telephony profiles were preserved while updating namespaces.
Obsolete source modules were removed after the API passed its health check.

Anna and the calendar service had production changes beyond the local source
baseline, including CIM integration and calendar coordination. Their replacement
images were built from the previously running images and migrated namespaces
without replacing those changes. The corresponding host source trees were also
migrated with their production changes preserved. Deployment manifests record
the resulting files and hashes; adapted production files are not claimed to be
byte-identical to the source commit.

| Component | Active release |
| --- | --- |
| API | Source overlay; `ki-team-api` restarted successfully |
| Anna | `mkx-anna:d3d51a4195f2` |
| Calendar | `mkx-calendar:d3d51a4195f2` |

Existing Compose layers, environment, mounts, and runtime users were preserved.
Only the worker and calendar containers were recreated. Asterisk was not
restarted; its start timestamp remained `2026-09-25T17:28:35.625645533Z`.
No active calls were present before the worker restart.

## Verification

- Local relevant regression suite: 630 tests passed; Ruff passed. See the
  implementation and Anna migration records for the local verification scope.
- Staged API application imports and KEA role checks passed.
- Both replacement images passed isolated import checks before activation.
- All 31 API overlay files were hash-verified after deployment.
- Public API health and MKX widget configuration returned HTTP 200; the widget
  identifies KEA and retains voice and upload capabilities.
- A public KEA WebSocket conversation received its greeting and an assistant
  response. The synthetic conversation was closed and its summary persisted.
  Visitor marker: `mkx-release-smoke-d3d51a4195f2`. No CRM handoff was triggered.
- Calendar health returned HTTP 200 in production mode.
- Both deployed containers were running with restart count zero and the source
  commit release label.
- Anna's SIP endpoint and contact were present and idle (`Not in use`). The
  contact reports `NonQual`; this is not an OPTIONS reachability measurement.

No real telephone call, provider voice session, or calendar booking was tested.
Health, registration, imports, and text chat do not establish those end-to-end
outcomes.

## Evidence and rollback material

The durable server archive is
`/opt/ki-team-releases/mkx-cleanup-d3d51a4195f2` (mode `0700`). It contains the
deployment manifests, API backup, preserved host source backups, image build
material, `api-deploy-result.json`, `final-verification.json`, and
`chat-smoke-result.json`. The original working release directory is
`/var/tmp/mkx-cleanup-d3d51a4195f2-r2`.

Previous images remain tagged:

- `mkx-anna-before:d3d51a4195f2`
- `mkx-calendar-before:d3d51a4195f2`

The added Compose image overrides are:

- `/opt/anna/releases/mkx-cleanup-d3d51a4195f2/compose.namespace.yaml`
- `/opt/anna-calendar/releases/mkx-cleanup-d3d51a4195f2/compose.namespace.yaml`

A rollback must restore the backed-up host/API sources and previous images using
the preserved full Compose configuration, including all existing production
overrides. Check for active calls before recreating Anna. Do not restart Asterisk
for a worker-only rollback.
