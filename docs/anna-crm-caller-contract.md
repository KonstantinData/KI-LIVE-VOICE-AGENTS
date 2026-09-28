# Anna caller recognition and reception handoff

Status: proposed implementation contract, 2026-09-25. No lookup endpoint is
currently implemented or deployed by this document.

See [reception role](anna-reception-role.md) for owner-defined behavior.

## Separation of responsibilities

The website repository owns authenticated CRM endpoints, contact matching and
record derivation. The phone runtime must not query the CRM database directly
or automate the authenticated dashboard at `app.mein-kuechenexperte.de`.

Use explicitly configured HTTPS endpoints and existing secret provisioning;
do not infer an API from the dashboard URL. Every request authenticates the
tenant, the Anna agent and the source system. Secrets remain outside source
control. The model cannot choose an endpoint, tenant, recipient or contact ID.

## Lookup before named address

Proposed website-owned endpoint: `POST /anna-caller-lookup.php`.
Do not configure the runtime to call it until the receiver is implemented.

Request fields:

- `tenant_id`: fixed `mein-kuechenexperte`.
- `agent_id`: fixed `anna-phone-assistant`.
- `source_system`: fixed `ki-live-voice-agents`.
- `session_id`: runtime-generated call UUID.
- `caller_phone`: from the incoming SIP call through the configured trusted
  gateway; never from model arguments. Missing/private numbers skip lookup.

CRM performs exact matching after consistent phone normalization. National
German numbers require an explicit default region; `0049` and `+49` must match.
Never use substring or last-digits matching. Search must be tenant-scoped and
return no result rather than guess when normalization is impossible.

Response outcomes:

- `unique`: one contact, a short-lived opaque `contact_ref`, structured
  `first_name`, `last_name`, optional explicitly stored `salutation` and
  `preferred_form_of_address`.
- `none`: no match; no name/reference returned.
- `ambiguous`: several matches; no candidate list or names returned.
- `unavailable`: lookup failed; no name/reference returned.

The reference must be bound to tenant, agent, session and expiry and verified by
the website receiver on handoff. Anna receives only the name needed for the
confirmation question. Do not return email, address, project history or notes.
Do not log the lookup number, candidate name or reference.

## Call-scoped confirmation

Runtime states: `not_requested`, `candidate`, `confirmed`, `rejected`,
`unavailable`. The call holds its own candidate/reference; no global cache.

Only an explicit affirmative answer to the name question may move `candidate`
to `confirmed`. A denial clears the candidate from active use and continues
neutrally. Corrected/new names do not overwrite the CRM record. The model may
report the caller's confirmation using a bounded tool, but cannot supply an
arbitrary contact reference. The runtime adds its own verified reference to
the final handoff only when the confirmation state permits it.

Caller ID and spoken name confirmation support intake association only. They
are not authentication for viewing or changing private customer records.

## Reception handoff changes

Extend or version the existing `/anna-voice-handoff.php` contract. Preserve
compatibility with existing callers during deployment; explicitly select the
new contract in Anna only after receiver verification.

New intake needs:

- stable event/session IDs and UTC occurrence time;
- optional runtime-held `contact_ref` with the confirmation outcome;
- confirmed name and preferred form of address;
- request category and short factual summary;
- preferred response channel, confirmed callback number or email, reachability;
- optional caller-provided reference and urgency;
- confirmation to forward the request and contact details;
- optional, separately accepted customer email or transcript processing.

Allow a phone-only callback with no email or transcript requirement. Do not
reuse the current three mandatory consent flags to implicitly require an email.
Represent existing matters, complaints, coordination and partner requests as
requests/activities, not automatically as new `consultation_inquiry` leads.

Recipient selection is fixed server-side to Konstantin Milonas initially.
Owner-confirmed notification destination: `kontakt@mein-kuechenexperte.de`.
Verify the actual configured internal destination; do not infer delivery merely
from the presence of `CONTACT_EMAIL`. No free-form recipient field comes from
the language model. Report capture and notification outcomes separately.

Owner-provided mailbox settings: OVHcloud, `ssl0.ovh.net`, IMAP 993 with
SSL/TLS; SMTP 587 with STARTTLS. Port 587 negotiates TLS using STARTTLS, rather
than implicit TLS. Full mailbox address is the login name. No password is stored
here. SMTP delivery belongs to the website CRM receiver; Anna does not require
IMAP access to read the mailbox for this workflow. Existing production mail
configuration must be verified without printing credentials before changing it.
Reference: [OVHcloud MX Plan configuration](https://help.ovhcloud.com/csm/pl-mx-plan-thunderbird-macos-configuration?id=kb_article_view&sysparm_article=KB0052133).

For confirmed existing contacts, add the intake activity without rewriting
their master data. For new/unresolved callers, capture the request for human
review; do not merge on an unconfirmed number or overwrite names via email.
Retain idempotency and ensure safe retries do not create duplicate requests or
notifications.

## Current source gaps

Website source audit found:

- `www/anna-voice-handoff.php`: existing dedicated authenticated receiver.
- `www/includes/crm/anna_voice_handoff.php`: mandatory email/transcript and
  coupled email consent; fixed consultation purpose and FRITZ!Box source.
- `www/includes/crm/crm_capture_derivation.php`: contact derivation requires a
  valid email and matches contacts by normalized email.
- `www/includes/crm/crm_records_repository.php`: UI text search uses `LIKE`,
  which is not a suitable phone identity lookup.
- `database/migrations/002_create_crm_core_records.sql`: no dedicated salutation,
  normalized phone or caller confirmation fields.

These source findings are not a claim about private production records or a
live end-to-end CRM test. The website checkout already contains substantial
uncommitted work; implementation must preserve it.

## Required verification before enabling

Test normalized exact matches, withheld numbers, ambiguous/shared numbers,
cross-tenant rejection, invalid/expired references, timeout, denied identity,
phone-only capture, correct fixed recipient, delivery failure, idempotent retry
and no master-data overwrite. Verify known and unknown synthetic contacts in a
controlled CRM environment before a real phone acceptance call. Keep Anna's
existing audio and single-greeting regression suite passing.
