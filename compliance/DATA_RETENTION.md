# Datenlösch- und Aufbewahrungskonzept
**Rechtsgrundlage:** Art. 5 Abs. 1 lit. e DSGVO
**Stand:** März 2026

---

## Übersicht Löschfristen

| Datenkategorie | Tabelle | Aufbewahrungsfrist | Aktion nach Frist | Status |
| --- | --- | --- | --- | --- |
| Chat-Nachrichten (Rohdaten) | messages | 6 Monate | Löschen | ⏳ Geplant |
| Konversations-Metadaten | conversations | 6 Monate | Löschen | ⏳ Geplant |
| Lead-Daten (ohne Konversion) | leads | 12 Monate | Anonymisieren | ⏳ Geplant |
| Lead-Daten (mit Konversion) | leads | 36 Monate | Anonymisieren | ⏳ Geplant |
| Terminbuchungen | appointments | 36 Monate | Archivieren | ⏳ Geplant |
| Follow-ups | followups | 24 Monate | Löschen | ⏳ Geplant |
| Feedback | feedback | 24 Monate | Anonymisieren | ⏳ Geplant |
| Audit-Trail / Events | events | 36 Monate | Archivieren (gesetzl. Pflicht) | ⏳ Geplant |
| Google Calendar Tokens | berater.calendar_tokens | Bei Disconnect | Löschen | ✅ Implementiert |

---

## Anonymisierungsregeln

Anonymisierung bedeutet: Name, E-Mail, Telefon werden durch Pseudonymwerte ersetzt.
Die statistischen Daten (Score, Budget-Klasse) bleiben erhalten.

```sql
-- Anonymisierung eines Leads nach Ablauf der Frist
UPDATE leads SET
  name = 'Anonymisiert',
  email = NULL,
  phone = NULL,
  profile = jsonb_set(profile, '{name}', '"Anonymisiert"')
WHERE created_at < NOW() - INTERVAL '12 months'
  AND status NOT IN ('appointment', 'customer');
```

---

## Technische Umsetzung (geplant)

Der APScheduler in `src/api/services/scheduler.py` führt täglich um 02:00 Uhr folgende Jobs aus:

- `cleanup_old_conversations()` — Löscht Messages + Conversations älter als 6 Monate
- `anonymise_old_leads()` — Anonymisiert Leads nach 12/36 Monaten
- `cleanup_old_followups()` — Löscht abgeschlossene Follow-ups nach 24 Monaten

**Implementierungsstatus:** Ausstehend — muss vor Go-Live implementiert werden.

---

## Betroffenenrechte (Art. 17 DSGVO — Recht auf Löschung)

Nutzer können jederzeit die Löschung ihrer Daten beantragen via:
`DELETE /gdpr/delete?visitor_id=<id>`

**Implementierungsstatus:** Ausstehend — muss vor Go-Live implementiert werden.
