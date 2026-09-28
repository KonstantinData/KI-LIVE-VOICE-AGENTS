"""Current-user Windows logon start and bounded supervision for Anna only."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from getpass import getpass
import os
from pathlib import Path
import subprocess
import sys
import time

from .credentials import CredentialStoreError, load_credentials, save_credentials
from .runtime_status import read_status, write_status

REPO_ROOT = Path(__file__).resolve().parents[2]
TENANT = "mein-kuechenexperte"
AGENT = "anna-phone-assistant"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "KI-LIVE-VOICE-AGENTS-Anna"
LABELS = {
    "unknown": "Noch kein Status vorhanden",
    "starting": "Startet",
    "setup_required": "Einmalige Zugangsdaten-Einrichtung erforderlich",
    "configuration_error": "Telefonprofil oder Abhängigkeiten prüfen",
    "network_unavailable": "FRITZ!Box im lokalen Netz noch nicht erreichbar",
    "registering": "Meldet sich an der FRITZ!Box an",
    "registered": "An der FRITZ!Box angemeldet; wartet auf Anrufe",
    "in_call": "Gespräch läuft",
    "voice_error": "KI-Verbindung fehlgeschlagen oder Gesprächslimit erreicht",
    "registration_error": "SIP-Anmeldung fehlgeschlagen",
    "retrying": "Verbindungsaufbau wird erneut versucht",
    "microsip_running": "MicroSIP schließen; Anna wartet auf den freien Telefonzugang",
    "stopped": "Gestoppt",
}


def state_directory() -> Path:
    """Keep process status outside the repository, scoped to the current user."""
    return Path(os.environ["LOCALAPPDATA"]) / "KI-LIVE-VOICE-AGENTS" / "anna"


@contextmanager
def instance_lock():
    """A Windows file lock is automatically released if the supervisor exits."""
    import msvcrt

    directory = state_directory()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "worker.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            yield False
        else:
            try:
                yield True
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def startup_command() -> list[str]:
    """No secrets, shell interpolation or working-directory assumptions."""
    pythonw = REPO_ROOT / "venv" / "Scripts" / "pythonw.exe"
    entry = REPO_ROOT / "deploy" / "anna" / "background.py"
    if not pythonw.is_file() or not entry.is_file():
        raise RuntimeError("Lokale Python-Umgebung oder Startdatei fehlt.")
    return [str(pythonw), str(entry), "--logon"]


def install_autostart() -> None:
    """Install only Anna's current-user logon entry; no admin or service changes."""
    import winreg

    command = subprocess.list2cmdline(startup_command())
    if len(command) > 260:
        raise RuntimeError("Der Repository-Pfad ist für den Windows-Autostart zu lang.")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, command)


def autostart_installed() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, RUN_NAME)
        return value == subprocess.list2cmdline(startup_command())
    except FileNotFoundError:
        return False


def remove_autostart() -> None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_NAME)
    except FileNotFoundError:
        pass


def start_background() -> None:
    with instance_lock() as acquired:
        if not acquired:
            return
        (state_directory() / "stop").unlink(missing_ok=True)
    command = startup_command()[:-1] + ["--worker"]
    subprocess.Popen(command, cwd=REPO_ROOT,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)


def request_stop() -> None:
    directory = state_directory()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "stop").touch()


