# Compliance-Report — 10.03.2026 19:13 UTC

## Zusammenfassung

| Kennzahl | Wert |
| --- | --- |
| Geprüfte Dateien | 123 |
| Findings gesamt | 21 |
| 🔴 KRITISCH | 2 |
| 🟠 HOCH | 18 |
| 🟡 MITTEL | 1 |
| 🔵 NIEDRIG | 0 |
| ⚪ HINWEIS | 0 |
| Auto-fixable | 0 von 21 |

## 🔴 KRITISCH (2 Findings)

### GOV-2026-0019 — 1.4_RECHTE_DER_BETROFFENEN

**Rechtsgrundlage:** Art. 15 + Art. 20 DSGVO — Auskunft + Datenportabilität
**Fundort:** `src/api/routes/`
**Deadline:** Vor Go-Live — Betroffenenrechte müssen implementiert sein
**Auto-fixable:** Nein

**Problem:**
Endpoint fehlt: Kunden können ihre Daten nicht abrufen (Art. 15/20 DSGVO).

**So muss es sein:**
Implementiere GET /gdpr/export mit vollständiger Funktion: Datenexport als JSON über alle Tabellen (leads, conversations, messages, appointments, followups) gefiltert nach visitor_id oder Lead-ID. Löschung muss kaskadierend über alle Tabellen erfolgen.

**Fix-Beispiel:**

```python
@router.get('/gdpr/export')
async def gdpr_export(visitor_id: str, session=Depends(get_session)):
    # Load all data for this visitor across all tables
    lead = await get_lead_by_visitor(visitor_id, session)
    return {'lead': lead, 'conversations': [...], 'messages': [...]}

@router.delete('/gdpr/delete')
async def gdpr_delete(visitor_id: str, session=Depends(get_session)):
    # Cascade delete or anonymise all visitor data
    await anonymise_visitor(visitor_id, session)
```

**Referenzen:** Art. 15 + Art. 20 DSGVO — Auskunft + Datenportabilität

---

### GOV-2026-0020 — 1.4_RECHTE_DER_BETROFFENEN

**Rechtsgrundlage:** Art. 17 DSGVO — Recht auf Löschung
**Fundort:** `src/api/routes/`
**Deadline:** Vor Go-Live — Betroffenenrechte müssen implementiert sein
**Auto-fixable:** Nein

**Problem:**
Endpoint fehlt: Kunden können ihre Daten nicht löschen lassen (Art. 17 DSGVO).

**So muss es sein:**
Implementiere DELETE /gdpr/delete mit vollständiger Funktion: Datenexport als JSON über alle Tabellen (leads, conversations, messages, appointments, followups) gefiltert nach visitor_id oder Lead-ID. Löschung muss kaskadierend über alle Tabellen erfolgen.

**Fix-Beispiel:**

```python
@router.get('/gdpr/export')
async def gdpr_export(visitor_id: str, session=Depends(get_session)):
    # Load all data for this visitor across all tables
    lead = await get_lead_by_visitor(visitor_id, session)
    return {'lead': lead, 'conversations': [...], 'messages': [...]}

@router.delete('/gdpr/delete')
async def gdpr_delete(visitor_id: str, session=Depends(get_session)):
    # Cascade delete or anonymise all visitor data
    await anonymise_visitor(visitor_id, session)
```

**Referenzen:** Art. 17 DSGVO — Recht auf Löschung

---

## 🟠 HOCH (18 Findings)

### GOV-2026-0001 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/agents/lisa/agent.py` Zeile 135
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 135 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0002 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/agents/lisa/agent.py` Zeile 175
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 175 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0003 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/agents/lisa/tools/extract_lead_data.py` Zeile 185
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 185 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0004 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/api/routes/google_calendar.py` Zeile 54
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 54 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0005 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/api/routes/google_calendar.py` Zeile 93
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 93 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0006 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/api/routes/google_calendar.py` Zeile 140
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 140 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0007 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/api/routes/google_calendar.py` Zeile 166
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 166 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0012 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/api/websocket/chat_handler.py` Zeile 36
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 36 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0013 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/core/google_calendar.py` Zeile 159
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 159 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0014 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/core/memory.py` Zeile 58
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 58 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0015 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/core/memory.py` Zeile 66
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 66 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0016 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/core/memory.py` Zeile 77
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 77 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0017 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/core/memory.py` Zeile 98
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 98 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0018 — 5.1_DATEN_ISOLATION

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. b DSGVO — Zweckbindung
**Fundort:** `src/core/memory.py` Zeile 108
**Deadline:** Vor Go-Live — Datenlecks zwischen Studios verhindern
**Auto-fixable:** Nein

**Problem:**
DB-Query in Zeile 108 ohne erkennbaren studio_id-Filter. Ohne Tenant-Isolation können Daten studio-übergreifend geleakt werden.

**So muss es sein:**
Jede Datenbankabfrage auf mandantenfähigen Tabellen MUSS .where(<Model>.studio_id == studio_id) enthalten.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
result = await session.execute(select(Lead))

