# Olivia voice-quality tuning, 2026-10-09

A subsequent employee-facing refinement is deployed; see [its current evidence](olivia-communication-2026-10-09.md).

## Requested behavior

Konstantin reported that Olivia sounds computer-like in both timbre and wording.
The change tunes the existing Liquisto assistant's voice delivery and channel
instructions. The approved Olivia de Jong persona and canonical identity remain
unchanged: `liquisto / liquisto-assistant / internal-authenticated`.

## Scoped change

- Voice selection: `shimmer` to `marin` in the existing live-voice registry entry.
- Model remains `gpt-realtime-2.1`; transport, turn detection, navigation contract,
  tools, sideband, rights, provider credentials and server settings remain fixed.
- Channel instructions now specify warm attentive delivery, varied sentence
  melody, conversational pacing, short thought pauses, short spoken sentences,
  varied openers, focused clarification and natural interruption recovery.
- Short examples demonstrate missing information, suggestions and the existing
  no-business-write boundary. No fabricated facts, human identity or actions.
- No artificial laughter, breath noises, filler sounds or repetitive role recitals.
- Text prompt, persona, approved identity, navigation rules and all native
  memory hooks are byte-equivalent outside the Voice channel instruction block.

The official [Realtime conversation guide](https://developers.openai.com/api/docs/guides/realtime-conversations)
recommends `marin` and `cedar` for best voice quality. Its voice selection applies
when a new session is created; an existing session that has emitted audio cannot
change voices. The [Realtime prompting guide](https://developers.openai.com/api/docs/guides/voice-prompting)
supports explicit tone, conversational pacing, examples and varied phrasing.
These are configuration choices, not proof of subjective perceived quality.

## Exact production pins

- Host: `scas-runtime-prod`, `178.105.62.169`.
- Container: `liquisto-assistant-liquisto-local-assistant-1`.
- Inspected baseline:
  `sha256:62d21cbfa33540e72de32a1e986d650f30ff8056ba27a2fc34ee31b0846e6636`.
- Voice-quality image:
  `sha256:0fd86a4347dffffb5f72d105e70d24cc301376541f6b407e62613adf7c326cf0`.
- Tag: `liquisto-assistant-liquisto-local-assistant:olivia-voice-quality-20261009`.
- Shared prompt SHA-256:
  `c84427cd58cb5a3ad3c03b29697bd82f9b301b9746724104dd8f704c979becf3`.
- Registry SHA-256:
  `6276d032a442746b318726210c0d236ae213e7f7df169d7c6e8a5445e372fda3`.
- Unchanged provider adapter SHA-256:
  `1d348ae123d2b16945f7aa15e91a57d71693b0f1e6dc6820ed8ddb6fe587a6f4`.

The dedicated two-file overlay uses the exact final identity/memory-enabled
image from the preceding deployment. The guard allows only the canonical voice
change and the Voice instruction literal, pins all existing memory/provider hooks,
requires exact output image/file hashes, and verifies unchanged container config,
mounts and private networks before/after replacement. The previous container is
retained stopped as `liquisto-assistant-liquisto-local-assistant-1-pre-voice-quality-20261009`.
It does not replace the runtime with a plain repository image lacking memory hooks.
Packaged code preserves the inspected baseline's CRLF encoding so the guard's
byte comparison outside the Voice instruction literal is exact. Git checkout
line-ending conversion is not a permission to change deployed file hashes.

## Identity Core and data

Identity Core revision **2** is retained. No operator append is appropriate:
this is channel-delivery tuning consistent with its existing collegial style,
not a new persona or agent identity. No memory database write or migration is
performed by deployment. Ordinary text/Voice remain read-only and capture/forget
remain the existing closed authenticated preference operations. The sealed
technical memory authorization profile is unchanged.

## Verification

Local assistant/navigation/provider suite: 143 passed; changed-surface Ruff passed.
Dedicated Voice deployment guard: 34 tests passed. Complete memory README/CI
suite: 243 tests and 41 subtests passed; full repository Ruff passed. Its 17
PostgreSQL tests are skipped locally and were already separately verified before
this tuning; no database schema, Identity Core or preference-operation code changed.
The Voice call test checks `marin` in both API response and provider session
output. The guarded deployment checks and final live evidence are recorded below.

The controlled production switch completed and verified identical container
configuration, native memory/provider hooks and all prompt bytes outside the
Voice rules. The server's existing Compose memory override is pinned to the new
immutable image for future recreation; its private memory settings are unchanged.

Live configuration inspection confirms `marin`, `gpt-realtime-2.1`, the new speech
rules and the same navigation-only tool. The unchanged native acceptance check
passed in **read-only** mode after deployment: signed memory context, current
authority, native chat/Voice-init hooks, wrong-digest/foreign-subject rejection
and unchanged tools. Its protected synthetic write test is not repeated because
preference operations, operator code and their earlier live acceptance are
unchanged. No user record was deleted or written for this tuning.

The protected memory inspection confirms Identity Core revision 2 and unchanged
technical core. Scope counts remain 0 active episode/assertion/evidence/reflection
rows, 8 retired events and 2 retired batches, equal to the preceding deployment.
An inspector's suggested next revision 3 was not appended.

Subjective acoustic quality and a real employee audio conversation remain to
be assessed separately from backend Voice initialization. Start a new Olivia
Voice session after deployment; a pre-existing session keeps its original voice.

The real signed native text regression request returned HTTP 200 with Olivia de
Jong, no prepared actions and identical memory context before/after. This proves
the text path continues to work; it is not an acoustic Voice evaluation.