def microsip_running() -> bool:
    """Avoid replacing a human's active SIP registration; never kill MicroSIP."""
    result = subprocess.run(
        ["tasklist.exe", "/FI", "IMAGENAME eq MicroSIP.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=10, check=True,
    )
    return '"microsip.exe"' in result.stdout.lower()


def supervise() -> int:
    """Run at most one child, retry transient failures, and honor local stop."""
    with instance_lock() as acquired:
        if not acquired:
            return 0
        directory = state_directory()
        stop = directory / "stop"
        status = directory / "status.json"
        child = None
        try:
            while not stop.exists():
                if not load_credentials(TENANT, AGENT):
                    write_status(status, "setup_required")
                    return 2
                if microsip_running():
                    write_status(status, "microsip_running")
                    for _ in range(30):
                        if stop.exists():
                            break
                        time.sleep(1)
                    continue
                write_status(status, "starting")
                child = subprocess.Popen([
                    str(REPO_ROOT / "venv" / "Scripts" / "python.exe"),
                    "-m", "src.telephony", "--run", "--non-interactive",
                    "--tenant", TENANT, "--agent", AGENT,
                    "--stop-file", str(stop), "--status-file", str(status),
                    "--parent-pid", str(os.getpid()),
                ], cwd=REPO_ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                while child.poll() is None and not stop.exists():
                    time.sleep(1)
                if stop.exists():
                    break
                # Permanent configuration/credential failures need user action.
                if child.returncode in {2, 3}:
                    return child.returncode
                write_status(status, "retrying")
                for _ in range(30):
                    if stop.exists():
                        break
                    time.sleep(1)
        except (CredentialStoreError, OSError, subprocess.SubprocessError):
            write_status(status, "configuration_error")
            return 1
        finally:
            if child is not None and child.poll() is None:
                stop.touch()
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    child.wait(timeout=5)
            if stop.exists():
                write_status(status, "stopped")
        return 0


def configure() -> int:
    """User-confirmed local storage; never collect secrets in chat or files."""
    print("Einmalige Einrichtung für Annas automatischen Start.")
    print("Die Zugangsdaten werden im Windows-Anmeldeinformationsmanager dieses Benutzers gespeichert.")
    print("Sie werden nicht in Projektdateien geschrieben oder im Chat angezeigt.")
    if input("Geschützt speichern und Windows-Autostart aktivieren? [ja/nein]: ").strip().lower() != "ja":
        print("Einrichtung abgebrochen.")
        return 1
    credentials = {
        "username": input("SIP-Benutzername aus der FRITZ!Box: ").strip(),
        "password": getpass("SIP-Passwort (unsichtbar): "),
        "api_key": getpass("OpenAI-API-Schlüssel (unsichtbar): "),
        "crm_handoff_secret": getpass("CRM-Handoff-Schlüssel (unsichtbar): "),
    }
    if not all(credentials.values()):
        print("Nichts gespeichert: Zugangsdaten unvollständig.")
        return 1
    save_credentials(TENANT, AGENT, credentials)
    install_autostart()
    start_background()
    print("Einrichtung abgeschlossen. Anna startet nach dem Schließen von MicroSIP im Hintergrund.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Anna: Windows-Autostart verwalten")
    modes = parser.add_mutually_exclusive_group(required=True)
    for action in ("install", "setup", "start", "logon", "worker", "stop", "status", "remove"):
        modes.add_argument(f"--{action}", action="store_true")
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        print("Diese Einrichtung ist nur für Windows verfügbar.")
        return 1
    try:
        if args.worker:
            return supervise()
        if args.logon:
            if autostart_installed():
                start_background()
            return 0
        if args.setup:
            return configure()
        if args.install:
            install_autostart()
            print("Autostart bei Windows-Anmeldung eingerichtet.")
        elif args.start:
            start_background()
            print("Anna wird im Hintergrund gestartet.")
        elif args.stop:
            request_stop()
            print("Anna wird gestoppt. Der Windows-Autostart bleibt eingerichtet.")
        elif args.remove:
            request_stop()
            remove_autostart()
            print("Autostart entfernt. Gespeicherte Zugangsdaten bleiben im Windows-Tresor.")
        elif args.status:
            print("Windows-Autostart: " + ("aktiv" if autostart_installed() else "nicht eingerichtet"))
            print("Zugangsdaten: " + ("gespeichert" if load_credentials(TENANT, AGENT) else "noch einzurichten"))
            with instance_lock() as acquired:
                print("Hintergrundprozess: " + ("läuft nicht" if acquired else "läuft"))
            value = read_status(state_directory() / "status.json")
            print("Letzter Status: " + LABELS.get(value["state"], "Unbekannt"))
            if "updated_at" in value:
                print("Stand: " + value["updated_at"])
        return 0
    except (CredentialStoreError, OSError, RuntimeError, subprocess.SubprocessError):
        print("Einrichtung oder Zugriff fehlgeschlagen. Windows-Benutzer und Projektpfad prüfen.")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("Einrichtung abgebrochen.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
