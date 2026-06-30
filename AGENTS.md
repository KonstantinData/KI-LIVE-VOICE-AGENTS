# AGENTS.md — KI-Mitarbeiter-Team

> **Diese Datei ist die zentrale Arbeitsanweisung für Codex.**
> Sie beschreibt den aktuellen Repository-Scope und die verbindlichen
> Arbeitsregeln für Backend, Widget, Dashboard, Agenten und Compliance.

---

## PROJEKTZIEL

Dieses Repository ist die Plattform für ein Team aus KI-Agenten,
die in Küchen- und Möbelgeschäften verschiedene Mitarbeiter-Rollen übernehmen.
Jeder Agent hat eine eigene Persönlichkeit, eigene Tools und eigenes Fachwissen,
aber alle teilen sich dieselbe Infrastruktur, Datenbank und Kommunikationsschicht.

### Agenten-Scope
| Agent | Rolle | Phasen |
|---|---|---|
| Lisa | Empfang & Lead-Management | Phase 1 (Erstkontakt), aktiv im MVP |
| Max | Beratung, Planung & Verkauf | Phase 2, 3, 4, später |
| Anna | Sachbearbeitung & Auftragsmanagement | Phase 5, 6, später |
| Tom | Logistik, Montage & Koordination | Phase 7, später |
| Sara | Qualität, Service & Kundenbindung | Phase 8, 9, später |

### Ziel-Websites für die Einbindung
Die Agenten werden als Chat-Widget (JavaScript) in Kunden-Websites
eingebettet. Erste Ziel-Website: **www.mein-kuechenexperte.de**

---

## AKTUELLER MVP-SCOPE

Dieses Repository enthält inzwischen mehr als die Grundstruktur:
- Datenbank-Schema mit Alembic-Migrationen für PostgreSQL + pgvector
- Shared Agent-Core (Basisklasse, LLM-Wrapper, Memory, Tools)
- Lisa als MVP-Agent für Erstkontakt, Lead-Erfassung und Terminwunsch
- FastAPI Backend mit tenant-gefilterten MVP-Routen
- WebSocket-Chat mit DSGVO-Consent-, Origin- und Größenprüfung
- React/Vite Dashboard mit echten API-Ansichten
- einbettbares Widget mit DSGVO-Consent-Gate und kleiner Preact-Runtime
- Governance-/Compliance-Agent für DSGVO, EU AI Act, Multi-Tenant und Security
- kontrollierte Feature Flags für E-Mail- und Google-Calendar-Integrationen

Max, Anna, Tom und Sara sind weiterhin nicht Teil des MVP und werden erst in
separaten Schritten ergänzt.

---

## TECH-STACK

| Komponente | Technologie | Begründung |
|---|---|---|
| **Agent-Logik + Backend** | Python 3.12+ | Bestes AI-Ökosystem (LangChain, etc.) |
| **API-Framework** | FastAPI | Async, schnell, WebSocket-Support, auto Docs |
| **ORM** | SQLAlchemy 2.0 + Alembic | Standard, async-fähig, Migrations |
| **Agent LLM** | Anthropic Codex API | Bestes Tool Use + Reasoning |
| **Embeddings** | OpenAI API (text-embedding-3-small) | Günstig, bewährt |
| **Datenbank** | PostgreSQL 16 + pgvector | Relational + Vektorsuche |
| **Task Queue** | Kein (vorerst) — in-process mit APScheduler | MVP-einfach |
| **Widget** | React-Komponenten + Preact Compat + Vite (IIFE) | Klein und einbettbar in jede Website |
| **Dashboard** | React + Vite + Tailwind | Admin-Oberfläche |
| **Hosting Backend** | Hetzner Cloud | EU, DSGVO, günstig |
| **CDN + DNS** | Cloudflare | SSL, CDN, DDoS-Schutz |
| **Reverse Proxy** | Caddy | Auto-HTTPS |
| **Python Env** | venv (Standard-Library) | Kein conda/poetry nötig |
| **Paketmanager Python** | pip + requirements.txt | Einfach, Standard |
| **Paketmanager JS** | pnpm | Für Widget + Dashboard |

