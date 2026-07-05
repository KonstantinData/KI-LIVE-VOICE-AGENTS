# Verzeichnis der Verarbeitungstätigkeiten
**Rechtsgrundlage:** Art. 30 DSGVO
**Stand:** März 2026
**Verantwortlicher:** [Name und Kontakt eintragen]

---

## Verarbeitung 1: KI-Chat-Erstberatung (Lisa)

| Feld | Inhalt |
| --- | --- |
| Name | KI-Chat-Erstberatung |
| Zweck | Automatisierte Erstberatung für Küchenstudio-Interessenten |
| Rechtsgrundlage | Art. 6 Abs. 1 lit. a DSGVO (Einwilligung) |
| Betroffene Personen | Website-Besucher des Küchenstudios |
| Datenkategorien | Chat-Verlauf, Name, E-Mail, Telefon (optional), Budget-Angaben |
| Empfänger intern | Studio-Berater (über Dashboard) |
| Empfänger extern | OpenAI API (LLM-Verarbeitung, Live Voice, Embeddings) |
| Drittlandtransfer | USA — OpenAI (SCC-Mechanismus) |
| Löschfrist | Chat-Rohdaten: 6 Monate; Lead-Daten: 12 Monate nach letztem Kontakt |
| TOM | TLS-Verschlüsselung, Pseudonymisierung via visitor_id, Zugangskontrolle |

---

## Verarbeitung 2: Lead-Scoring und -Qualifizierung

| Feld | Inhalt |
| --- | --- |
| Name | Automatisches Lead-Scoring |
| Zweck | Priorisierung von Beratungsanfragen für Studio-Berater |
| Rechtsgrundlage | Art. 6 Abs. 1 lit. f DSGVO (Berechtigtes Interesse) |
| Betroffene Personen | Chat-Nutzer die Kontaktdaten angegeben haben |
| Datenkategorien | Budget, Zeitrahmen, Küchenstil, Raumgröße, Kontaktdaten |
| Score-Kriterien | Sachliche Merkmale (Budget, Timeline) — KEINE demografischen Merkmale |
| Empfänger | Studio-Berater |
| Drittlandtransfer | USA — OpenAI (Score-Berechnung via LLM) |
| Löschfrist | Mit Lead-Daten: 12 Monate |
| TOM | Keine Diskriminierungsmerkmale im Scoring-Algorithmus |

---

## Verarbeitung 3: Terminverwaltung

| Feld | Inhalt |
| --- | --- |
| Name | Beratungstermin-Buchung |
| Zweck | Organisation von Beratungsgesprächen |
| Rechtsgrundlage | Art. 6 Abs. 1 lit. b DSGVO (Vertragsanbahnung) |
| Betroffene Personen | Interessenten mit Terminwunsch |
| Datenkategorien | Name, E-Mail, Telefon, Wunschtermin |
| Empfänger extern | Google Calendar API (OAuth, Studio-Berater-Kalender) |
| Drittlandtransfer | USA/EU — Google (SCC-Mechanismus + Standardvertragsklauseln) |
| Löschfrist | 36 Monate (geschäftliche Aufbewahrungspflicht) |
| TOM | OAuth 2.0, Tokens verschlüsselt gespeichert |
