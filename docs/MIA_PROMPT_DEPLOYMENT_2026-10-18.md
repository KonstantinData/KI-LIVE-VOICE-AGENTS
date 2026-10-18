# MIA prompt package deployment — 2026-10-18

Source commit: `257fddfe407b6ac464a98eb1d0dbf8566f2d6eb9`.
Branch: `codex/mia-phase-zero-20261014`.

The approved design journey and identity refinement were committed and the
offline MIA package was placed in `/var/www/ki-team/src/agents/mein_kuechenexperte/mia`
on `ki-team-prod-nbg1-01`. The parent MKX README was updated as well: ten files
were deployed, including the two existing package initializers needed for
imports. This is source-package delivery, not activation of a public MIA agent.

## Verification

- 470 core and telephone tests passed locally; Ruff passed for `src` and `tests`.
- A staged server-side check composed both prompts with production dependencies
  and registry data before source files were applied.
- The same check passed against the installed package: Du address mode, resolved
  concept label, internal quality-goal wording and truthful action boundaries.
- All ten deployed files matched their release SHA-256 hashes.
- Tenant registry content and the running API process ID were unchanged.
- The public API health endpoint returned HTTP 200.
- MIA remains absent from the live voice registry. No API restart, database
  migration, dependency update, widget release, Anna update or calendar restart
  was performed.

## Release and rollback

The protected release directory is
`/opt/ki-team-releases/mia-prompts-257fddfe407b`.
`manifest.json` records the exact file set, content hashes, previous-file hashes
or absence, registry hash and API process ID. `deployment-result.json` records
the result. Original files are in `backup`; staged source and the no-provider
composition check are retained alongside them.

Rollback restores only manifest-listed files from backup and removes only those
manifest-listed files that were previously absent. Do not replace the whole
production checkout: unrelated production changes remain in place.

## Remaining implementation boundary

Rendering, image-card UI, upload, download, secure continuation, storage,
handoff and booking are prompt requirements, not features supplied by this
package. A trusted availability binding, runtime/profile and application
integration are still required before MIA activation. These checks do not prove
model dialogue quality or a working public planning journey.

The operator's pre-existing local edit in `docs/mia/README.md` was excluded from
the release and remains untouched.
