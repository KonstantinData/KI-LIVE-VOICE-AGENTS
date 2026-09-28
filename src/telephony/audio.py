"""Bounded G.711 buffers without an intermediate eight-bit linear conversion."""

from threading import Lock

PCMU_SILENCE = b"\xff"


class PcmuBuffer:
    """Keep only unread audio and preserve bounded RTP timestamp gaps as silence."""

    def __init__(self, max_bytes: int = 8000 * 30) -> None:
        self._lock = Lock()
        self._data = bytearray()
        self._position: int | None = None
        self._max_bytes = max_bytes

    def read(self, length: int = 160) -> bytes:
        with self._lock:
            size = min(length, len(self._data))
            result = bytes(self._data[:size])
            del self._data[:size]
            if self._position is not None:
                self._position += size
            return result.ljust(length, PCMU_SILENCE)

    def write(self, offset: int, data: bytes) -> None:
        with self._lock:
            if self._position is None:
                self._position = offset
            # Resolve 32-bit RTP timestamp rollover around the read position.
            relative = (offset - self._position + 2**31) % 2**32 - 2**31
            if relative < 0:
                data = data[-relative:]
                relative = 0
            if not data:
                return
            # A discontinuity must not allocate an arbitrary sparse buffer.
            if relative + len(data) > self._max_bytes:
                self._data.clear()
                self._position = offset
                relative = 0
                data = data[:self._max_bytes]
            end = relative + len(data)
            if end > len(self._data):
                self._data.extend(PCMU_SILENCE * (end - len(self._data)))
            self._data[relative:end] = data


def pcmu_to_pcma(data: bytes) -> bytes:
    import audioop

    return audioop.lin2alaw(audioop.ulaw2lin(data, 2), 2)


def pcma_to_pcmu(data: bytes) -> bytes:
    import audioop

    return audioop.lin2ulaw(audioop.alaw2lin(data, 2), 2)
