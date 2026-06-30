# Datenschutz-Folgenabschätzung (DPIA)
**Rechtsgrundlage:** Art. 35 DSGVO
**Stand:** März 2026
**Verantwortlicher:** [Name des Verantwortlichen eintragen]

## 1. Beschreibung der Verarbeitung

**System:** KI-Mitarbeiter-Team — Lisa (KI-Empfangsdame)
**Zweck:** Automatisierte Erstberatung und Lead-Qualifizierung für Küchen- und Möbelstudios
**Verarbeitungsart:** Chat-basierte Erfassung von Interessentendaten, KI-gestützte Profilierung, Lead-Scoring

## 2. Notwendigkeit und Verhältnismäßigkeit

### Rechtsgrundlage
- Einwilligung (Art. 6 Abs. 1 lit. a DSGVO) — für Chat-Verarbeitung
- Berechtigtes Interesse (Art. 6 Abs. 1 lit. f DSGVO) — für Lead-Management

### Erhobene Datenkategorien
| Kategorie | Pflicht | Zweck |
| --- | --- | --- |
| Name | Nein | Persönliche Ansprache |
| E-Mail | Nein | Terminbestätigung |
| Telefon | Nein | Rückruf |
| Budget-Rahmen | Nein | Lead-Qualifizierung |
| Zeitrahmen | Nein | Lead-Qualifizierung |
| Chat-Verlauf | Ja | Kontexterhalt |

## 3. Risikobewertung

| Risiko | Wahrscheinlichkeit | Schwere | Maßnahme |
| --- | --- | --- | --- |
| Datenleck durch Multi-Tenant-Fehler | Mittel | Hoch | studio_id auf jeder Query |
| Profiling ohne Einwilligung | Niedrig | Hoch | Consent-Banner vor Chat |
| Datenweitergabe an LLM-Provider | Mittel | Mittel | AVV mit Anthropic/OpenAI |
| Unbegrenzte Datenspeicherung | Hoch | Mittel | Retention-Policy implementiert |

## 4. Maßnahmen zur Risikominderung

- [ ] Consent-Banner vor Chat-Start implementiert
- [ ] AVV mit Anthropic, OpenAI, Resend, Google abgeschlossen
- [ ] Retention-Policy: Konversationen 6 Monate, Leads 12 Monate
- [ ] Multi-Tenant-Isolation: studio_id auf jeder DB-Query
- [ ] Verschlüsselung: TLS für alle Verbindungen, Tokens verschlüsselt at rest

## 5. Konsultation der Datenschutzbehörde

- Erforderlich: [ ] Ja [ ] Nein
- Falls ja, Datum der Konsultation: ___________

## 6. Genehmigung

Verantwortlicher: _________________________ Datum: _____________
Datenschutzbeauftragter (falls vorhanden): _________________________ Datum: _____________
