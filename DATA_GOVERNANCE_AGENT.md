# DATA_GOVERNANCE_AGENT.md — Compliance-Prüfagent

> **Arbeitsanweisung für Codex**
> Erstelle einen DataGovernance-Agenten, der jedes relevante Script im
> Repository automatisch auf Einhaltung der DSGVO und des EU AI Act prüft.

---

## WAS DIESER AGENT TUT

Der DataGovernance-Agent ist KEIN KI-Mitarbeiter für Kunden.
Er ist ein internes Entwicklungswerkzeug — ein automatischer Compliance-Prüfer,
der bei jedem Commit, jedem PR oder auf Abruf den gesamten Codestand scannt
und ein detailliertes Log schreibt mit:

1. **Was nicht passt** (exakte Datei, exakte Zeile, exakter Verstoß)
2. **Warum es nicht passt** (Verweis auf DSGVO-Artikel oder EU AI Act-Artikel)
3. **Wie es aussehen muss** (konkreter Fix-Vorschlag mit Code-Beispiel)
4. **Schweregrad** (KRITISCH / HOCH / MITTEL / NIEDRIG / HINWEIS)
5. **Deadline** (wann muss es spätestens behoben sein laut Regulierung)

---

## RECHTLICHER RAHMEN (Stand: März 2026)

Der Agent prüft gegen zwei Regelwerke:

### A. DSGVO (Datenschutz-Grundverordnung, EU 2016/679)
Vollständig in Kraft seit 25.05.2018. Bußgelder bis 20 Mio. EUR oder 4% des
weltweiten Jahresumsatzes.

### B. EU AI Act (Verordnung (EU) 2024/1689)
Gestaffelte Anwendung:
- Seit 02.02.2025: Verbotene AI-Praktiken (Art. 5)
- Ab 02.08.2025: GPAI-Verpflichtungen + AI Literacy (Art. 4)
- Ab 02.08.2026: Hochrisiko-AI (Annex III), Transparenzpflichten (Art. 50),
  Konformitätsbewertungen, technische Dokumentation, CE-Kennzeichnung
- Ab 02.08.2027: Volle Anwendung für alle Systeme

### C. Ergänzende Regelungen (werden mitgeprüft)
- TTDSG (Telekommunikation-Telemedien-Datenschutz-Gesetz) — DE-spezifisch
- ePrivacy-Verordnung (soweit Entwurf relevant)
- BDSG (Bundesdatenschutzgesetz) — DE-spezifische Ergänzungen zur DSGVO

---

## PRÜFKATEGORIEN

Der Agent prüft den Code in folgenden Kategorien:

### KATEGORIE 1: PERSONENBEZOGENE DATEN (DSGVO)

