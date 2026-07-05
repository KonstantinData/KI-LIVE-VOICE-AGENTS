# KI-LIVE-VOICE-AGENTS

🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md)

---

A multi-tenant system for AI-powered live voice and chat agents that helps kitchen and furniture stores handle customer inquiries from first contact to secure staff handoff.

---

## What is this?

This project is the technical foundation for tenant-specific Live Voice Agents. The runtime agent is generic; name, prompt profile, tools, policies, knowledge, upload rules, and widget copy are composed from the tenant registry.

The system is designed as a **ready-to-use platform**: A kitchen studio receives a tenant, configures its profile, and the selected Live Voice Agent starts working. Multiple tenants can use the system simultaneously without affecting each other.

---

## How does the integration work?

The system is **not a replacement** for the existing website — it integrates invisibly:

```html
<!-- A single line in the existing website -->
<script
  src="https://widget.mein-kuechenexperte.de/loader.iife.js"
  data-studio="mein-kuechenexperte"
  data-voice="true"
></script>
```

That's it. The chat button appears, and the tenant-configured agent is ready. For `mein-kuechenexperte`, the public widget agent is called **KEA**.

---

## Tenant Runtime Model

A single chat window for the visitor — in the background, a tenant-specific runtime profile is loaded.

| Layer | Purpose |
| ---- | ------- |
| **Tenant profile** | Widget name, hostnames, locale, privacy, upload and voice flags |
| **Live Voice Agent profile** | Prompt profile, model, voice, skills, tools, scopes, policies, validators |
| **Skill pack** | Tenant-specific capabilities and audit requirements |
| **Runtime** | Uses only modules and data allowed by the selected profile |

> **Current status:** `mein-kuechenexperte` is registered as the first tenant. `KEA` is its public widget name, technically represented as a tenant profile for the generic Live Voice Agent.

---

## What does it look like for the end customer?

A visitor to `www.mein-kuechenexperte.de` sees a chat button in the corner. They click, write or speak their question, and **KEA** responds immediately. The conversation feels natural. In the background, the system captures relevant project data, evaluates the prospect, and prepares the next step.

The kitchen studio sees everything in an admin dashboard at `app.mein-kuechenexperte.de`: which leads have come in, what was discussed, which appointments are upcoming.

---

## Where does what run?

| Component | URL | Platform |
| --------- | --- | -------- |
| **Chat Widget** (for website visitors) | `widget.mein-kuechenexperte.de` | Cloudflare Pages |
| **Admin Dashboard** (for studio operators) | `app.mein-kuechenexperte.de` | Cloudflare Pages |
| **Backend / AI** (invisible in background) | `api.mein-kuechenexperte.de` | Hetzner Cloud (EU) |
| **Main website** (unchanged) | `www.mein-kuechenexperte.de` | existing |

---

## What is currently complete?

### Infrastructure & Backend

- Complete **database schema** (prospects, conversations, appointments, knowledge base, audit trail)
- **API server** with all necessary endpoints (authentication, chat, studios, leads, appointments, etc.)
- **Real-time chat** via WebSocket — messages are transmitted in milliseconds
- **Live Voice Agents** via browser WebRTC — voice runs through a server-side OpenAI Realtime broker without browser API keys
- **Knowledge search**: The system can semantically search a studio's product database and pass relevant information to the AI
- **Memory system**: Each agent remembers what was discussed in previous conversations with a customer
- **Multi-studio operation**: Any number of studios can use the system in parallel — completely separated from each other

### AI Core

- Pre-built **agent structure**: Each new agent follows the same 7-step process (load context → understand request → retrieve knowledge → use tools → respond → save)
- Connection to **OpenAI** for natural conversations, live voice, and complex reasoning
- **Tool system**: Agents can independently perform actions (check appointments, send emails, save data)
- **Tenant registry**: New tenants receive their own profiles, skill packs, policies, and widget identity without a new hard-coded agent

### Frontend

- **Chat widget**: A `<script>` tag is enough to integrate into any existing website; text chat remains the fallback for voice mode
- **Admin dashboard**: Web interface for the kitchen studio with login, overviews, and navigation
- Both frontends **live on Cloudflare Pages** with automatic SSL and custom domains

### Deployment & Operations

- **Backend** runs on a European server (Hetzner, GDPR-compliant)
- **Frontends** via Cloudflare Pages — fast, worldwide, fail-safe
- Automatic deployments: Every code push triggers a new build
- Configuration and deployment scripts for quick setup

---

## Project Structure (simplified)

```text
KI-LIVE-VOICE-AGENTS/
│
├── src/
│   ├── core/          # Shared core of all agents (LLM, memory, knowledge, tools)
│   ├── agents/        # Runtime agent implementation and legacy agent modules
│   ├── api/           # API server (endpoints, WebSocket, authentication)
│   └── db/            # Database models and migrations
├── registry/          # Tenant profiles and tenant-specific skill packs
├── schemas/           # Machine-readable tenant/runtime contracts
│
├── frontends/
│   ├── widget/        # Chat widget → widget.mein-kuechenexperte.de
│   └── dashboard/     # Admin dashboard → app.mein-kuechenexperte.de
│
├── tests/             # Automated tests
└── deploy/            # Server configuration and deployment scripts
```