---

## ORDNERSTRUKTUR

Erstelle exakt diese Struktur. Jede Datei wird weiter unten beschrieben.

```
KI-Mitarbeiter-Team-Kuechen-und-Moebelgeschaeft/
│
├── AGENTS.md                          # Diese Datei
├── README.md                          # Projekt-Dokumentation
├── .gitignore
├── .env.example                       # Alle Umgebungsvariablen (Template)
├── Makefile                           # Convenience-Befehle
├── setup.sh                           # Einmal-Setup-Script
│
│
│ #══════════════════════════════════════
│ # PYTHON BACKEND + AGENTEN
│ #══════════════════════════════════════
│
├── requirements.txt                   # Alle Python-Dependencies
├── requirements-dev.txt               # Dev-Dependencies (pytest, etc.)
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/                          # ══ SHARED AGENT CORE ══
│   │   ├── __init__.py
│   │   ├── base_agent.py              # Abstrakte Agent-Basisklasse
│   │   ├── llm.py                     # Codex API Wrapper
│   │   ├── embeddings.py              # OpenAI Embedding Wrapper
│   │   ├── memory.py                  # Kurzzeit + Langzeit-Gedächtnis
│   │   ├── knowledge.py               # Wissensbasis-Suche (pgvector)
│   │   ├── tool_runner.py             # Tool-Execution-Engine
│   │   ├── tool_registry.py           # Tool-Registrierung + Discovery
│   │   └── types.py                   # Agent-spezifische Pydantic Models
│   │
│   ├── agents/                        # ══ AGENTEN (aktuell leer) ══
│   │   ├── __init__.py
│   │   └── _template/                 # Vorlage für neue Agenten
│   │       ├── __init__.py
│   │       ├── agent.py               # Agent-Klasse (erbt von BaseAgent)
│   │       ├── system_prompt.py       # System-Prompt Builder
│   │       ├── tools/                 # Agent-spezifische Tools
│   │       │   ├── __init__.py
│   │       │   └── _example_tool.py   # Beispiel-Tool als Vorlage
│   │       └── prompts/               # Prompt-Bausteine
│   │           └── __init__.py
│   │
│   ├── api/                           # ══ FASTAPI BACKEND ══
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI App + Startup/Shutdown
│   │   ├── config.py                  # Pydantic Settings (Env-Variablen)
│   │   ├── deps.py                    # Dependency Injection (DB, Auth)
│   │   ├── websocket/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py            # WebSocket Connection Manager
│   │   │   └── chat_handler.py       # Chat WebSocket Endpoint
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py             # GET /health
│   │   │   ├── auth.py               # POST /auth/login, OAuth
│   │   │   ├── studios.py            # Studio CRUD
│   │   │   ├── leads.py              # Lead CRUD
│   │   │   ├── conversations.py      # Konversation CRUD
│   │   │   ├── appointments.py       # Termin CRUD
│   │   │   ├── followups.py          # Follow-up CRUD
│   │   │   ├── knowledge.py          # Wissensbasis CRUD
│   │   │   ├── feedback.py           # Feedback CRUD
│   │   │   ├── dashboard.py          # KPI-Stats
│   │   │   └── widget_config.py      # Widget-Branding
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # JWT Middleware
│   │   │   ├── tenant.py             # Multi-Tenant (studio_id)
│   │   │   └── rate_limit.py         # Rate Limiting
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── calendar_service.py   # Google Calendar API
│   │       ├── email_service.py      # Resend E-Mail
│   │       └── scheduler.py          # APScheduler Cron-Jobs
│   │
│   └── db/                            # ══ DATENBANK ══
│       ├── __init__.py
│       ├── database.py                # Async Engine + Session Factory
│       ├── models/                    # SQLAlchemy Models
│       │   ├── __init__.py
│       │   ├── base.py               # Declarative Base + Mixins
│       │   ├── studio.py             # Studio + Config
│       │   ├── berater.py            # Berater
│       │   ├── lead.py               # Lead + Score + Profil
│       │   ├── conversation.py       # Konversation
│       │   ├── message.py            # Einzelne Nachricht
│       │   ├── appointment.py        # Termin
│       │   ├── followup.py           # Follow-up
│       │   ├── knowledge_chunk.py    # Wissens-Eintrag + Vektor
│       │   ├── feedback.py           # Feedback
│       │   └── event.py              # Audit Trail
│       ├── seed.py                    # Seed-Daten (Pilotstudio)
│       └── alembic/                   # Migrations
│           ├── env.py
│           ├── versions/              # Migration-Files
│           └── script.py.mako
│
├── alembic.ini                        # Alembic Konfiguration
│
├── tests/                             # ══ TESTS ══
│   ├── __init__.py
│   ├── conftest.py                    # Pytest Fixtures (Test-DB, etc.)
│   ├── test_core/
│   │   ├── test_base_agent.py
│   │   ├── test_llm.py
│   │   └── test_memory.py
│   └── test_api/
│       ├── test_health.py
│       └── test_auth.py
│
│
│ #══════════════════════════════════════
│ # JAVASCRIPT FRONTENDS
│ #══════════════════════════════════════
│
├── frontends/
│   ├── widget/                        # Chat-Widget (einbettbar)
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts             # Baut als IIFE Bundle
│   │   └── src/
│   │       ├── main.tsx               # Entry: Mount in Shadow DOM
│   │       ├── Widget.tsx             # Button + Chat-Fenster
│   │       ├── ChatWindow.tsx         # Nachrichtenverlauf + Input
│   │       ├── MessageBubble.tsx      # Einzelne Nachricht
│   │       ├── TypingIndicator.tsx    # "Lisa tippt..."
│   │       ├── hooks/
│   │       │   └── useWebSocket.ts    # WS Connection + Reconnect
│   │       ├── styles/
│   │       │   └── widget.css         # Scoped CSS (KEIN Tailwind)
│   │       └── lib/
│   │           └── config.ts          # Widget Config aus data-Attributen
│   │
│   └── dashboard/                     # Admin-Dashboard
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── tailwind.config.ts
│       └── src/
│           ├── main.tsx
│           ├── App.tsx                # Router
│           ├── pages/
│           │   ├── Login.tsx
│           │   ├── Dashboard.tsx      # KPI Übersicht
│           │   ├── Leads.tsx
│           │   ├── LeadDetail.tsx
│           │   ├── Conversations.tsx
│           │   ├── Appointments.tsx
│           │   ├── FollowUps.tsx
│           │   ├── Knowledge.tsx
│           │   ├── Feedback.tsx
│           │   └── Settings.tsx
│           ├── components/
│           │   ├── Layout.tsx         # Sidebar + Header
│           │   ├── StatsCard.tsx
│           │   ├── LeadTable.tsx
│           │   ├── ChatViewer.tsx
│           │   └── ScoreBadge.tsx
│           └── lib/
│               ├── api.ts             # Fetch Wrapper
│               └── auth.ts            # JWT Management
│
│
│ #══════════════════════════════════════
│ # DEPLOYMENT
│ #══════════════════════════════════════
│
└── deploy/
    ├── ecosystem.config.cjs           # PM2 Config (für Node Frontends)
    ├── Caddyfile                      # Reverse Proxy
    ├── setup-server.sh                # Hetzner Server Bootstrap
    └── systemd/
        └── kitchenflow-api.service    # Systemd Unit für Python Backend
```

