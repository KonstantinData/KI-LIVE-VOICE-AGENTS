# Mein Kuechenexperte Runtime Knowledge

This folder contains tenant-scoped knowledge that may be loaded by the runtime
agent.

## Contract

- `chunks.json` is the versioned source for prompt and future vector import.
- `tenant_id` must match `registry/tenants/mein-kuechenexperte/tenant.json`.
- `scope_id` must match the tenant `knowledge.scope_id`.
- Chunk `category` values should stay aligned with `LisaAgent.get_knowledge_categories()`.
- Do not add secrets, raw customer data, private uploads, CRM records, or
  unverifiable contact details.
- Unknown facts must stay explicit instead of being filled with placeholders.

## Runtime Behavior

KEA currently receives these chunks as static tenant context in the system
prompt. The same chunks are shaped to be importable into the `knowledge_chunks`
table later for semantic retrieval.

The deterministic text-chat flow is maintained separately from the voice system
prompt. Its direct FAQ answers use the `service-pricing`, `planning-services`,
`service-boundaries`, `public-contact`, `project-documents`, and
`consultation-process` chunks. Keep those contents customer-ready German prose,
not internal instructions. Existing cached voice agents require a runtime restart
or cache invalidation to receive changed static knowledge; existing sessions may
retain their original context. Editing this folder alone does not verify a live
deployment.

## Public Website Verification

Public content was verified on 2026-09-27 against direct HTTPS responses from
`https://mein-kuechenexperte.de/`. Search-engine copies of `/kontakt` and
`/fachplanung` were stale and were not used for the refreshed facts. Website-derived
chunks record source URLs and `verified_at`; the owner-approved values and the
restricted contact-handoff instructions retain their original authority.

Verified sources:

- `/`, `/faq`, `/preise`, `/kontakt`, `/ueber-uns`
- `/neubau`, `/renovierung`, `/orientierung`, `/angebot_und_planung_pruefen`
- `/fachplanung`, `/wohnen`, `/esszimmer`, `/hauswirtschaftsraum`,
  `/vorratsraum`, `/backkitchen`

The current offer uses individually agreed scope and total prices, not the former
fixed planning packages. The free introductory conversation is not a planning
check. The scope includes adjacent furniture solutions but excludes ordering,
delivery, assembly, acceptance, continuous project supervision, and executable
technical planning. Public email: `kontakt@mein-kuechenexperte.de`, verified by
decoding the contact page's Cloudflare email-protection attribute. Do not restore
old package prices or the former email address from cached pages.
