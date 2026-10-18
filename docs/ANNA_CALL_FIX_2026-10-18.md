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
