# Processing Register - Runtime Scope

**Legal basis:** GDPR Art. 30  
**Status:** July 2026

## Processing 1: Widget Chat And Live Voice Runtime

| Field | Content |
| --- | --- |
| Purpose | Provide AI-supported first project intake through chat and voice |
| Legal basis | Consent for chat/voice processing; legitimate interest for runtime security |
| Data subjects | Website visitors |
| Data categories | Visitor ID, conversation messages, final voice transcripts where enabled, project context, consent metadata |
| Internal recipients | Runtime operators with operational access |
| External recipients | OpenAI where enabled; external CRM only through handoff payloads |
| Storage | Hetzner runtime database and private upload storage |
| Retention | Runtime retention policy in `DATA_RETENTION.md` |
| Safeguards | TLS, tenant isolation, origin checks, consent checks, no raw audio storage by default |

## Processing 2: Project Upload Runtime

| Field | Content |
| --- | --- |
| Purpose | Store and summarize customer project files for the current inquiry |
| Legal basis | Consent |
| Data categories | File metadata, private file content, AI summary, conversation linkage |
| External recipients | OpenAI for analysis when consented; external CRM receives metadata and signed access flow |
| Storage | Private backend upload storage |
| Safeguards | File type/size validation, tenant-scoped metadata, signed short-lived access links, audit events |

## Processing 3: External CRM Handoff

| Field | Content |
| --- | --- |
| Purpose | Transfer accepted contact, usage, and upload metadata to the tenant CRM |
| Legal basis | Consent and pre-contractual inquiry handling |
| Data categories | Sanitized contact form data, project summary, upload metadata, usage tokens/cost metadata |
| Recipient | `mein-kuechenexperte` CRM in the separate website repository |
| Safeguards | Shared-secret webhook authentication, purpose-limited payloads, no raw audio, no public upload URLs |
