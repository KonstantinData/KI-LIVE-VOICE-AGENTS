# Anna direct owner and customer email

Implemented and enabled on 2026-09-25 at the owner's request.

## Delivery mode

`ANNA_DIRECT_SMTP=true` selects direct internal notification instead of the
legacy CRM endpoint, which also sends email. This prevents dual delivery.
The existing tenant, agent and tool authorization checks still apply.
The internal recipient, sender and login mailbox are fixed to
`kontakt@mein-kuechenexperte.de`. An optional customer summary goes only to the
single validated customer address confirmed during the call.

After explicit contact-forwarding consent, Anna sends the confirmed name,
return contact, request summary, reachability and optional notes to Konstantin.
A telephone number is sufficient for a callback; email is optional in this mode.
No transcript is attached. Customer email requires separate explicit
`customer_summary_consent_confirmed` and `email_confirmed` booleans. Anna asks
before the once-per-call submission; declining keeps callback intake available.
The customer receives only the agreed summary, not internal notes or transcript.
CRM capture is not claimed. Internal and customer SMTP outcomes are independent;
Anna must report partial acceptance honestly and must not repeat either send.
Caller lookup and CRM persistence remain separate implementation work.
The direct-mode prompt describes these actual capabilities and the reception role.

SMTP uses ssl0.ovh.net:587, verified STARTTLS, then authentication. Success means
SMTP acceptance, not proof of inbox delivery. Delivery is attempted once per
call; a confirmed or uncertain SMTP outcome is cached for that call. There is
no durable outbox or automatic retry after a process restart.

## Deployment and credentials

The owner maintains `/etc/anna/smtp.env` outside the repository. The directory
is root-only (0700); the file is root:10002 (0640), allowing Anna's container
group to read its read-only mount at `/run/secrets/anna_smtp`. No password is
stored in source, image layers or container environment variables.

Install `deploy/anna-server/compose.smtp.yaml` on the server as
`/opt/anna/deploy/anna-server/compose.override.yaml`. Default compose commands
then preserve the opt-in and the Anna-only credential mount. Asterisk is not
recreated. Rebuild and recreate only Anna after source changes.

Required file keys: SMTP_HOST, SMTP_PORT, SMTP_SECURITY, SMTP_USER, SMTP_PASS,
SMTP_FROM_EMAIL, CONTACT_EMAIL. The transport requires the fixed host, port,
starttls security and mailbox described above. Dotenv interpolation is disabled.

Rollback code and image: `/opt/anna/backups/smtp-20260925/` and
`anna-server-anna:before-smtp-20260925`. To restore legacy delivery, disable the
SMTP override and restore the previous code/image before recreating only Anna.
Do not expose credentials with compose config or environment dumps.

## Verification

132 telephony tests passed and Ruff passed, including SMTP TLS/authentication,
fixed recipients, sanitized errors, phone-only intake, consent gating, no CRM
request in direct mode, and truthful prompt/tool delivery semantics.
Live OVH authentication succeeded from the Anna image with the protected mount.
The running production container then invoked the actual handoff function with
synthetic test data and an empty transcript. OVH accepted the owner notification;
the result explicitly reported `crm_captured=false` and
`customer_summary_requested=false`. Inbox receipt and a real caller conversation
remain unverified. The test subject is `Anna: Neues Telefonanliegen` and its body
identifies it as a technical delivery test.

### Customer summary extension

The subsequent customer-summary extension passed 169 telephony tests and Ruff.
The updated production container sent both messages through the actual handoff
function with synthetic data and the owner mailbox as the test customer address.
OVH accepted both the internal notification and the customer summary; the result
reported both delivery flags true and CRM capture false. Inbox receipt and an
end-to-end real caller conversation remain unverified.
The pre-extension rollback image is
`anna-server-anna:before-customer-email-20260925`; source backups are in
`/opt/anna/backups/customer-email-20260925/`.
