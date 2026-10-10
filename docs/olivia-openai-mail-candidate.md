# Olivia synthetic OpenAI pilot — 2026-10-10

Local candidate based on KI PR 18 head
`3b56514196534e7ac0e0784803fcd8e9c7ac27bf`. Productive mail, Voice, Memory,
transport, service secrets and deployment configuration are unchanged.
The Liquisto meeting-briefing work remains a separate paused task.

## Historical paused checkpoint — 2026-10-10

Konstantin requested a saved local checkpoint while changing work location.
The missing-order-status example and its mocked language fixture are updated;
prompt regression checks now require the concrete question. A new offline
regression verifies that an already consumed batch remains blocked after a
prompt revision; the usage-bound case derives its threshold from the payload.
The companion SCAS runbook contains the unapproved seven-day / USD 1 direct-mail
technical draft. No productive integration is implemented or activated.

**These new changes are not yet tested.** No test process is running and no
focused pytest run has started for this checkpoint. Whitespace checks passed.
Previous passing checks belong to KI `18e005a`, not this revised prompt.
Next step after explicit resumption: run the three focused test files
`test_liquisto_mail_route.py`, `test_liquisto_mail_openai.py` and
`test_liquisto_openai_synthetic_batch.py` once offline with mocked HTTP, then
Ruff for the changed Python files and record results against the final commit.
Keep the consumed paid batch blocked. No further API calls, real-mail reads,
key binding, deployment or activation are authorized. The actual-mail proposal
remains pending approval. Pause all further work until resumption.

## Authorized acceptance scope

Konstantin explicitly approved the narrow protected-key boolean check and an
isolated test process with **at most five OpenAI HTTP calls total and USD 0.10**.
Only invented mail texts and synthetic references are permitted. No actual
mail, CRM, ERP or Memory may be sent; no mail delivery or service switch is
authorized. The coordinating Runtime thread owns execution. This worktree has
made no real API call and has not read the protected key.

The parent reports that `/etc/liquisto-assistant/olivia-openai.env` contains
exactly one nonempty `OLIVIA_OPENAI_API_KEY`, root:root mode 0600, no symlink.
There is no fallback to `OPENAI_API_KEY`.

**Completed; do not run again.** The Runtime thread reports one successful
generation at KI commit `18e005af1e8503daf8e71ed220e91d1b5eb4675e`:
1,329 input / 165 output tokens, conservative cost USD .000432. Four cases
were useful; the missing-order-status case copied the generic missing-source
example. The local correction now asks: "Zu deinen Aufträgen liegen mir keine
Statusdaten vor. Welchen Auftrag meinst du?" This prompt change is tested only
offline; it has not been evaluated with a further model call. The original
`olivia-synthetic-five-case-v1` batch ID and persistent ledger stay consumed,
including after this payload change. No additional probe or acceptance run is
authorized. The instructions below record the completed historical procedure.

Run five fixed cases **in one batch**: invented Condata reference, unavailable
order status, minimal greeting, English request, and a web/tool injection.
Each case has its own context; only Condata has the explicitly fictional
reference. The complete batch makes **one generation HTTP call**, including
model-access verification. No `/input_tokens`, `/models` or separate probe is
called. Access errors, rate limits and timeouts consume that same one attempt.

## Model, token accounting and cost