```
Prüfe JEDEN Codepfad, der personenbezogene Daten verarbeitet:

1.1 DATENMINIMIERUNG (Art. 5 Abs. 1 lit. c DSGVO)
    - Werden nur die Daten erhoben, die für den Zweck nötig sind?
    - Gibt es Felder, die erhoben aber nirgends verwendet werden?
    - Werden mehr Daten an das LLM gesendet als nötig?
    FINDING wenn: Ein Feld in einem Model/Schema existiert, das nirgends
    im Business-Logic-Code gelesen wird.
    FIX: Feld entfernen oder Zweck dokumentieren.

1.2 ZWECKBINDUNG (Art. 5 Abs. 1 lit. b DSGVO)
    - Wird der Zweck der Datenerhebung klar dokumentiert?
    - Werden Daten, die für Zweck A erhoben wurden, für Zweck B genutzt?
    - Werden Chat-Daten für Training verwendet ohne explizite Einwilligung?
    FINDING wenn: Daten aus der conversations-Tabelle an einen
    Trainings-/Analytics-Prozess übergeben werden ohne Consent-Check.
    FIX: Consent-Flag prüfen ODER Daten anonymisieren vor Weitergabe.

1.3 SPEICHERBEGRENZUNG (Art. 5 Abs. 1 lit. e DSGVO)
    - Gibt es ein Löschkonzept für jede Datenkategorie?
    - Gibt es Retention-Policies in Code oder Konfiguration?
    - Werden alte Konversationen automatisch gelöscht/anonymisiert?
    FINDING wenn: Kein TTL/Retention-Mechanismus für Tabellen mit
    personenbezogenen Daten existiert.
    FIX: Retention-Policy implementieren:
      - Konversations-Rohdaten: 6 Monate, dann löschen
      - Lead-Daten ohne Konversion: 12 Monate, dann anonymisieren
      - Feedback-Daten: 24 Monate
      - Events/Audit-Trail: 36 Monate (gesetzliche Aufbewahrungspflicht)

1.4 RECHTE DER BETROFFENEN (Art. 15-22 DSGVO)
    - Gibt es einen API-Endpunkt für Datenauskunft (Art. 15)?
    - Gibt es einen API-Endpunkt für Datenlöschung (Art. 17)?
    - Gibt es einen API-Endpunkt für Datenportabilität (Art. 20)?
    - Gibt es einen Mechanismus für Widerspruch (Art. 21)?
    - Gibt es einen Mechanismus für Einschränkung der Verarbeitung (Art. 18)?
    FINDING wenn: Kein /api/gdpr/export oder /api/gdpr/delete Endpunkt existiert.
    FIX: GDPR-Endpoints implementieren mit vollständigem Daten-Export als JSON
    und kaskadierender Löschung über alle Tabellen.

1.5 EINWILLIGUNG (Art. 6, 7 DSGVO)
    - Wird VOR dem Chat eine Einwilligung eingeholt?
    - Ist die Einwilligung freiwillig, spezifisch, informiert und unmissverständlich?
    - Wird die Einwilligung dokumentiert (Zeitstempel, Text, Version)?
    - Kann die Einwilligung jederzeit widerrufen werden?
    - Ist der Chat auch OHNE Einwilligung nutzbar (Freiwilligkeit)?
    FINDING wenn: Das Widget den Chat startet ohne vorherigen Consent-Dialog.
    FIX: Consent-Banner VOR Chat-Start mit:
      - Welche Daten werden erhoben
      - Zu welchem Zweck
      - Wie lange gespeichert
      - Hinweis auf KI-Verarbeitung
      - Widerrufsrecht
      - Link zur Datenschutzerklärung

1.6 AUFTRAGSVERARBEITUNG (Art. 28 DSGVO)
    - Wird für jeden externen Dienst (OpenAI, Resend, Google)
      ein AVV-Hinweis im Code/Config dokumentiert?
    - Werden Daten an Dienste außerhalb der EU gesendet?
    - Ist ein Transfer-Mechanismus dokumentiert (SCC, Angemessenheitsbeschluss)?
    FINDING wenn: API-Calls an openai.com ohne
    Dokumentation des Drittlandtransfers.
    FIX: In config.py oder PRIVACY.md dokumentieren:
      - OpenAI (USA): SCC + DPA vorhanden: [Ja/Nein]
      - Resend (USA): SCC + DPA vorhanden: [Ja/Nein]
      - Google (USA/EU): SCC + DPA vorhanden: [Ja/Nein]

1.7 DATENSCHUTZ DURCH TECHNIKGESTALTUNG (Art. 25 DSGVO — Privacy by Design)
    - Sind personenbezogene Daten in der DB verschlüsselt (at rest)?
    - Wird HTTPS für alle Verbindungen erzwungen?
    - Sind Passwörter gehasht (bcrypt/argon2), nicht verschlüsselt?
    - Sind API-Keys und Tokens verschlüsselt gespeichert?
    - Gibt es eine Pseudonymisierung von Kundendaten wo möglich?
    FINDING wenn: Passwörter als Plaintext oder mit MD5/SHA gespeichert werden.
    FIX: bcrypt oder argon2id mit Mindest-Cost-Factor.
```

### KATEGORIE 2: KI-TRANSPARENZ (EU AI Act + DSGVO)