# NACHHER (COMPLIANT):
result = await session.execute(
    select(Lead).where(Lead.studio_id == studio_id)
)
```

**Referenzen:** Art. 5 Abs. 1 lit. b DSGVO, Art. 32 DSGVO

---

### GOV-2026-0021 — 1.3_SPEICHERBEGRENZUNG

**Rechtsgrundlage:** Art. 5 Abs. 1 lit. e DSGVO
**Fundort:** `src/api/services/scheduler.py`
**Deadline:** Vor Go-Live implementieren
**Auto-fixable:** Nein

**Problem:**
Kein Retention/Lösch-Mechanismus im Scheduler gefunden. Personenbezogene Daten werden unbegrenzt gespeichert.

**So muss es sein:**
Implementiere automatische Lösch-Jobs im Scheduler:
- Konversations-Rohdaten: 6 Monate → löschen
- Lead-Daten ohne Konversion: 12 Monate → anonymisieren
- Feedback-Daten: 24 Monate
- Events/Audit-Trail: 36 Monate (gesetzliche Aufbewahrungspflicht)

**Fix-Beispiel:**

```python
@scheduler.scheduled_job('cron', hour=2)
async def run_retention_cleanup():
    cutoff = datetime.now(UTC) - timedelta(days=180)
    await delete_old_conversations(cutoff)
    await anonymise_unconverted_leads(cutoff)
```

**Referenzen:** Art. 5 Abs. 1 lit. e DSGVO

---

### GOV-2026-0022 — 2.4_MENSCHLICHE_AUFSICHT

**Rechtsgrundlage:** Art. 14 EU AI Act — Human Oversight
**Fundort:** `src/db/models/studio.py`
**Deadline:** Vor Go-Live — Pflicht ab 02.08.2026
**Auto-fixable:** Nein

**Problem:**
Studio-Model hat kein is_active-Flag. Es gibt keinen Kill-Switch um Lisa für ein Studio sofort zu deaktivieren.

**So muss es sein:**
Studio-Model braucht: is_active: bool = True. Der WebSocket-Handler muss prüfen: if not studio.is_active: reject connection.

**Fix-Beispiel:**

```python
# In src/db/models/studio.py:
is_active: Mapped[bool] = mapped_column(Boolean, default=True)

# In chat_handler.py:
if not studio.is_active:
    await websocket.send_json({"type": "error", "message": "Service vorübergehend nicht verfügbar"})
    await websocket.close()
    return
```

**Referenzen:** Art. 14 EU AI Act

---

### GOV-2026-0023 — 3.4_BIAS_FAIRNESS

**Rechtsgrundlage:** Art. 5 EU AI Act + Art. 22 DSGVO
**Fundort:** `src/agents/lisa/tools/extract_lead_data.py`
**Deadline:** Vor Go-Live
**Auto-fixable:** Nein

**Problem:**
Lead-Score-Berechnung verwendet möglicherweise den Namen als Input. Scoring nach demographischen Merkmalen ist diskriminierend.

**So muss es sein:**
Score nur nach sachlichen Kriterien: Budget, Zeitrahmen, Küchenstil, Raumgröße, Konkretheit der Anfrage. NICHT nach: Name, Sprache, Herkunft, Adresse.

**Fix-Beispiel:**

```python
# COMPLIANT score factors:
# budget_range: +20, timeline: +15, kitchen_style: +10
# room_size: +5, email: +20, phone: +15
# NOT: name origin, language detected, address
```

**Referenzen:** Art. 5 EU AI Act, Art. 22 DSGVO

---

### GOV-2026-0025 — 4.3_INPUT_VALIDATION

**Rechtsgrundlage:** Art. 32 DSGVO + OWASP Top 10 A03
**Fundort:** `src/api/websocket/__init__.py`
**Deadline:** Vor Go-Live beheben
**Auto-fixable:** Nein

**Problem:**
Keine erkennbare Längenbegrenzung für User-Input im Chat-Handler. Unbegrenzte Eingaben ermöglichen Prompt-Injection und DoS.

**So muss es sein:**
Maximale Nachrichtenlänge von 2.000 Zeichen erzwingen. User-Input in <user_message> Tags wrappen für Prompt-Isolation.

**Fix-Beispiel:**

```python
MAX_MESSAGE_LENGTH = 2000

if len(user_message) > MAX_MESSAGE_LENGTH:
    await websocket.send_json({'type': 'error', 'message': 'Nachricht zu lang'})
    return

# Wrap user input to prevent prompt injection
safe_input = f"<user_message>{user_message}</user_message>"
```

**Referenzen:** Art. 32 DSGVO, OWASP A03:2021

---

## 🟡 MITTEL (1 Finding)

### GOV-2026-0024 — 4.4_LOGGING_MONITORING

**Rechtsgrundlage:** Art. 32 DSGVO + Art. 12 EU AI Act
**Fundort:** `src/agents/governance/rules/security.py` Zeile 129
**Deadline:** Innerhalb von 30 Tagen beheben
**Auto-fixable:** Nein

**Problem:**
Log-Statement könnte email address im Klartext ausgeben: 'log.info("lead.created", email=lead.email)\n\n'

**So muss es sein:**
Personenbezogene Daten (Name, E-Mail, Telefon) dürfen NICHT im Klartext in Logs erscheinen. Nur IDs und anonymisierte Werte loggen.

**Fix-Beispiel:**

```python
# VORHER (VERSTOSS):
log.info("lead.created", email=lead.email)

# NACHHER (COMPLIANT):
log.info("lead.created", lead_id=str(lead.id))
```

**Referenzen:** Art. 32 DSGVO, Art. 12 EU AI Act

---

## Nächste Schritte

1. Alle KRITISCH-Findings sofort beheben (vor Go-Live Pflicht)
2. HOCH-Findings vor Go-Live abschließen
3. MITTEL-Findings innerhalb von 30 Tagen
4. `make compliance` nach jeder Änderung erneut ausführen

*Generiert von DataGovernanceAgent am 10.03.2026 19:13 UTC*