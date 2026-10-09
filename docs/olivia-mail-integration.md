# Dedicated Olivia employee mail transport

Status: implemented as an isolated review candidate; not wired into production,
not an autonomous inbox processor, and not a conversational mail tool.

## Ownership and authorization

The KI-LIVE-VOICE-AGENTS runtime owns the proposed narrow transport module
`src/api/services/liquisto_mail.py`. It holds no CRM business logic and neither
replaces nor widens the existing productive multi-account SCAS mail connector.
The host must use an independently composed and verified immutable SCAS mail
profile. There is still one SCAS runtime agent.

Confirmed scope from the user:

- Sender/mailbox: `olivia@liquisto.cloud`, already existing at OVH.
- IMAPS: `ssl0.ovh.net:993`, certificate-verified TLS.
- SMTP: `ssl0.ovh.net:587`, certificate-verified STARTTLS before authentication.
- Autonomous work-related transmission is authorized only to
  `konstantin@liquisto.com`, `konstantin.milonas@condata.io`, and
  `aernout@liquisto.com`.
- No `liquisto.com` mailbox administration or domain-wide routing changes are
  part of this work. The earlier .com/Google DNS finding is superseded for
  Olivia's actual .cloud mailbox; no Google routing change is necessary.

The authorization is bounded by actual employee/data-role grants. It does not
authorize selecting any Liquisto record or disclosing every report. An email
address, inbound From/Reply-To, persona statement, or ordinary conversation is
not a runtime grant or proof of employee identity.

## Transport behavior

- Every metadata check or send first requires a host-verified immutable profile
  matching Liquisto, its assistant, the fixed mailbox, versioned mail policy,
  permitted capability, and a subset of the exact three allowed recipients.
- The host verifier must check an authoritative existing SCAS seal, current
  membership/grants, task binding, and data-output authorization. Never implement
  the verifier as a request-supplied boolean or unconditional approval.
- The host must audit the authorized task/profile decision and transport result
  using metadata only. Do not log payloads, provider responses, or credentials.
- Sending requires explicit source grants in the host profile. The host must
  validate the supplied payload's provenance/purpose and recipient data
  visibility before calling the transport. The transport selects no sources.
- IMAP inspection logs in, selects INBOX read-only, and returns counts and
  mailbox generation only. It never fetches a message body, marks a message
  read, writes a flag, or expunges anything.
- SMTP inspection performs EHLO, STARTTLS, EHLO, authentication, and close only;
  it issues no message command and creates no outbox entry.
- Transmission accepts bounded plain text with a short subject and explicit
  address tuples. No attachments, raw MIME, arbitrary headers, sender override,
  host override, or credential override are supported.
- To/Cc/Bcc and SMTP envelope recipients are checked against both the fixed
  allowlist and the verified profile. Bcc is omitted from visible headers.
- Outbox rows contain only key/content digests and status, not mail bodies or
  passwords. A durable uncertain row is committed before SMTP transmission.
  Completed SMTP acceptance is replay-safe across restart. Any uncertain/partial
  transmission remains blocked for operator reconciliation, with no blind retry.
- `accepted` means the SMTP service accepted all envelope recipients. It does
  not claim delivery to the recipient's inbox or that an employee read it.
- Connection/authentication failures before transmission do not reserve a send.
  Provider error text and secret values are not exposed in public exceptions.

## Protected server files

Credentials are read from an explicit protected absolute path supplied by the
host. The proposed path is:

`/etc/liquisto-assistant/olivia-mail-credentials.json`

The JSON contract contains exactly `username` and `password`; username must
equal the fixed mailbox. Provision the password through the separately prepared
secure operator prompt, never chat, Git, examples, or documentation. Require
root/service ownership and mode 0600 on Linux. Mount read-only for the dedicated
workflow; never grant the conversational process extra credential access.
The credential reader validates Linux ownership and mode again on the opened
regular-file descriptor, uses no-follow where supported, and reads at most
8193 bytes to enforce its 8192-byte limit. Its immediate parent must be owned
by root/the service and not writable by group or others; provision it below
the protected `/etc/liquisto-assistant` tree. Windows ACLs remain an operator
responsibility rather than being inferred from Unix mode bits.

The dedicated outbox may live at:

`/var/lib/liquisto-assistant/olivia-mail/outbox.sqlite`

Precreate its protected parent directory with mode 0700 and the dedicated
workflow user's ownership; the adapter creates the database with mode 0600.
Preserve this durable state through deployment and rollback. Do not remove it
to reset tests, clear uncertain rows, or trigger a replay. Windows operator
files require equivalent owner-only ACLs; Linux is the runtime target.