```
2.1 KI-OFFENLEGUNG (Art. 50 Abs. 1 EU AI Act)
    - Wird dem Nutzer BEVOR er chattet mitgeteilt, dass er mit einer KI spricht?
    - Ist diese Information klar, verständlich und gut sichtbar?
    - Wird die KI-Natur nicht verschleiert?
    FINDING wenn: Das Widget die KI-Natur erst auf Nachfrage offenlegt.
    FIX: Im Consent-Banner UND in der ersten Begrüßungsnachricht klar machen:
    "Ich bin Lisa, die KI-Assistentin von [Studio]."

2.2 AUTOMATISIERTE ENTSCHEIDUNGEN (Art. 22 DSGVO)
    - Gibt es automatisierte Entscheidungen mit rechtlicher Wirkung?
    - Lead-Scoring: Wird ein Mensch einbezogen bevor Konsequenzen eintreten?
    - Wird der Nutzer über automatisierte Verarbeitung informiert?
    FINDING wenn: Lead-Score automatisch zu einer Handlung führt
    (z.B. automatischer Kontaktabbruch bei Score < 10) ohne Human-in-the-Loop.
    FIX: Bei jeder automatisierten Entscheidung mit Konsequenz:
    Autonomie-Stufe prüfen, Human-Freigabe einbauen.

2.3 ERKLÄRBARKEIT (Art. 13 EU AI Act — Transparenz für Nutzer)
    - Kann das Studio nachvollziehen, WARUM Lisa eine bestimmte Antwort gegeben hat?
    - Wird der Entscheidungsprozess geloggt (welche Tools aufgerufen, welcher Kontext)?
    - Kann ein Berater verstehen, warum ein Lead Score X bekommen hat?
    FINDING wenn: tool_calls in der messages-Tabelle nicht gespeichert werden.
    FIX: Jede LLM-Interaktion vollständig loggen:
      - System-Prompt (Version/Hash)
      - User-Message
      - Tool-Calls + Tool-Results
      - Assistant-Response
      - Token-Count + Kosten

2.4 MENSCHLICHE AUFSICHT (Art. 14 EU AI Act — Human Oversight)
    - Gibt es Autonomie-Stufen (Entwurf/Empfehlung/Autopilot)?
    - Kann ein Mensch jederzeit in ein Gespräch eingreifen?
    - Gibt es einen Kill-Switch (Lisa sofort deaktivieren)?
    - Werden Aktionen mit hohem Risiko immer von Menschen freigegeben?
    FINDING wenn: Kein Mechanismus existiert, Lisa pro Studio sofort zu deaktivieren.
    FIX: is_active Flag in Studio-Config + sofortige Wirkung auf neue Gespräche.
```

### KATEGORIE 3: RISIKOMANAGEMENT (EU AI Act)

