# Einwilligungstext-Versionshistorie
**Rechtsgrundlage:** Art. 7 DSGVO
**Stand:** März 2026

---

## Zweck dieses Dokuments

Jede Änderung am Einwilligungstext muss hier dokumentiert werden.
Bei einer Datenpanne oder Aufsichtsbehörden-Anfrage muss nachweisbar sein:
**Wann wurde welchem Text zugestimmt?**

---

## Aktuelle Version

### Version 1.0 — [Datum eintragen — noch nicht veröffentlicht]

**Status:** Entwurf — noch nicht im Einsatz

**Einwilligungstext (DE):**

> Ich bin damit einverstanden, dass meine Eingaben im Chat von einer Künstlichen Intelligenz
> (KI-Assistent "Lisa") verarbeitet werden, um meine Anfrage zu beantworten und einen
> Beratungstermin zu ermöglichen.
>
> **Was gespeichert wird:** Chat-Verlauf, freiwillig angegebene Kontaktdaten (Name, E-Mail,
> Telefon), Budgetrahmen und Zeitplanung.
>
> **Wie lange:** Chat-Verläufe werden nach 6 Monaten gelöscht. Kontaktdaten nach 12 Monaten
> anonymisiert (sofern kein Kundenverhältnis entsteht).
>
> **Meine Rechte:** Auskunft, Löschung, Widerspruch jederzeit möglich unter [E-Mail des Studios].
>
> **Widerruf:** Ich kann meine Einwilligung jederzeit für die Zukunft widerrufen.
>
> Weitere Informationen: [Link zur Datenschutzerklärung]

**Text-Hash (SHA256):** [wird bei Aktivierung berechnet und eingetragen]
**Aktiviert am:** [noch nicht aktiviert]
**Deaktiviert am:** —

---

## Änderungshistorie

| Version | Datum | Änderung | Grund |
| --- | --- | --- | --- |
| 1.0 | [ausstehend] | Initiale Version | Go-Live Vorbereitung |

---

## Implementierungshinweis

In der Datenbank muss eine `consents`-Tabelle existieren:

```sql
CREATE TABLE consents (
  id UUID PRIMARY KEY,
  visitor_id VARCHAR(255) NOT NULL,
  consent_version VARCHAR(10) NOT NULL,  -- z.B. "1.0"
  consent_text_hash VARCHAR(64) NOT NULL, -- SHA256 des Textes
  granted_at TIMESTAMP WITH TIME ZONE NOT NULL,
  ip_address VARCHAR(45),               -- Optional, für Nachweis
  user_agent TEXT                       -- Optional
);
```

**Implementierungsstatus:** Ausstehend — muss vor Go-Live implementiert werden.
