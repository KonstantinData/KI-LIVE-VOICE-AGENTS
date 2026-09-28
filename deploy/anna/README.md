# Anna: local FRITZ!Box telephone worker

Anna belongs to `KI-LIVE-VOICE-AGENTS`, tenant `mein-kuechenexperte`.
The separate website repository continues to own CRM UI and CRM data.
Notion tracking for this implementation was explicitly waived by the owner;
the unrelated Kuechenexperte AAI Chatbot repository must not be used.

## Implemented

- Explicit `phone_agents` opt-in, with only `anna-phone-assistant` enabled.
- Independent German phone prompt and public tenant knowledge.
- Optional FRITZ!Box SIP registration and inbound G.711 audio using pyVoIP.
- Bidirectional audio to OpenAI Realtime, paced playback, interruption handling,
  one concurrent call and a ten-minute call limit.
- Windows logon autostart for the current user, with a single background supervisor,
  retry after transient network failures and stop/status commands.
- One-time, locally confirmed credential entry into Windows Credential Manager,
  scoped to this tenant/agent and Windows user. No plaintext credential files.
- No outbound dialing, audio files, transcript persistence,
  contact capture, CRM writes, calendar booking or transfer to a human.

The telephone dependency is not imported by the FastAPI/widget runtime. Enabling
browser voice does not enable telephony. Other tenants default to no phone agents.

## Automatic start on Windows

Run `Anna-Einrichten.cmd` once and confirm protected storage. Enter the SIP
username/password and API key in the local terminal. The setup installs a
current-user `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` entry named
`KI-LIVE-VOICE-AGENTS-Anna`. It starts after this user logs in, not before login.
It requires no administrator account or system-wide Windows service.

The entry launches `pythonw.exe` and the absolute `background.py` entry point,
so the startup working directory does not matter. Keep this repository and its
`venv` at their configured paths. Re-run setup/install if the repository moves.

- `Start-Anna.cmd`: start in the background without credential prompts.
- `Anna-Status.cmd`: show autostart, credential presence, process and latest status.
- `Anna-Stoppen.cmd`: stop now; the next Windows login starts Anna again.
- `Anna-Autostart-Entfernen.cmd`: stop and remove only Anna's logon entry.

The supervisor waits while MicroSIP is running rather than killing it or replacing
its SIP registration. Disable MicroSIP's own autostart if Anna should always take
the account at login. Missing credentials leave a `setup_required` status; run
`Anna-Einrichten.cmd` to complete them. The setup may also be rerun after SIP
account credentials change. A display-name-only change needs no credential update.

Only status/lock/stop files live under `%LOCALAPPDATA%\KI-LIVE-VOICE-AGENTS\anna`.
The secrets live in Windows Credential Manager under
`KI-LIVE-VOICE-AGENTS/phone/mein-kuechenexperte/anna-phone-assistant`.
Removing autostart deliberately retains the credential; remove that exact entry
in Windows Credential Manager when it is no longer needed.
No password or API key appears in the startup command, environment files or logs.
The child watches a handle to its supervisor and exits if the supervisor dies.

## Installation and manual diagnostics

Use Python 3.12 (the current development environment). From the repository root:

```powershell
venv\Scripts\python.exe -m pip install -r requirements-telephony.txt
venv\Scripts\python.exe -m src.telephony --check --tenant mein-kuechenexperte --agent anna-phone-assistant
```

Connect this PC to the normal FRITZ!Box LAN, not the guest network. The existing
FRITZ!Box LAN/WLAN IP telephone account must receive only the intended test number.
The FRITZ!Box account/number assignment is the authoritative inbound route to Anna;
the CLI does not inspect the called number. Do not share this account across tenants.

Close MicroSIP for that account. For an optional foreground diagnostic run:

```powershell
venv\Scripts\python.exe -m src.telephony --run --tenant mein-kuechenexperte --agent anna-phone-assistant
```

Saved Windows credentials are reused automatically. Without saved credentials,
the foreground diagnostic command can prompt for the FRITZ!Box **SIP account
username**, SIP password and OpenAI API key without saving them. This is not the
router administrator account. No secret is accepted as a command-line argument.
Existing process variables
`FRITZBOX_SIP_USERNAME`, `FRITZBOX_SIP_PASSWORD`, `OPENAI_API_KEY`, or an already
configured ignored repository `.env`, are supported. Do not commit credentials.
An OpenAI API account with Realtime access and usage credit is required; the
ChatGPT subscription is not used by this worker.

The worker detects its local IPv4 address from the route to `fritz.box`. To choose
an interface explicitly, use `--server <router-LAN-IP> --local-ip <PC-LAN-IP>`.
Restrict inbound Windows firewall access for this Python process to the
FRITZ!Box's LAN IP on the private network. pyVoIP does not authenticate the sender
of every incoming SIP/RTP packet. SDP media addresses are checked against the
configured router, but this is not a substitute for a source-IP firewall rule.
The SIP listener uses UDP 5062, RTP UDP 10000-10020; OpenAI uses outbound TLS 443.
Do not create internet-facing port forwards. The PC must stay awake during calls.

