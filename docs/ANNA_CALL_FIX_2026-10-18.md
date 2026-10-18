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

## Dedicated SMTP identity correction

The operator clarified that Anna owns `anna.weber@mein-kuechenexperte.de`.
Commit `6028eaebf854e22308c3baa994efa646fc953ef0` separates that SMTP login and
sender identity from the fixed operational recipient
`kontakt@mein-kuechenexperte.de`. Customer mail continues to reply to the
operational mailbox. The full telephone suite again passed 409 tests; targeted
Ruff passed.

The operator updated the protected secret. A subsequent check found a typo in
the public login field and a changed operational recipient. Only `SMTP_USER` and
`CONTACT_EMAIL` were corrected after a protected server-side backup; the
password was retained unchanged and never printed. The corrected public
configuration validates, but the no-send authentication probe still fails.

Both services now use derived images `mkx-anna:mailbox-6028eaebf854` and
`mkx-calendar:mailbox-6028eaebf854`. Existing production mail functions were
preserved using narrowly matched identity replacements. Four source invariants
were checked for each service: matching host/container source hashes, unchanged
environment values, unchanged mounts, and unchanged runtime user. Both containers
are running with restart count zero; Asterisk was not restarted. A verification
attempt rolled back before mount-list comparison was made independent of order;
the subsequent activation passed.

The deployment record and rollback images are recorded under
`/opt/anna/releases/mailbox-6028eaebf854`. The protected SMTP backup is not a
repository artifact. No email was sent. Provider authentication for Anna's own
mailbox remains the blocking acceptance gate.

## Configured implicit TLS support and network diagnosis

The operator selected `SMTP_PORT=465` and `SMTP_SECURITY=SSL` and confirmed
successful webmail login. The application previously rejected this valid TLS
mode before connecting. Commit `9019be859c3ac54a447ff4d7f5c7ab45718f3f2c` fixes
that restriction: 465/SSL uses `SMTP_SSL` with certificate verification;
587/STARTTLS remains supported. Insecure or mismatched port/mode combinations
remain rejected. All 412 telephone tests and targeted Ruff passed.

Both services were deployed using derived images
`mkx-anna:tls-9019be859c3a` and `mkx-calendar:tls-9019be859c3a`. Their source hashes,
running state, environment values, mounts, users, and accepted SMTP configuration
were verified. Asterisk was not restarted. Release and rollback records are in
`/opt/anna/releases/tls-9019be859c3a`. The protected SMTP configuration was not
changed during this TLS correction.

The remaining failure on the configured port occurs before authentication:
TCP connections from the production host to `ssl0.ovh.net:465` time out.
The same endpoint completes verified TLS from the operator workstation.
Production host port 587 connects and completes STARTTLS, but an independent
no-send test with the current credentials still returns SMTP 535 there.
Webmail success therefore does not establish SMTP authentication from this host.

The host's UFW policy allows outbound traffic, iptables OUTPUT accepts traffic,
and no relevant local blocking rule was found. The port-465 behavior is
consistent with Hetzner Cloud's documented default outbound SMTP restriction;
the specific account-level restriction has not been inspected in its control
panel. See [Hetzner Cloud FAQ](https://docs.hetzner.com/de/cloud/servers/faq/).
Provider-side port 465 access must be resolved before testing authentication with
the selected production transport. No message was sent by any diagnostic test.
