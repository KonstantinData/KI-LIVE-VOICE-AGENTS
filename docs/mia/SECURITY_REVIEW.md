# Preliminary security review
Status: Phase 0 technical review, no legal certification or activation approval.
No confirmed active P0 incident established. The following P1 findings block public MIA activation.

## Release blockers and evidence
| Finding | Source evidence | Required control / proof |
|---|---|---|
| Missing cross-transport agent/session identity | R Conversation:17; chat_handler:153; voice_sessions:84 | immutable binding, unknown profile rejected, mid-session switch denied |
| Unprotected visitor/UUID resume | R voice_sessions.py:84-113 | scoped random capability, hashed at rest, expiry/rotation/revocation; no ID-only access |
| Declared MIME fallback | R project_upload_runtime.py:44-53 | quarantine/full decode and bounded safe parser; invalid bytes/polyglot rejected |
| Count-before-write upload quota, missing tenant predicate | same:145-170 | tenant-scoped atomic reservation across concurrent workers |
| In-memory limits, browser usage authority | R middleware/rate_limit.py:15; voice.py:576 | durable server reservations and provider deadline/concurrency |
| Retention 90-day copy vs 180/1095 defaults | R tenant.json:30; config.py:68; scheduler.py:35 | one approved policy; abandoned sessions expire; single leased cleanup owner |
| PDF page PII can reach provider | R project_uploads.py:186-206 | explicit minimization/provider disclosure; no false full-redaction claim |
| Legacy/new CRM disconnect + replay gaps | W crm-template-adoption.md:139; contact repository:240 | approved limited receiver, atomic dedupe/outbox; actual synthetic receipt |
| MIA media/resume/deletion unimplemented | source inventory | private protected media; full lifecycle/ownership tests |
| Booking authority absent | Anna-only grant; Zeeg embed | distinct actor/calendar grant, specific confirmation and status reconciliation |

## Threat boundaries
Treat visitor text, uploads/OCR, catalog content and provider output as untrusted data. These inputs cannot select tenants, grant tools, alter endpoint routes, request arbitrary calendars or overwrite historical evidence. Validate typed fields and service permissions independently of prompts.
Never solicit uncontrolled voice contact details. Secure form supplies contact and purpose-specific consent. No raw audio storage. Transcript storage/summary policy is explicit and minimized.
MIA AI identity and concept limitations visible before interaction and beside media. Microphone permission does not authorize marketing, CRM processing or provider upload on its own.
Private generated media never become public website assets. Signed grants bind tenant/agent/project/media/revision/expiry/intended consumer; no-store/nosniff. Resume bearer tokens must not appear in logs/ordinary URLs/CRM payloads.
Common manufacturer catalog contains no tenant customer/projects/discounts/credentials. Neutral catalog grants do not imply cross-area memory access.

## Current legal source check
Technical controls need purpose/lawful-basis, notice, minimization, retention, processor/transfer and appropriate security review; no compliance certification is claimed.
Primary sources inspected by H:
- [GDPR](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679)
- [AI Act Article 50](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50)
- [Commission transparency guidance](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems)
Assess provider/deployer obligations and machine-readable generated-media provenance; visible labels alone do not close every legal duty.

## Security acceptance
Negative tests cover forged/expired/revoked capabilities, profile switching, cross-tenant/agent/project/media, malicious uploads, hidden instructions, quota races, unknown write outcome, replay conflict, origin bypass and secret-free browser/log artifacts.
Independent H/I must review the combined state. No public activation until P0/P1 are resolved or an explicit approved scope deviation exists.
