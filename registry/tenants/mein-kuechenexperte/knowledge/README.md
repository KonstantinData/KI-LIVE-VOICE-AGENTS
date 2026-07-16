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
