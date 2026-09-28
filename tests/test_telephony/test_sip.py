"""SIP boundary tests without network traffic or account credentials."""

from enum import Enum
import math
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from src.telephony import sip


class State(Enum):
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    ENDED = "ENDED"


@pytest.mark.parametrize("codec,silence", [("PCMA", 0xD5), ("PCMU", 0xFF)])
def test_real_rtp_payload_matches_negotiated_g711_codec(codec, silence):
    pytest.importorskip("pyVoIP")
    sip._load_phone_class()
    from pyVoIP.RTP import PayloadType, RTPClient

    client = object.__new__(RTPClient)
    client.preference = getattr(PayloadType, codec)
    # G.711 silence has distinct wire values: a mislabeled codec becomes noise.
    assert client.encode_packet(b"\xff" * 160) == bytes([silence]) * 160


@pytest.mark.parametrize("codec", ["PCMA", "PCMU"])
def test_real_rtp_speech_band_tone_survives_encoding(codec):
    pytest.importorskip("pyVoIP")
    import audioop

    sip._load_phone_class()
    from pyVoIP.RTP import PayloadType, RTPClient

    client = object.__new__(RTPClient)
    client.preference = getattr(PayloadType, codec)
    import struct

    tone = struct.pack("<1600h", *(
        round(100 * math.sin(2 * math.pi * 440 * n / 8000)) for n in range(1600)
    ))
    pcmu = audioop.lin2ulaw(tone, 2)
    encoded = client.encode_packet(pcmu)
    decode = audioop.alaw2lin if codec == "PCMA" else audioop.ulaw2lin
    decoded = decode(encoded, 2)
    error = audioop.add(tone, audioop.mul(decoded, 2, -1), 2)
    assert audioop.rms(error, 2) < 10


def test_rtp_clock_compensates_processing_and_wraps_headers(monkeypatch):
    now = [0.0]
    packets = []
    client = SimpleNamespace(
        NSD=True, preference=8, outSequence=65535, outTimestamp=4294967200,
        outSSRC=1, outIP="192.168.1.1", outPort=10000,
        pmout=SimpleNamespace(read=lambda: b"\x80" * 160),
        encode_packet=lambda data: b"\xd5" * len(data),
    )

    def send(packet, destination):
        packets.append((now[0], packet))
        now[0] += 0.003
        if len(packets) == 3:
            client.NSD = False

    client.sout = SimpleNamespace(sendto=send)
    monkeypatch.setattr(sip.time, "perf_counter", lambda: now[0])
    monkeypatch.setattr(sip.time, "sleep", lambda delay: now.__setitem__(0, now[0] + delay))
    sip._transmit_rtp(client)
    assert [stamp for stamp, _ in packets] == pytest.approx([0, 0.02, 0.04])
    assert all(len(packet) == 172 for _, packet in packets)
    assert [int.from_bytes(packet[2:4], "big") for _, packet in packets] == [65535, 0, 1]
    assert [int.from_bytes(packet[4:8], "big") for _, packet in packets] == [4294967200, 64, 224]


class FakeCall:
    def __init__(self):
        self.state = State.RINGING
        self.denied = False
        self.output = []
        self.RTPClients = [SimpleNamespace(
            preference=SimpleNamespace(name="PCMU"), read=self.read_audio,
        )]

    def answer(self):
        self.state = State.ANSWERED

    def deny(self):
        self.denied = True
        self.state = State.ENDED

    def hangup(self):
        self.state = State.ENDED

    def read_audio(self, *, length, blocking):
        assert (length, blocking) == (160, False)
        return b"\xff" * length

    def write_audio(self, data):
        self.output.append(data)


class FakePhone:
    def __init__(self, *args, **kwargs):
        self.options = kwargs
        self.state = "INACTIVE"

    def start(self):
        self.state = "REGISTERED"

    def stop(self):
        self.state = "INACTIVE"

    def get_status(self):
        return SimpleNamespace(name=self.state)