---

## SETUP-ANWEISUNGEN

### setup.sh — Erstelle dieses Script im Repo-Root

```bash
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
echo "--- Node.js Dependencies (Frontends) ---"
cd frontends/widget && pnpm install && cd ../..
cd frontends/dashboard && pnpm install && cd ../..
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
```

---

## PYTHON DEPENDENCIES

### requirements.txt
```
# API Framework
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-multipart>=0.0.12

# WebSocket
websockets>=13.0

# Datenbank
sqlalchemy[asyncio]>=2.0.35
asyncpg>=0.30.0
alembic>=1.14.0
pgvector>=0.3.6

# AI / LLM
anthropic>=0.42.0
openai>=1.58.0

# Validierung + Settings
pydantic>=2.10.0
pydantic-settings>=2.7.0

# Auth
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# E-Mail
resend>=2.0.0

# Kalender
google-auth>=2.36.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.155.0

# Scheduling
apscheduler>=3.10.4

# Utils
python-dotenv>=1.0.1
httpx>=0.28.0
structlog>=24.4.0
```

### requirements-dev.txt
```
# Testing
pytest>=8.3.0
pytest-asyncio>=0.24.0
pytest-cov>=6.0.0

# Linting + Formatting
ruff>=0.8.0

# Type Checking
mypy>=1.13.0
```