```
3.1 RISIKOKLASSIFIZIERUNG (Art. 6 EU AI Act)
    - Ist das AI-System klassifiziert (Minimal/Limited/High/Unacceptable)?
    - Für KitchenFlow/Lisa: Primär "Limited Risk" (Transparenzpflichten)
    - ABER: Wenn Lisa Entscheidungen über Kreditwürdigkeit/Finanzierung
      beeinflusst → könnte "High Risk" werden
    FINDING wenn: Keine Risikoklassifizierung dokumentiert ist.
    FIX: Erstelle AI_RISK_CLASSIFICATION.md im Repo mit:
      - Systemname + Version
      - Einsatzzweck
      - Risikokategorie + Begründung
      - Betroffene Personen
      - Potentielle Schäden

3.2 QUALITÄTSMANAGEMENTSYSTEM (Art. 17 EU AI Act — für High-Risk)
    - Gibt es dokumentierte Prozesse für Updates?
    - Gibt es ein Changelog für System-Prompt-Änderungen?
    - Gibt es Testprotokolle?
    FINDING wenn: System-Prompts geändert werden ohne Versionierung.
    FIX: System-Prompt-Versioning einbauen:
      - Jede Prompt-Änderung als neuen Datensatz speichern (nicht überschreiben)
      - Timestamp + Author + Diff

3.3 TECHNISCHE DOKUMENTATION (Art. 11 + Annex IV EU AI Act)
    - Gibt es eine allgemeine Beschreibung des AI-Systems?
    - Sind Design-Entscheidungen dokumentiert?
    - Sind Trainings-/Testdaten beschrieben (hier: Wissensbasis-Inhalte)?
    - Sind Leistungsmetriken definiert und gemessen?
    FINDING wenn: Kein TECHNICAL_DOCUMENTATION.md existiert.
    FIX: Erstelle Dokument mit:
      - Systemübersicht + Architektur
      - Verwendete Modelle + Versionen
      - Datenquellen + Datenflüsse
      - Leistungsmetriken + Monitoring
      - Bekannte Limitierungen
      - Kontaktinformationen des Verantwortlichen

3.4 BIAS & FAIRNESS PRÜFUNG
    - Werden bestimmte Kundengruppen systematisch anders behandelt?
    - Gibt es im System-Prompt Anweisungen, die diskriminieren könnten?
    - Werden Lead-Scores fair vergeben (kein Bias nach Name/Herkunft)?
    FINDING wenn: Lead-Score-Berechnung den Namen des Leads als Input verwendet.
    FIX: Score-Berechnung ausschließlich auf sachliche Kriterien beschränken
    (Budget, Zeitrahmen, Konkretheit der Wünsche — NICHT Name, Sprache, Herkunft).
```

### KATEGORIE 4: DATENSICHERHEIT (DSGVO Art. 32 + EU AI Act)

```
4.1 VERSCHLÜSSELUNG
    - Ist TLS 1.2+ für alle externen Verbindungen erzwungen?
    - Ist die Datenbank-Verbindung verschlüsselt?
    - Sind sensible Felder (calendar_tokens, api_keys) verschlüsselt at rest?
    - Werden Backups verschlüsselt?
    FINDING wenn: DATABASE_URL kein "sslmode=require" enthält.
    FIX: sslmode=require in Connection String.

4.2 AUTHENTIFIZIERUNG & AUTORISIERUNG
    - Sind alle API-Endpunkte mit Auth geschützt (außer /health und Widget)?
    - Ist JWT mit ausreichender Schlüssellänge konfiguriert (min. 256 bit)?
    - Gibt es Rate Limiting auf allen Endpunkten?
    - Sind Default-Credentials geändert?
    FINDING wenn: Ein API-Endpunkt ohne Auth-Middleware erreichbar ist
    (außer explizit öffentliche Endpunkte).
    FIX: Auth-Middleware als Default, explizites Opt-out für öffentliche Routes.

4.3 INPUT VALIDATION & PROMPT INJECTION
    - Werden alle User-Inputs validiert (Zod/Pydantic)?
    - Gibt es Schutz gegen Prompt Injection?
    - Gibt es Schutz gegen SQL Injection?
    - Gibt es Schutz gegen XSS im Widget?
    - Maximale Nachrichtenlänge begrenzt?
    FINDING wenn: User-Input direkt in einen f-String/Template eingesetzt wird
    der an das LLM geht, ohne Sanitization.
    FIX: Input-Sanitization-Layer VOR dem LLM-Call:
      - Maximale Länge (2.000 Zeichen)
      - Bekannte Injection-Patterns filtern
      - User-Input in <user_message> Tags wrappen im Prompt
      - Output-Prüfung: Enthält die Antwort System-Prompt-Teile?

4.4 LOGGING & MONITORING (Art. 12 EU AI Act — Record-Keeping)
    - Werden alle relevanten Aktionen geloggt?
    - Enthält das Log: Zeitstempel, Actor, Aktion, betroffene Daten?
    - Werden Logs manipulationssicher gespeichert?
    - Werden Logs NICHT mit personenbezogenen Daten im Klartext geschrieben?
    FINDING wenn: Logger personenbezogene Daten (E-Mail, Name, Telefon)
    im Klartext in Logdateien schreibt.
    FIX: PII-Filter im Logger: Automatische Maskierung von E-Mail, Telefon,
    Name in Log-Output. Nur IDs loggen, nicht Klartext-Daten.

4.5 SECRETS MANAGEMENT
    - Sind ALLE Secrets in .env (nicht hardcoded)?
    - Ist .env in .gitignore?
    - Werden Secrets in Fehlermeldungen/Logs geleakt?
    - Gibt es API-Keys im Code (auch in Kommentaren)?
    FINDING wenn: Ein String, der wie ein API-Key aussieht
    (sk-, re_, AIza, etc.) im Code vorkommt.
    FIX: Sofort entfernen, Key rotieren, aus Git-History entfernen.
```

