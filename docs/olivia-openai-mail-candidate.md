# Olivia synthetic OpenAI pilot — 2026-10-10

Local candidate based on KI PR 18 head
`3b56514196534e7ac0e0784803fcd8e9c7ac27bf`. Productive mail, Voice, Memory,
transport, service secrets and deployment configuration are unchanged.
The Liquisto meeting-briefing work remains a separate paused task.

## Authorized acceptance scope

Konstantin explicitly approved the narrow protected-key boolean check and an
isolated test process with **at most five OpenAI HTTP calls total and USD 0.10**.
Only invented mail texts and synthetic references are permitted. No actual
mail, CRM, ERP or Memory may be sent; no mail delivery or service switch is
authorized. The coordinating Runtime thread owns execution. This worktree has
made no real API call and has not read the protected key.

The parent reports that `/etc/liquisto-assistant/olivia-openai.env` contains
exactly one nonempty `OLIVIA_OPENAI_API_KEY`, root:root mode 0600, no symlink.
Model access remains unverified. There is no fallback to `OPENAI_API_KEY`.

Run five fixed cases **in one batch**: invented Condata reference, unavailable
order status, minimal greeting, English request, and a web/tool injection.
Each case has its own context; only Condata has the explicitly fictional
reference. There are normally **two HTTP calls**: exact input-token count and
one generation. Five separately counted generations would exceed the approved
five-call total and are not the approved acceptance procedure.

## Model, token accounting and cost

