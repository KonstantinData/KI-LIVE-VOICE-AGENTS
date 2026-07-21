# KI-LIVE-VOICE-AGENTS

🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md)

---

Ein mandantenfähiges System für KI-gestützte Live-Voice- und Chat-Agenten, das Küchen- und Möbelgeschäfte bei Kundenanfragen unterstützt — vom ersten Kontakt bis zur sicheren Übergabe an ein externes CRM.

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

Für `mein-kuechenexperte` liegt das CRM im separaten Repository `mein-kuechenexperte`. Dieses Voice-Agent-Backend übergibt Kontakt- und Usage-Daten nur über CRM-Webhooks und betreibt selbst kein CRM-Dashboard.

---

## Wo läuft was?

| Komponente | URL | Plattform |
| ---------- | --- | --------- |
| **Chat-Widget** (für Websitebesucher) | `widget.mein-kuechenexperte.de` | Cloudflare Pages |
| **CRM / Website-App** (separates Repo) | Externes CRM | `mein-kuechenexperte` |
| **Backend / KI** (unsichtbar im Hintergrund) | `api.mein-kuechenexperte.de` | Hetzner Cloud (EU) |
| **Hauptwebsite** (unverändert) | `www.mein-kuechenexperte.de` | bestehend |

---

## Was ist aktuell fertig gebaut?

### Infrastruktur & Backend

- **Runtime-Datenbankschema** für Studio, Gespräche, Nachrichten, Upload-Kontext und Audit-Trail
- **API-Server** mit Runtime-Endpunkten für Widget, WebSocket, Live Voice, Uploads und CRM-Handoff
- **Echtzeit-Chat** via WebSocket — Nachrichten werden in Millisekunden übertragen
- **Live Voice Agents** via Browser-WebRTC — Sprache läuft über einen serverseitigen OpenAI-Realtime-Broker ohne Browser-API-Key
- **Wissenssuche**: Das System kann in der Produktdatenbank eines Studios semantisch suchen und passende Informationen an die KI weitergeben
- **Gedächtnissystem**: Jeder Agent nutzt erlaubten Gesprächskontext, ohne für `mein-kuechenexperte` CRM-Leads lokal zu führen
- **Multi-Studio-Betrieb**: Beliebig viele Studios können das System parallel nutzen — vollständig voneinander getrennt

### KI-Kern

- Vorgefertigte **Agentenstruktur**: Jeder neue Agent folgt demselben 7-Schritte-Ablauf (Kontext laden → Anfrage verstehen → Wissen abrufen → Tools nutzen → Antworten → Speichern)
- Anbindung an **OpenAI** für natürliche Gespräche, Live Voice und komplexes Reasoning
- **Tool-System**: Agenten nutzen nur tenant-erlaubte Runtime-Tools; `mein-kuechenexperte` verwendet sichere CRM-Handoffs statt lokaler Lead-Tools
- **Tenant-Registry**: Neue Tenants erhalten eigene Profile, Skill-Packs, Policies und Widget-Identität ohne neuen hart codierten Agenten

### Frontend

- **Chat-Widget**: Ein `<script>`-Tag reicht zur Integration in jede bestehende Website; Textchat bleibt Fallback für den Sprachmodus
- Das **CRM-Dashboard** für `mein-kuechenexperte` liegt im Repository `mein-kuechenexperte`

### Deployment & Betrieb

- **Backend** läuft auf einem europäischen Server (Hetzner, DSGVO-konform)
- **Widget** über Cloudflare Pages — schnell, weltweit, ausfallsicher
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
│   ├── api/           # Runtime-API-Server (Voice, Uploads, Widget, Handoff)
│   └── db/            # Datenbankmodelle und Migrationen
├── registry/          # Tenant-Profile und tenant-spezifische Skill-Packs
├── schemas/           # Maschinenlesbare Tenant-/Runtime-Verträge
│
├── frontends/
│   ├── widget/        # Chat-Widget → widget.mein-kuechenexperte.de
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
| KI-Modell | OpenAI | Gespräche, Tool-Nutzung und Live Voice über einen Provider |
| Embeddings | OpenAI | Günstige, bewährte Vektorisierung für Wissenssuche |
| Chat | WebSocket | Echtzeit-Kommunikation ohne Seitenneuladung |
| Live Voice | OpenAI Realtime + WebRTC | Niedrige Latenz, VAD und Unterbrechungen im Browser |
| Widget | React + Vite | Kleines Bundle, läuft isoliert auf jeder Website |
| Hosting Backend | Hetzner (EU) | DSGVO-konform, zuverlässig, kosteneffizient |
| Hosting Widget | Cloudflare Pages | Globales CDN, automatische SSL-Zertifikate, kostenlos |

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