### KATEGORIE 5: MULTI-TENANT ISOLATION (DSGVO + Sorgfaltspflicht)

```
5.1 DATEN-ISOLATION
    - Filtert JEDE Datenbankabfrage nach studio_id?
    - Gibt es eine Query, die ALLE Studios' Daten zurückgibt?
    - Kann ein Studio die Daten eines anderen Studios sehen?
    FINDING wenn: Eine SQL-Query oder ORM-Abfrage KEINEN studio_id Filter hat
    (außer in explizit markierten Admin-Queries).
    FIX: studio_id Filter als Middleware/Mixin, der automatisch greift.

5.2 VEKTOR-ISOLATION
    - Sind Embeddings in der Wissensbasis nach studio_id getrennt?
    - Kann eine Vektor-Suche Ergebnisse aus einem anderen Studio liefern?
    FINDING wenn: knowledge.search() keinen studio_id Filter im WHERE hat.
    FIX: studio_id als Pflicht-Parameter in jeder Vektor-Suche.

5.3 LLM-KONTEXT-ISOLATION
    - Werden Daten aus Studio A NIE an das LLM im Kontext von Studio B gesendet?
    - Enthält der System-Prompt nur Daten des aktuellen Studios?
    FINDING wenn: Memory/Knowledge-Loader keinen studio_id Check enthält.
    FIX: Assert studio_id Match bei jedem Context-Load.
```

### KATEGORIE 6: WORAN DU NICHT GEDACHT HAST

