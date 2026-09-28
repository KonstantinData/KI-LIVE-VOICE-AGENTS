# ANNA Microsoft 365 calendar integration

## Scope and current state

### Business-account migration (2026-09-28)

The owner requires the **business** Microsoft account for the master-calendar
address. The earlier personal-account authorization was the wrong destination,
despite sharing the same email alias. Calendar mode has been disabled during
migration to prevent further personal-calendar writes. The existing appointment
is retained by explicit owner instruction; do not copy, move or delete it.
Business-only code is deployed with 347 telephone tests passed and Ruff clean.
Runtime hashes match local config.py and oauth.py. The service is back in
production mode, but phone-client reads return `oauth_login_required` until
fresh business authorization. The persistent `compose.calendar-business.yaml`
overlay mounts `/var/lib/anna-calendar-business` as the service data directory;
the previous `/var/lib/anna-calendar` store is retained and not reused.
Backup: `/opt/anna-backups/business-calendar-code-20260928T145557Z`.
Never roll back to personal-account access without explicit owner authorization.
Business authorization and read-only acceptance subsequently completed on
2026-09-28 after the owner changed the app registration's `signInAudience` from
`PersonalMicrosoftAccount` to `AzureADMyOrg`. Live Graph confirms both mail and
UPN match the business master address, default calendar `Kalender`, owner address
matching the business account and `canEdit=true`. The running phone client
successfully returned free slots and rejected October 3 with `public_holiday`.
No business-calendar event was created by this verification; real-call write and
desktop visibility acceptance remain to be checked. Historical activation evidence below refers
to the previous personal-account connection and is not business acceptance.

Area: mein-kuechenexperte.de. Master calendar: `kontakt@konstantinmilonas.de`.
Operation notifications: `kontakt@mein-kuechenexperte.de`. This service belongs exclusively to the
`mein-kuechenexperte` / `anna-phone-assistant` identity. KEA has no calendar grant.

The isolated service at `/opt/anna-calendar` is in `production` mode as of
2026-09-28. The owner explicitly authorized activation and supplied the schedule.
The running Anna phone worker is connected through the private Docker network;
calendar tools are enabled only for Anna. Production requires complete validated
scheduling policy; missing or invalid policy fails closed.

## Approved booking policy

Source: `deploy/anna-server/calendar-policy.json`, owner-confirmed on 2026-09-28.
Timezone: Europe/Berlin. Appointment: free initial consultation, 30 minutes.
Minimum gap to other busy calendar events: 15 minutes, including events outside
the search window. The buffer may extend outside booking hours.

Owner-requested update on 2026-09-28: bookings and rescheduling require at least
24 elapsed hours of notice. This is internal scheduling information and must not
be explained to callers. Search must omit earlier slots; availability, preparation
and the final write must revalidate the cutoff. Cancellation remains available.

Deployed with the simplified confirmation dialogue on 2026-09-28 after 368
telephone tests and Ruff passed. Live phone-client searches returned no slots
within 23 hours, rejected a next-morning availability request, and returned
eligible September 30 slots. The loaded phone profile includes the new purpose
field and one-final-confirmation instruction. Anna registered again; Asterisk
was not restarted. No calendar records were changed by verification.
Source/config backup: `/opt/anna-backups/notice-dialog-20260928T163325Z`.
Rollback images: `anna-rollback:notice-dialog-20260928` and
`anna-calendar-rollback:notice-dialog-20260928`. Actual spoken dialogue still
requires a real-call acceptance check.

| Day | Booking windows |
| --- | --- |
| Monday | 09:00–19:00 |
| Tuesday–Friday | 09:00–12:30 and 18:30–19:00 |
| Saturday | 15:00–17:00 |
| Sunday | None |

The complete appointment must fit in one window. Search, preparation and final
create/reschedule all enforce duration, windows and buffer. Existing non-Anna
events block availability but remain non-editable by Anna.