## Verification and current limits

The previous MicroSIP test demonstrated FRITZ!Box/PC audio, not Anna's bridge.
Automated tests use fake phone/provider endpoints and check isolation, audio flow,
interruption, call limits and cleanup. A successful registration is not proof of
OpenAI access or an end-to-end call. Run these manual acceptance checks:

1. Start the worker and verify successful registration.
2. Call the assigned number externally; hear Anna's KI disclosure and greeting.
3. Ask a kitchen-project question; verify both audio directions.
4. Interrupt Anna while she speaks; old speech must stop promptly.
5. Hang up, then call again; also cancel a call before it is answered.
6. Stop using `Anna-Stoppen.cmd` (or Ctrl+C in foreground mode) and confirm unregistering.
7. After the one-time setup, sign out/in and verify registration without prompts.

Implementation verification on 2026-09-21 after the audio corrections: all 284 repository tests passed;
`ruff check src tests`, tenant JSON schema validation and local `--check` passed.
The full test run required execution outside the restricted filesystem sandbox
because Windows denied pytest access to its temporary directories.

The current-user logon entry was installed and read back. Its logon entry point
was exercised without credentials and correctly stopped with `setup_required`.
Actual Windows sign-out/sign-in and a real KI call remain manual acceptance checks.

Local preflight resolved the router and selected a local interface. After the
operator saved credentials, Anna was observed registered with the FRITZ!Box.
The idle worker was restarted with the new knowledge loader and registered again
at 2026-09-21T16:53:27Z. All 22 curated entries were verified in the generated
telephone instructions. The operator subsequently reported choppy, distorted and
slow audio in a real call. The pinned library's PCMA encoder incorrectly emitted
PCMU; the adapter now encodes the negotiated format. Both bridge and RTP output
now use compensated high-resolution deadlines, with a scoped Windows 1 ms timer
request. Tests cover G.711 wire silence, speech-band tone distortion, frame drift,
RTP counter rollover and timer cleanup. A local 100-frame timing check took
2.0012 seconds against a 2.000-second target. Post-fix listening acceptance is
still required; automated checks do not certify end-to-end call quality.

No secrets or live-call proof are included in this repository. If provider setup
fails, the worker declines/closes the call rather than leaving a silent call open.
There is no human-transfer or voicemail fallback yet. The pyVoIP 1.6.8 CANCEL
compatibility handler terminates pending calls using the library's busy response;
full SIP interoperability and Windows sleep/reconnect behavior need live testing.
This is an initial single-call local implementation, not a production telephony SLA.
Audio goes to the external provider; no claim of entirely local processing is made.

## Stop and rollback

Stop with `Anna-Stoppen.cmd` (or Ctrl+C for foreground mode). MicroSIP can then
use the account again. `Anna-Autostart-Entfernen.cmd` also removes the login entry.
Set Anna's `enabled` to `false` in the tenant registry to deny new calls on the next
profile check. An already running call is bounded by its configured time limit.
This change does not alter KEA, Olivia, FRITZ!Box routing, or other agents.

## Next increments

Anna's dedicated public knowledge is maintained in
[`anna.json`](../../registry/tenants/mein-kuechenexperte/knowledge/anna.json).
See [source review and maintenance](../../registry/tenants/mein-kuechenexperte/knowledge/ANNA.md)
for provenance, conflict decisions and automatic expiry. Updates to that file are
read at the next call; code changes require restarting the worker when idle.

Anna uses `gpt-realtime-1.5` for the customer-facing speech-to-speech call and
the `marin` voice. Her tenant profile exposes one bounded action:
`submit_phone_contact_handoff`. It requires separately confirmed contact and
transcript consent, confirmed contact details, and a caller-approved summary.
The runtime forwards the transient transcript and summary to the configured
tenant CRM webhook; it does not persist either locally. The website CRM owns
the internal notification and customer summary email.

Run `Anna-Einrichten.cmd` again after enabling this tool. The setup stores the
CRM handoff secret together with the SIP and OpenAI credentials in Windows
Credential Manager. Existing three-field credentials remain readable, but the
worker reports setup as incomplete until the new secret is supplied. Secret
values are never printed or stored in repository files.

Before unattended use, validate repeated and cancelled calls, firewall behavior,
provider availability, and operational fallback on the target FRITZ!Box 6591 Cable.
Appointment booking and human transfer are not available and Anna must not claim
those actions.

References: [pyVoIP 1.6.8](https://pyvoip.readthedocs.io/en/v1.6.8/Examples.html),
[Realtime audio and interruptions](https://developers.openai.com/api/docs/guides/realtime-conversations).