Use `gpt-6-luna`, Responses, JSON-schema output, reasoning `none`, and standard
service tier `default`. The current
[model reference](https://developers.openai.com/api/docs/models/gpt-6-luna)
supports these features and lists no dated snapshot. The alias does not pin
quality permanently; verify the resulting synthetic answers before release.

The batch computes its conservative input bound entirely offline. OpenAI's
[byte-level BPE description](https://github.com/openai/tiktoken/blob/main/README.md)
explains that tokenization compresses bytes; count one token per UTF-8 byte,
without the unsafe average-four-bytes shortcut. Count the **entire serialized
request**, including system/user instructions, role labels and repeated output
schema, then add **16,384 tokens** for the fixed two-role provider framing and
schema transformation. This generous allowance is an engineering bound, not an
official promise of exact framing size or a matching local-model tokenizer.

The executed complete payload was 6,414 bytes, giving an offline bound of 22,798
input tokens. A hard local byte cap of 8,192 gives a worst-case planning ceiling
of **24,576 input tokens**. Batch output is capped at **1,280 tokens total** and
each answer at 60 words. Unexpected reported input usage above the offline
bound, or output usage above its cap, rejects the result and never triggers a
retry. No extra API fee needs to be inferred for a token-counting request.

The [published standard prices](https://developers.openai.com/api/docs/pricing)
on 2026-10-10 are USD 0.10/M input, 0.125/M cache writes and 0.50/M output.
Ceilings cover both input plus cache-write charges together and
the 10% regional premium: USD 0.25/M input and 0.60/M output. No Fast tier is
selected; the input cap stays below the long-context premium threshold.

```text
executed historical payload: ceil(22798 * .25/M + 1280 * .60/M) = USD .006468
local cap: ceil(24576 * .25/M + 1280 * .60/M) = USD .006912
five such attempts: 5 * USD .006912 = USD .034560 < USD .10
```

The protected SQLite ledger reserves **USD .01 before each HTTP attempt**,
including access failures and timeouts. Atomic transactions enforce at most
five attempts over its lifetime, so reservations cannot exceed USD .05.
No retry, redirect, proxy inheritance, fallback or refund resets that limit.
The one fixed batch is claimed permanently before its first request; restart
does not permit replay or resume. All processes must use the same persistent
ledger. Never delete, replace or rotate it to gain quota.

These are conservative request bounds under the cited tariffs, not an
account-wide billing limit. The one-time batch permits only one generation;
the shared five-attempt ledger remains an additional ceiling for all approved
processes. Do not perform separate model-access probes or additional requests.

## Historical Runtime-thread procedure — consumed, no rerun

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
single-call standalone batch above. The inactive signed per-case route retains
its separate exact token preflight contract; do not enable it for this batch.
A label alone cannot prove free text synthetic;
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

## Implemented local direct-mail adapter — pending live approval

The coordinating parent proposed seven days from activation, USD 1 total,
`gpt-6-luna`, `store:false`, and draft answers only for new direct mail from
`konstantin@liquisto.com` or `konstantin.milonas@condata.io` to
`olivia@liquisto.cloud`. Only the current subject and new text may enter the
provider request; attachments, quoted history, CRM, ERP and Memory are excluded.
Secrets and particularly sensitive personal data are excluded. This is a
proposal, not real-data, key-binding or activation authorization.

`src/api/services/liquisto_direct_draft.py` now implements the separate default-off
`DirectDraftProvider` host adapter. It accepts only closed `{subject, new_text}`
bytes, reuses the fixed Olivia persona with empty context, caps the entire
request at 8192 bytes/output at 512 tokens, fixes `gpt-6-luna`/`store:false`,
and has no tools/counter/probe/retry/fallback. A mandatory host callback verifies
authority/content and debits the private seven-day/USD1 ledger **before** the
key supplier or HTTP client is touched. Errors/output drift are sanitized.
It is not imported by application startup, exposed as a route or bound to keys.

The SCAS companion `apps/liquisto-mail/olivia_mail_worker/direct_drafts.py`
implements private admission/state, current-text projection, trusted sender and
content gates, sealed Gateway orchestration and saved draft retrieval.
Its runbook `docs/runbooks/liquisto-olivia-openai-synthetic-pilot.md`, section
"Implemented local direct-mail draft", gives activation/return steps and the
required cross-checkout offline integration test. The ordinary mailworker,
synthetic ledger limits/transports, credentials and sender were not changed. The existing
signed route remains synthetic-only and cannot carry productive mail. The
completed synthetic ledger is never reused/reset as a productive grant.

The new provider tests use only HTTP MockTransport and an invented key. The
joined SCAS test invokes this actual adapter after real Gateway/SQLite admission
and reopens the unsent draft. No genuine mail or provider call is used.
A trusted Authority/MTA verifier, actual existing enrollment, private draft-access
binding, independently locked combined host dependencies, and specific live-data,
key-binding and activation approvals remain prerequisites.

KI PR 18 and SCAS PR 610 remain stacked dependencies. Obtain exact-commit CI,
required code-owner review, separate real-data/provider/retention approval and
specific secret binding/deployment approval before productive use. Preserve the
deployed Memory overlay. No push, merge, deployment, new grant or credentials
are authorized by this candidate.