Statutory public holidays in Baden-Wuerttemberg (`DE-BW`) are excluded using
Europe/Berlin local dates, including German Unity Day on October 3. The local
implementation covers New Year, Epiphany, Good Friday, Easter Monday, Labour Day,
Ascension Day, Whit Monday, Corpus Christi, German Unity Day, All Saints and both
Christmas holidays. Easter-relative dates are calculated without an external
calendar dependency. Availability checks, search, preparation and final
create/reschedule reject holidays even when weekly hours would otherwise allow
them. Cancellation of existing holiday appointments remains possible. The policy
tool reports the exclusion and region. Deployed on 2026-09-28 after 332 telephone
tests passed and changed-file Ruff checks passed. Read-only checks through the
running phone client reject October 3 with `public_holiday`, return no slots that
day, and still return slots on October 10. The existing October 3 appointment
was preserved at the owner's request. No test booking was created.
Rollback source: `/opt/anna-backups/holiday-fix-20260928T144646Z`;
previous image: `anna-calendar-rollback:holiday-20260928`. Only the calendar
sidecar was recreated, with zero active calls; phone and Asterisk were unchanged.

Slot search also enforces the caller's retained time-of-day preference. Morning
ends at 12:00, afternoon is after 12:00 and ends by 18:00, and starts from 18:00
belong to early evening or evening. A broad afternoon search therefore includes
Monday afternoon and Saturday 15:00–17:00, while the Tuesday–Friday 18:30 window
does not count as afternoon. These policy windows remain internal and are never
read back to callers.

## Production activation evidence

307 telephone tests passed; changed-code Ruff passed. Running container hashes
match all six published runtime files. Live checks verified delegated Graph read,
production policy through Anna's actual HTTP client, and five available slots.
Anna's SIP contact is present; worker and calendar service report zero restarts.
The unauthenticated internal status endpoint returns 401. Protected env files
remain mode 0600. No OAuth secret or encryption key is passed to the phone worker.
No real appointment was created by these activation checks. Real-call booking,
rescheduling, cancellation, hangup and notification receipt remain live acceptance.

The 2026-09-28 afternoon-search follow-up passed 326 telephone tests and Ruff.
Read-only production searches returned Monday starts at 12:30, 13:00 and 13:30,
and Saturday starts at 15:00, 15:30 and 16:00. No appointment was created.

Rollback source snapshots: `/opt/anna-backups/calendar-activation-20260928-0130`.
Protected configuration backup: `/opt/anna-backups/calendar-config-20260927T232706Z`.
Previous images: `anna-calendar-rollback:activation-20260928` and
`anna-rollback:calendar-activation-20260928`. Preserve OAuth and operation data.

The activation helper validates the policy, saves protected config backups, and
sets persistent Compose overlays without restarting services:

```bash
python3 /opt/anna-calendar/deploy/anna-server/activate-calendar.py \
  --policy /opt/anna-calendar/deploy/anna-server/calendar-policy.json
```

Do not run this again merely to inspect status. For subsequent restarts use
`cd /opt/anna-calendar && docker compose -p anna-calendar up -d` and the existing
Anna project in `/opt/anna/deploy/anna-server`; their `.env` files now retain the
required Compose file lists. Restart Anna only with zero active call channels.

## Architecture and changed files

- `src/agents/anna/calendar/config.py`: fixed mailbox and fail-closed environment.
- `oauth.py`: delegated authorization code + PKCE, browser-bound expiring state,
  encrypted SQLite token vault, serialized refresh and `/me` identity check.
- `graph.py`: bounded Graph client, paginated calendarView, conditional writes,
  immutable IDs, UTC and sanitized errors.
- `store.py`, `service.py`: encrypted operation ledger, cross-process write lock,
  collision recheck, prepared session-bound confirmations, idempotency, snapshots
  and notification status. Only ANNA-owned events can be changed or deleted.
- `app.py`: separate HTTP service, protected internal tools, OAuth callback.
- `src/telephony/calendar_tools.py`: narrow domain tools and a new affirmative
  caller turn required after preparation. No Graph credentials in voice sessions.
- `src/telephony/profiles.py`, `__main__.py`: opt-in ANNA profile/handler integration.
- `src/telephony/mail.py`: fixed MKE-operations notification using existing SMTP.
- `requirements-calendar.txt`, `deploy/anna-server/Dockerfile.calendar`,
  `compose.calendar.yaml`, `calendar.nginx.conf`, `configure-calendar.py`:
  isolated sidecar and protected setup. `compose.calendar-client.yaml` is active
  on the phone worker; `compose.calendar-network.yaml` joins the private network.
- Tests: `test_calendar_oauth_graph.py`, `test_calendar_service.py`,
  `test_calendar_boundary.py` under `tests/test_telephony`.