---

## .env.example

```env
# ═══════════════════════════════════════
# Server
# ═══════════════════════════════════════
APP_ENV=development
APP_PORT=8000
APP_HOST=0.0.0.0
LOG_LEVEL=DEBUG

# ═══════════════════════════════════════
# Datenbank
# ═══════════════════════════════════════
DATABASE_URL=postgresql+asyncpg://ki_team:PASSWORT@localhost:5432/ki_mitarbeiter

# ═══════════════════════════════════════
# Anthropic Codex (Agent-Gehirn)
# ═══════════════════════════════════════
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=Codex-sonnet-4-20250514
ANTHROPIC_MAX_TOKENS=1024

# ═══════════════════════════════════════
# OpenAI (Embeddings)
# ═══════════════════════════════════════
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# ═══════════════════════════════════════
# Resend (E-Mail)
# ═══════════════════════════════════════
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=lisa@mein-kuechenexperte.de
RESEND_FROM_NAME=Lisa | Mein Küchenexperte

# ═══════════════════════════════════════
# Google Calendar OAuth
# ═══════════════════════════════════════
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://api.mein-kuechenexperte.de/auth/google/callback

# ═══════════════════════════════════════
# Auth (Dashboard)
# ═══════════════════════════════════════
JWT_SECRET=HIER-MINDESTENS-32-ZEICHEN-ZUFAELLIGER-STRING
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080

# ═══════════════════════════════════════
# Encryption (Calendar Tokens etc.)
# ═══════════════════════════════════════
ENCRYPTION_KEY=HIER-64-ZEICHEN-HEX-STRING

# ═══════════════════════════════════════
# URLs
# ═══════════════════════════════════════
API_URL=https://api.mein-kuechenexperte.de
WS_URL=wss://api.mein-kuechenexperte.de
DASHBOARD_URL=https://app.mein-kuechenexperte.de
WIDGET_URL=https://widget.mein-kuechenexperte.de
WEBSITE_URL=https://www.mein-kuechenexperte.de

# ═══════════════════════════════════════
# CORS
# ═══════════════════════════════════════
CORS_ORIGINS=["https://www.mein-kuechenexperte.de","https://mein-kuechenexperte.de","https://app.mein-kuechenexperte.de"]
```

---

## .gitignore

```
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/

# Environment
.env
.env.local
.env.production

# Node
node_modules/
frontends/widget/dist/
frontends/dashboard/dist/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite3
```

---

## Makefile

```makefile
.PHONY: setup dev test lint migrate seed

# Komplettes Setup
setup:
	chmod +x setup.sh && ./setup.sh

# venv aktivieren (muss mit 'source' aufgerufen werden)
# Nutze: source venv/bin/activate

# Entwicklungsserver starten
dev:
	source venv/bin/activate && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Tests
test:
	source venv/bin/activate && pytest tests/ -v --cov=src

# Linting
lint:
	source venv/bin/activate && ruff check src/ tests/

# Format
format:
	source venv/bin/activate && ruff format src/ tests/

# Datenbank-Migration erstellen
migration:
	source venv/bin/activate && alembic revision --autogenerate -m "$(msg)"

# Migration ausführen
migrate:
	source venv/bin/activate && alembic upgrade head

# Seed-Daten laden
seed:
	source venv/bin/activate && python -m src.db.seed
```

