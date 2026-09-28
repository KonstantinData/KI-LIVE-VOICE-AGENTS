"""Absolute Windows logon entry point, independent of the startup directory."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.telephony.autostart import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
