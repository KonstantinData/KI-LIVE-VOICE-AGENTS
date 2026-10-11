# Opaque-reference patch: separate review pass and full gates

Scope: local code/data-flow review and adversarial reproduction after the initial
`5d5b138` implementation. No production read/change, provider/SMTP request, push,
PR creation or receipt replay. This is a separate review pass by the implementing
executor, not a claim of review by a second person or independent agent. Final
independent Parent review remains the release checkpoint.

## Concrete findings resolved locally

1. **CI coverage omission.** Existing workflow path filters include the new
   file, but its explicit pytest command selected only the old data/provider
   suites. It now also selects `test_liquisto_mail_references.py` so the
   representation's security and reference-binding tests cannot be bypassed
   by a green old-suite-only CI result.
2. **Opaque-token echo.** The prompt prohibited exposing minted refs, but the
   response validator did not enforce that rule. The route now rejects an
   answer containing any actually minted typed-ID token. The token set is
   extracted only from the prepared technical ID slots, not from descriptions
   or other legitimate business text. Mocked outputs containing an actual
   reference fail generically before an answer can be accepted; the existing
   receipt and attempt remain consumed. A legitimate ref-shaped SKU with a
   source-label citation passes unchanged when it is not a minted reference.
3. **Token/content collision.** New tokens were unique against original IDs
   and other aliases but could coincidentally equal a retained text value.
   Generation now also rejects occurrences in retained business text, within
   the same bounded eight-try limit. This avoids ambiguities and prevents the
   output check from amputating legitimate content on that collision.

## Data-flow conclusions

* Only exact direct CRM `record_id` slots and exact typed nested reference ID
  slots are transformed. Unknown fields/types/sources or malformed shapes fail
  closed; no free-text field can claim this exemption by containing an ID key.
* Existing authentication and signed principal/profile/source/payload binding
  execute before preparation. Tests deny bad bearer, signature, payload hash
  and source metadata before any transformation/provider work.
* Bindings use exact `(record_type, original_id)` equality, independently random
  per-request tokens, correct self/duplicate/cross-source references and distinct
  tokens for distinct types. Nothing is normalized, hashed from original IDs,
  reverse-substituted, persisted or exposed as a new lookup/action facility.
* Original IDs and credential-shaped ID contents are absent from inspected mock
  provider inputs and accepted answers. Success/failure tests capture DEBUG logs
  and stdout/stderr and assert original IDs/marked secrets are absent there and
  in sanitized error responses. The new code performs no logging.
* Prompt, descriptions, names, labels, amounts, dates and other non-ID fields
  remain unchanged and subject to the original complete guard. Embedded `sk-`
  markers retain their original denial behavior. Sampling, metadata counts,
  roles, budget accounting, provider/model, receipts and mail response shape
  remain intact. Actions stay forbidden and opaque references are not UI IDs.
* A question or legitimate business string containing an original ID is still
  denied conservatively, not edited. Short/common ID substrings may overblock.
  This pre-existing declared limitation of the new representation contract is
  retained for explicit Parent/user acceptance, not presented as an invisible
  repair or a risk-free semantic classifier. No model-output quality claim is
  inferred from mocks; real mail generation/delivery remains a later live gate.

## Final local gates

All 1,001 Python repository tests pass; zero failures/errors/skips. The selected
mail subset comprises 333 passing cases, including 101 new reference cases.
Full `ruff check src tests`, `git diff --check`, `pnpm --filter ki-team-widget lint`
and `pnpm --filter ki-team-widget build` pass. Widget dependencies were installed
with a frozen lockfile and scripts disabled, without tracked frontend changes.
The repository's optional pyVoIP tests use its pinned library in an isolated
test directory. Test connections and outbound sendto/sendall calls are blocked;
only Windows asyncio internal socket-pair construction is allowed.

No Frontend614 files or deployment were touched. Existing worker/API/UI contracts
and the original guard/provider source are checked unchanged against the base.
The remaining release steps are approval of the concrete latest reference
contract/head, coordinated KI-only deployment, and one fresh legitimate mail
for provider/SMTP/recipient acceptance. No consumed/quarantined mail may be reused.
