# Auftragsverarbeiter-Übersicht
**Rechtsgrundlage:** Art. 28 DSGVO
**Stand:** März 2026

---

## Übersicht aller externen Dienstleister

| Anbieter | Dienst | Sitz | Drittlandtransfer | AVV | SCC | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Anthropic PBC | Claude LLM API | USA | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |
| OpenAI Inc. | Embeddings API | USA | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |
| Resend Inc. | E-Mail-Versand | USA | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |
| Google LLC | Calendar API, OAuth | USA/EU | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |
| Hetzner Online GmbH | Server-Hosting | Deutschland | Nein — EU | ✅ | — | ✅ EU-Hosting |
| Cloudflare Inc. | CDN, DNS, DDoS | USA | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |

---

## Detailbeschreibung

### Anthropic PBC
- **Dienst:** Claude AI — Sprachverarbeitung für Chat-Antworten
- **Daten die übertragen werden:** Chat-Verlauf (pseudonymisiert), System-Prompt
- **AVV-Link:** https://www.anthropic.com/legal/data-processing-agreement
- **Aktion:** AVV prüfen und unterzeichnen / akzeptieren

### OpenAI Inc.
- **Dienst:** text-embedding-3-small — Vektorisierung der Wissensbasis
- **Daten die übertragen werden:** Studio-Wissensinhalte (kein PII)
- **AVV-Link:** https://openai.com/policies/data-processing-addendum
- **Aktion:** AVV prüfen und unterzeichnen / akzeptieren

### Google LLC
- **Dienst:** Google Calendar API für Terminbuchungen
- **Daten die übertragen werden:** Termindetails, Berater-E-Mail, Kunden-E-Mail (optional)
- **Aktion:** Google Workspace AVV aktivieren (Daten-Verarbeitungszusatz)

### Hetzner Online GmbH
- **Dienst:** Dedicated Server für Python-Backend und PostgreSQL
- **Daten:** Alle Produktionsdaten
- **AVV:** Verfügbar unter https://www.hetzner.com/rechtliches/datenschutz
- **Status:** EU-Hosting — kein Drittlandtransfer

---

## Nächste Schritte

1. [ ] Anthropic AVV prüfen und durch Nutzung der API akzeptieren
2. [ ] OpenAI AVV prüfen und durch Nutzung der API akzeptieren
3. [ ] Google Workspace AVV aktivieren (falls Google Workspace genutzt)
4. [ ] Resend AVV prüfen
5. [ ] Cloudflare AVV prüfen
6. [ ] Alle AVVs in diesem Dokument dokumentieren (Datum, Version)