```
6.1 COOKIE-CONSENT (TTDSG § 25 + ePrivacy)
    - Setzt das Widget Cookies oder LocalStorage?
    - Wird dafür eine Einwilligung eingeholt?
    - Die visitor_id: Wie wird sie generiert? Ist sie ein Tracking-Cookie?
    FINDING wenn: visitor_id als Cookie gespeichert wird ohne Consent.
    FIX: visitor_id als Session-Only generieren (kein Cookie) ODER
    Consent vor dem Setzen einholen.

6.2 KINDERSCHUTZ (Art. 8 DSGVO + Art. 5 EU AI Act)
    - Gibt es einen Mechanismus, wenn Minderjährige den Chat nutzen?
    - Darf Lisa Daten von unter-16-Jährigen (DE: unter-16) erheben?
    FINDING wenn: Kein Alterscheck oder -hinweis existiert.
    FIX: Im Consent-Dialog: "Dieses Angebot richtet sich an Personen ab 16 Jahren."

6.3 BARRIEREFREIHEIT DES CONSENT-DIALOGS
    - Ist der Consent-Dialog auch ohne JavaScript lesbar?
    - Ist er per Tastatur bedienbar?
    - Hat er ausreichenden Kontrast?
    FINDING wenn: Consent nur als JavaScript-Popup ohne Fallback.
    FIX: Noscript-Fallback, aria-Labels, Kontrastprüfung.

6.4 RECHT AUF MENSCHLICHEN KONTAKT
    - Kann der Nutzer JEDERZEIT einen menschlichen Ansprechpartner verlangen?
    - Ist die Eskalation in jedem Chat-Zustand möglich?
    - Wird die Telefonnummer/E-Mail des Studios angezeigt?
    FINDING wenn: Kein Eskalationsmechanismus im Widget sichtbar ist.
    FIX: Permanent sichtbarer "Mit einem Mitarbeiter sprechen"-Button im Widget.

6.5 IMPRESSUM & DATENSCHUTZERKLÄRUNG
    - Verlinkt das Widget auf das Impressum?
    - Verlinkt das Widget auf die Datenschutzerklärung?
    - Enthält die DSE alle KI-spezifischen Informationen?
    FINDING wenn: Widget keinen Link zur DSE enthält.
    FIX: Footer im Widget: "Datenschutz | Impressum"

6.6 AUFBEWAHRUNG VON EINWILLIGUNGEN
    - Wird jede Consent-Erteilung mit Timestamp gespeichert?
    - Wird die Version des Consent-Textes mitgespeichert?
    - Kann nachgewiesen werden, WANN WER WELCHEM Text zugestimmt hat?
    FINDING wenn: Consent nur als Boolean gespeichert wird ohne Timestamp/Version.
    FIX: Consent-Tabelle:
      - id, visitor_id, consent_version, consent_text_hash, granted_at, ip_address

6.7 DATENPANNE (Art. 33, 34 DSGVO — Breach Notification)
    - Gibt es einen dokumentierten Prozess für Datenpannen?
    - Gibt es einen Mechanismus zur Erkennung von Datenlecks?
    - Ist klar, wer innerhalb von 72 Stunden die Behörde informiert?
    FINDING wenn: Kein INCIDENT_RESPONSE.md existiert.
    FIX: Erstelle Dokument mit:
      - Verantwortlicher für Meldung
      - Kontaktdaten der zuständigen Aufsichtsbehörde
      - Checkliste: Was melden? An wen? In welcher Frist?
      - Template für die Meldung

6.8 DPIA (Datenschutz-Folgenabschätzung, Art. 35 DSGVO)
    - Wurde eine DPIA durchgeführt für die KI-gestützte Profilierung?
    - Lead-Scoring = Profiling = DPIA wahrscheinlich erforderlich
    FINDING wenn: Keine DPIA.md oder DPIA-Dokumentation existiert.
    FIX: DPIA erstellen mit:
      - Beschreibung der Verarbeitung
      - Zweck und Rechtsgrundlage
      - Notwendigkeit und Verhältnismäßigkeit
      - Risiken für die Rechte der Betroffenen
      - Maßnahmen zur Risikominderung

6.9 VERANTWORTLICHKEIT FÜR KI-AUSGABEN
    - Wer haftet, wenn Lisa falsche Informationen gibt?
    - Wer haftet, wenn Lisa Preiszusagen macht, die nicht stimmen?
    - Gibt es einen Disclaimer im Widget?
    FINDING wenn: Kein Haftungshinweis im Widget oder in der DSE.
    FIX: "Alle Angaben im Chat sind unverbindlich. Verbindliche
    Informationen erhalten Sie in der persönlichen Beratung."

6.10 ÜBERWACHUNG DES LLM-OUTPUTS (EU AI Act Art. 9 — Risikomanagement)
    - Werden LLM-Antworten auf problematische Inhalte geprüft?
    - Was passiert, wenn das LLM halluziniert (falsche Preise, falsche Fakten)?
    - Gibt es ein Monitoring für Antwortqualität?
    FINDING wenn: Keine Output-Validation nach dem LLM-Call existiert.
    FIX: Post-Processing-Layer:
      - Enthält die Antwort Preisangaben? → Warnung
      - Enthält die Antwort externe URLs? → Blockieren
      - Enthält die Antwort System-Prompt-Fragmente? → Blockieren
      - Enthält die Antwort Wettbewerber-Namen? → Warnung

6.11 VERARBEITUNGSVERZEICHNIS (Art. 30 DSGVO)
    - Existiert ein Verzeichnis aller Verarbeitungstätigkeiten?
    FINDING wenn: Kein PROCESSING_REGISTER.md existiert.
    FIX: Erstelle Verzeichnis mit pro Verarbeitung:
      - Name der Verarbeitung
      - Verantwortlicher
      - Zweck
      - Kategorien betroffener Personen
      - Kategorien personenbezogener Daten
      - Empfänger
      - Drittlandtransfers
      - Löschfristen
      - TOM (technische und organisatorische Maßnahmen)
```

