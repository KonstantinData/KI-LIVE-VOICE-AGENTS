# Isolated Olivia native mail adapter

Status: additive native code deployed on 2026-10-09; automatic mail remains disabled.
Native source `5c69d91` was overlaid onto the inspected productive baseline. The
current healthy native image is
`sha256:df227a228450bfc56d4d179320cf73037c4f010c3d192a2a16d8b91d221a26e4`. <!-- Public digest; pragma: allowlist secret -->

The deployment preserved all environment values, Memory hooks, private networks
and existing channel restrictions. `OLIVIA_MAIL_ENABLED=false`; the new native
mail route returns 503 while disabled. Default native acceptance passed read-only
for signed Memory context, text hooks, Voice initialization, invalid digest and
foreign-subject rejection. Identity Core remains revision 2, Olivia de Jong.
No preference capture/forget, incoming mail body, mail inference or SMTP send
was performed. Real employee text/audio conversations remain a separate category.

The sibling SCAS worker, Control authority and CRM replay migration were installed
separately with zero active mail enrollments/profiles/policies/credentials. An
explicit product User-Agent correction was also installed in the disabled worker;
it changes no business or Memory rights. Employee enrollment, current source
permissions, exact immutable profile review and enabled end-to-end acceptance
remain mandatory. See the owning
[SCAS deployment record](https://github.com/KonstantinData/skill-centric-agent-system/blob/4473d22/docs/runbooks/liquisto-olivia-mail-deployment-2026-10-09.md)
for exact image pins, native Compose override, live Control checks and rollback.


The additive router is `/assistant/mail/respond`. The existing assistant route,
provider, shared prompt, Voice and native Memory hooks are untouched. The sole
entry-point addition imports and includes the new router in
`src/api/liquisto_assistant_main.py`. Apply that exact addition to the inspected
live entry point, rather than replacing a Memory-patched entry point wholesale.

Separate mail settings use `OLIVIA_MAIL_` environment keys:

- `ENABLED` defaults false.
- `RUNTIME_TOKEN` is a dedicated ASCII token with at least 32 characters. The
  ordinary assistant service token is explicitly rejected as mail configuration.
- `RECEIPT_KEY_PATH` is an absolute protected regular file containing 64
  lowercase hex characters (32 bytes), optionally followed by one newline.
- `REPLAY_PATH` is a private persistent SQLite file in a protected directory.

Do not share the receipt signing key with the host worker. KI's protected key
verifies Control authority; it is independent of Memory tokens and profile seals.

The dedicated Bearer and JSON `X-Olivia-Mail-Receipt` header are both mandatory.
Receipt envelope is exactly `{receipt, signature}`. Its exact authority schema
uses `contract_version=0.1.0`, `operation=respond`, fixed tenant/agent, actual
principal, canonical recipient, installed profile ID/hash, message key, sorted
unique source IDs, exact body-byte SHA256, nonce and integer UTC Unix expiry.
HMAC-SHA256 signs recursively sorted UTF-8 JSON without whitespace; signature is
64 lowercase hex characters. Maximum remaining lifetime is 60 seconds.

The request body is exactly:

```json
{
  "contract_version": "olivia-mail-respond-v1",
  "tenant_id": "liquisto",
  "agent_id": "liquisto-assistant",
  "principal_id": "actual-existing-principal",
  "recipient": "konstantin@liquisto.com",
  "profile_id": "actual-reviewed-installed-profile",
  "profile_sha256": "<64-lowercase-hex>",
  "message_key": "host-message-key",
  "source_ids": ["crm-open-tasks"],
  "prompt": "Bitte fasse meine offenen Aufgaben zusammen.",
  "context": [{
    "source_id": "crm-open-tasks",
    "label": "Open tasks",
    "system": "liquisto-crm",
    "permission": "crm:read",
    "observed_at": "2026-10-09T12:00:00Z",
    "classification": "internal",
    "content": "Synthetic minimized projection."
  }]
}
```

This example is a schema illustration, not an enrollment/profile grant. Actual
sources are a subset of `liquisto-business-purpose`, `crm-companies`, `crm-deals`,
`crm-open-tasks`. Request source IDs must equal the actual unique context source
IDs, not a ceiling containing missing items. Maximum eight context items, 4,000
characters per item, 20,000 aggregate and 48,000 request bytes. Only the already
approved three correspondents are permitted. Unknown/duplicate JSON fields,
altered bytes, claims, sources, expired receipts and other operations fail closed.

Nonce and principal/message/profile binding are reserved durably before local
inference. Failure is quarantined: replay or a newly issued nonce for the same
message cannot regenerate it. The ledger stores hashes only and is not cleared.
The local provider and shared persona remain authoritative. Returned actions,
extra output fields and non-JSON provider replies are rejected. Successful output
is only `{contract_version: "olivia-mail-answer-v1", answer: "..."}`. No Memory
calls, source retrieval, tools, business mutations or SMTP occur in this route.

The transport accepts a host-only `thread_capability` of exactly 43 URL-safe
characters and a closed boolean `thread_invitation`. Only the initial invitation
uses `<olivia-thread.{token}@liquisto.cloud>` as Message-ID. Replies receive a
unique stable idempotency-based Message-ID and retain the issued anchor in
`In-Reply-To` and `References`. Both threading inputs are included in the content
hash; changing them on a retry is denied. Existing non-thread ledger hashes remain
compatible. No arbitrary headers, attachments, sender or host override was added.
Fresh authoritative SEND verification runs once, after TLS/login and durable
reservation, immediately before transmission. A denied or uncertain operation
remains quarantined and cannot be automatically retried.

The Content-Type must be application/json, optionally UTF-8 charset. Actual
bytes must decode as strict UTF-8 without BOM. Source metadata is fixed:
business-purpose is public/tenant:read/liquisto-tenant-registry; all three CRM
sources are internal/crm:read/liquisto-crm. Signed mismatches still fail closed.

Validation: focused mock tests include the unchanged transport tests; Ruff
passed for all changed Python surfaces. Tests do not access live mail/provider.

The separate authority, live grants, enrolled employee, profile release review,
CRM source projection, host pipeline and deployment guard must be supplied by
their owners. This candidate cannot mint authority or activate itself.
