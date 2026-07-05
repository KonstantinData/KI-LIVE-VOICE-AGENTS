# KI-LIVE-VOICE-AGENTS

🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md)

---

Ein mandantenfähiges System für KI-gestützte Live-Voice- und Chat-Agenten, das Küchen- und Möbelgeschäfte bei Kundenanfragen unterstützt — vom ersten Kontakt bis zur sicheren Übergabe an das Team.

---

## Was ist das hier?

Dieses Projekt ist die technische Grundlage für tenant-spezifische Live Voice Agents. Der Runtime-Agent ist generisch; Name, Prompt-Profil, Tools, Richtlinien, Wissen, Upload-Regeln und Widget-Texte werden pro Tenant aus der Registry zusammengesetzt.

Das System ist als **fertige Plattform** konzipiert: Ein Küchenstudio bekommt einen Tenant, richtet sein Profil ein, und der passende Live Voice Agent geht direkt an die Arbeit. Mehrere Tenants können das System gleichzeitig nutzen, ohne sich gegenseitig zu beeinflussen.

---

## Wie funktioniert die Integration?

Das System ist **kein Ersatz** für die bestehende Website — es wird unsichtbar dort hineinintegriert:

```html
<!-- Eine einzige Zeile in der bestehenden Website -->
<script
  src="https://widget.mein-kuechenexperte.de/loader.iife.js"
  data-studio="mein-kuechenexperte"
  data-voice="true"
></script>
```

Das war es. Der Chat-Button erscheint, und der für diesen Tenant konfigurierte Agent ist einsatzbereit. Für `mein-kuechenexperte` heißt der öffentliche Widget-Agent **KEA**.

---

## Tenant-Runtime-Modell

Ein einziges Chat-Fenster für den Besucher — im Hintergrund wird ein tenant-spezifisches Runtime-Profil geladen.

| Ebene | Aufgabe |
| ---- | ------- |
| **Tenant-Profil** | Widget-Name, Hostnames, Sprache, Datenschutz, Upload- und Voice-Flags |
| **Live Voice Agent Profil** | Prompt-Profil, Modell, Stimme, Skills, Tools, Scopes, Policies, Validatoren |
| **Skill-Pack** | Tenant-spezifische Fähigkeiten und Audit-Anforderungen |
| **Runtime** | Nutzt nur die im Profil erlaubten Module und Daten |

> **Aktueller Stand:** `mein-kuechenexperte` ist als erster Tenant registriert. `KEA` ist dort der öffentliche Widget-Name, technisch aber ein Tenant-Profil für den generischen Live Voice Agent.

---

## Wie sieht das für den Endkunden aus?

Ein Besucher auf `www.mein-kuechenexperte.de` sieht einen Chat-Button in der Ecke. Er klickt, schreibt oder spricht seine Frage — und **KEA** antwortet sofort. Die Unterhaltung fühlt sich wie ein echtes Gespräch an. Im Hintergrund erfasst das System relevante Projektdaten, bewertet den Interessenten und bereitet den nächsten Schritt vor.

Das Küchenstudio sieht alles in einem Admin-Dashboard unter `app.mein-kuechenexperte.de`: welche Leads eingegangen sind, was besprochen wurde, welche Termine bevorstehen.

---

## Wo läuft was?

| Komponente | URL | Plattform |
| ---------- | --- | --------- |
| **Chat-Widget** (für Websitebesucher) | `widget.mein-kuechenexperte.de` | Cloudflare Pages |
| **Admin-Dashboard** (für Studiobetreiber) | `app.mein-kuechenexperte.de` | Cloudflare Pages |
| **Backend / KI** (unsichtbar im Hintergrund) | `api.mein-kuechenexperte.de` | Hetzner Cloud (EU) |
| **Hauptwebsite** (unverändert) | `www.mein-kuechenexperte.de` | bestehend |

---

## Was ist aktuell fertig gebaut?

### Infrastruktur & Backend

- Vollständiges **Datenbankschema** (Interessenten, Gespräche, Termine, Wissensbasis, Audit-Trail)
- **API-Server** mit allen nötigen Endpunkten (Authentifizierung, Chat, Studios, Leads, Termine u.v.m.)
- **Echtzeit-Chat** via WebSocket — Nachrichten werden in Millisekunden übertragen
- **Live Voice Agents** via Browser-WebRTC — Sprache läuft über einen serverseitigen OpenAI-Realtime-Broker ohne Browser-API-Key
- **Wissenssuche**: Das System kann in der Produktdatenbank eines Studios semantisch suchen und passende Informationen an die KI weitergeben
- **Gedächtnissystem**: Jeder Agent merkt sich, was in früheren Gesprächen mit einem Kunden besprochen wurde
- **Multi-Studio-Betrieb**: Beliebig viele Studios können das System parallel nutzen — vollständig voneinander getrennt

