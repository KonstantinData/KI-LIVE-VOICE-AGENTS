# AI Risk Classification

**Legal basis:** EU AI Act  
**Status:** July 2026  
**System:** KI-LIVE-VOICE-AGENTS runtime

## System Overview

| Field | Content |
| --- | --- |
| System name | KI-LIVE-VOICE-AGENTS |
| Tenant example | `mein-kuechenexperte` |
| Public agent name | KEA |
| Purpose | AI-supported chat and live voice intake for customer project inquiries |
| Data boundary | Runtime processing and external CRM handoff only |

## Classification

Current classification: **Limited Risk**

Rationale:

- The system interacts directly with natural persons and therefore requires
  transparent AI disclosure.
- It does not make binding legal, financial, credit, employment, education,
  law-enforcement, migration, or biometric decisions.
- It does not own CRM acceptance/rejection decisions or CRM record workflows.

## High-Risk Triggers To Avoid

- Using runtime scoring for credit, financing, or legally relevant eligibility.
- Using protected characteristics for prioritization.
- Treating AI summaries as binding professional advice without human review.

## Required Controls

- Clear disclosure that users interact with AI.
- Consent before chat/voice processing.
- Human review for CRM follow-up and project assessment.
- Tenant isolation and audit logging.