---

## LOG-FORMAT

Der Agent schreibt alle Findings in: `compliance/governance_log.json`

Jedes Finding hat folgende Struktur:

```json
{
  "id": "GOV-2026-0001",
  "timestamp": "2026-03-10T14:30:00Z",
  "severity": "KRITISCH",
  "category": "DSGVO",
  "subcategory": "1.5_EINWILLIGUNG",
  "regulation": "Art. 6 Abs. 1 DSGVO",
  "file": "frontends/widget/src/Widget.tsx",
  "line": 42,
  "finding": "Chat wird gestartet ohne vorherige Einwilligung des Nutzers. Der WebSocket-Connect erfolgt sofort beim Laden des Widgets, bevor der Nutzer dem Chat zugestimmt hat.",
  "must_be": "WebSocket-Verbindung darf ERST aufgebaut werden, nachdem der Nutzer dem Consent-Dialog aktiv zugestimmt hat. Der Consent-Dialog muss enthalten: Hinweis auf KI-Verarbeitung, Zweck der Datenerhebung, Speicherdauer, Widerrufsrecht, Link zur Datenschutzerklärung.",
  "fix_example": "// VORHER (VERSTOSS):\nuseEffect(() => { connectWebSocket(); }, []);\n\n// NACHHER (COMPLIANT):\nconst [consentGiven, setConsentGiven] = useState(false);\nuseEffect(() => { if (consentGiven) connectWebSocket(); }, [consentGiven]);",
  "deadline": "Sofort — muss VOR dem Go-Live behoben sein",
  "auto_fixable": true,
  "references": [
    "DSGVO Art. 6 Abs. 1 lit. a",
    "DSGVO Art. 7",
    "TTDSG § 25"
  ]
}
```

Zusätzlich wird ein **menschenlesbarer Report** generiert:
`compliance/governance_report.md`

Mit Zusammenfassung:
```markdown
# Compliance-Report — [Datum]

## Zusammenfassung
- Geprüfte Dateien: 47
- Findings gesamt: 12
- KRITISCH: 2
- HOCH: 3
- MITTEL: 4
- NIEDRIG: 2
- HINWEIS: 1
- Auto-fixable: 7 von 12

## Kritische Findings (sofort beheben)
...

## Hohe Findings (vor Go-Live beheben)
...
```

---

## TECHNISCHE UMSETZUNG

Erstelle den Agenten als Python-Modul in: `src/agents/governance/`

```
src/agents/governance/
├── __init__.py
├── agent.py              # Hauptlogik: Scannt Repo, generiert Findings
├── rules/
│   ├── __init__.py
│   ├── dsgvo.py          # DSGVO-spezifische Prüfregeln
│   ├── eu_ai_act.py      # EU AI Act-spezifische Prüfregeln
│   ├── security.py       # Sicherheits-Prüfregeln
│   ├── multi_tenant.py   # Multi-Tenant-Isolation
│   └── documentation.py  # Dokumentationspflichten
├── scanner.py            # AST-basierter Code-Scanner (Python + TypeScript)
├── report.py             # Report-Generator (JSON + Markdown)
├── models.py             # Pydantic Models (Finding, Report, Severity)
└── config.py             # Welche Regeln aktiv, welche Pfade scannen
```

### Wie der Scanner funktioniert

Der Scanner kombiniert drei Ansätze:

1. **Statische Code-Analyse (AST):**
   - Python: `ast` Modul — parst Python-Dateien, sucht nach Patterns
   - TypeScript/JS: `tree-sitter` oder Regex-basiert
   - Sucht nach: fehlenden Auth-Decorators, fehlenden studio_id-Filtern,
     hardcodierten Secrets, unvalidiertem Input, fehlendem Error Handling

2. **Datei-/Struktur-Prüfung:**
   - Existieren Pflichtdokumente? (DPIA.md, PROCESSING_REGISTER.md, etc.)
   - Existieren Consent-Mechanismen im Widget?
   - Existieren Lösch-Endpoints?
   - Existieren Retention-Policies?