### KI-Kern

- Vorgefertigte **Agentenstruktur**: Jeder neue Agent folgt demselben 7-Schritte-Ablauf (Kontext laden → Anfrage verstehen → Wissen abrufen → Tools nutzen → Antworten → Speichern)
- Anbindung an **Anthropic Claude** (modernste Sprachmodell-Technologie) für natürliche Gespräche und komplexes Reasoning
- **Tool-System**: Agenten können eigenständig Aktionen ausführen (Termine prüfen, E-Mails senden, Daten speichern)
- **Tenant-Registry**: Neue Tenants erhalten eigene Profile, Skill-Packs, Policies und Widget-Identität ohne neuen hart codierten Agenten

### Frontend

- **Chat-Widget**: Ein `<script>`-Tag reicht zur Integration in jede bestehende Website; Textchat bleibt Fallback für den Sprachmodus
- **Admin-Dashboard**: Weboberfläche für das Küchenstudio mit Login, Übersichten und Navigation
- Beide Frontends **live auf Cloudflare Pages** mit automatischem SSL und Custom Domains

### Deployment & Betrieb

- **Backend** läuft auf einem europäischen Server (Hetzner, DSGVO-konform)
- **Frontends** über Cloudflare Pages — schnell, weltweit, ausfallsicher
- Automatische Deployments: Jeder Code-Push löst einen neuen Build aus
- Konfigurations- und Deployment-Skripte für schnelle Einrichtung

---

## Projektstruktur (vereinfacht)

```text
KI-LIVE-VOICE-AGENTS/
│
├── src/
│   ├── core/          # Gemeinsamer Kern aller Agenten (LLM, Gedächtnis, Wissen, Tools)
│   ├── agents/        # Runtime-Agent-Implementierung und Legacy-Agent-Module
│   ├── api/           # API-Server (Endpunkte, WebSocket, Authentifizierung)
│   └── db/            # Datenbankmodelle und Migrationen
├── registry/          # Tenant-Profile und tenant-spezifische Skill-Packs
├── schemas/           # Maschinenlesbare Tenant-/Runtime-Verträge
│
├── frontends/
│   ├── widget/        # Chat-Widget → widget.mein-kuechenexperte.de
│   └── dashboard/     # Admin-Dashboard → app.mein-kuechenexperte.de
│
├── tests/             # Automatisierte Tests
└── deploy/            # Server-Konfiguration und Deployment-Skripte
```

---

## Technologie (für Interessierte)

| Bereich | Technologie | Warum |
| ------- | ----------- | ----- |
| Backend | Python + FastAPI | Schnell, asynchron, ideal für KI-Anwendungen |
| Datenbank | PostgreSQL + pgvector | Relationale Daten + KI-Suche in einem System |
| KI-Modell | Anthropic Claude | Bestes Modell für Gespräche und eigenständiges Handeln |
| Embeddings | OpenAI | Günstige, bewährte Vektorisierung für Wissenssuche |
| Chat | WebSocket | Echtzeit-Kommunikation ohne Seitenneuladung |
| Live Voice | OpenAI Realtime + WebRTC | Niedrige Latenz, VAD und Unterbrechungen im Browser |
| Widget | React + Vite | Kleines Bundle, läuft isoliert auf jeder Website |
| Dashboard | React + Tailwind | Moderne, wartbare Admin-Oberfläche |
| Hosting Backend | Hetzner (EU) | DSGVO-konform, zuverlässig, kosteneffizient |
| Hosting Frontend | Cloudflare Pages | Globales CDN, automatische SSL-Zertifikate, kostenlos |

---

## Lokales Setup (für Entwickler)

```bash
# 1. Repository klonen
git clone https://github.com/KonstantinData/KI-LIVE-VOICE-AGENTS.git
cd KI-LIVE-VOICE-AGENTS

# 2. Einmalig einrichten (Python venv + alle Abhängigkeiten)
./setup.sh

# 3. Umgebungsvariablen konfigurieren
cp .env.example .env
# .env öffnen und API-Keys eintragen

# 4. Datenbank einrichten
source venv/bin/activate
make migrate

# 5. Backend starten
make dev
# → http://localhost:8000/health
# → http://localhost:8000/docs (API-Dokumentation)

# 6. Widget bauen (optional)
cd frontends/widget && pnpm install && pnpm build

# 7. Dashboard bauen (optional)
cd frontends/dashboard && pnpm install && pnpm build
```