The Graph adapter uses GET `/v1.0/me`, GET `/v1.0/me/calendarView`,
GET `/v1.0/me/events` for transaction reconciliation, and GET/POST/PATCH/DELETE
`/v1.0/me/events[/{id}]`. Delegated scopes are exactly `offline_access User.Read
Calendars.ReadWrite`. SMTP is reused; no Graph Mail.Send permission is requested.

## Protected configuration

Server file `/etc/anna/calendar.env` is root-owned mode 0600. Token/operation data
is at `/var/lib/anna-calendar` with directory mode 0700 and database mode 0600;
the encryption key is separate from that data. Preserve both in restricted backup.
Never print credentials in CI, logs, chat, or compose configuration output.

Required variables: `MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`,
`MS_REDIRECT_URI`, `MS_CALENDAR_USER`, `ANNA_CALENDAR_ENCRYPTION_KEY`,
`ANNA_CALENDAR_API_TOKEN`, `ANNA_CALENDAR_DATA_DIR`, `ANNA_CALENDAR_MODE`.
Use disabled mode until app configuration is supplied, and test mode for initial
acceptance. Production additionally requires `ANNA_CALENDAR_WEEKLY_HOURS` (JSON,
Monday=0 through Sunday=6), `ANNA_CALENDAR_DURATION_MINUTES` and
`ANNA_CALENDAR_BUFFER_MINUTES`. The sidecar reuses `/etc/anna/smtp.env` read-only.
Use the specific business directory ID for both `MS_TENANT_ID` and
`MS_AUTHORITY_TENANT`. Generic `common`, `organizations` and `consumers`
authorities are rejected. Pending authorizations and saved tokens are bound to
the directory, app client ID and master-calendar address; legacy personal tokens
require a fresh login. A matching email alias alone does not prove business
account identity.

Exact Entra **Web** redirect URI:

`https://api.mein-kuechenexperte.de/anna-calendar/auth/microsoft/callback`

Setup steps (operator, not the caller):

1. Local PowerShell: `ssh root@46.225.221.42`.
2. Remote Linux shell: `python3 /opt/anna-calendar/deploy/anna-server/configure-calendar.py`.
   Enter tenant ID, application ID and client secret **value** at hidden prompts.
3. Remote shell: `cd /opt/anna-calendar`, then
   `docker compose -p anna-calendar -f deploy/anna-server/compose.calendar.yaml up -d`.
4. View `ANNA_CALENDAR_API_TOKEN` only in the private SSH terminal. Open
   `https://api.mein-kuechenexperte.de/anna-calendar/auth/microsoft/start`, enter
   that setup token, and sign in as the master-calendar owner. Never send the
   setup token or client secret through chat.
5. Run the test-event acceptance sequence before any phone activation.
   Remote shell: `docker exec anna-calendar-anna-calendar-1 python /app/calendar-smoke.py`.
   This sends three authorized test notifications to the MKE operations mailbox and
   stops on any uncertain result; inspect the ledger before retrying.

Nginx adds only `/anna-calendar/`; the existing KEA location is preserved.
Internal endpoints are not public. OAuth access logging is disabled, errors do
not reflect provider bodies, and callback responses use no-store/no-referrer.
The sidecar binds to loopback 8735. A phone activation must connect the sidecar
to the existing ANNA Docker network and pass only the internal API token, service
URL and `ANNA_CALENDAR_TOOLS_ENABLED=true` to ANNA; never OAuth credentials.

## Write and notification semantics

Availability returns no customer details. Candidate lookup requires confirmed
name plus email or phone, original start, and consent. Caller-provided identity
traits are matching evidence, not strong identity proof; ambiguous matches fail
closed. Pre-existing appointments not created by this integration are deliberately
not editable until an explicit ownership/import policy exists.

Preparation expires after five minutes and is bound to the actual phone session.
The phone adapter additionally checks for a new explicit caller affirmation.
Contact correctness is confirmed once. When contact information is expressly
supplied for the booking, no separate question about its use for that booking is
required. Unrelated contact details must not acquire booking purpose implicitly.
Slot selection is followed by preparation and exactly one final confirmation
question. A prior slot selection or silence does not authorize the write.
Only a successful calendar result permits the phrase that the appointment is
entered; before writing Anna acknowledges the chosen slot without implying that
it has already been booked.
The service serializes its own writers and rechecks availability before Graph
writes. Graph offers no atomic global slot reservation: simultaneous manual or
third-party calendar writes remain a residual race and require operational review.
Changes use ETags and preserve the original body with appended reschedule history.
Deletion snapshots are encrypted before deletion and used for the owner email.

