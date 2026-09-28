"""Realtime telephone bridge tests with no network or credentials."""

import asyncio
import base64
import json

import pytest

from src.telephony.realtime import PhoneBridgeError, run_phone_call


SESSION = {"type": "realtime", "audio": {
    "input": {"format": {"type": "audio/pcmu"}},
    "output": {"format": {"type": "audio/pcmu"}},
}}


class Call:
    is_active = False

    def __init__(self):
        self.answered = False
        self.closed = False
        self.frames = []

    def answer(self):
        self.answered = self.is_active = True

    def hangup(self):
        self.is_active = False
        self.closed = True

    def read_audio(self):
        return b"\xff" * 160

    def write_audio(self, data):
        self.frames.append(data)


class Socket:
    def __init__(self):
        self.events = asyncio.Queue()
        self.sent = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def send(self, data):
        self.sent.append(json.loads(data))

    async def recv(self):
        return json.dumps(await self.events.get())

    def event(self, kind, **fields):
        self.events.put_nowait({"type": kind, **fields})


@pytest.fixture
def setup(monkeypatch):
    socket, call = Socket(), Call()
    monkeypatch.setattr("websockets.asyncio.client.connect", lambda *a, **kw: socket)
    return socket, call


async def wait_until(predicate):
    async with asyncio.timeout(1):
        while not predicate():
            await asyncio.sleep(0.001)


def start(call, **kwargs):
    return asyncio.create_task(run_phone_call(
        call, api_key="test-only", session_config=SESSION, greeting="Hallo", **kwargs,
    ))


@pytest.mark.asyncio
async def test_answer_waits_for_provider_and_audio_flows_both_ways(setup):
    socket, call = setup
    task = start(call)
    await wait_until(lambda: socket.sent)
    assert not call.answered
    socket.event("session.updated")
    await wait_until(lambda: call.answered)
    socket.event("response.created", response={"id": "r1"})
    socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                 delta=base64.b64encode(b"\xff" * 320).decode())
    socket.event("response.done", response={"id": "r1", "status": "completed"})
    await wait_until(lambda: len(call.frames) == 2)
    assert call.frames == [b"\xff" * 160, b"\xff" * 160]
    await wait_until(lambda: any(
        event["type"] == "input_audio_buffer.append" for event in socket.sent
    ))
    inputs = [e for e in socket.sent if e["type"] == "input_audio_buffer.append"]
    assert base64.b64decode(inputs[0]["audio"]) == b"\xff" * 160
    call.is_active = False
    await task
    assert call.closed and socket.closed


@pytest.mark.asyncio
async def test_pcmu_codes_are_preserved_in_both_directions(setup):
    socket, call = setup
    # Include every G.711 code, including quiet speech and both zero encodings.
    payload = bytes(range(256)) + bytes(range(64))
    call.read_audio = lambda: payload[:160]
    socket.event("session.updated")
    task = start(call)
    try:
        await wait_until(lambda: call.answered)
        socket.event("response.created", response={"id": "r1"})
        socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                     delta=base64.b64encode(payload).decode())
        socket.event("response.done", response={"id": "r1", "status": "completed"})
        await wait_until(lambda: len(call.frames) == 2)
        assert b"".join(call.frames) == payload
        await wait_until(lambda: any(
            event["type"] == "input_audio_buffer.append" for event in socket.sent
        ))
        inputs = [e for e in socket.sent if e["type"] == "input_audio_buffer.append"]
        assert base64.b64decode(inputs[0]["audio"]) == payload[:160]
    finally:
        call.is_active = False
        await task


@pytest.mark.asyncio
async def test_playback_prebuffers_new_response_to_avoid_start_underflow(setup):
    socket, call = setup
    socket.event("session.updated")
    task = start(call)
    await wait_until(lambda: call.answered)
    socket.event("response.created", response={"id": "r1"})
    socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                 delta=base64.b64encode(b"\xff" * 640).decode())
    await asyncio.sleep(0.05)
    assert call.frames == []
    socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                 delta=base64.b64encode(b"\xff" * 160).decode())
    await wait_until(lambda: call.frames)
    call.is_active = False
    await task