**Benötigt:** Python 3.12+, Node.js 20+, pnpm, PostgreSQL 16 mit pgvector

### Produktionsrelevante Konfiguration

- `ADMIN_PASSWORD_HASH` muss in Produktion gesetzt sein. Der Testzugang `admin / secret` funktioniert nur, wenn `ALLOW_DEMO_LOGIN=true` und `APP_ENV` nicht `production` ist.
- `JWT_SECRET` muss ein langer zufälliger Wert sein und darf nicht in Git landen.
- `ENABLE_EMAIL_SENDING` und `ENABLE_CALENDAR_SYNC` sind standardmäßig `false`. Externe Aktionen laufen erst, wenn die passenden API-/OAuth-Credentials gesetzt und die Flags bewusst aktiviert sind.
- `ENABLE_VOICE_SESSIONS` ist ein globaler Kill-Switch für Live Voice Agents. Zusätzlich muss das Tenant-Profil Voice aktivieren; das Widget kann den Tab per `data-voice="true"` anzeigen.
- Live Voice Agents nutzen `/voice/sessions/webrtc` und `/voice/session` als serverseitige OpenAI-Realtime-Broker. Standard-API-Keys bleiben im Backend; der Browser erhält nur kurzlebige Client-Secrets oder SDP-Antworten und sichere Session-Metadaten.
- Im Sprachmodus wird Mikrofonzugriff erst nach Consent und zusätzlichem Klick angefragt. Roh-Audio wird standardmäßig nicht gespeichert; finale Transkripte, Tool-Audits und Zusammenfassungen werden tenant-sicher gespeichert.
- `CORS_ORIGINS` muss die öffentliche Website und das Dashboard enthalten. WebSocket-Verbindungen werden serverseitig gegen diese Origins geprüft.
- Das Widget verbindet sich erst nach DSGVO-Einwilligung und sendet `consent=1` an `/ws/chat`.

### Verifikation

```bash
# Backend
python -m pytest -q
python -m ruff check src tests
python -m mypy src

# Migration gegen temporäre SQLite-DB prüfen
DATABASE_URL=sqlite+aiosqlite:///./tmp_migration_check.sqlite3 alembic upgrade head

# Frontends über den Workspace ausführen, damit pnpm allowBuilds greift
pnpm --filter ki-team-dashboard lint
pnpm --filter ki-team-dashboard build
pnpm --filter ki-team-widget lint
pnpm --filter ki-team-widget build
```

Das Widget nutzt im Produktionsbuild Preact Compat als gebündelte Runtime, damit `loader.iife.js` klein genug für eine einbettbare Website-Integration bleibt.

---

## Projektstatus

| Bereich | Status |
| ------- | ------ |
| Datenbankschema | Fertig mit Alembic-Migration |
| API-Grundgerüst | Fertig mit tenant-gefilterten MVP-Routen |
| WebSocket-Chat | Fertig mit Consent-, Origin- und Größenprüfung |
| Live Voice Agents | Fertig als feature-geflaggter WebRTC-Modus mit Consent, Tenant-Profil, Tool-Bridge und Text-Fallback |
| Agenten-Kern (Basis) | Fertig |
| Agenten-Vorlage | Fertig |
| Chat-Widget | Fertig mit DSGVO-Consent-Gate und kleinem IIFE-Bundle |
| Admin-Dashboard | Fertig als MVP mit echten API-Ansichten |
| Tenant `mein-kuechenexperte` | Aktiv mit Widget-Name KEA |
| Weitere Tenants | Über Registry-Struktur vorbereitet |
| Google Calendar Integration | Feature-Flag-gesteuert, OAuth-Routen abgesichert |
| E-Mail-Versand | Feature-Flag-gesteuert über Resend |

---

## Kontakt

Dieses Projekt wird entwickelt von **Konstantin** im Rahmen des Aufbaus von [mein-kuechenexperte.de](https://www.mein-kuechenexperte.de).

Fragen, Feedback oder Interesse an einer Zusammenarbeit? → GitHub Issues oder direkt per E-Mail.
