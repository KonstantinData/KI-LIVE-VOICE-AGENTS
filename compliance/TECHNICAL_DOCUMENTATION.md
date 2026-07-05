# Technische Dokumentation — KI-Mitarbeiter-Team
**Rechtsgrundlage:** Art. 11 + Annex IV EU AI Act
**Stand:** März 2026

---

## 1. Systemübersicht

**Systemname:** KI-Mitarbeiter-Team (Pilotphase: Lisa)
**Architektur:** Multi-Agent-System mit FastAPI-Backend, PostgreSQL-Datenbank, React-Widget

**Komponenten:**
| Komponente | Technologie | Version | Zweck |
| --- | --- | --- | --- |
| Agent-Core | Python 3.12 | — | Basisklasse + Orchestrierung |
| LLM | OpenAI | gpt-4o-mini | Sprachverarbeitung und Tool Use |
| Embeddings | OpenAI | text-embedding-3-small | Semantische Suche |
| Datenbank | PostgreSQL 16 + pgvector | — | Datenspeicherung |
| API | FastAPI | 0.115+ | REST + WebSocket |
| Widget | React + Vite | — | Chat-UI |
| Dashboard | React + Tailwind | — | Admin-Oberfläche |

---

## 2. Datenflüsse

```
Endkunde (Browser)
  │ WebSocket (wss://)
  ▼
FastAPI Backend (Hetzner, DE)
  │ HTTPS
  ├─► OpenAI API (USA) — Chat, Live Voice, Embeddings für Wissensbasis
  └─► PostgreSQL (Hetzner, DE) — Datenspeicherung
```

---

## 3. Verwendete Modelle

| Modell | Anbieter | Zweck | Drittland |
| --- | --- | --- | --- |
| gpt-4o-mini | OpenAI | Chat-Antworten + Tool Use | USA (SCC) |
| text-embedding-3-small | OpenAI | Vektorsuche in Wissensbasis | USA (SCC) |

---

## 4. Leistungsmetriken (zu befüllen nach Go-Live)

| Metrik | Zielwert | Aktuell |
| --- | --- | --- |
| Lead-Qualifizierungsrate | > 30% | TBD |
| Terminbuchungsrate | > 15% | TBD |
| Durchschnittliche Gesprächsdauer | < 10 min | TBD |
| Kundenzufriedenheit (Feedback) | > 4/5 | TBD |

---

## 5. Bekannte Limitierungen

- Lisa kann nur auf Basis der konfigurierten Wissensbasis antworten; Informationen außerhalb davon können zu Halluzinationen führen
- Lead-Scoring ist heuristisch; keine statistische Validierung
- Google Calendar Integration erfordert manuelle OAuth-Verbindung pro Berater

---

## 6. Kontakt

**Verantwortlicher:** [Name, E-Mail eintragen]
**Datenschutzbeauftragter:** [falls vorhanden — Name, E-Mail eintragen]
