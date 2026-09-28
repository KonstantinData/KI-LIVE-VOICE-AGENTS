# KEA contact handoff incident — 2026-09-27

## Evidence and ownership

The public widget submits to the runtime's `/voice/contact-handoff`, which
forwards to the website-owned `/agent-lead-webhook`. At 06:05:55 and 06:06:11 UTC,
runtime logs recorded upstream HTTP 500 and returned HTTP 502 to the widget.
The published PHP handler and its CRM dependencies matched the website checkout.
An authenticated empty payload returned the expected HTTP 400 without storage or
email side effects.

The website's SMTP configuration still selected `beratung@mein-kuechenexperte.de`.
Authentication to its configured OVH SMTP server failed with code 535. The existing
same-area `kontakt@mein-kuechenexperte.de` mailbox configuration authenticated
successfully against that server. The PHP handler's explicit customer-mail failure
branch returns HTTP 500 after capture persistence; the original request's stored
record and exact PHP exception were not inspected, so persistence is not claimed.

## Operational correction

Corrected the website host's root `.env`, `credentials/.env`, and `sender.php`
to use the verified contact mailbox for SMTP authentication, sender, and internal
contact destination. Credentials were handled only in memory and over encrypted
SSH/SFTP, never printed or written to the repository. Protected originals remain
at `/home/meinkum/.kea-smtp-repair-20260927` (directory 0700, backup files 0600).
Remote file readback verified the configuration updates. No runtime or CRM code
was changed for this repair.

## Verification and limits

Reloaded the actual website configuration and verified SMTP authentication and
acceptance of its envelope sender. Reset the transaction before any recipient or
message submission: no email was sent. A real contact-form submission and mailbox
delivery remain pending user verification. Do not label authentication success as
proof of end-to-end capture or email delivery.

A proposed full SQLite download was rejected by automatic approval review; it
was not executed. The investigation continued with code comparison and narrow
configuration/network probes without transferring the database.

## Follow-up

Track durable capture separately from notification failure in the website-owned
webhook, and make retries idempotent. The current handler can report failure after
successful persistence when customer email fails. This is a separate website
reliability task, not permission to import CRM logic into this runtime repository.
