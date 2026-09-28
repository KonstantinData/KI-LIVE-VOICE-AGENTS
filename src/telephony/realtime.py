"""Bounded, ephemeral PCMU bridge between SIP and OpenAI Realtime."""

from __future__ import annotations

import asyncio
import base64
from collections import deque
import json
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

from .sip import SipCall
from .timing import FrameClock, WindowsAudioTimer


class PhoneBridgeError(RuntimeError):
    """A sanitized telephone bridge failure without provider payloads."""


START_BUFFER_BYTES = 800  # 100 ms at 8 kHz; absorbs normal network jitter.
GREETING_INPUT_GUARD_SECONDS = 0.3


async def run_phone_call(
    call: SipCall,
    *,
    api_key: str,
    session_config: dict,
    greeting: str,
    max_call_seconds: int = 600,
    tool_handler: Callable[[str, dict[str, Any], str], Awaitable[dict[str, Any]]] | None = None,
) -> None:
    """Answer only after provider configuration succeeds; always close the call.

    The supplied session must select PCMU for both audio directions. No audio,
    transcripts, credentials or provider errors are logged or persisted.
    """
    tasks: list[asyncio.Task] = []
    timer = WindowsAudioTimer()
    try:
        from websockets.asyncio.client import connect

        if not api_key or max_call_seconds <= 0:
            raise PhoneBridgeError("Telephone session configuration is invalid.")
        audio = session_config.get("audio", {})
        if any(
            audio.get(direction, {}).get("format", {}).get("type") != "audio/pcmu"
            for direction in ("input", "output")
        ):
            raise PhoneBridgeError("Telephone sessions require PCMU audio.")
        model = quote(session_config.get("model", "gpt-realtime"), safe="")
        async with asyncio.timeout(max_call_seconds):
            async with connect(
                f"wss://api.openai.com/v1/realtime?model={model}",
                additional_headers={"Authorization": f"Bearer {api_key}"},
                open_timeout=15,
                close_timeout=3,
                max_size=2**20,
                max_queue=16,
            ) as socket:
                async def send(event: dict) -> None:
                    await socket.send(json.dumps(event))

                await send({"type": "session.update", "session": session_config})
                async with asyncio.timeout(15):
                    while True:
                        event = json.loads(await socket.recv())
                        if event.get("type") == "error":
                            raise PhoneBridgeError("The voice provider rejected the session.")
                        if event.get("type") == "session.updated":
                            break
                timer.acquire()
                call.answer()
                await send({"type": "response.create", "response": {
                    "instructions": (
                        "Sprich jetzt die folgende Begrüßung wortgetreu. Ändere, ergänze oder "
                        "ersetze kein einziges Wort. Warte danach auf die Antwort des Anrufers: "
                        f"{greeting}"
                    ),
                }})

                pending: deque[tuple[str, str, int, bytearray]] = deque()
                sent: dict[tuple[str, int], int] = {}
                interrupted: set[str] = set()
                active_response: str | None = None
                last_item: tuple[str, str, int] | None = None
                queued = 0
                playback_started: set[str] = set()
                first_audio_played = asyncio.Event()
                transcript_parts: list[str] = []
                completed_tool_calls: set[str] = set()

                async def receive() -> None:
                    nonlocal active_response, last_item, queued
                    while True:
                        event = json.loads(await socket.recv())
                        kind = event.get("type")
                        if kind == "error":
                            raise PhoneBridgeError("The voice provider reported a session failure.")
                        if kind == "response.created":
                            active_response = event["response"]["id"]
                        elif kind == "response.done":
                            if event.get("response", {}).get("status") == "failed":
                                raise PhoneBridgeError("The voice response failed.")
                            if event.get("response", {}).get("id") == active_response:
                                active_response = None
                        elif kind == "response.output_audio.delta":
                            response_id = event["response_id"]
                            if response_id in interrupted:
                                continue
                            pcm = base64.b64decode(event["delta"], validate=True)
                            if queued + len(pcm) > 8000 * 30:
                                raise PhoneBridgeError("Telephone playback exceeded its buffer limit.")
                            identity = (response_id, event["item_id"], event.get("content_index", 0))
                            if pending and pending[-1][:3] == identity:
                                pending[-1][3].extend(pcm)
                            else:
                                pending.append((*identity, bytearray(pcm)))
                            queued += len(pcm)
                        elif kind in {
                            "conversation.item.input_audio_transcription.completed",
                            "response.output_audio_transcript.done",
                        }:
                            text = " ".join(str(event.get("transcript") or "").split())
                            if text:
                                role = "Anrufer" if kind.startswith("conversation.item") else "Anna"
                                transcript_parts.append(f"{role}: {text}")
                        elif kind == "response.function_call_arguments.done":
                            call_id = str(event.get("call_id") or "")
                            name = str(event.get("name") or "")
                            if not call_id or call_id in completed_tool_calls:
                                continue
                            completed_tool_calls.add(call_id)
                            result: dict[str, Any]
                            try:
                                arguments = json.loads(event.get("arguments") or "{}")
                                if not isinstance(arguments, dict) or tool_handler is None:
                                    raise ValueError
                                result = await tool_handler(
                                    name, arguments, "\n".join(transcript_parts)
                                )
                            except Exception:
                                # Tool details and customer data must not be reflected to the model.
                                result = {"success": False, "error": "handoff_failed"}
                            await send({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": call_id,
                                    "output": json.dumps(result, ensure_ascii=False),
                                },
                            })
                            await send({"type": "response.create"})
                        elif kind == "input_audio_buffer.speech_started":
                            interrupted.update(chunk[0] for chunk in pending)
                            # A normal caller turn must not truncate a fully
                            # played, completed reply and erase its transcript.
                            unfinished_last_item = last_item is not None and (
                                active_response == last_item[0]
                                or any(chunk[:3] == last_item for chunk in pending)
                            )
                            if unfinished_last_item:
                                interrupted.add(last_item[0])
                            if active_response:
                                interrupted.add(active_response)
                                # Server VAD also cancels generation; dropping late deltas
                                # handles audio already in flight without a cancel race.
                            truncations = {(p[1], p[2]) for p in pending}
                            if unfinished_last_item:
                                truncations.add((last_item[1], last_item[2]))
                            pending.clear()
                            queued = 0
                            last_item = None
                            for item_id, index in truncations:
                                await send({"type": "conversation.item.truncate",
                                            "item_id": item_id, "content_index": index,
                                            "audio_end_ms": sent.get((item_id, index), 0) // 8})

                async def capture() -> None:
                    clock = FrameClock()
                    # Do not let line noise cancel the greeting before its first
                    # syllable. Normal caller interruption works after 300 ms.
                    await first_audio_played.wait()
                    await asyncio.sleep(GREETING_INPUT_GUARD_SECONDS)
                    while call.is_active:
                        pcm = call.read_audio()
                        if pcm:
                            await send({"type": "input_audio_buffer.append", "audio":
                                        base64.b64encode(pcm).decode("ascii")})
                        await clock.wait()

                async def playback() -> None:
                    nonlocal queued, last_item
                    clock = FrameClock()
                    while call.is_active:
                        if pending:
                            response_id, item_id, index, pcm = pending[0]
                            response_buffered = sum(
                                len(chunk[3]) for chunk in pending if chunk[0] == response_id
                            )
                            # Provider chunks normally align to 20 ms. A final short
                            # frame is padded only after generation ends. New responses
                            # start with 100 ms buffered to prevent audible RTP underflow.
                            ready = (
                                response_id in playback_started
                                or response_buffered >= START_BUFFER_BYTES
                                or response_id != active_response
                            )
                            if ready and (len(pcm) >= 160 or response_id != active_response):
                                playback_started.add(response_id)
                                frame = bytes(pcm[:160])
                                del pcm[:160]
                                queued -= len(frame)
                                call.write_audio(frame.ljust(160, b"\xff"))
                                first_audio_played.set()
                                sent[(item_id, index)] = sent.get((item_id, index), 0) + len(frame)
                                last_item = (response_id, item_id, index)
                                if not pcm:
                                    pending.popleft()
                        await clock.wait()

                tasks = [asyncio.create_task(fn()) for fn in (receive, capture, playback)]
                try:
                    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        task.result()
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        raise
    except PhoneBridgeError:
        raise
    except TimeoutError:
        raise PhoneBridgeError("The telephone session reached its time limit.") from None
    except Exception:
        raise PhoneBridgeError("The telephone audio connection failed.") from None
    finally:
        try:
            call.hangup()
        except Exception:
            pass
        timer.release()