@pytest.mark.asyncio
async def test_short_response_flushes_without_full_start_buffer(setup):
    socket, call = setup
    socket.event("session.updated")
    task = start(call)
    await wait_until(lambda: call.answered)
    socket.event("response.created", response={"id": "r1"})
    socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                 delta=base64.b64encode(b"\xff" * 100).decode())
    socket.event("response.done", response={"id": "r1", "status": "completed"})
    await wait_until(lambda: call.frames)
    assert call.frames == [b"\xff" * 160]
    call.is_active = False
    await task


@pytest.mark.asyncio
async def test_interruption_discards_queued_and_late_audio(setup):
    socket, call = setup
    socket.event("session.updated")
    task = start(call)
    await wait_until(lambda: call.answered)
    socket.event("response.created", response={"id": "r1"})
    socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                 delta=base64.b64encode(b"\xff" * 8000).decode())
    await wait_until(lambda: call.frames)
    socket.event("input_audio_buffer.speech_started")
    await wait_until(lambda: any(e["type"] == "conversation.item.truncate" for e in socket.sent))
    count = len(call.frames)
    truncated = next(e for e in socket.sent if e["type"] == "conversation.item.truncate")
    assert truncated["audio_end_ms"] == count * 20
    socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                 delta=base64.b64encode(b"\xff" * 160).decode())
    await asyncio.sleep(0.05)
    assert len(call.frames) == count
    call.is_active = False
    await task


@pytest.mark.asyncio
async def test_normal_caller_turn_preserves_fully_played_greeting(setup):
    socket, call = setup
    socket.event("session.updated")
    task = start(call)
    try:
        await wait_until(lambda: call.answered)
        socket.event("response.created", response={"id": "greeting"})
        socket.event("response.output_audio.delta", response_id="greeting", item_id="hello",
                     delta=base64.b64encode(b"\xff" * 320).decode())
        socket.event("response.done", response={"id": "greeting", "status": "completed"})
        await wait_until(lambda: len(call.frames) == 2)
        socket.event("input_audio_buffer.speech_started")
        await wait_until(socket.events.empty)
        assert not any(e["type"] == "conversation.item.truncate" for e in socket.sent)
        # A subsequent answer still uses the same conversation normally.
        socket.event("response.created", response={"id": "answer"})
        socket.event("response.output_audio.delta", response_id="answer", item_id="reply",
                     delta=base64.b64encode(b"\xfe" * 160).decode())
        socket.event("response.done", response={"id": "answer", "status": "completed"})
        await wait_until(lambda: len(call.frames) == 3)
        assert call.frames[-1] == b"\xfe" * 160
    finally:
        call.is_active = False
        await task


@pytest.mark.asyncio
@pytest.mark.parametrize("generation_done", [True, False], ids=[
    "completed-generation-with-pending-playback", "active-generation-with-audio-in-flight",
])
async def test_unfinished_audio_still_truncates_on_caller_interruption(setup, generation_done):
    socket, call = setup
    socket.event("session.updated")
    task = start(call)
    try:
        await wait_until(lambda: call.answered)
        socket.event("response.created", response={"id": "r1"})
        length = 8000 if generation_done else 800
        socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                     delta=base64.b64encode(b"\xff" * length).decode())
        if generation_done:
            socket.event("response.done", response={"id": "r1", "status": "completed"})
            await wait_until(lambda: len(call.frames) > 0)
        else:
            # No queued audio remains, but the response is still generating.
            await wait_until(lambda: len(call.frames) == 5)
        socket.event("input_audio_buffer.speech_started")
        await wait_until(lambda: any(
            e["type"] == "conversation.item.truncate" for e in socket.sent
        ))
        count = len(call.frames)
        truncated = next(e for e in socket.sent if e["type"] == "conversation.item.truncate")
        assert truncated["item_id"] == "i1"
        assert truncated["audio_end_ms"] == count * 20
        assert count < length // 160 if generation_done else count == 5
        socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                     delta=base64.b64encode(b"\xfe" * 800).decode())
        await asyncio.sleep(0.05)
        assert len(call.frames) == count
    finally:
        call.is_active = False
        await task


