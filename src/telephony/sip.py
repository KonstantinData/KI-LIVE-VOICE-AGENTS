"""Optional FRITZ!Box SIP adapter; audio is G.711 PCMU at 8 kHz.

The callback owns a call until it returns. It must block for the entire bridge
session: pyVoIP uses the callback thread lifetime to clean up calls.
"""

from __future__ import annotations

import importlib
from copy import copy
import socket
import time
from threading import Lock
from typing import Any, Callable, Protocol

from .audio import PcmuBuffer, pcma_to_pcmu, pcmu_to_pcma


class SipCall(Protocol):
    """Audio and lifecycle interface consumed by the realtime bridge."""

    @property
    def is_active(self) -> bool: ...

    def answer(self) -> None: ...

    def hangup(self) -> None: ...

    def read_audio(self) -> bytes: ...

    def write_audio(self, data: bytes) -> None: ...


class SipAdapterError(RuntimeError):
    """Sanitized failure safe to present without SIP packets or credentials."""


def _discard_debug(*args: Any, **kwargs: Any) -> None:
    """Never print SIP packets, authorization headers, or caller identifiers."""


def _encode_rtp_packet(client: Any, payload: bytes) -> bytes:
    """Preserve PCMU, converting other G.711 audio at full linear precision."""
    from pyVoIP.RTP import PayloadType, RTPParseError

    if client.preference == PayloadType.PCMU:
        return payload
    if client.preference == PayloadType.PCMA:
        return pcmu_to_pcma(payload)
    raise RTPParseError("Unsupported telephone audio codec")


def _transmit_rtp(client: Any) -> None:
    """Pace 8 kHz RTP with QPC deadlines, including correct counter rollover."""
    deadline = time.perf_counter()
    while client.NSD:
        payload = client.encode_packet(client.pmout.read())
        packet = (
            bytes((0x80, int(client.preference)))
            + (client.outSequence % 65536).to_bytes(2, "big")
            + (client.outTimestamp % 4294967296).to_bytes(4, "big")
            + client.outSSRC.to_bytes(4, "big")
            + payload
        )
        try:
            client.sout.sendto(packet, (client.outIP, client.outPort))
        except OSError:
            # Socket closure races with normal call shutdown.
            if not client.NSD:
                return
        client.outSequence = (client.outSequence + 1) % 65536
        client.outTimestamp = (client.outTimestamp + len(payload)) % 4294967296
        deadline += 0.02
        now = time.perf_counter()
        if now > deadline + 0.02:
            deadline = now
        if deadline > now:
            time.sleep(deadline - now)


def _deny_ringing(call: Any) -> None:
    """Reject calls, including upstream's stop-before-RTP-start defect."""
    try:
        call.deny()
    except AttributeError:
        # pyVoIP 1.6.8 sends busy, then stops RTP clients whose socket is only
        # created by answer(). Complete bookkeeping only for this exact case.
        clients = getattr(call, "RTPClients", ())
        if not clients or any(hasattr(client, "sin") for client in clients):
            raise
        call.state = type(call.state).ENDED
        call.phone.calls.pop(call.call_id, None)


def _media_offer_rejection(request: Any, router_ip: str) -> str | None:
    """Return a caller-safe reason when an SDP offer is outside our boundary."""
    try:
        connections = request.body["c"]
        media = request.body["m"]
    except (AttributeError, KeyError, TypeError, IndexError):
        return "malformed"
    if not connections:
        return "missing_connection"
    if any(
        connection["address"] != router_ip
        or connection.get("address_count", 1) != 1
        for connection in connections
    ):
        return "foreign_or_multicast_connection"
    if len(media) != 1 or media[0]["type"] != "audio":
        return "unsupported_media"
    if media[0].get("port_count", 1) != 1:
        return "multiple_media_ports"
    return None


def _router_media_only(request: Any, router_ip: str) -> bool:
    """Accept one audio stream addressed only to the configured router."""
    return _media_offer_rejection(request, router_ip) is None