@pytest.fixture
def phone_factory(monkeypatch):
    monkeypatch.setattr(sip, "_load_phone_class", lambda: FakePhone)
    monkeypatch.setattr(sip.socket, "gethostbyname", lambda server: "192.168.1.1")

    def make(callback):
        return sip.FritzBoxPhone("router.test", "test", "test", "192.168.1.2", callback)

    return make


def test_registration_configuration_and_audio_contract(phone_factory):
    def callback(call):
        assert not call.is_active
        call.answer()
        assert call.is_active
        assert call.read_audio() == b"\xff" * 160
        call.write_audio(b"\xff" * 160)
        with pytest.raises(ValueError):
            call.write_audio(b"short")

    phone = phone_factory(callback)
    assert phone._phone.options["sipPort"] == 5062
    assert phone._phone.options["rtpPortHigh"] == 10020
    phone.start()
    assert phone.status == "REGISTERED"
    raw = FakeCall()
    phone._incoming(raw)
    assert raw.state == State.ENDED
    assert len(raw.output) == 1
    phone.stop()
    assert phone.status == "INACTIVE"


def test_concurrent_call_is_denied_and_next_call_can_start(phone_factory):
    entered, release = Event(), Event()
    calls = []

    def callback(call):
        calls.append(call)
        call.answer()
        entered.set()
        assert release.wait(3)

    phone = phone_factory(callback)
    first, second = FakeCall(), FakeCall()
    worker = Thread(target=phone._incoming, args=(first,))
    worker.start()
    try:
        assert entered.wait(3)
        phone._incoming(second)
        assert second.denied
        assert first.state == State.ANSWERED
        assert len(calls) == 1
    finally:
        release.set()
        worker.join(3)
    phone._incoming(FakeCall())
    assert len(calls) == 2


def test_callback_failure_is_sanitized_and_call_closed(phone_factory, capsys):
    def callback(call):
        call.answer()
        raise RuntimeError("sensitive caller context")

    phone = phone_factory(callback)
    raw = FakeCall()
    phone._incoming(raw)
    assert phone.last_call_failed
    assert raw.state == State.ENDED
    assert capsys.readouterr() == (
        "Telephone audio codec: PCMU\nSIP call handler failed: RuntimeError\n", "",
    )


def test_cancelled_or_stopping_call_never_reaches_agent(phone_factory):
    calls = []
    phone = phone_factory(calls.append)
    cancelled = FakeCall()
    cancelled.state = State.ENDED
    phone._incoming(cancelled)
    phone.stop()
    ringing = FakeCall()
    phone._incoming(ringing)
    assert calls == []
    assert ringing.denied


def test_real_library_cancel_callback_closes_pending_call():
    pytest.importorskip("pyVoIP")
    phone_class = sip._load_phone_class()
    # Avoid constructor: no SIP sockets or registration needed for dispatch.
    phone = object.__new__(phone_class)
    raw = FakeCall()
    phone.calls = {"test-call": raw}
    phone.callback(SimpleNamespace(method="CANCEL", headers={"Call-ID": "test-call"}))
    assert raw.denied
    assert raw.state == State.ENDED


def test_real_library_debug_is_suppressed(capsys):
    library = pytest.importorskip("pyVoIP")
    sip._load_phone_class()
    library.DEBUG = True
    try:
        library.debug("secret", "secret error")
        assert capsys.readouterr() == ("", "")
    finally:
        library.DEBUG = False


