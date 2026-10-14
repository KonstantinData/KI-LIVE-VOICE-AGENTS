# Product requirements
Status: proposed; not implemented. Product owner A, coordinator accountable.

## Product and release scope
MIA (mia-kitchen-design) is an explicitly selected AI concept assistant for mein-kuechenexperte.de. KEA remains available independently; Anna remains a phone-only agent.
Flow: select MIA -> voice/text choice -> natural discovery with conditional visual aids -> concept -> up to five targeted revisions -> optional secure contact -> optional explicitly confirmed booking -> correct CRM handoff.
The structured brief, uncertainty and image form one concept. Images are not manufacture-ready plans. Contact is not required to see or revise a concept. Communicate the immediate visible-result goal at entry; show the visitor's first concept before optional postcode/name/email/phone capture. Do not substitute a later-contact promise or generic stock picture for that result.
MKE currently positions itself as an independent adviser. Ballerina source access does not establish dealer status, price authority, supplier availability or public media rights.

### Demonstrator
One source-bound, fully verified small Ballerina series subset; synthetic participants/uploads; full discovery/brief/concept/revision journey; protected handoff preview and clearly labelled synthetic CRM/calendar outcomes. No production writes.
An unpaid schematic renderer and provider fixtures can prove UI/model workflow. Claim real photorealistic generation only after authorized actual image-generation/edit tests. Fixture voice/image/calendar evidence never closes real-provider gates.

### Production MVP
Server-bound identity and permissions on every transport; natural voice + complete text fallback; validated source/profile constraints; immutable revisions/private media; durable jobs/cancel/recovery; effective budgets; protected resume; secure contact; real test CRM delivery and provider-confirmed booking; retention, monitoring, independent QA and rollback.
Missing real booking or CRM proof remains an MVP blocker. CARAT does not block the demonstrator.

### Later
Vendor-verified/licensed CARAT adapter and practical import test; expanded approved catalogs/studios; professionally reviewed technical planning.

## Acceptance requirements
| ID | User need / decisive result |
|---|---|
| MIA-01 | KEA/MIA have independent entries; selected identity is enforced server-side, cannot switch existing session or select Anna |
| MIA-02 | Voice/text both complete discovery; denied microphone/disconnection yields text continuation, no automatic recording |
| MIA-03 | Natural dialog covers use/household, priorities, style/materials, room and optional budget; no recited answer summaries or fixed picture questionnaire; proportionate empathy and context-appropriate light humor; corrections/skipped answers supported |
| MIA-04 | Internal structured brief distinguishes customer facts, extracted data, assumptions, unknowns and conflicts; no mandatory spoken recap; dimensions unknown remain null; clarify specific ambiguities only |
| MIA-05 | Personalized concept references the accepted brief/version; no false technical/product/price guarantee |
| MIA-06 | One initial concept + five successful revisions; requested structured changes only; previous versions viewable; visual drift disclosed |
| MIA-07 | Optional validated private PDF/sketch/image input; provider-processing disclosure and bounded analysis |
| MIA-08 | Consent-based scoped resume with expiry/revocation; IDs or contact-form submission alone do not verify ownership |
| MIA-09 | Optional protected postcode/first-name/last-name/email/phone form after first visible concept; initial generation/refinement never require these fields; no solicited spoken PII; separate purposes and no compulsory marketing consent |
| MIA-10 | Selected concept, structured wishes, assumptions, media/history references reach the authoritative CRM once; retries observable |
| MIA-11 | Correct calendar/service/timezone; availability recheck, explicit action-bound confirmation; provider success before confirmed UI |
| MIA-12 | Generation/CRM/calendar failures preserve last confirmed state; retry/cancel/restart never invent success or duplicate effects |
| MIA-13 | 320px mobile, keyboard, screen reader, zoom/reflow, focus, reduced motion and useful image description |
| MIA-14 | No browser API keys; tenant/agent/project isolation, injection resistance, private media and enforced deletion/retention |
| MIA-15 | Atomic voice/model/image/edit/upload/concurrency/storage/spend limits; attribution by tenant/agent/function |
| MIA-16 | KEA/Anna source and actual customer journeys regressions checked; MIA kill switch independent |
| MIA-17 | Neutral export documents geometry/material/appliance/source/uncertainty; CARAT import never claimed without practical evidence |
| MIA-18 | Timing and perceived 70-80% match evaluated reproducibly, separate objective dimensions and customer rating |
| MIA-19 | Backup/restore/rollback/alerts exercised; production only after concrete approval |

## Customer wording candidates
Follow [conversation design](CONVERSATION_DESIGN.md): one relevant next question, optional brief acknowledgment, no formulaic recap. Audible empathy/humor requires separate live-voice validation.
- Entry: “MIA – Küchenideen entwickeln”; preserve KEA existing name/purpose.
- Introduction: “Ich bin MIA, Ihre KI-Assistentin für erste Küchenideen.”
- Image: “KI-Konzeptvisualisierung. Maße, technische Machbarkeit und konkrete Produkte sind noch nicht fachlich geprüft.”
- Unknown room: “Die Maße sind noch offen. Ich kennzeichne die Annahmen.”
- Secure form: “Bitte tragen Sie Ihre Kontaktdaten hier im geschützten Formular ein.”
- Timeout: “Die Buchung ist noch nicht bestätigt. Wir prüfen den Status.”
- Confirmation only on authoritative result: “Ihr Termin ist bestätigt.”

## Synthetic journeys
1. No measurements: useful inspiration, island feasibility unresolved.
2. 2.4 x 3.1m room, door/window, island desire conflicting with circulation.
3. Family/two cooks/storage, no open shelves: functional and must-avoid fidelity.
4. Accessible-use needs: retain preferences, no accessibility certification.
5. Voice interruption changes dark to light fronts; corrected brief used.
6. Five revisions: front/worktop/handles/appliance position/lighting.
7. Optional uncertain-scale plan, then corrected measurement and source provenance.
8. Invalid Ballerina series/width/front/discontinued choice rejected.
9. Microphone denied, narrow mobile, no contact: complete successful journey.
10. Image/CRM outage, duplicate form click and restart.
11. Competing slot booking and timeout-after-write reconciliation.
12. Expired/foreign resume capability: no disclosure.

Discovery 2-3 minutes and 70-80% perceived match are hypotheses. A possible 2026-10-16 meeting is unconfirmed. Budget and real-user pilot remain open.