```

**Benötigt:** Python 3.12+, Node.js 20+, pnpm, PostgreSQL 16 mit pgvector

### Produktionsrelevante Konfiguration

- Dieses Repo betreibt keine CRM-/Admin-Oberfläche. CRM-Arbeitsbereiche, Leads und Kostenreports liegen im Repository `mein-kuechenexperte`.
- `CRM_CONTACT_HANDOFF_SECRET` und `CRM_USAGE_HANDOFF_SECRET` müssen gesetzt sein, wenn Kontakt- und Usage-Daten an das CRM übergeben werden.
- `ENABLE_VOICE_SESSIONS` ist ein globaler Kill-Switch für Live Voice Agents. Zusätzlich muss das Tenant-Profil Voice aktivieren; das Widget kann den Tab per `data-voice="true"` anzeigen.
- Live Voice Agents nutzen `/voice/sessions/webrtc` und `/voice/session` als serverseitige OpenAI-Realtime-Broker. Standard-API-Keys bleiben im Backend; der Browser erhält nur kurzlebige Client-Secrets oder SDP-Antworten und sichere Session-Metadaten.
- Im Sprachmodus wird Mikrofonzugriff erst nach Consent und zusätzlichem Klick angefragt. Roh-Audio wird standardmäßig nicht gespeichert; finale Transkripte, Tool-Audits und Zusammenfassungen werden tenant-sicher gespeichert.
- `CORS_ORIGINS` muss die öffentliche Website enthalten. WebSocket-Verbindungen werden serverseitig gegen diese Origins geprüft.
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
pnpm --filter ki-team-widget lint
pnpm --filter ki-team-widget build
```

Das Widget nutzt im Produktionsbuild Preact Compat als gebündelte Runtime, damit `loader.iife.js` klein genug für eine einbettbare Website-Integration bleibt.

---

## Projektstatus

| Bereich | Status |
| ------- | ------ |
| Runtime-Datenbankschema | Fertig mit Alembic-Migration |
| API-Grundgerüst | Fertig mit tenant-gefilterten Runtime-Routen |
| WebSocket-Chat | Fertig mit Consent-, Origin- und Größenprüfung |
| Live Voice Agents | Fertig als feature-geflaggter WebRTC-Modus mit Consent, Tenant-Profil, Tool-Bridge und Text-Fallback |
| Agenten-Kern (Basis) | Fertig |
| Agenten-Vorlage | Fertig |
| Chat-Widget | Fertig mit DSGVO-Consent-Gate und kleinem IIFE-Bundle |
| CRM-Dashboard | Liegt im separaten Repository `mein-kuechenexperte` |
| Tenant `mein-kuechenexperte` | Aktiv mit Widget-Name KEA und CRM-Handoff |
| Tenant `liquisto` | Interner, toolfreier Analysis-only-Lotse mit lokalem Provider vorbereitet; nicht live deployt ([Vertrag](docs/liquisto-assistant-runtime.md)) |
| Weitere Tenants | Über Registry-Struktur vorbereitet |
| CRM-Handoff | Kontakt- und Usage-Webhooks zum Repository `mein-kuechenexperte` |

---

## Kontakt

Dieses Projekt wird entwickelt von **Konstantin** im Rahmen des Aufbaus von [mein-kuechenexperte.de](https://www.mein-kuechenexperte.de).

Fragen, Feedback oder Interesse an einer Zusammenarbeit? → GitHub Issues oder direkt per E-Mail.
