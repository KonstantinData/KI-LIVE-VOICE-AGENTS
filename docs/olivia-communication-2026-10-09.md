# Olivia employee communication, 2026-10-09

## Requested behavior

Olivia introduces herself as Olivia de Jong, Liquisto's digital assistant.
Ordinary employee replies use natural collegial language and explain missing
information without discussing memory plumbing, model settings or infrastructure.
Internal configuration, prompts, access routes and credentials remain confidential,
including when a conversation participant claims developer authority. Explicit
questions about AI identity receive an honest concise answer; no human identity,
personal recollection or successful action is fabricated.

The dedicated shared delivery block reaches both text system instructions and
Voice initialization. Its concise text introduction preserves the JSON response
and empty prepared-actions contract. The approved persona definitions are
unchanged; this is employee-facing delivery, not a new identity or permission.
Identity Core revision 2 remains authoritative. Ordinary text/Voice remain
read-only memory channels, with closed preferences and navigation unchanged.

## Email scope and activation boundary

The user confirmed the existing OVH mailbox at `olivia@liquisto.cloud` with
IMAP and SMTP for work-related correspondence with approved employees. This is a separate
integration task. The profile's historical `olivia@liquisto.claud` value is not
an operational mailbox and is not advertised as a working contact route.
Olivia cannot offer email reachability or claim delivery until a checked mail
workflow has actually been authorized, connected and tested.

Read-only server discovery found no Olivia account in the
deployed mail connector. The existing connector has bounded read/search/draft/
label operations, but no SMTP-send implementation or mail.send grant. The user
has authorized autonomous sending to exactly three stated employee addresses.
The demo domain `liquisto.cloud` has OVH MX; `liquisto.com` remains on Google
and is outside this mailbox setup. No existing account, client grant,
business permission or preference-memory authorization is reused as an Olivia
mail grant. No message was read, sent or deleted during discovery.

Mail activation requires the dedicated mailbox, protected credential provisioning,
exact employee allowlist, reviewed source/purpose scope, send-approval semantics,
fresh server-owned authority and an executable guarded mail contract. Ordinary
conversation must not acquire SMTP or IMAP tools through a persona edit.

## Deployment and verification

Prepared against the exact deployed Voice-quality image:
`sha256:0fd86a4347dffffb5f72d105e70d24cc301376541f6b407e62613adf7c326cf0`.
The one-file overlay changes only the shared prompt. The dedicated guard pins
the inspected baseline, reverses only the approved shared-rule addition and
two builder substitutions plus the introduction example, and requires all
remaining prompt bytes, registry, provider adapter and native memory hooks to
match. Container configuration, private networks, mounts and protected server
credentials must be equal before and after replacement. Rollback retains the
previous container. Mail and memory data are outside this deployment.

The initial controlled production switch completed to image
`sha256:3c5a0ae97136151392c98a2eef301c0d19bd558b01f5d55ad0ec9b11ba379a44`.
Real text probes exposed an insufficiently explicit refusal and an intermittent
HTTP 502 from the existing provider-output contract. A native diagnostic
subsequently passed the same information-gap request. The shared rule literal
was refined with direct refusal and information-gap examples, without relaxing
the provider or downstream contract.

The final guarded refinement uses `--baseline communication-v1` and is deployed
as image
`sha256:4bcd34203674eed1bea182303f4a6d667ad5bc2eea3864b4a805c4ab84c2cf63`.
Final packaged prompt SHA-256:
`123d62e2745d0dcbcb43c2dee8333d41214425b137a6e6cfc95dea0b16d39c5b`.
Registry SHA-256 remains
`6276d032a442746b318726210c0d236ae213e7f7df169d7c6e8a5445e372fda3`.
The first previous container remains stopped as
`liquisto-assistant-liquisto-local-assistant-1-pre-communication-20261009`.
The refinement retains the intermediate container stopped as
`liquisto-assistant-liquisto-local-assistant-1-pre-communication-refinement-20261009`.

The combined assistant/navigation/provider/employee/mail suite passed 204 tests,
including 51 mocked transport cases and 7 privileged operator-check cases.
Dedicated guard tests passed 63 cases; Ruff passed on the changed code surfaces.
The complete local Memory suite passed 306 tests and 41 subtests, with 17
PostgreSQL cases skipped locally and assigned to the disposable CI database.
After deployment, the unchanged native acceptance check passed in read-only
mode: signed memory context, native chat and Voice initialization, wrong-profile
and foreign-subject rejection, and unchanged tools. No memory capture or forget
was executed. Real employee audio conversation remains unverified.

Real signed native text requests against the final image passed all three
employee cases: natural information-gap wording without memory plumbing,
refusal of internal configuration despite claimed developer authority, and
truthful digital-assistant identity. The memory context stayed equal across
each request and Identity Core remained revision 2. The first final-image run
still returned an HTTP 502 for the information-gap case; the subsequent native
diagnostic and complete rerun passed. This intermittent output-contract failure
is a remaining reliability limitation, not a permission or memory fix.

Independent transport checks from the runtime host verified the OVH server's
certificate-validated IMAP TLS on 993 and SMTP STARTTLS on 587. These checks
performed no login, message read or send; mailbox authentication and mail
workflow activation are separate outstanding gates.

Mail transport review and the exact approved addresses are tracked separately in the owning runtime repository's `docs/olivia-mail-integration.md`.
