# Olivia OpenAI mail candidate — 2026-10-10

Status: local preparation only, based on KI PR 18 head
`3b56514196534e7ac0e0784803fcd8e9c7ac27bf`. No provider request, secret read,
productive environment binding, deployment, enrollment, or mail delivery is part
of this change. The Workbench research workflow remains paused.

## Model and bounded pilot proposal

Use `gpt-6-luna` through the Responses API for short German/English mail answers.
The [current model guide](https://developers.openai.com/api/docs/guides/latest-model)
recommends Luna for focused, cost-sensitive work. The
[model reference](https://developers.openai.com/api/docs/models/gpt-6-luna)
lists Responses and structured outputs, supports `reasoning.effort=none`, and
currently gives no dated snapshot to pin. Validate access and current model
behavior before release; a model alias is not an immutable quality guarantee.

Proposed later approval: five manually initiated synthetic tests, at most USD
0.10 in total. This is a new Olivia mail pilot proposal, not an inherited tenant
or research budget. Each request carries one trusted instruction plus one JSON
user projection: at most 1,200 prompt characters and one synthetic reference of
at most 4,000 content characters. Entire provider JSON is limited to 24,000 UTF-8
bytes; output is capped at 512 tokens, 60 words, and no prepared actions.

Current standard prices are USD 0.10 per million uncached input tokens and USD
0.50 per million output tokens; cache writes are USD 0.125 per million tokens.
As a conservative planning estimate, 30,000 input tokens at the cache-write
rate plus 512 output tokens cost about USD 0.0041 per attempt, before region
adjustments. Reserve USD 0.01 per attempt. Bytes are not tokens; this estimate
is not an enforced monetary account limit. The code enforces five lifetime
attempts in a protected ledger, including failures, without retries. Verify
pricing, region, account limits, billing currency, and actual usage before any
paid acceptance run; stop if the approved total cannot be maintained.

## Separate authority and data boundary

The additive internal route is `POST /assistant/mail/openai/respond` in the
Liquisto-only entrypoint. The existing `/assistant/mail/respond`, local model,
shared persona, Voice, mail transport, and native Memory integration retain
their own contracts. No shared/main API exposes the pilot router.

The request contract is `olivia-mail-openai-respond-v1`, with
`data_policy=synthetic-only-v1`. It preserves the existing tenant/agent,
principal, recipient, profile ID/hash, message key, source IDs, prompt, and
context bindings. Context is empty or exactly one source
`synthetic-public-reference`, with system `liquisto-synthetic-test-fixture`, permission
`synthetic:read`, and classification `public`. Existing CRM, ERP, Memory,
attachments, raw email history, and internal/confidential source classifications
are rejected. A synthetic label cannot prove that free text contains no real
data: the trusted issuing authority must inspect the exact approved fixture.
Neither this code nor the key alone grants real mail data transfer to OpenAI.

The existing dedicated mail Bearer is required and must differ from the Voice
service token. A new HMAC-signed receipt additionally requires exactly:

- `contract_version=olivia-openai-receipt-v1` and `operation=respond-openai`;
- `provider=openai`, `model=gpt-6-luna`, `data_policy=synthetic-only-v1`;
- all matching request identity/profile/source bindings, exact body-byte
  SHA-256, one-use nonce, and a remaining lifetime of at most 60 seconds.

Old `0.1.0/respond` receipts cannot activate this route. Existing SCAS issuance
and mail workers do not implement the new purpose and are not changed here.
Control-owned policy filtering, immutable profile validation, egress approval,
fixture approval, and a compatible issuer remain prerequisites for activation.
Do not distribute the Control receipt key to a worker or bypass issuance.

The model sees only prompt plus source ID, label, observation date, and content;
it receives no recipient, principal, profile, nonce, signing key, or mailbox
credentials. All user/source text remains untrusted user data. Existing mail
instructions require honest missing-information answers and prohibit web
research, additional retrieval, action execution, delivery claims, and invented
memory. Model changes alone provide no new research capability.

## Configuration remains disabled

`OLIVIA_MAIL_OPENAI_ENABLED=false` by default. Activation also requires existing
mail enablement, a new explicit receipt, and:

- `OLIVIA_OPENAI_API_KEY`: separate provider secret; no fallback to
  `OPENAI_API_KEY`, Voice, Memory, or another tenant's key.
- `OLIVIA_MAIL_OPENAI_LEDGER_PATH`: absolute protected persistent SQLite file
  inside a protected directory; Linux mode 0600, no symlinks.
- `OLIVIA_MAIL_OPENAI_MAX_REQUESTS`: defaults zero, allowed 1–5 for the pilot.

No Compose environment or secret volume is added. Parent coordination identifies
`/etc/liquisto-assistant/olivia-openai.env` as the separate intended secret file.
Its contents and binding are not inspected by this worktree. The parent's latest
metadata report verifies root ownership and mode 0600 after explicit approval.
The separate content check and productive binding remain unapproved. Do not
reuse the existing generic key.

Only `https://api.openai.com/v1/responses` is called, with verified HTTPS,
`store:false`, standard service tier, JSON-schema output, and no tools,
conversation IDs, background work, redirect following, environment proxies, or
automatic retry. A timeout or any provider failure consumes its quota slot.
The provider response is limited to 64,000 decoded bytes; refusals, incomplete
responses, tool output, annotations, malformed/duplicate JSON, extra answer
fields, and nonempty actions fail closed with a sanitized error.

`store:false` disables Responses application storage; it does not establish
Zero Data Retention or an approved European processing configuration. OpenAI's
[data controls](https://developers.openai.com/api/docs/guides/your-data) describe
separate abuse-monitoring and cache retention. Recipient, retention, project,
region, and source authorization must be approved before real data use.

The ledger stores only hashed nonce/message bindings, counts attempts atomically
across processes, persists across restarts, and contains no prompt, response,
email address, or provider secret. Keep it for the entire approved pilot; do not
delete or rotate it to reset the cap. Exhaustion is HTTP 429, replay 409,
authorization denial 403, disabled/unavailable configuration 503, and a
sanitized provider failure 502. The existing answer wire contract is retained.

## Verification and release prerequisites

Run the offline contract and Liquisto regression surfaces:

```powershell
python -m pytest tests/test_api/test_liquisto_mail_openai.py tests/test_api/test_liquisto_mail_route.py tests/test_api/test_liquisto_mail.py tests/test_api/test_liquisto_assistant.py tests/test_api/test_liquisto_provider_format.py tests/test_api/test_liquisto_employee_communication.py tests/test_api/test_liquisto_navigation_sideband.py -q
python -m ruff check src tests
```

These use scripted HTTP/model fixtures only. Condata, order status, minimal
input, English, and web-research examples verify transport and prompt boundaries;
they are neither real research nor evidence of this model's language quality.
Separate paid synthetic acceptance must test factual restraint, correct German,
source attribution, missing-input questions, and injection resistance on the
exact reviewed commit before any productive recommendation.

Local verification of this candidate: the seven listed Liquisto test modules
produced 319 passes and two failures. Both failures are the existing
`test_employee_rules_are_trusted_channel_instructions[text|voice]` assertion for
`Biete keine E-Mail-Erreichbarkeit an`. The shared prompt, assistant router, and
employee test file have no diff against the PR 18 base; this parallel prompt/test
inconsistency is not repaired here. Ruff passed for all `src` and `tests`.
The system Python lacked `structlog`; verification used the already installed KI
virtual environment. Windows pytest temporary-file access required an approved
local execution outside the sandbox with a fresh dedicated temporary directory.
No real provider traffic or mail was involved.

KI PR 18 remains a stacked dependency; SCAS PR 610 was open with a failing
Contract-test check at inspection. Do not claim their CI, approved profiles,
native Memory overlays, or productive mail path are ready from these tests.
Before release, reconcile those exact heads, run their applicable gates and
joint contract checks, preserve the deployed Memory overlay, and obtain the
specific secret binding and deployment approval. No merge or deploy is
authorized by this candidate document.