---

## DATENBANK-SCHEMA

Erstelle SQLAlchemy Models in `src/db/models/`. Nutze das Async-Pattern
von SQLAlchemy 2.0. Jedes Model in eigener Datei.

### Base Model (src/db/models/base.py)

Alle Models erben von einer gemeinsamen Base-Klasse mit diesen Mixins:
- `id`: UUID, Primary Key, default uuid4
- `created_at`: DateTime mit Timezone, default utcnow
- `updated_at`: DateTime mit Timezone, default utcnow, onupdate utcnow

### Tabellen (identisch zur vorherigen Spezifikation)

**studios** — Ein Datensatz pro Küchenstudio
- id, name, slug (unique), config (JSON), api_key (unique), created_at, updated_at

**berater** — Berater eines Studios
- id, studio_id (FK), name, email, specialization, calendar_provider,
  calendar_tokens (JSON, verschlüsselt), working_hours (JSON),
  appointment_duration_minutes, is_active, created_at

**leads** — Erfasste Interessenten
- id, studio_id (FK), visitor_id, status, score, name, email, phone,
  profile (JSON), summary, source_channel, created_at, updated_at

**conversations** — Chat-Gespräche
- id, studio_id (FK), lead_id (FK, nullable), visitor_id, channel,
  status, summary, metadata (JSON), created_at, updated_at

**messages** — Einzelne Nachrichten
- id, conversation_id (FK), role, content, tool_calls (JSON),
  token_count, created_at

**appointments** — Beratungstermine
- id, studio_id (FK), lead_id (FK), berater_id (FK), datetime,
  duration_minutes, status, external_calendar_id, confirmation_sent,
  reminder_sent, notes, created_at

**followups** — Geplante Nachfass-Aktionen
- id, studio_id (FK), lead_id (FK), type, channel, scheduled_at,
  content, status, autonomy_level, sent_at, created_at

**knowledge_chunks** — Wissensbasis mit Vektoren
- id, studio_id (FK), category, title, content, embedding (vector 1536),
  metadata (JSON), created_at, updated_at

**feedback** — Bewertungen von Agent-Antworten
- id, studio_id (FK), message_id (FK), rating, correction, created_at

**events** — Audit Trail
- id, studio_id (FK), type, actor, payload (JSON), created_at

### Wichtige Constraints
- Alle Tabellen mit studio_id: Index auf studio_id für schnelle Filterung
- knowledge_chunks.embedding: HNSW Index für Vektorsuche
- leads: Composite Index auf (studio_id, status, score)
- messages: Index auf (conversation_id, created_at)

---

## AGENT CORE (src/core/)

### base_agent.py — Abstrakte Basisklasse

Jeder Agent (Lisa, Max, Anna, Tom, Sara) erbt von `BaseAgent`.
Die Basisklasse definiert den Agent-Loop:

```python
class BaseAgent(ABC):
    """
    Abstrakte Basisklasse für alle KI-Agenten.

    Jeder Agent durchläuft bei einer eingehenden Nachricht
    den gleichen 7-Schritte-Prozess:
    1. Kontext laden (Studio, Lead, History)
    2. Absicht erkennen
    3. Wissen abrufen (Wissensbasis durchsuchen)
    4. Tools bereitstellen
    5. LLM aufrufen (Codex mit System-Prompt + Tools)
    6. Tool-Calls ausführen (falls vorhanden)
    7. Ergebnis speichern + zurückgeben

    Subklassen implementieren:
    - get_system_prompt() -> str
    - get_tools() -> list[Tool]
    - get_knowledge_categories() -> list[str]
    """

    @abstractmethod
    def get_system_prompt(self, studio, knowledge, feedback) -> str:
        ...

    @abstractmethod
    def get_tools(self) -> list:
        ...

    @abstractmethod
    def get_knowledge_categories(self) -> list[str]:
        ...

    async def process_message(self, message, conversation, studio) -> str:
        """Der 7-Schritte-Loop. Wird NICHT überschrieben."""
        ...
```

