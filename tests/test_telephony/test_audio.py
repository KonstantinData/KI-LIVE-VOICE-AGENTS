"""Wire fidelity, loss handling, and bounded telephone audio retention."""

from types import SimpleNamespace

import pytest

from src.telephony.audio import PcmuBuffer
from src.telephony import sip


def test_underflow_and_timestamp_gaps_use_pcmu_silence():
    buffer = PcmuBuffer()
    assert buffer.read() == b"\xff" * 160
    buffer.write(100, b"abc")
    buffer.write(105, b"def")
    assert buffer.read(10) == b"abc\xff\xffdef\xff\xff"
    buffer.write(108, b"ghi")
    assert buffer.read(3) == b"ghi"


def test_timestamp_rollover_and_late_packets():
    buffer = PcmuBuffer()
    buffer.write(2**32 - 2, b"ab")
    assert buffer.read(2) == b"ab"
    buffer.write(0, b"cd")
    buffer.write(2**32 - 2, b"xy")
    assert buffer.read(2) == b"cd"


def test_consumed_audio_is_discarded_and_discontinuities_are_bounded():
    buffer = PcmuBuffer(max_bytes=320)
    for offset in range(0, 16000, 160):
        buffer.write(offset, b"a" * 160)
        assert buffer.read() == b"a" * 160
        assert len(buffer._data) == 0
    buffer.write(10000000, b"b" * 1000)
    assert len(buffer._data) == 320
    assert buffer.read() == b"b" * 160


def test_real_rtp_pcmu_codes_are_preserved_in_both_directions():
    pytest.importorskip("pyVoIP")
    sip._load_phone_class()
    from pyVoIP.RTP import PayloadType, RTPClient

    client = object.__new__(RTPClient)
    client.preference = PayloadType.PCMU
    client.pmin = PcmuBuffer()
    codes = bytes(range(256))
    client.parse_pcmu(SimpleNamespace(timestamp=42, payload=codes))
    assert client.read(256, blocking=False) == codes
    assert client.encode_packet(codes) == codes


def test_real_pcma_conversion_uses_sixteen_bit_reference():
    pytest.importorskip("pyVoIP")
    import audioop

    sip._load_phone_class()
    from pyVoIP.RTP import PayloadType, RTPClient

    client = object.__new__(RTPClient)
    client.preference = PayloadType.PCMA
    client.pmin = PcmuBuffer()
    codes = bytes(range(256))
    client.parse_pcma(SimpleNamespace(timestamp=42, payload=codes))
    assert client.read(256, blocking=False) == audioop.lin2ulaw(audioop.alaw2lin(codes, 2), 2)
    assert client.encode_packet(codes) == audioop.lin2alaw(audioop.ulaw2lin(codes, 2), 2)


@pytest.mark.parametrize("payload_type", [0, 8])
def test_real_rtp_wire_packet_dispatch_preserves_full_precision(payload_type):
    pytest.importorskip("pyVoIP")
    import audioop

    sip._load_phone_class()
    from pyVoIP.RTP import PayloadType, RTPClient

    client = object.__new__(RTPClient)
    client.assoc = {payload_type: PayloadType(payload_type)}
    client.pmin = PcmuBuffer()
    codes = bytes(range(256))
    header = bytes((0x80, payload_type)) + b"\x00\x01" + (42).to_bytes(4, "big") + b"\x00\x00\x00\x01"
    client.parse_packet(header + codes)
    expected = codes if payload_type == 0 else audioop.lin2ulaw(audioop.alaw2lin(codes, 2), 2)
    assert client.read(256, blocking=False) == expected


def test_quiet_sine_does_not_suffer_eight_bit_quantization():
    pytest.importorskip("pyVoIP")
    import audioop
    import math
    import struct

    sip._load_phone_class()
    from pyVoIP.RTP import PayloadType, RTPClient

    client = object.__new__(RTPClient)
    client.preference = PayloadType.PCMU
    client.pmin = PcmuBuffer()
    linear = struct.pack("<800h", *(
        round(100 * math.sin(2 * math.pi * 440 * n / 8000)) for n in range(800)
    ))
    wire = audioop.lin2ulaw(linear, 2)
    client.parse_pcmu(SimpleNamespace(timestamp=42, payload=wire))
    actual = client.encode_packet(client.read(len(wire), blocking=False))
    assert actual == wire
    reference = audioop.ulaw2lin(wire, 2)
    old = audioop.ulaw2lin(audioop.lin2ulaw(audioop.ulaw2lin(wire, 1), 1), 2)
    old_error = audioop.add(reference, audioop.mul(old, 2, -1), 2)
    assert audioop.rms(old_error, 2) > audioop.rms(reference, 2)
