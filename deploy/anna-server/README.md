# Anna server deployment

This deployment keeps the tenant-scoped Anna worker behind a local Asterisk
gateway. Asterisk owns the Easybell registration and public SIP/RTP boundary;
Anna can register only on the private Docker network and has no outbound dialplan.

The checked-in Compose profile is opt-in. For a new installation, copy
`.env.example` to `.env`, set mode `0600`, and start only after Easybell
verification and all secrets are available, using
`docker compose --profile enabled up -d --build`.

Persistent data is mounted from `/var/lib/ki-team/anna`. Raw call audio and full
transcripts are not stored. Asterisk exposes UDP 5060 and UDP 20000-20020; restrict
the Hetzner firewall to Easybell traffic wherever the platform supports the
provider FQDN. OpenAI and CRM use outbound TLS 443.

`PUBLIC_IP` must be the server's fixed public IPv4 address. It is used only in
SIP/SDP advertisements; do not place credentials in that variable.

Easybell SIP Trunk values:

- registrar: `voip.easybell.de`
- SIP: UDP 5060
- provider RTP range: UDP 20000-50000
- codecs used here: G.711 A-law and u-law

Do not start the profile until the account is verified, the assigned number is
routed to the trunk, and the website CRM webhook has the matching handoff secret.

## Audio contract and troubleshooting

The SIP worker and Realtime bridge exchange 160-byte G.711 PCMU frames (20 ms
at 8 kHz). PCMU samples pass through unchanged. If Asterisk negotiates PCMA,
the SIP boundary converts between PCMA and PCMU through signed 16-bit linear
samples. Never use 8-bit linear PCM for this conversion: quiet speech loses
resolution and becomes distorted. PCMU silence is `0xff`, including buffer
underflow, timestamp gaps and final-frame padding.

Only one RTP audio stream is supported. Repeated trusted SDP connection lines
must resolve to one stream; the upstream library's linear-PCM mixing must not
be applied to G.711 bytes. Codec diagnostics contain only codec names, not SIP
packets, caller identifiers, raw audio or transcripts.

The user confirmed a successful real call before the September 2026 audio
optimization. Asterisk allows both `alaw` and `ulaw`; that configuration alone
does not prove the codec of a completed call. Verify the next call with sanitized
codec diagnostics. Live audio quality requires a comparison call even when the
automated fidelity and lifecycle tests pass.

## Conversation start and interruptions

The bridge requests the greeting once in the initial response. The persistent
Anna prompt handles the ongoing conversation and must not repeat the greeting
instruction on every caller turn. After the caller states an intent, Anna
addresses that intent directly using the information already provided.

When speech interrupts buffered or still-generating audio, truncate the unheard
portion in the provider conversation. Do not truncate a completed response that
has already played in full: its heard content must remain in the conversation
history for the next answer.

## Updating the existing Anna worker

The active deployment is at `/opt/anna/deploy/anna-server`. Preserve its local
Compose settings, secrets and data mounts. Check there are no active calls,
back up the current source files and retain the previous Anna image before
uploading tested changes. Run on the server:

```bash
cd /opt/anna/deploy/anna-server
docker compose exec -T asterisk asterisk -rx 'core show channels count'
docker compose build anna
docker compose up -d --no-deps --force-recreate anna
docker compose logs --since=2m --tail=50 anna
docker compose exec -T asterisk asterisk -rx 'pjsip show contacts'
```

Do not restart Asterisk for a worker-only audio update. Confirm Anna has
registered again before requesting one short comparison call. Check greeting
onset, quiet speech, interruptions and natural pacing, then confirm call cleanup.