### llm.py — Codex API Wrapper

```python
class LLMClient:
    """
    Wrapper um die Anthropic Codex API.

    - Unterstützt Tool Use (function calling)
    - Retry-Logic mit Exponential Backoff
    - Token-Counting für Kostentracking
    - Prompt Caching für System-Prompts
    """

    async def chat(self, system_prompt, messages, tools=None) -> LLMResponse:
        ...

    async def embed(self, text) -> list[float]:
        """Nutzt OpenAI text-embedding-3-small"""
        ...
```

### memory.py — Gedächtnis-Management

```python
class MemoryManager:
    """
    Verwaltet Kurzzeit- und Langzeitgedächtnis.

    Kurzzeit: Letzte N Nachrichten der aktuellen Konversation
    Langzeit: Zusammenfassungen + extrahierte Fakten pro Lead
    Studio: Aggregierte Learnings pro Studio
    """

    async def get_context(self, conversation_id, studio_id) -> AgentContext:
        ...

    async def store_summary(self, lead_id, summary) -> None:
        ...

    async def get_lead_history(self, lead_id) -> str:
        ...
```

### knowledge.py — Wissensbasis (pgvector)

```python
class KnowledgeBase:
    """
    Semantische Suche in der Wissensbasis eines Studios.

    Nutzt pgvector für Ähnlichkeitssuche:
    1. Nachricht wird embedded (OpenAI)
    2. Ähnlichste Chunks aus knowledge_chunks werden geladen
    3. Top-K Ergebnisse werden als Kontext zurückgegeben
    """

    async def search(self, query, studio_id, categories=None, limit=5) -> list:
        ...

    async def add_chunk(self, studio_id, category, title, content) -> None:
        ...
```

### tool_runner.py — Tool-Execution

```python
class ToolRunner:
    """
    Führt Tool-Calls von Codex aus.

    Codex gibt Tool-Calls zurück. Der ToolRunner:
    1. Validiert die Parameter (Pydantic)
    2. Führt die Tool-Funktion aus
    3. Gibt das Ergebnis an Codex zurück
    4. Loggt die Ausführung
    """

    def register(self, tool: BaseTool) -> None:
        ...

    async def execute(self, tool_name, parameters) -> ToolResult:
        ...

    def get_tool_definitions(self) -> list[dict]:
        """Gibt die Tool-Definitionen im Codex-Format zurück."""
        ...
```

### _template/ — Vorlage für neue Agenten

Die `_template/` Ordnerstruktur dient als Kopiervorlage.
Wenn ein neuer Agent (z.B. Lisa) erstellt wird:
1. `_template/` nach `lisa/` kopieren
2. Agent-Klasse implementieren
3. System-Prompt schreiben
4. Tools definieren

---

## FASTAPI BACKEND (src/api/)

### main.py — App-Setup

```python
# FastAPI App mit:
# - CORS Middleware (Origins aus .env)
# - Lifespan Handler (DB Connection, Scheduler starten)
# - Alle Router einbinden
# - WebSocket-Endpoint für Chat
# - Exception Handler (strukturierte Fehlerantworten)
```

### config.py — Pydantic Settings

```python
class Settings(BaseSettings):
    """
    Lädt alle Umgebungsvariablen aus .env mit Validierung.
    Wenn eine Pflicht-Variable fehlt, crasht die App sofort
    mit einer klaren Fehlermeldung.
    """
    model_config = SettingsConfigDict(env_file=".env")

    app_env: str = "development"
    app_port: int = 8000
    database_url: str
    anthropic_api_key: str
    openai_api_key: str
    jwt_secret: str
    # ... alle weiteren Variablen
```

### websocket/chat_handler.py — Chat-Endpoint

