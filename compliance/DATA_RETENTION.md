# Data Retention Concept

**Legal basis:** GDPR Art. 5(1)(e) storage limitation  
**Status:** July 2026

## Runtime Data In This Repository

| Data category | Runtime table/storage | Retention | Action |
| --- | --- | --- | --- |
| Conversations | `conversations` | 180 days by default | Delete or anonymize by scheduled cleanup |
| Messages and transcripts | `messages` | 180 days by default | Delete or anonymize by scheduled cleanup |
| Private project uploads | private upload storage + message metadata | 180 days by default | Delete file and mark metadata as deleted |
| Audit events | `events` | 1095 days by default | Retain for operational audit, then archive/delete |
| Knowledge chunks | `knowledge_chunks` | tenant policy | Remove when source is removed or tenant is deprovisioned |

## External CRM Data

Lead, contact, activity, cost-report, and CRM workspace retention is owned by
the `mein-kuechenexperte` repository for the `mein-kuechenexperte` tenant. This
runtime only sends sanitized handoff payloads and does not retain CRM record
ownership tables.

## Implementation Notes

- `src/api/services/scheduler.py` enforces runtime cleanup.
- Upload cleanup removes known expired files and orphan files below the private
  upload root.
- Handoff endpoints must not include raw audio, unrestricted transcripts, or
  public file URLs.
