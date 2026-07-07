# Data Protection Impact Assessment - Runtime Scope

**Legal basis:** GDPR Art. 35  
**Status:** July 2026

## Processing Description

**System:** KI-LIVE-VOICE-AGENTS runtime  
**Tenant:** `mein-kuechenexperte`  
**Agent:** KEA  
**Purpose:** AI-supported chat and live voice project intake, project upload
handling, and secure handoff to an external CRM.

This repository does not operate the CRM dashboard, CRM record derivation, lead
CRUD, or CRM reporting.

## Data Categories

| Category | Required | Purpose |
| --- | --- | --- |
| Visitor/session identifiers | Yes | Runtime conversation assignment |
| Chat messages and final transcripts | Yes where feature is used | Context and service continuity |
| Project details | Optional | Inquiry qualification and handoff summary |
| Uploaded files | Optional and consented | Project context and team review |
| Contact form data | Optional and consented | External CRM handoff |

## Risk Assessment

| Risk | Likelihood | Severity | Mitigation |
| --- | --- | --- | --- |
| Cross-tenant data exposure | Low | High | Tenant profile checks, scoped DB reads, origin validation |
| Contact details entering voice stream | Medium | Medium | Prompt rules, secure form requirement, no voice PII policy |
| Upload exposure | Low | High | Private storage, signed short-lived CRM access, no public URLs |
| Excessive retention | Medium | Medium | Scheduled runtime retention cleanup |
| Unintended CRM ownership in runtime | Low | Medium | CRM boundary documented in `AGENTS.md`; handoff-only integration |

## Safeguards

- Consent gate before chat/voice processing.
- Microphone access only after explicit browser action.
- Raw audio is not stored by default.
- Upload analysis requires explicit consent.
- Contact and usage data are handed off through authenticated webhooks.
- CRM screens and CRM persistence live outside this repository.