Use `gpt-6-luna`, Responses, JSON-schema output, reasoning `none`, and standard
service tier `default`. The current
[model reference](https://developers.openai.com/api/docs/models/gpt-6-luna)
supports these features and lists no dated snapshot. The alias does not pin
quality permanently; verify the resulting synthetic answers before release.

Every generation is preceded by the official
[input-token counter](https://developers.openai.com/api/docs/guides/token-counting)
at `POST https://api.openai.com/v1/responses/input_tokens`. It receives exactly
the same model, input, text/schema and reasoning fields as generation, including
role/schema overhead. A count outside 1–8192 rejects generation. The generation
must report that exact input usage and output usage within its cap. The entire
request is also capped at 24,000 UTF-8 bytes; bytes are not a token estimate.

The [published standard prices](https://developers.openai.com/api/docs/pricing)
on 2026-10-10 are USD 0.10/M input, 0.125/M cache writes and 0.50/M output.
Ceilings cover both input plus cache-write charges together and
the 10% regional premium: USD 0.25/M input and 0.60/M output. No Fast tier is
selected; the input cap stays below the long-context premium threshold.

```text
single case: ceil(8192 * .25/M + 512 * .60/M) = USD .002356
five-case batch: ceil(8192 * .25/M + 2560 * .60/M) = USD .003584
```

The protected SQLite ledger reserves **USD .01 before each HTTP attempt**,
including counting, failures and timeouts. Atomic transactions enforce at most
five attempts over its lifetime, so reservations cannot exceed USD .05.
No retry, redirect, proxy inheritance, fallback or refund resets that limit.
The one fixed batch is claimed permanently before its first request; restart
does not permit replay or resume. All processes must use the same persistent
ledger. Never delete, replace or rotate it to gain quota.

These are request bounds under the cited tariffs, not an account-wide billing
limit. The counter documentation does not explicitly promise zero fees.
The Runtime operator must confirm that account/region pricing fits the USD .01
per-call reservation before execution; stop if it cannot be established. A
separate access probe is unnecessary and would itself consume approved calls.

## Isolated Runtime-thread procedure

Use a separate checkout of the exact reviewed KI commit and existing locked
Python dependencies. Do not start or modify the productive service. Establish
one root-owned mode 0700 persistent pilot directory and use its existing ledger
for every attempt. The output path must be new; the script creates it with mode
0600 and refuses overwriting. No environment sourcing or plaintext key argument
is needed.

```bash
python deploy/liquisto-assistant/run_openai_synthetic_batch.py --describe
python deploy/liquisto-assistant/run_openai_synthetic_batch.py \
  --key-file /etc/liquisto-assistant/olivia-openai.env \
  --ledger-file /var/lib/liquisto-assistant/openai-pilot/http-budget.sqlite \
  --output-file /var/lib/liquisto-assistant/openai-pilot/synthetic-result.json \
  --approved-price-snapshot openai-gpt-6-luna-standard-20261010
```

`--describe` reads no key, performs no HTTP and consumes no quota; it prints the
exact provider payload hash and ceilings. The second command is owned solely by
the approved Runtime thread. Do not run it from both threads. An uncertain or
failed batch stops permanently; retain the ledger/result and report sanitized
status. Never rerun under a new directory or batch ID.

Stdout contains only batch ID, status and attempt count. The protected result
contains the five synthetic answers, validated token usage and conservative
generation-cost ceiling, and stays on Hetzner. Evaluate separately:
German clarity, fictional reference attribution, honest unknown order status,
useful clarification on minimal input, English response, refusal to invent web
research or completed actions. Passing wire/schema tests is not semantic success
and synthetic Condata is not real research. Capture actual usage/billing from
approved account metadata when available, without exporting secrets or raw
provider outputs to Cloudflare or chat.

## Separately inactive SCAS integration

`POST /assistant/mail/openai/respond` exists only in the Liquisto entrypoint,
with `OLIVIA_MAIL_OPENAI_ENABLED=false` by default. It requires the dedicated
existing mail Bearer plus a **new-purpose** signed receipt. Ordinary local
respond/read/send or Memory receipts cannot authorize OpenAI transfer.
The request binds tenant, agent, principal, canonical recipient, fresh profile
ID/hash, pilot ID, exact request bytes, message and source set. Only zero sources
or `synthetic-public-reference` with public synthetic metadata are accepted.
Real CRM/ERP/Memory/history data is rejected.

The receipt additionally pins pilot SHA-256, provider, model, synthetic data
policy, token caps, five attempts, USD .10 budget and the price snapshot. A
configured immutable pilot digest is mandatory. Nonce/message replay and logical
request reservations are separate from the shared total HTTP budget. The ledger
contains hashes and counts only. Configuration disabled/unavailable is 503,
authority denial 403, replay 409, logical exhaustion 429, provider failure 502.

The SCAS companion has a default-disabled issuer, empty migration, candidate
composer and sealed ToolGateway synthetic runner. Preparing these does not
approve profiles, apply SQL, enable egress or connect productive mail. That
per-case integration is verified offline; the approved paid acceptance uses the
two-call standalone batch above. A label alone cannot prove free text synthetic;
the separately reviewed manifest binds the exact five fixture hashes.

Both paths use verified HTTPS, `store:false`, no tools/retrieval, no conversation
or background state. Refusals, incomplete responses, annotations, tool output,
duplicate/malformed JSON, nonempty actions and answers over 60 words fail closed.
[Data controls](https://developers.openai.com/api/docs/guides/your-data) distinguish
Responses storage from abuse monitoring and caching: `store:false` is not Zero
Data Retention or approval for European real-business-data processing.

## Offline verification and release gates

```powershell
python -m pytest tests/test_api/test_liquisto_mail_openai.py tests/test_api/test_liquisto_openai_synthetic_batch.py tests/test_api/test_liquisto_mail_route.py tests/test_api/test_liquisto_mail.py tests/test_api/test_liquisto_assistant.py tests/test_api/test_liquisto_provider_format.py tests/test_api/test_liquisto_employee_communication.py tests/test_api/test_liquisto_navigation_sideband.py -q
python -m ruff check src tests deploy/liquisto-assistant/run_openai_synthetic_batch.py
```

All provider transport in these tests is mocked. Stale employee-rule assertions
now reflect the approved `olivia@liquisto.cloud` persona: naming its
address does not claim delivery, read or sending authority. The shared persona
was not changed. Final commit hashes and observed gate results belong in the
handoff evidence; offline success is not a productive deployment claim.
The existing tenant-registry tests likewise now expect the already approved
Olivia de Jong identity and internal digital-assistant role. Only Liquisto
assertions changed; no other tenant configuration was used or modified.

KI PR 18 and SCAS PR 610 remain stacked dependencies. Obtain exact-commit CI,
required code-owner review, separate real-data/provider/retention approval and
specific secret binding/deployment approval before productive use. Preserve the
deployed Memory overlay. No push, merge, deployment, new grant or credentials
are authorized by this candidate.