```python
# WebSocket Endpoint: /ws/chat?studio={slug}&visitor={visitor_id}
#
# 1. Studio anhand slug laden → 404 wenn nicht gefunden
# 2. Konversation finden oder erstellen (via visitor_id)
# 3. Richtigen Agent für das Studio laden (vorerst nur Lisa)
# 4. Bei jeder Nachricht: agent.process_message() aufrufen
# 5. Antwort über WebSocket zurücksenden
# 6. Bei Disconnect: Konversation als "closed" markieren (nach Timeout)
```

### routes/ — REST API

Alle Routes folgen dem gleichen Pattern:
- Pydantic Schema für Request/Response
- Dependency Injection für DB Session + Auth
- studio_id Filter bei JEDER Query (Multi-Tenant)
- Strukturierte Fehlerantworten

**Aktueller Stand:** Die produktionsrelevanten MVP-Routen sind implementiert
und müssen tenant-gefiltert bleiben. Neue Routen dürfen keine 501-Stubs als
produktiven Endzustand enthalten; nicht verfügbare Integrationen werden über
Feature Flags deaktiviert und klar dokumentiert.

---

## FRONTENDS (frontends/)

### Widget — Chat-Widget (frontends/widget/)

Vite Config: Baut als IIFE-Bundle (ein .js + ein .css File).
Output: `frontends/widget/dist/loader.js`

Einbindung auf Kunden-Website:
```html
<script
  src="https://widget.mein-kuechenexperte.de/v1/loader.js"
  data-studio="mein-kuechenexperte"
  data-api="wss://api.mein-kuechenexperte.de"
></script>
```

Das Widget zeigt einen Button, öffnet ein Chat-Fenster, erzwingt vor der
WebSocket-Verbindung die DSGVO-Einwilligung und spricht mit dem echten
Backend-Chat. Der Produktionsbuild nutzt Preact Compat als gebündelte Runtime.

### Dashboard — Admin-Dashboard (frontends/dashboard/)

React SPA mit React Router und Tailwind.
API Client spricht mit dem FastAPI Backend.

Das Dashboard enthält Login, Sidebar-Navigation und echte API-Ansichten für
KPI-Stats, Leads, Gespräche, Termine, Follow-ups, Wissensbasis, Feedback und
Studio-Einstellungen. Neue Platzhalterseiten sind nur zulässig, wenn sie nicht
im produktiven MVP verlinkt sind.

---

## PRODUCTION-READY MVP CHECKS

1. **Setup läuft:**
   - `./setup.sh` erstellt venv, installiert alle Dependencies
   - Keine Fehler bei pip install oder pnpm install

2. **Python Backend startet:**
   - `make dev` startet den FastAPI Server auf Port 8000
   - GET http://localhost:8000/health → 200 mit Status-Info
   - API Docs erreichbar: http://localhost:8000/docs (Swagger)

3. **Datenbank funktioniert:**
   - `make migrate` führt alle Migrations aus
   - Alle Tabellen existieren in PostgreSQL
   - pgvector Extension ist aktiv

4. **Agent-Core und Lisa sind testbar:**
   - `make test` läuft durch
   - BaseAgent kann instanziiert werden (mit Dummy-Subclass)
   - LLM Wrapper kann Claude aufrufen (mit API Key)
   - Embedding Wrapper kann Vektoren erzeugen

5. **WebSocket funktioniert:**
   - Verbindung zu ws://localhost:8000/ws/chat?studio=test&visitor=123&consent=1
   - Verbindung ohne Consent wird abgelehnt
   - Nachricht senden → Lisa verarbeitet und persistiert die Nachricht

6. **Widget baut:**
   - `pnpm --filter ki-team-widget build` erzeugt dist/loader.iife.js
   - Bundle ist < 100KB
   - Auf Test-HTML-Seite: Button erscheint, Chat-Fenster öffnet sich

7. **Dashboard baut:**
   - `pnpm --filter ki-team-dashboard build` erzeugt dist/
   - Login-Seite wird angezeigt
   - Nach Login: Dashboard zeigt echte tenant-gefilterte Daten

8. **agents/_template/ existiert:**
   - Vorlage ist vollständig und dokumentiert
   - Kann für Max, Anna, Tom oder Sara kopiert werden als Startpunkt

---

## CODE-REGELN

