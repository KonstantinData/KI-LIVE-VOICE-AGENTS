# Proposed MIA operations runbook
Status: preparation only. Do not execute production changes from this proposal.

## Isolated development
Use C planning branch and one separate worktree per implementer. W original dirty checkout is read-only; obtain clean verifiable source without deleting unknown refs, then explicitly reconcile dirty design.
Local FastAPI + local widget + PHP website + CRM test adapter; synthetic fixtures, fake calendar/CRM/provider by default.
Disposable test schema/database on existing local PostgreSQL engine or approved local container, private scratch media. No production credentials, DB/uploads/WAL/state mounts.
Candidate nonconflicting loopback ports: API 18080, widget 15173, PHP 18081, CRM test 18725; verify free before use. No public staging domain required for deterministic rehearsal.
Real provider calls require explicit bounded budget; real CRM/calendar only approved synthetic test destinations.
Existing KI-TEAM host staging is a production-host mutation and needs scoped authorization. No additional server or storage volume established as necessary.

## Proposed limits
Default-off independent MIA/voice/image/handoff/booking switches. Their final setting names belong in schema/config docs during implementation.
- Voice hard maximum 5min, discovery target2-3min measured separately.
- One initial image + max5 successful edits; one active generation/project.
- 3 uploads/session, 10MiB/file, 30MiB/session; separately bound PDF pages/decoded pixels/CPU.
- Initial2 concurrent MIA sessions / 1 generation worker.
- Max24 model operations/session;1 known-transient retry within original reservation.
- Provider deadline120s is an initial candidate, not success SLA; timeout may be outcome_unknown.
- Worker ceiling1 CPU/1.5GiB RAM; project-media cap1GiB candidate.
- Proposed demo retention7d, opt-in resume30d; production policy independently approved.
- Monetary caps remain unset/disabled until concrete budget/pricing approved. Unknown billing cannot be treated as zero.

## Job operation
Persist lease/attempt/provider request ID/reservation before dispatch. Reconcile stale in-flight job; do not replay ambiguous paid operation automatically.
Cancellation stops new attempts and publication; retain last complete revision. Do not claim refunded spending.
Outbox handoff retries use same event/payload hash and original receipt. Mail failure cannot erase persisted intake or trigger second lead.
Single leased cleanup owner; abandoned sessions and grants expire under approved policy.

## Operational acceptance
30min load at proposed concurrency: no OOM, >=2GiB remaining host RAM, disk<80%, no lost completed revisions.
20 simultaneous requests at one remaining quota -> exactly one provider dispatch.
MIA switch blocks new dispatch within5s; KEA/Anna remain operational; proposed p95 regression <=10% relative to measured baseline.
Synthetic encrypted DB+media backup restored isolated; verify hashes/counts/ownership/delete markers/resume revocations.
Rollback rehearsal target10min; proposed RPO24h/RTO60min need owner approval and proof.
Alerts: queue lease/timeout, provider errors, budget exhaustion, disk threshold, retention failures and outbox backlog. Logs contain opaque refs and minimized metadata, no customer transcript/audio/tokens.

## Release and rollback
Before requesting user approval prepare exact repos/SHAs/file hashes/routes/services/migrations/config changes, target CRM/calendar, backup+restore receipts, reversible migration compatibility, monitored rollout/kill-switch proof and independent QA/security report.
Website OVH/SFTP, widget Cloudflare and runtime/CRM Hetzner are separate releases. No full-sync deletion; exact allowed file/service set only.
No runtime CRM migration or tenant database repurposing. Existing DKH remains unrelated.
Rollback restores application version and flags without deleting production DB/media or using down -v. Do not destructively roll back migrations; compatibility/recovery procedure must be tested.
Explicit production activation approval is mandatory. Source commit/PR, installed service, enabled flag and actual live acceptance are separate states.
