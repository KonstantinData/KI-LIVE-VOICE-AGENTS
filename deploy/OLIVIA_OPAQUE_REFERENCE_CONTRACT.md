# Olivia regular-mail opaque-reference contract

Status: implemented and tested locally only; production review/approval pending.
Based on reviewed KI commit `9c280f309a6e09a65ac1bc0fa98435d802707069`.
Neither the word-boundary proposal `70aa408` nor its recognition tradeoff is
included. The complete existing `SENSITIVE` expression and external-data guard
are unchanged.

## Answer purpose and minimal implementation

The regular mail route returns only `olivia-mail-answer-v1` and `answer`.
`prepared_actions` must be empty; there are no tools, CRM lookups, or action
execution. Its factual citations use source labels. Consequently the model
does not need real CRM IDs or a reversible map to prepare this answer.
Request-local references retain the relationship graph without disclosing IDs.

The route calls the new `prepare_external_reference_messages` service only in
the regular OpenAI branch, after the existing runtime authentication, closed
request/source metadata validation, signed role/source/payload receipt binding,
expiry check and receipt reservation. It runs before provider preflight, budget
reservation, key loading and any HTTP attempt. The provider's existing guard
still checks the final payload. Local-model, pilot, widget and web assistant
routes do not invoke the service.

## Explicit external data representation

Only these exact fields in the already selected, permission-filtered CRM
projection are non-exportable technical identities:

| Source / slot | Binding type |
| --- | --- |
| `crm-companies.content[].record_id` | `company` |
| `crm-deals.content[].record_id` | `deal` |
| `crm-open-tasks.content[].record_id` | `activity` |
| `crm-open-tasks.content[].related_records[].record_id` | Its validated `record_type` |

Reference types are the five actual CRM link types: `company`, `contact`, `deal`,
`activity`, `relationship`. Unknown types, fields, sources, duplicate sources,
malformed IDs and malformed projection metadata fail closed. ID values must
be nonblank strings of at most 240 characters without ASCII control characters.
They are compared exactly, without normalization or prefix stripping.

After validation, every original technical ID is replaced, irrespective of
whether the original happens to resemble a key. This is a declared non-export
policy for typed identities, not a claim that a credential-shaped ID is safe
to disclose. An original ID containing a real secret would remain internal;
no substring, hash, suffix, or encrypted version of it is sent to the model.
Secrets or ordinary IDs repeated in retained text are not rewritten: the
request is denied if an original ID occurs in any retained string value.

Each `(record_type, exact_original_id)` pair receives a server-generated
`ref-` plus 24 random hex digits (96 bits), unique within this request. Same
typed identities reuse the same token, including links to supplied records;
the same spelling in different types receives different tokens. Random token
collisions and exact matches with any original ID are retried at most eight
times, then denied. Each new request gets independent tokens. No new key,
credential binding, persistent alias table or external reverse lookup exists.
The temporary map stays in process memory and is discarded after preparation.

All other values stay unchanged: question, descriptions, names, industry,
amounts, dates, pipeline/stage IDs, record types, labels and source timestamps.
The unchanged full secret/sensitive guard checks the retained projection before
alias generation and checks the final payload again. Embedded `sk-` markers in
free text still block after letters, digits, underscores and Unicode letters.
There is no global word-boundary relaxation or exception for arbitrary text
containing `record_id`. This does not anonymize business names or other text.

`model_projection` retains provided/shown/truncated counts and adds
`reference_contract: "olivia-mail-opaque-refs-v1"`. Existing one-record sampling
and source order remain unchanged. The system instruction tells the model
these are temporary technical references, not real CRM IDs, not evidence of
unseen record contents, and not executable capabilities. It should cite source
labels rather than tokens. There is no reverse substitution in the answer.

## Binding, evidence and limitations

Provenance rests on the existing receipt-verified CRM source and role boundary,
not on an invented secret-disjoint ID grammar. The receipt continues binding
the exact original payload; it is verified before transformation. Within the
model input, equality and type-specific relationships are preserved and every
original business value remains attributable to the same source label.
The new metadata names the external representation contract. This does not
create durable per-token audit evidence or allow reconstruction from a later
answer; the current mail contract does not provide that facility.

An ID repeated in the question or another retained string now causes denial,
even when it is not a secret. Substring comparison is conservative and can
also deny short/common IDs. This is deliberate fail-closed behavior, not silent
rewriting. IDs above the current 240-character boundary, controls, unstructured
sources, unknown link types and malformed data are not made acceptable by this
change. Pipeline/stage IDs are outside this narrow representation change and
remain subject to the original guard. A compromised trusted source can still
mislabel business data; the signed boundary is not a semantic classifier.

## Synthetic acceptance and joint frontend boundary

The chosen mail suites and the new adversarial suite run only with synthetic
fixtures, in-memory/temporary SQLite and ASGI/HTTP/SMTP mocks. Outbound socket
connections are blocked; only Windows asyncio's internal socket pairs are
allowed. Tests cover the actual `task-` false-positive shape, credential-shaped
IDs, embedded keys in free text, ID repetition in text, schema impersonation,
type-specific/self/duplicate/unseen graph links, independent per-request refs,
collisions, malformed IDs, closed JSON, replay prevention, budgets and ordering
of preparation after authentication/receipt validation. Assertions inspect the
mock provider request and verify original IDs and ID-contained secrets are
absent, while all non-ID record values remain unchanged.

Local verification: 327 tests passed, with no failures or skips, including
95 new reference-contract cases. Ruff and `git diff --check` passed. The
explicit before/after case proves the unchanged marker rule denies the original
synthetic task ID, accepts the non-exportable-ID representation, and still
denies the same original bytes when present in the question.

The frontend's `/assistant/respond` and native CRM identities are unchanged.
The mail worker's `/assistant/mail/respond` still consumes exactly the existing
`olivia-mail-answer-v1` response. No frontend614 file, CRM ID, migration, source
role, communication circle, DKIM/origin policy, budget, provider/model selection,
key binding or SMTP configuration changes. Opaque refs appear only in the
regular OpenAI model input and cannot be used by the UI for navigation/actions.

## Concrete production approval and live acceptance still pending

Review/approval is needed specifically for this external reference contract:
the listed technical ID slots become non-exportable, random request-local refs
replace them, and repeated-ID text fails closed. It is not approval for a
secret-matcher relaxation. Build/deploy only the reviewed KI change against the
verified current baseline; preserve worker53a2444, timer, existing receipts,
historical signature seeds, quarantines, outbox, credentials, roles and budgets.
Do not reconcile unrelated Compose containers or reuse consumed mail/receipts.

After a separately approved coordinated deployment, use one fresh legitimate
Konstantin mail for live acceptance: normal timer, valid origin, role-approved
context, new receipt, successful preflight, exactly one provider attempt with
existing budget accounting, one new SMTP acceptance and actual recipient
confirmation. Provider generation or SMTP delivery has not been tested live
by this patch. Correlate only sanitized timing/status evidence; do not log raw
payloads, original IDs, subjects, bodies or credentials. Frontend acceptance
continues independently with its existing roles, API contracts and action
confirmation behavior. No automatic deployment, replay, send or shutdown is
part of the local checkpoint.