The master-calendar address is used only for Microsoft Graph access; it is never
an email recipient. Calendar-operation emails go only to the MKE operations
mailbox. Customer email remains subject to the existing explicit consent and
confirmed-email flow; this calendar workflow does not send unconfirmed customer mail.

An ambiguous write is persisted as uncertain and is not blindly retried.
SMTP acceptance is not inbox delivery. Notification failures remain durable and
visible through authenticated `/internal/status`; an operator can POST
`/internal/retry-notifications` without repeating the calendar change. SMTP
cannot guarantee exactly-once delivery after ambiguous network failures; stable
Message-IDs support diagnosis, but do not guarantee recipient deduplication.

## Historical initial verification and remaining acceptance

Local telephone suite: 197 passed. Follow-up changed-code checks: 10 passed.
OAuth coverage includes state/PKCE, wrong identity, token encryption/refresh,
provider failure, pagination and conditional writes. Service coverage includes
concurrent slot requests, cross-session rejection, hangup, uncertain writes,
notification-only retry, DST rejection, foreign events, create/move/delete and
preserved history. Boundary tests cover KEA exclusion and fixed email recipient.

Deployed smoke checks: disabled service starts; HTTPS origin start page 200,
callback without authorization 400, private namespace 404, KEA health 200.
Public local-connection checks: KEA health, calendar health and setup page 200.
Server-origin public requests received Cloudflare 403, while direct-origin and
local public checks passed; this is recorded separately from service health.
Existing SMTP authentication succeeds. KEA baseline checks: 67 local files and 87 server files,
zero changes against the task-start snapshots. Existing phone containers were
not restarted.

Recipient correction: the Microsoft master calendar remains
`kontakt@konstantinmilonas.de`, while calendar-operation notifications now go
only to `kontakt@mein-kuechenexperte.de`. A final synthetic run verified create,
move/history and delete with three SMTP acceptances for the MKE mailbox. No
synthetic ANNA TEST event remains in the master calendar. The earlier test
notifications addressed to the master-calendar mailbox predate this correction;
they cannot be recalled.

Initial app setup, OAuth, synthetic create/move/delete, approved policy and
production activation are now complete. Mailbox receipt and live phone
confirmation/hangup acceptance remain separate checks. Historical test defaults
(Mon–Fri 09:00–17:00, flexible duration, no buffer) are not production policy.

OAuth login completed successfully for the personal master account. The deployed
test harness completed the explicit synthetic sequence: create, owner SMTP
acceptance, reschedule with original-body/history verification, owner SMTP
acceptance, cancel, owner SMTP acceptance. The durable operation ledger reports
three `complete` operations and zero pending/failed notifications. The temporary
ANNA TEST appointment was deleted. Inbox and Spam receipt verification remains
an operator check; SMTP acceptance alone does not prove delivery.

Final deployed smoke check: public setup and health 200, unauthenticated callback
400, internal status path 404, KEA health 200. Executing the test harness while
disabled stops with `Refused: explicit test mode required.` before any write.

## Git handoff

Current branch: `codex/anna-phone-agent`, with existing dirty tracked files and
untracked ANNA work preserved. No commit, push, branch deletion or merge performed.
Open pull requests: none at the handoff check. Local branches retained:
`codex/anna-phone-agent`, `codex/liquisto-navigation-crm-network`,
`codex/liquisto-navigation-delivery-observability`,
`codex/liquisto-navigation-single-call-prompt`, `codex/liquisto-voice-navigation`,
`codex/liquisto-voice-navigation-v1-2`, `main`. Existing remote-tracking branches:
`origin/codex/liquisto-navigation-delivery-observability`,
`origin/codex/liquisto-voice-navigation`, `origin/main` (not refreshed for this
non-Git deployment task).

## Official references

- [Microsoft authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow)
- [Baden-Wuerttemberg statutory public holidays](https://im.baden-wuerttemberg.de/de/service/feiertage)
- [Calendar view](https://learn.microsoft.com/en-us/graph/api/calendar-list-calendarview?view=graph-rest-1.0)
- [Create event](https://learn.microsoft.com/en-us/graph/api/calendar-post-events?view=graph-rest-1.0)
- [Update event](https://learn.microsoft.com/en-us/graph/api/event-update?view=graph-rest-1.0)
