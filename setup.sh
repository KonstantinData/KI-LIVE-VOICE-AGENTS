#!/bin/bash
set -e

echo "=== KI-Mitarbeiter-Team Setup ==="
echo ""

# Prüfe Python Version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED="3.12"
if [ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]; then
    echo "FEHLER: Python $REQUIRED+ benötigt. Installiert: $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION gefunden"

# Prüfe Node.js
if ! command -v node &> /dev/null; then
    echo "FEHLER: Node.js nicht gefunden. Installiere Node.js 20+"
    exit 1
fi
echo "✓ Node.js $(node --version) gefunden"

# Prüfe pnpm
if ! command -v pnpm &> /dev/null; then
    echo "pnpm nicht gefunden, installiere..."
    corepack enable
    corepack prepare pnpm@latest --activate
fi
echo "✓ pnpm gefunden"

# Python venv erstellen
echo ""
echo "--- Python Virtual Environment ---"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ venv erstellt"
else
    echo "✓ venv existiert bereits"
fi

# venv aktivieren
source venv/bin/activate
echo "✓ venv aktiviert"

# Python Dependencies installieren
echo ""
echo "--- Python Dependencies ---"
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
echo "✓ Python Dependencies installiert"

# Node.js Dependencies installieren
echo ""
echo "--- Node.js Dependencies (Widget) ---"
cd frontends/widget && pnpm install && cd ../..
echo "✓ Node.js Dependencies installiert"

# .env Datei
echo ""
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠ .env aus .env.example erstellt — BITTE AUSFÜLLEN!"
else
    echo "✓ .env existiert bereits"
fi

echo ""
echo "=== Setup abgeschlossen ==="
echo ""
echo "Nächste Schritte:"
echo "  1. .env Datei ausfüllen (API Keys etc.)"
echo "  2. PostgreSQL Datenbank anlegen"
echo "  3. source venv/bin/activate"
echo "  4. alembic upgrade head"
echo "  5. python -m src.api.main"