def test_real_unanswered_rtp_client_can_be_rejected():
    pytest.importorskip("pyVoIP")
    sip._load_phone_class()
    from pyVoIP.RTP import RTPClient
    from pyVoIP.VoIP import CallState, VoIPCall

    raw = object.__new__(VoIPCall)
    raw.state = CallState.RINGING
    raw.call_id = "test-call"
    raw.request = SimpleNamespace(headers={"Call-ID": raw.call_id})
    raw.phone = SimpleNamespace(server="router.test", port=5060, calls={raw.call_id: raw})
    raw.sip = SimpleNamespace(
        gen_busy=lambda request: "busy",
        out=SimpleNamespace(sendto=lambda *args: None),
    )
    raw.RTPClients = [object.__new__(RTPClient)]
    sip._deny_ringing(raw)
    assert raw.state == CallState.ENDED
    assert raw.phone.calls == {}
    # Avoid unrelated library destructor port bookkeeping on this socketless fake.
    del raw.phone


@pytest.mark.parametrize("address,count", [("203.0.113.1", 1), ("192.168.1.1", 2)])
def test_foreign_or_multiple_media_connections_rejected(address, count):
    request = SimpleNamespace(body={
        "c": [{"address": address, "address_count": count}],
        "m": [{"type": "audio", "port_count": 1}],
    })
    assert not sip._router_media_only(request, "192.168.1.1")


def test_single_router_audio_stream_allowed():
    request = SimpleNamespace(body={
        "c": [{"address": "192.168.1.1", "address_count": 1}],
        "m": [{"type": "audio", "port_count": 1}],
    })
    assert sip._router_media_only(request, "192.168.1.1")


def test_duplicate_router_connection_lines_allowed():
    request = SimpleNamespace(body={
        "c": [
            {"address": "192.168.1.1", "address_count": 1},
            {"address": "192.168.1.1", "address_count": 1},
        ],
        "m": [{"type": "audio", "port_count": 1}],
    })
    assert sip._router_media_only(request, "192.168.1.1")


def test_duplicate_connections_are_normalized_without_mutating_offer(monkeypatch):
    pytest.importorskip("pyVoIP")
    phone_class = sip._load_phone_class()
    phone = object.__new__(phone_class)
    phone.server = "192.168.1.1"
    captured = []
    monkeypatch.setattr(phone_class.__bases__[0], "callback", lambda self, req: captured.append(req))
    connection = {"address": phone.server, "address_count": 1}
    request = SimpleNamespace(method="INVITE", body={
        "c": [dict(connection), dict(connection)],
        "m": [{"type": "audio", "port_count": 1}],
    })
    phone.callback(request)
    assert len(request.body["c"]) == 2
    assert captured[0].body["c"] == [connection]
    from pyVoIP.VoIP import VoIPCall
    from pyVoIP.RTP import PayloadType
    from src.telephony.audio import PcmuBuffer

    raw = object.__new__(VoIPCall)
    raw.RTPClients = []
    raw.sendmode = "sendrecv"
    raw.dtmf_callback = lambda value: None
    raw.create_rtp_clients(
        {0: PayloadType.PCMU}, "127.0.0.1", 10000, captured[0], 10002,
    )
    assert len(raw.RTPClients) == 1
    assert isinstance(raw.RTPClients[0].pmin, PcmuBuffer)
    assert isinstance(raw.RTPClients[0].pmout, PcmuBuffer)


def test_multiple_rtp_clients_cannot_be_answered():
    raw = FakeCall()
    raw.RTPClients *= 2
    with pytest.raises(sip.SipAdapterError, match="could not be answered"):
        sip._PyVoipCall(raw).answer()
    assert raw.state == State.RINGING


def test_invalid_invite_rejected_before_library_creates_call():
    pytest.importorskip("pyVoIP")
    phone = object.__new__(sip._load_phone_class())
    phone.server, phone.port = "192.168.1.1", 5060
    sent = []
    phone.sip = SimpleNamespace(
        gen_busy=lambda request: "busy",
        out=SimpleNamespace(sendto=lambda *args: sent.append(args)),
    )
    phone.callback(SimpleNamespace(method="INVITE", body={}))
    assert sent == [(b"busy", ("192.168.1.1", 5060))]