## Integration and acceptance sequence

1. Review and version the transport and its mocked tests. No chat/Voice route,
   navigation tool, Memory hook, preference operation, or Identity Core changes
   are required or permitted by this transport alone.
2. Provision mailbox credentials in protected server configuration. Confirm
   DNS/routing and provider access for the .cloud mailbox without altering .com.
3. Compose the dedicated read-only connection-check profile through SCAS and
   implement a verifier backed by the authoritative sealed profile. Do not use
   the existing technical Memory profile as a mail authorization.
4. Verify IMAP metadata and SMTP TLS/login with no fetch and no transmission.
5. Compose a separately governed work-output mail profile with source grants,
   role visibility, fixed sender, and the exact approved recipients. The user
   already approved bounded autonomous sending; that authorization does not
   eliminate SCAS seal/grant validation.
6. Run a bounded synthetic receive/send acceptance only to an explicitly
   selected approved address. Report SMTP acceptance separately from real inbox
   delivery. Never use existing user messages as test fixtures.
7. Build a later inbox processor only after employee identity verification,
   permitted incoming tasks, source/output types, and retention are specified.
   Do not trust From/Reply-To or treat email prompt text as policy.
8. Advertise mail reachability in Olivia's persona only after the path is live
   and verified. Ordinary chat/Voice remain without mail-send tools. Memory
   writes stay restricted to their existing closed preference operations.

## Remaining activation inputs

- Authoritative mail profile composition and host verifier wiring.
- Actual report/source/data-role grants and bounded task binding.
- Synthetic acceptance to konstantin@liquisto.com and actual receive-path evidence. The user already authorized sending to this exact address; no new send approval is inferred.
- Inbox processing/user identity/retention definition if incoming messages are
  intended to trigger autonomous work (the transport intentionally does not).

During implementation and mocked tests, no mail was sent or read and no
productive mailbox, DNS, service, grant, account, provider secret, or memory
record was changed. Subsequent protected credential provisioning is recorded below.

## Local verification

- 51 mocked transport tests passed using the KI runtime's Python environment.
- 7 mocked privileged operator checks also passed; 58 total staged tests pass.
- Ruff passed for the staged source and tests.
- Coverage includes all recipient channels, TLS before login, immutable and
  restrictive profile gates, denied credentials access before authorization,
  read-only IMAP metadata, no-send SMTP inspection, restart/replay protection,
  conflicting keys, partial/uncertain transmission, concurrent reservation,
  wrong mailbox credentials, oversized/injected headers, and sanitized errors.
- Windows sandbox denied pytest temporary-directory access. Tests were rerun
  with technical approval and a fresh staging-only temporary directory; no
  productive mailbox or server was contacted.

## Privileged connection verification

`deploy/liquisto-assistant/verify_olivia_mail_login.py` is a separate operator
check. It requires effective root and the exact `scas-runtime-prod` hostname,
reads only the fixed protected credential path, and uses the reviewed release's
transport credential loader. It creates no dummy SCAS profile, supplies no
always-true verifier, and grants no runtime authority.

The operator check authenticates IMAP, selects INBOX read-only, checks metadata,
and authenticates SMTP after STARTTLS. It then logs out/quits. No message bodies
or SMTP message commands are used. Its output consists only of named boolean
results; provider error text, credentials, mailbox counts, and UID values are
not printed. Run it from a reviewed release containing the source tree, only
after the protected credentials have been provisioned. A successful login check
still does not activate sending or establish real inbox delivery.

The secure operator helper is `deploy/liquisto-assistant/provision-olivia-mail-secret.ps1`. It prompts locally without echo and passes credentials only through SSH stdin to the root-owned provisioner. It does not activate the mail workflow.


## Protected mailbox login verification, 2026-10-09

The operator provisioned the existing OVH mailbox password through the secure
local prompt and SSH stdin. The subsequent root-only checker on
`scas-runtime-prod` confirmed protected credential availability, successful
certificate-validated IMAP TLS authentication/read-only INBOX metadata and
SMTP STARTTLS authentication. No credential values, mailbox counts or provider
responses were exported. No message body was fetched, flag changed or message
sent. Credential contents remain exclusively in protected server configuration.

This closes the credential and login gate only. Mail profile composition, host
verifier wiring, source/employee data visibility, bounded inbox work and actual
send/receive acceptance remain open. No runtime mail service or conversational
mail tool was activated; ordinary Memory permissions remain unchanged.
