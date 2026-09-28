@echo off
setlocal
cd /d "%~dp0..\.."
if not exist "venv\Scripts\python.exe" (
    echo Die lokale Python-Umgebung fehlt. Siehe deploy/anna/README.md.
    pause
    exit /b 1
)
"venv\Scripts\python.exe" -m src.telephony.autostart --start
pause
