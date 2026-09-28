"""Local telephone worker with interactive or managed Windows credentials."""

from __future__ import annotations

import argparse
import asyncio
from getpass import getpass
import importlib.util
import ipaddress
import os
from pathlib import Path
import socket
import sys
import time
import uuid

from dotenv import load_dotenv

from .profiles import phone_session_config
from .credentials import CredentialStoreError, load_credentials
from .runtime_status import write_status

REPO_ROOT = Path(__file__).resolve().parents[2]


def local_addresses(server: str, local_ip: str | None = None) -> tuple[str, str]:
    """Resolve a private LAN registrar and select the local IPv4 route to it."""
    server_ip = socket.gethostbyname(server)
    address = ipaddress.IPv4Address(server_ip)
    if not address.is_private or address.is_loopback or address.is_unspecified:
        raise ValueError("Der SIP-Server muss die lokale FRITZ!Box sein.")
    if not local_ip:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect((server_ip, 5060))
            local_ip = probe.getsockname()[0]
    address = ipaddress.IPv4Address(local_ip)
    if not address.is_private or address.is_loopback or address.is_unspecified:
        raise ValueError("Eine lokale IPv4-Adresse dieses PCs ist erforderlich.")
    return server_ip, local_ip


def main(argv: list[str] | None = None) -> int:
    """Check locally or explicitly register the chosen tenant/agent pair."""
    parser = argparse.ArgumentParser(description="Anna: lokale FRITZ!Box-Telefonbrücke")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Prüfen, ohne Anrufe anzunehmen")
    mode.add_argument("--run", action="store_true", help="Telefon-Agent starten")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--server", default="fritz.box")
    parser.add_argument("--local-ip", default=None)
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--status-file", type=Path)
    parser.add_argument("--stop-file", type=Path)
    parser.add_argument("--parent-pid", type=int)
    args = parser.parse_args(argv)
    if args.parent_pid is not None:
        from .parent_watch import watch_parent

        watch_parent(args.parent_pid)

    def status(state: str) -> None:
        write_status(args.status_file, state)

    def stopping() -> bool:
        return args.stop_file is not None and args.stop_file.exists()

    load_dotenv(REPO_ROOT / ".env", override=False)
    try:
        phone_session_config(args.tenant, args.agent)
    except (ValueError, OSError):
        print("Telefonprofil nicht freigegeben oder ungültig.")
        status("configuration_error")
        return 3
    missing = [name for name in ("pyVoIP", "websockets")
               if importlib.util.find_spec(name) is None]
    if missing:
        print("Telefon-Abhängigkeiten fehlen. requirements-telephony.txt installieren.")
        status("configuration_error")
        return 3
    try:
        server, local_ip = local_addresses(args.server, args.local_ip)
    except (OSError, ValueError):
        print("FRITZ!Box nicht im lokalen Netz erreichbar. Netzwerk/Serveradresse prüfen.")
        status("network_unavailable")
        return 1
    print(f"Telefonprofil: {args.tenant} / {args.agent}")
    print(f"FRITZ!Box: {server}; lokale Telefonadresse: {local_ip}")
    try:
        saved = load_credentials(args.tenant, args.agent) if sys.platform == "win32" else None
    except CredentialStoreError:
        print("Gespeicherte Zugangsdaten nicht lesbar. Anna-Einrichten.cmd verwenden.")
        status("setup_required")
        return 2
    credentials = {
        name: (saved or {}).get(name) or os.getenv(variable) or ""
        for name, variable in (("username", "FRITZBOX_SIP_USERNAME"),
                               ("password", "FRITZBOX_SIP_PASSWORD"),
                               ("api_key", "OPENAI_API_KEY"),
                               ("crm_handoff_secret", "ANNA_VOICE_WEBHOOK_SECRET"))
    }
    if args.check:
        for label, name in (("SIP-Benutzername", "username"),
                            ("SIP-Passwort", "password"),
                            ("OpenAI-API-Schlüssel", "api_key"),
                            ("CRM-Handoff-Schlüssel", "crm_handoff_secret")):
            state = "vorhanden" if credentials[name] else "beim Start einzugeben"
            print(f"{label}: {state}")
        print("Lokale Prüfung bestanden. Keine SIP-Anmeldung und kein KI-Aufruf ausgeführt.")
        return 0
    if (args.non_interactive or not sys.stdin or not sys.stdin.isatty()) and not all(credentials.values()):
        print("Zugangsdaten fehlen. Bitte Anna-Einrichten.cmd einmalig ausführen.")
        status("setup_required")
        return 2
    print("MicroSIP für diesen Zugang jetzt schließen. Ende mit Strg+C.")
    username = credentials["username"] or input("SIP-Benutzername: ").strip()
    password = credentials["password"] or getpass("SIP-Passwort (unsichtbar): ")
    api_key = credentials["api_key"] or getpass("OpenAI-API-Schlüssel (unsichtbar): ")
    crm_handoff_secret = credentials["crm_handoff_secret"] or getpass(
        "CRM-Handoff-Schlüssel (unsichtbar): "
    )
    if not all((username, password, api_key, crm_handoff_secret)):
        print("Start abgebrochen: Zugangsdaten unvollständig.")
        status("setup_required")
        return 2

    from .realtime import PhoneBridgeError, run_phone_call
    from .sip import FritzBoxPhone, SipAdapterError

    def incoming(call):
        print("Eingehender Anruf: Sprachverbindung wird aufgebaut.", flush=True)
        # Recheck local registry authority for each call, not only at startup.
        from src.tenants.registry import get_tenant_profile

        get_tenant_profile.cache_clear()
        session_config, initial_greeting, limit = phone_session_config(args.tenant, args.agent)
        profile = get_tenant_profile(args.tenant).phone_agent(args.agent)
        from .contact_handoff import submit_phone_contact_handoff
        from .mail import SMTPDeliveryError
        phone_session_id = str(uuid.uuid4())
        from .calendar_tools import CALENDAR_ACTIONS, PhoneCalendarTools
        from .conversation_state import PhoneConversationState

        conversation_state = PhoneConversationState()
        calendar = PhoneCalendarTools(
            args.tenant, args.agent, phone_session_id, state=conversation_state,
        )
        delivery_result = None

        async def handle_tool(name, arguments, transcript):
            nonlocal delivery_result
            if name in CALENDAR_ACTIONS:
                return await calendar.execute(name, arguments, transcript)
            if name != "submit_phone_contact_handoff":
                raise ValueError("Unsupported telephone tool")
            arguments = conversation_state.enrich_handoff(arguments, transcript)
            if os.getenv("ANNA_DIRECT_SMTP") == "true" and delivery_result is not None:
                return delivery_result
            try:
                result = await submit_phone_contact_handoff(
                    tenant_id=args.tenant,
                    agent=profile,
                    arguments=arguments,
                    transcript=transcript,
                    contact_secret=crm_handoff_secret,
                    session_id=phone_session_id,
                )
            except SMTPDeliveryError:
                # SMTP acceptance can be uncertain after a network interruption.
                # Do not automatically retry and risk duplicate owner messages.
                if os.getenv("ANNA_DIRECT_SMTP") == "true":
                    delivery_result = {"success": False, "error": "delivery_not_confirmed"}
                    print("Interne E-Mail: Versand nicht bestätigt.", flush=True)
                raise
            if os.getenv("ANNA_DIRECT_SMTP") == "true":
                delivery_result = result
                for key, label in (("internal_email_sent", "Interne E-Mail"),
                                   ("customer_email_sent", "Kunden-E-Mail")):
                    if key == "customer_email_sent" and not result.get("customer_summary_requested"):
                        continue
                    state = "bestätigt" if result.get(key) else "nicht bestätigt"
                    print(f"{label}: SMTP-Annahme {state}.", flush=True)
            return result
        async def run_with_calendar():
            try:
                await run_phone_call(
                    call, api_key=api_key, session_config=session_config,
                    greeting=initial_greeting, max_call_seconds=limit,
                    tool_handler=handle_tool,
                )
            finally:
                await calendar.close()

        status("in_call")
        try:
            asyncio.run(run_with_calendar())
            print("Gespräch beendet.")
            status("registered")
        except PhoneBridgeError:
            print("Sprachverbindung beendet: KI-Verbindung oder Gesprächslimit prüfen.")
            status("voice_error")

    phone = None
    try:
        if stopping():
            status("stopped")
            return 0
        phone = FritzBoxPhone(server, username, password, local_ip, incoming)
        status("registering")
        phone.start()
        deadline = time.monotonic() + 30
        while phone.status not in {"REGISTERED", "FAILED"} and time.monotonic() < deadline:
            time.sleep(0.25)
        if phone.status != "REGISTERED":
            print("SIP-Anmeldung fehlgeschlagen. Anmeldedaten und lokale Firewall prüfen.")
            status("registration_error")
            return 1
        print("Anna ist an der FRITZ!Box angemeldet und wartet auf Testanrufe.")
        status("registered")
        while phone.status not in {"FAILED", "INACTIVE"}:
            if stopping():
                status("stopped")
                return 0
            time.sleep(0.5)
        print("SIP-Anmeldung unterbrochen. Telefonbrücke bitte erneut starten.")
        status("registration_error")
        return 1
    except KeyboardInterrupt:
        print("Anna wird abgemeldet.")
        status("stopped")
        return 0
    except SipAdapterError:
        print("Telefonverbindung fehlgeschlagen. Lokale Einrichtung prüfen.")
        status("registration_error")
        return 1
    finally:
        if phone is not None:
            try:
                phone.stop()
            except SipAdapterError:
                print("Telefonverbindung konnte nicht sauber abgemeldet werden.")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("Start abgebrochen.")
        raise SystemExit(1) from None