def _load_phone_class() -> Any:
    """Load optional dependency only when a phone is constructed."""
    try:
        library = importlib.import_module("pyVoIP")
        if library.__version__ != "1.6.8":
            raise SipAdapterError("The phone adapter requires pyVoIP 1.6.8.")
        library.DEBUG = False
        library.debug = _discard_debug
        # Import the public entry point first; SIP-first imports are circular.
        base_phone = importlib.import_module("pyVoIP.VoIP").VoIPPhone
        rtp = importlib.import_module("pyVoIP.RTP")
        if not getattr(rtp.RTPClient, "_anna_pcmu", False):
            class PcmuRtpClient(rtp.RTPClient):
                _anna_pcmu = True
                encode_packet = _encode_rtp_packet
                trans = _transmit_rtp

                def __init__(self, *args: Any, **kwargs: Any) -> None:
                    super().__init__(*args, **kwargs)
                    self.pmin = PcmuBuffer()
                    self.pmout = PcmuBuffer()

                def parse_pcmu(self, packet: Any) -> None:
                    self.pmin.write(packet.timestamp, packet.payload)

                def parse_pcma(self, packet: Any) -> None:
                    self.pmin.write(packet.timestamp, pcma_to_pcmu(packet.payload))

            rtp.RTPClient = PcmuRtpClient
        # Modules retain aliases to debug, including its unconditional error path.
        for name in ("pyVoIP.RTP", "pyVoIP.SIP", "pyVoIP.VoIP.VoIP"):
            importlib.import_module(name).debug = _discard_debug
        class CancelAwarePhone(base_phone):
            def callback(self, request: Any) -> None:
                if getattr(request, "method", None) == "INVITE":
                    rejection = _media_offer_rejection(request, self.server)
                    if rejection is not None:
                        print(f"SIP offer rejected: {rejection}", flush=True)
                        response = self.sip.gen_busy(request)
                        self.sip.out.sendto(
                            response.encode("utf8"), (self.server, self.port)
                        )
                        return
                    # SDP may repeat the same trusted connection at session and
                    # media scope. Upstream otherwise creates two RTP streams.
                    request = copy(request)
                    request.body = dict(request.body)
                    request.body["c"] = [request.body["c"][0]]
                # 1.6.8 forwards CANCEL but its phone callback ignores it.
                # Close ringing calls before the delayed application callback.
                if getattr(request, "method", None) == "CANCEL":
                    call = self.calls.get(request.headers.get("Call-ID"))
                    if call is not None and call.state.name == "RINGING":
                        try:
                            _deny_ringing(call)
                        except Exception:
                            pass
                    return
                super().callback(request)

        return CancelAwarePhone
    except ImportError:
        raise SipAdapterError("Install the optional telephone dependencies first.") from None


class _PyVoipCall:
    def __init__(self, call: Any) -> None:
        self._call = call

    @property
    def is_active(self) -> bool:
        return self._call.state.name == "ANSWERED"

    def answer(self) -> None:
        try:
            clients = self._call.RTPClients
            if len(clients) != 1:
                raise SipAdapterError("Telephone calls require one audio stream.")
            self._call.answer()
            print(f"Telephone audio codec: {clients[0].preference.name}", flush=True)
        except Exception:
            raise SipAdapterError("The incoming call could not be answered.") from None

    def hangup(self) -> None:
        try:
            if self._call.state.name == "RINGING":
                _deny_ringing(self._call)
            elif self.is_active:
                self._call.hangup()
        except Exception:
            # A remote hangup may race with local cleanup.
            if self._call.state.name != "ENDED":
                raise SipAdapterError("The call could not be closed.") from None

    def read_audio(self) -> bytes:
        if not self.is_active:
            return b""
        try:
            clients = self._call.RTPClients
            if len(clients) != 1:
                raise SipAdapterError("Telephone calls require one audio stream.")
            return clients[0].read(length=160, blocking=False)
        except Exception:
            raise SipAdapterError("Telephone audio could not be read.") from None

    def write_audio(self, data: bytes) -> None:
        if len(data) != 160:
            raise ValueError("Telephone output must contain one 160-byte PCMU frame.")
        if not self.is_active:
            return
        try:
            self._call.write_audio(data)
        except Exception:
            raise SipAdapterError("Telephone audio could not be written.") from None


class FritzBoxPhone:
    """Receive at most one call; never expose an outbound dialing interface.

    ``on_call`` runs on the library callback thread and must not return while
    the bridge still owns the call. The caller paces audio in 20 ms frames.
    """

    def __init__(
        self,
        server: str,
        username: str,
        password: str,
        local_ip: str,
        on_call: Callable[[SipCall], None],
        sip_port: int = 5062,
        rtp_port_low: int = 10000,
        rtp_port_high: int = 10020,
    ) -> None:
        self._call_lock = Lock()
        self._on_call = on_call
        self._stopping = False
        self._active_call: _PyVoipCall | None = None
        self.last_call_failed = False
        factory = _load_phone_class()
        try:
            router_ip = socket.gethostbyname(server)
            self._phone = factory(
                router_ip, 5060, username, password, myIP=local_ip,
                callCallback=self._incoming, sipPort=sip_port,
                rtpPortLow=rtp_port_low, rtpPortHigh=rtp_port_high,
            )
        except Exception:
            raise SipAdapterError("The telephone adapter could not be initialized.") from None

    @property
    def status(self) -> str:
        """Return a registration state without any account or caller data."""
        return self._phone.get_status().name

    def start(self) -> None:
        self._stopping = False
        try:
            self._phone.start()
        except Exception:
            raise SipAdapterError("SIP registration could not be started.") from None

    def stop(self) -> None:
        self._stopping = True
        try:
            if self._active_call is not None:
                self._active_call.hangup()
        finally:
            try:
                self._phone.stop()
            except Exception:
                raise SipAdapterError("The telephone adapter could not be stopped.") from None

    def _incoming(self, raw_call: Any) -> None:
        call = _PyVoipCall(raw_call)
        if not self._call_lock.acquire(blocking=False):
            self._close(call)
            return
        try:
            if self._stopping or raw_call.state.name != "RINGING":
                return
            self._active_call = call
            self.last_call_failed = False
            self._on_call(call)
        except Exception as error:
            # Callback exceptions must never escape with caller/account context.
            print(
                f"SIP call handler failed: {type(error).__name__}",
                flush=True,
            )
            self.last_call_failed = True
        finally:
            self._close(call)
            self._active_call = None
            self._call_lock.release()

    def _close(self, call: _PyVoipCall) -> None:
        try:
            call.hangup()
        except SipAdapterError:
            self.last_call_failed = True