@pytest.mark.asyncio
async def test_provider_rejection_does_not_answer_or_leak_error(setup):
    socket, call = setup
    socket.event("error", error={"message": "sensitive provider payload"})
    with pytest.raises(PhoneBridgeError, match="rejected") as error:
        await start(call)
    assert "sensitive" not in str(error.value)
    assert not call.answered
    assert call.closed and socket.closed


@pytest.mark.asyncio
async def test_timeout_cleans_up_active_call_and_tasks(setup):
    socket, call = setup
    socket.event("session.updated")
    before = set(asyncio.all_tasks())
    with pytest.raises(PhoneBridgeError, match="time limit"):
        await start(call, max_call_seconds=0.05)
    assert call.answered and call.closed and socket.closed
    assert set(asyncio.all_tasks()) <= before


@pytest.mark.asyncio
async def test_excessive_audio_buffer_fails_closed(setup):
    socket, call = setup
    socket.event("session.updated")
    socket.event("response.output_audio.delta", response_id="r1", item_id="i1",
                 delta=base64.b64encode(b"\xff" * 240001).decode())
    with pytest.raises(PhoneBridgeError, match="buffer limit"):
        await start(call)
    assert call.closed and socket.closed


@pytest.mark.asyncio
async def test_provider_failure_during_call_closes_audio_tasks(setup):
    socket, call = setup
    socket.event("session.updated")
    task = start(call)
    await wait_until(lambda: call.answered)
    socket.event("response.done", response={"id": "r1", "status": "failed",
                                           "status_details": {"error": "private"}})
    with pytest.raises(PhoneBridgeError, match="response failed"):
        await task
    assert call.closed and socket.closed


@pytest.mark.asyncio
async def test_external_cancellation_closes_call(setup):
    socket, call = setup
    socket.event("session.updated")
    task = start(call)
    await wait_until(lambda: call.answered)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert call.closed and socket.closed


@pytest.mark.asyncio
async def test_audio_timer_released_when_call_is_cancelled(setup, monkeypatch):
    socket, call = setup
    events = []

    class Timer:
        def acquire(self):
            events.append("acquire")

        def release(self):
            events.append("release")

    monkeypatch.setattr("src.telephony.realtime.WindowsAudioTimer", Timer)
    socket.event("session.updated")
    task = start(call)
    await wait_until(lambda: call.answered)
    assert events == ["acquire"]
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert events == ["acquire", "release"]


@pytest.mark.asyncio
async def test_function_call_receives_transcript_and_returns_bounded_output(setup):
    socket, call = setup
    received = []

    async def handler(name, arguments, transcript):
        received.append((name, arguments, transcript))
        return {"success": True}

    socket.event("session.updated")
    task = start(call, tool_handler=handler)
    await wait_until(lambda: call.answered)
    socket.event(
        "conversation.item.input_audio_transcription.completed",
        transcript="Ich wünsche einen Rückruf.",
    )
    socket.event("response.output_audio_transcript.done", transcript="Gerne.")
    socket.event(
        "response.function_call_arguments.done",
        call_id="call-1",
        name="submit_phone_contact_handoff",
        arguments=json.dumps({"contact_consent_confirmed": True}),
    )
    await wait_until(lambda: any(
        event.get("item", {}).get("type") == "function_call_output"
        for event in socket.sent
    ))
    assert received == [(
        "submit_phone_contact_handoff",
        {"contact_consent_confirmed": True},
        "Anrufer: Ich wünsche einen Rückruf.\nAnna: Gerne.",
    )]
    output = next(event for event in socket.sent if event.get("item", {}).get("type") == "function_call_output")
    assert json.loads(output["item"]["output"]) == {"success": True}
    responses = [event for event in socket.sent if event["type"] == "response.create"]
    assert responses == [
        {"type": "response.create", "response": {"instructions": (
            "Sprich jetzt die folgende Begrüßung wortgetreu. Ändere, ergänze oder "
            "ersetze kein einziges Wort. Warte danach auf die Antwort des Anrufers: Hallo"
        )}},
        {"type": "response.create"},
    ]
    call.is_active = False
    await task
