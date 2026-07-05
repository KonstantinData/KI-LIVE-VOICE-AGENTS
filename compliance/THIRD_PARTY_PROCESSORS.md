# Auftragsverarbeiter-Übersicht
**Rechtsgrundlage:** Art. 28 DSGVO
**Stand:** März 2026

---

## Übersicht aller externen Dienstleister

| Anbieter | Dienst | Sitz | Drittlandtransfer | AVV | SCC | Status |
| --- | --- | --- | --- | --- | --- | --- |
| OpenAI Inc. | Chat, Realtime Voice, Embeddings API | USA | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |
| Resend Inc. | E-Mail-Versand | USA | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |
| Google LLC | Calendar API, OAuth | USA/EU | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |
| Hetzner Online GmbH | Server-Hosting | Deutschland | Nein — EU | ✅ | — | ✅ EU-Hosting |
| Cloudflare Inc. | CDN, DNS, DDoS | USA | Ja — USA | [ ] | [ ] | ⚠️ Ausstehend |

---

## Detailbeschreibung

### OpenAI Inc.
- **Dienst:** Chat, Live Voice, Embeddings — Sprachverarbeitung, Tool-Nutzung, Realtime-Voice und Vektorisierung
- **Daten die übertragen werden:** Chat-Verlauf (pseudonymisiert), System-Prompt, Studio-Wissensinhalte, Nutzeranfragen für semantische Suche
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

1. [ ] OpenAI AVV prüfen und durch Nutzung der API akzeptieren
2. [ ] Google Workspace AVV aktivieren (falls Google Workspace genutzt)
3. [ ] Resend AVV prüfen
4. [ ] Cloudflare AVV prüfen
5. [ ] Alle AVVs in diesem Dokument dokumentieren (Datum, Version)