3. **LLM-gestützte Analyse (optional, für komplexe Fälle):**
   - System-Prompts auf Bias und Diskriminierung prüfen
   - Datenschutzerklärung auf Vollständigkeit prüfen
   - Code-Logik auf unbeabsichtigte Datenflüsse prüfen

### Aufruf

```bash
# Kompletter Scan
python -m src.agents.governance.agent --scan-all

# Nur geänderte Dateien (für CI/CD)
python -m src.agents.governance.agent --scan-changed

# Nur eine Kategorie
python -m src.agents.governance.agent --category dsgvo

# Report generieren
python -m src.agents.governance.agent --report

# Auto-Fix (nur für auto_fixable Findings)
python -m src.agents.governance.agent --auto-fix
```

### Makefile-Integration

```makefile
# Compliance-Check (in bestehendes Makefile einfügen)
compliance:
	source venv/bin/activate && python -m src.agents.governance.agent --scan-all --report

compliance-fix:
	source venv/bin/activate && python -m src.agents.governance.agent --auto-fix
```

---

## PFLICHTDOKUMENTE DIE DER AGENT PRÜFT (und einfordert)

Der Agent prüft, ob folgende Dokumente im Repo existieren.
Wenn nicht, ist das ein HOCH-Finding mit Template-Vorschlag.

| Dokument | Zweck | Rechtsgrundlage |
|---|---|---|
| `compliance/DPIA.md` | Datenschutz-Folgenabschätzung | Art. 35 DSGVO |
| `compliance/PROCESSING_REGISTER.md` | Verarbeitungsverzeichnis | Art. 30 DSGVO |
| `compliance/AI_RISK_CLASSIFICATION.md` | KI-Risikoklassifizierung | Art. 6 EU AI Act |
| `compliance/TECHNICAL_DOCUMENTATION.md` | Technische Dokumentation | Art. 11 EU AI Act |
| `compliance/INCIDENT_RESPONSE.md` | Datenpannen-Prozess | Art. 33, 34 DSGVO |
| `compliance/DATA_RETENTION.md` | Löschkonzept mit Fristen | Art. 5 Abs. 1 lit. e DSGVO |
| `compliance/THIRD_PARTY_PROCESSORS.md` | Auftragsverarbeiter-Übersicht | Art. 28 DSGVO |
| `compliance/CONSENT_VERSIONS.md` | Versionshistorie der Einwilligungstexte | Art. 7 DSGVO |
| `PRIVACY.md` oder Link zur DSE | Datenschutzerklärung | Art. 13, 14 DSGVO |

---

## WANN DER AGENT LÄUFT

1. **Manuell:** `make compliance` — jederzeit durch den Entwickler
2. **Pre-Commit Hook:** Automatisch vor jedem Commit (nur geänderte Dateien)
3. **CI/CD:** Bei jedem Pull Request auf GitHub (voller Scan)
4. **Wöchentlich:** Scheduled Run für den vollständigen Report

---

## PRIORITÄT DER IMPLEMENTIERUNG

Baue den Agenten in dieser Reihenfolge:

1. **Pflichtdokumente-Check** (existieren die Dateien?) — 30 Minuten
2. **Secrets-Scanner** (API-Keys im Code?) — 30 Minuten
3. **Auth-Check** (alle Endpoints geschützt?) — 1 Stunde
4. **Multi-Tenant-Check** (studio_id überall?) — 1 Stunde
5. **Consent-Check** (Widget-Einwilligung?) — 1 Stunde
6. **Retention-Check** (Löschfristen?) — 1 Stunde
7. **GDPR-Endpoints-Check** (Export/Löschung?) — 1 Stunde
8. **Report-Generator** (JSON + Markdown) — 1 Stunde
9. **LLM-basierte Analyse** (Bias, Prompts) — 2 Stunden
10. **Auto-Fix** (einfache Fixes automatisch) — 2 Stunden
