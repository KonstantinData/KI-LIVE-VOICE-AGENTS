# KEA website knowledge refresh — 2026-09-27

## Scope and source

Active area: mein-kuechenexperte.de. The tenant knowledge snapshot reflects the
current public website, including independent kitchen and adjacent-room planning,
individually agreed scope and fees, the free introductory conversation, service
boundaries, documents, and the current public email address. Source URLs and review
date are recorded in the knowledge chunks and their README.

The public widget text path uses `KeaTextFlow`, not the general LLM prompt. Direct
website questions now use the curated tenant chunks. The old fixed EUR 42.80
answer was removed. Voice prompt guidance no longer promotes a free professional
check, obsolete packages, or the former consulting app. Website document upload
after approval is distinguished from optional widget upload for AI intake.

## Verification

- Local: 37 tests passed across tenant knowledge, base-agent prompts, tenant
  registry, deterministic text flow, and voice routes; Ruff passed for changed
  Python files.
- Production-baseline staging: 23 tests passed across tenant knowledge, text
  flow, and voice routes using the server environment.
- After publication: service active; origin and public health returned 200;
  deployed file hashes matched the release manifest.
- The deployed realtime configuration contains the new knowledge and no old
  fixed-price, free-check, or consulting-app claims. No paid provider session or
  spoken conversation was created for this check.
- Public WebSocket verified with four synthetic questions: former strategy-check
  price, Backkitchen planning, delivery/assembly boundaries, and email address.
  No contact form was submitted. Python's default HTTP user agent received 403
  from the public edge; a normal browser user agent returned 200 and the WebSocket
  questions passed.

## Targeted publication

The running server baseline was `eb97b0938f11e4d0315e7487cf27c626aa37b157`,
older than the local checkout. Only the two knowledge files, four shared prompt
files, text-flow service and nodes, the text-flow test, and the server's existing
voice-prompt wording were published. The newer local `voice_sessions.py` was not
copied wholesale: its equivalent business wording was applied to the older
server's `voice_prompt.py`, preserving the deployed API and tenant routing.

Every preimage was verified before writing. Original files and a before/after
SHA-256 manifest are in `/var/backups/ki-team-kea-website-20260927`. The service
`ki-team-api` was restarted to clear cached knowledge. Existing voice sessions
may retain their original provider context; start a new conversation.

No commit or PR was created. The release is a documented working-tree patch on
the server; reconcile these files before a future Git-based release. Existing
local Anna, CRM-handoff, model, and tenant-profile work was not published.

## Separate follow-up

The legacy Python studio-knowledge fallback contains demonstration business
details. Normal KEA routing uses the registry snapshot and does not load those
details. Replacing that fallback with a safe missing-knowledge response is a
separate hardening task, tracked in the repository's Notion issues.
