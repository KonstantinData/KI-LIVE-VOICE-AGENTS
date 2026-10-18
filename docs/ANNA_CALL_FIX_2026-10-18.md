# Anna call failure remediation — 2026-10-18

## Observed failure and verification

The operator's real test call failed twice at `find_free_slots` with
`invalid_datetime`, followed by an unconfirmed internal email handoff. No caller
transcript or contact details are retained in this record.

A separate read-only production search using date-correct Europe/Berlin offsets
and the configured appointment duration returned three morning appointments.
The original tool arguments were not logged, so the exact malformed date value
cannot be reconstructed. A no-send SMTP probe reached authentication and failed
with `SMTPAuthenticationError`, code 535. The mounted secret exists and its
configuration and password formatting checks passed; this does not establish
that the credential is accepted by the provider.

## Changes

- Search-only date normalization accepts ISO dates and unambiguous local Berlin
  datetimes, resolving each boundary's offset independently across DST changes.
  Wrong explicit Berlin offsets produce correction arguments and a single
  instructed retry. Malformed, nonexistent, or ambiguous local times produce
  actionable validation errors. Availability and write validation stay strict.
- Tool descriptions distinguish input errors from calendar outages and remove
  the fixed summer-offset example.
- Anna must not offer another send or repeat consent after failed or uncertain
  delivery in the same call. She gives the fixed public email alternative,
  distinguishes partial outcomes, and cannot promise a personal response.
- Failed direct delivery explicitly returns `delivery_not_confirmed`,
  `retry_automatically=false`, and next-step guidance. The existing per-call
  result cache continues to prevent duplicate sends.
- SMTP authentication errors have a distinct sanitized code. Internal email
  failure logging includes only an allowlisted error classification, never
  provider replies, credentials, or customer data.

## Acceptance and remaining gate

The complete telephone test suite passed: 409 tests. Ruff passed for `src` and
`tests`. Tests cover DST transitions, correction/rejection paths, partial email
outcomes, sanitized authentication failures, and assembled prompt instructions.

The operator must repair the mailbox access and update `SMTP_PASS` only in the
protected server secret `/etc/anna/smtp.env`. Do not place credentials in chat,
Git, logs, or this document. This correction does not claim to restore email
delivery while authentication is rejected.

After secret repair, repeat the no-send authentication check. A fresh real call
must then verify date selection and conversation closure. Actual message
delivery and booking remain separate acceptance steps; none were triggered by
the diagnostic probes.

## Production deployment

Commit `c3fb7e8f83535ec957baa21d80a91c0223b0f1e6` was deployed in
`mkx-anna:call-fix-c3fb7e8f8353`, derived from the active production image.
The four-file patch preserves existing production CIM and diagnostic additions.
The running container and host sources were hash-verified; the environment
values, mounts, and runtime user were preserved. Asterisk was not restarted.

An isolated, network-disabled image check verified DST handling, assembled prompt
instructions, and a simulated failed handoff with retries disabled. A subsequent
read-only live search through the deployed `PhoneCalendarTools` accepted local
datetimes without offsets and returned three morning appointments. Anna's SIP
endpoint and contact were present and idle after activation.

Deployment manifests, patched source, original host files, and verification
results are in `/opt/anna/releases/call-fix-c3fb7e8f8353`. The image override is
`compose.call-fix.yaml` in that directory. The previous image remains available
as `mkx-anna:before-call-fix-c3fb7e8f8353`; the original full Compose file list is
recorded in `before.json`. Check active calls before any rollback, restore host
files from `host-backup`, and recreate only Anna with the prior Compose layers.

The first activation verification rolled back because it compared environment
list ordering. Verification was changed to compare environment names and values
independently of ordering; the subsequent activation passed. No call was active
at either restart. Mail authentication is still pending operator secret repair;
no real message or booking was submitted during this release.
