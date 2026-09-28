# Anna prompt composition and supported behavior

Status: deployed to the Anna worker on 2026-09-28. The running container matches
the three tested runtime files. Anna's SIP contact is present, the provider trunk
is registered, and the worker reports zero restarts. Direct SMTP remains enabled.
Calendar tools were subsequently activated on 2026-09-28 with the owner-approved
weekly windows, 30-minute free initial consultation and 15-minute buffer; see
`anna-calendar-integration.md`. No live conversation was tested.

Rollback: source backup at `/opt/anna-backups/prompt-20260928-0101/source-before.tar.gz`
and previous image `anna-rollback:prompt-20260928-0101`. The newly added
`calendar_tools.py` was absent before deployment. Server settings and Asterisk
were preserved. Image configuration smoke checks passed without network access.
The external Realtime session check was blocked by automatic approval review;
provider acceptance of the changed session requires separate approval/verification.

## Sources and assembly

`src/agents/anna/prompt.py` owns the shared identity, language, conversation,
public-information, privacy and authority rules. It also owns separate direct
email, CRM handoff and calendar sections. `src/telephony/profiles.py` resolves
the tenant grants and calendar opt-in, then builds both the tool list and prompt.
Calendar rules are selected explicitly; prose is no longer modified using string
replacement. Knowledge remains restricted to Anna's approved tenant scope.

Anna handles the caller's actual request without mandatory project qualification.
She answers public factual questions but does not recommend products or paid
services, provide kitchen design advice or promise callback deadlines.
The runtime issues the greeting once. The prompt prevents repeated introductions.

## Capability contracts

| Capability | Rules |
| --- | --- |
| Contact tool absent | No handoff, email or CRM capture promises; offer the public contact address. |
| Direct email (`ANNA_DIRECT_SMTP` exactly `true`) | Confirm name and return channel; obtain internal forwarding consent. Phone-only callbacks are supported. No transcript or CRM record. Resolve optional customer summary consent and confirmed email before the single tool call. Evaluate both delivery flags separately. |
| CRM handoff (other SMTP values) | Require valid email, contact consent, transcript consent and acceptance of the requested customer summary. Send the transient transcript only with consent. CRM capture and requested email are not evidence of email delivery. |
| Calendar opt-in enabled | Read current time and approved policy with get_booking_policy, then use availability tools. Identify existing appointments through confirmed contact and original start time. Prepare every write, read back the returned summary with unambiguous date, time and timezone, then obtain a fresh explicit caller confirmation before writing. |
| Calendar opt-in disabled | No availability checks, booking, rescheduling or cancellation promises. |

A calendar change remains successful when only its notification fails. Unknown
write results require manual clarification, never automatic retry. Finding an
appointment does not itself authorize a change. Do not disclose other customers'
appointment details. Test-mode restrictions remain enforced by the calendar service.
Known time preferences are retained and passed to slot search. Anna searches all
matching upcoming days instead of assuming that one weekday's windows apply to
the rest of the week. Monday and Saturday afternoon availability is therefore
considered without disclosing the internal weekly schedule.

## Booking dialogue update (2026-09-28)

Deployed after 368 telephone tests and Ruff passed. Live loaded-profile checks
confirm the new instructions and purpose field; Anna is registered. Spoken
behavior has not yet been verified in a real call after this update.

The minimum 24-hour booking notice is internal and is never explained to callers.
Anna offers only eligible slots. She confirms an email address once for correctness
and does not ask a second permission question when it was explicitly supplied for
booking. Unrelated contact information does not establish booking purpose.
After a clear slot selection she acknowledges the choice ("Dann nehmen wir ..."),
prepares the appointment, and asks exactly one final confirmation question
("Dann buche ich ... Ist das so richtig?"). A new affirmative caller turn permits
the write. Slot selection or silence alone is insufficient. "Der Termin ist
eingetragen" is reserved for a confirmed successful calendar write. Corrections
invalidate the affected confirmation and require only that corrected value to
be checked again.

## Language and remaining limits

### Professional contact references and regional comprehension

Anna uses neutral forwarding language by default and `Herr Milonas` when a
personal reference is necessary. The full name remains valid for business
identity and signatures; account addresses and identifiers are unchanged. No
personal availability or callback promise may be invented.

Swabian and Stuttgart/Baden-Wuerttemberg regional speech is interpreted by
meaning and context. Anna responds in standard German without imitating or
commenting on the dialect. Explicit clock times and spelled letters take
priority over dialect interpretation. Ambiguous half-day clock expressions
require a short clarification rather than a guess from booking windows.
Appointment preferences are normalized in call-scoped state; time-specific
exclusions must stay scoped to their date. An expressed wish for a short meeting
does not change the approved duration. Name/email correctness and one final
booking confirmation remain enforced.

Text-level regression tests establish deterministic normalization and tool
constraints, not acoustic recognition quality. Real regional speech over the
telephone requires separate acceptance, including background noise and ambiguous
time expressions.

Deployed on 2026-09-28 after 393 telephone tests and targeted Ruff checks passed.
The running profile contains the professional address and regional-language rules.
A read-only business-calendar search for next Monday with early-evening context
and "Dreiviertel sechse" returned 2026-10-05 17:45-18:15 Europe/Berlin.
Both services are running and Anna's SIP contact is registered. No appointment
was created during validation. Rollback sources and images were retained under
`/opt/anna-backups/dialect-20260928T164646Z` and the matching `dialect-20260928T164646Z`
rollback image tags. Real telephone speech acceptance remains a separate task.

German with formal address is the default. Clear English speech switches the
conversation to English; individual foreign words do not. Transcription no longer
forces a German language hint. The calendar confirmation guard accepts bounded
German and English affirmative responses only after preparation and a new caller
turn; qualified, negative and unrelated responses do not authorize writes.

This is not a claim of fully localized delivery: customer email subjects and
framing remain German. The direct-email summary can use the conversation language.
The legacy CRM payload still labels its transcript `de-DE`; multilingual metadata
and downstream email localization need a separate contract change and verification.
Outbound dialing is not implemented. Anna may collect callback requests through
an available handoff tool but cannot call customers herself.

This document describes current prompt behavior. The broader target in
`anna-reception-role.md`, including CRM caller recognition, is not implied to be
implemented by this change.

## Verification

Run Ruff on the changed Python files and the telephone test suite. The session
matrix covers both delivery modes, contact grant present/absent and calendar
enabled/disabled. Calendar confirmation tests cover fresh versus stale consent,
English and German replies, rejections and action mismatches. Before deployment,
perform live German and English calls, including interruptions, phone-only intake,
optional customer summary and calendar notification failure handling.