1. **Python 3.12+ Features nutzen** — Type Hints überall, match/case wo sinnvoll
2. **Pydantic v2 für alle Schemas** — Request, Response, Config
3. **Async/Await durchgehend** — FastAPI + SQLAlchemy Async + httpx
4. **Keine Datei über 250 Zeilen** — aufteilen
5. **Docstrings in jeder Klasse und öffentlichen Funktion** — auf Englisch (siehe Regel 4)
6. **Logging mit structlog** — JSON Format, jede wichtige Aktion loggen
7. **Umgebungsvariablen NIEMALS hardcoden** — alles über Settings
8. **Jede DB-Query filtert nach studio_id** — Multi-Tenant von Anfang an
9. **Keine Secrets in Git** — .env in .gitignore
10. **Type Safety** — mypy strict, ruff für Linting/Formatting

---

## DOKUMENTATIONS-REGELN

### Regel 1 — Zweisprachige READMEs

Jede `README.md` (Deutsch) hat eine `README.en.md` (Englisch).
Beide inhaltlich identisch. Oben in jeder Datei ein Sprachlink-Umschalter:

```md
🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md)
```

Gilt für jedes Verzeichnis im Repo das eine README enthält.

### Regel 2 — Script-Header (Datei-Docstring)

Jede Python-Datei beginnt mit einem englischen Modul-Docstring der beantwortet:

- **What** — Was ist diese Datei?
- **Does** — Was tut sie?
- **Why** — Warum existiert sie?
- **Who** — Wer nutzt sie (welche anderen Module/Klassen)?
- **Depends on** — Wovon hängt sie ab?

Beispiel:

```python
"""
Google Calendar Integration
============================
What:    Service layer for Google Calendar API access.
Does:    OAuth flow, token management, free-slot detection, event creation.
Why:     Decouples calendar logic from the booking tool; one place to swap providers.
Who:     BookAppointmentTool, google_calendar route.
Depends: google-auth, google-auth-oauthlib, google-api-python-client, src.api.config
"""
```

### Regel 3 — Inline-Dokumentation

Jede Funktion/Methode bekommt einen englischen Docstring mit:

- Kurzbeschreibung (1 Satz)
- `Args:` (falls Parameter vorhanden)
- `Returns:` (falls Rückgabewert)

Nicht-triviale Stellen bekommen `# NOTE:` Kommentare die **Business-Logik** erklären — nicht den Code paraphrasieren.

```python
# NOTE: wished_datetime is free text from the customer (e.g. "Wednesday 4pm").
# We map it to the next available business slot — exact parsing comes later.
```

### Regel 4 — Sprach-Matrix

| Bereich | Sprache | Begründung |
| --- | --- | --- |
| UI-Texte (Widget, Dashboard) | Deutsch | Kundenseitig |
| Chat-Antworten (Lisa, Max, …) | Deutsch | Kundenseitig |
| READMEs | Deutsch + Englisch | Beide Versionen |
| Code, Variablen, Funktionen | Englisch | Universell lesbar |
| Kommentare & Docstrings | Englisch | Universell lesbar |
| Commit Messages | Englisch | Conventional Commits |
| Log-Einträge | Englisch | Tool-kompatibel |
| Error Messages (API) | Englisch | Standard |
| `.env`-Keys | Englisch (SCREAMING_SNAKE_CASE) | Standard |

### Regel 5 — Commit Messages

Conventional Commits auf Englisch. Format: `type(scope): description`

| Typ | Wann |
| --- | --- |
| `feat:` | Neue Funktionalität |
| `fix:` | Bugfix |
| `docs:` | Nur Dokumentation |
| `refactor:` | Kein neues Feature, kein Fix |
| `test:` | Tests hinzugefügt/geändert |
| `chore:` | Build, Dependencies, Config |
| `style:` | Formatierung, kein Logik-Änderung |

Beispiele:

```text
feat(lisa): add extract_lead_data tool with incremental scoring
fix(calendar): refresh token before creating event
docs(readme): add bilingual setup instructions
```