---

## Technology (for interested parties)

| Area | Technology | Why |
| ---- | ---------- | --- |
| Backend | Python + FastAPI | Fast, asynchronous, ideal for AI applications |
| Database | PostgreSQL + pgvector | Relational data + AI search in one system |
| AI Model | OpenAI | Conversations, tool use, and live voice through one provider |
| Embeddings | OpenAI | Cheap, proven vectorization for knowledge search |
| Chat | WebSocket | Real-time communication without page reload |
| Live Voice | OpenAI Realtime + WebRTC | Low latency, VAD, and interruptions in the browser |
| Widget | React + Vite | Small bundle, runs isolated on any website |
| Dashboard | React + Tailwind | Modern, maintainable admin interface |
| Hosting Backend | Hetzner (EU) | GDPR-compliant, reliable, cost-effective |
| Hosting Frontend | Cloudflare Pages | Global CDN, automatic SSL certificates, free |

---

## Local Setup (for developers)

```bash
# 1. Clone repository
git clone https://github.com/KonstantinData/KI-LIVE-VOICE-AGENTS.git
cd KI-LIVE-VOICE-AGENTS

# 2. One-time setup (Python venv + all dependencies)
./setup.sh

# 3. Configure environment variables
cp .env.example .env
# Open .env and enter API keys

# 4. Set up database
source venv/bin/activate
make migrate

# 5. Start backend
make dev
# → http://localhost:8000/health
# → http://localhost:8000/docs (API documentation)

# 6. Build widget (optional)
cd frontends/widget && pnpm install && pnpm build

# 7. Build dashboard (optional)
cd frontends/dashboard && pnpm install && pnpm build
```

**Required:** Python 3.12+, Node.js 20+, pnpm, PostgreSQL 16 with pgvector

### Production-Relevant Configuration

- `ADMIN_PASSWORD_HASH` must be set in production. The test login `admin / secret` only works when `ALLOW_DEMO_LOGIN=true` and `APP_ENV` is not `production`.
- `JWT_SECRET` must be a long random value and must never be committed.
- `ENABLE_EMAIL_SENDING` and `ENABLE_CALENDAR_SYNC` default to `false`. External actions only run when the matching API/OAuth credentials are configured and the feature flags are deliberately enabled.
- `ENABLE_VOICE_SESSIONS` is the global kill switch for Live Voice Agents. The tenant profile must also enable voice; the widget can show the tab with `data-voice="true"`.
- Live Voice Agents use `/voice/sessions/webrtc` and `/voice/session` as server-side OpenAI Realtime brokers. Standard API keys stay in the backend; the browser receives only short-lived client secrets or SDP answers and safe session metadata.
- In voice mode, microphone access is requested only after consent and an additional click. Raw audio is not stored by default; final transcripts, tool audits, and summaries are stored tenant-safely.
- `CORS_ORIGINS` must include the public website and dashboard. WebSocket connections are checked server-side against these origins.
- The widget connects only after GDPR consent and sends `consent=1` to `/ws/chat`.

### Verification

```bash
# Backend
python -m pytest -q
python -m ruff check src tests
python -m mypy src

# Check migrations against a temporary SQLite database
DATABASE_URL=sqlite+aiosqlite:///./tmp_migration_check.sqlite3 alembic upgrade head

# Run frontends through the workspace so pnpm allowBuilds applies
pnpm --filter ki-team-dashboard lint
pnpm --filter ki-team-dashboard build
pnpm --filter ki-team-widget lint
pnpm --filter ki-team-widget build
```

The widget production build aliases React to Preact Compat so the bundled `loader.iife.js` stays small enough for website embedding.

---

## Project Status

| Area | Status |
| ---- | ------ |
| Database schema | Complete with Alembic migration |
| API framework | Complete with tenant-scoped MVP routes |
| WebSocket chat | Complete with consent, origin, and size checks |
| Live Voice Agents | Complete as feature-flagged WebRTC mode with consent, tenant profile, tool bridge, and text fallback |
| Agent core (base) | Complete |
| Agent template | Complete |
| Chat widget | Complete with GDPR consent gate and small IIFE bundle |
| Admin dashboard | Complete as MVP with real API views |
| Tenant `mein-kuechenexperte` | Active with public widget name KEA |
| Additional tenants | Prepared through the registry structure |
| Google Calendar integration | Feature-flagged with secured OAuth routes |
| Email sending | Feature-flagged through Resend |

---

## Contact

This project is being developed by **Konstantin** as part of building [mein-kuechenexperte.de](https://www.mein-kuechenexperte.de).

Questions, feedback, or interested in collaboration? → GitHub Issues or directly via email.
