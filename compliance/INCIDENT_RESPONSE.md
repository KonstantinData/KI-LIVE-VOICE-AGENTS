# Incident Response — Datenpannen-Prozess
**Rechtsgrundlage:** Art. 33, 34 DSGVO
**Stand:** März 2026

---

## Meldepflichten

| Situation | Frist | An wen |
| --- | --- | --- |
| Datenpanne mit Risiko für Betroffene | 72 Stunden | Aufsichtsbehörde |
| Datenpanne mit HOHEM Risiko | Unverzüglich | Betroffene Personen direkt |
| Keine Meldepflicht | — | Wenn kein Risiko nachweisbar |

**Zuständige Aufsichtsbehörde (Deutschland):**
Bayerisches Landesamt für Datenschutzaufsicht (BayLDA) — oder je nach Bundesland des Betreibers.

---

## Verantwortlichkeiten

| Rolle | Person | Kontakt |
| --- | --- | --- |
| Meldeverantwortlicher | [Name eintragen] | [E-Mail eintragen] |
| Technischer Ansprechpartner | [Name eintragen] | [E-Mail eintragen] |
| Datenschutzbeauftragter | [falls vorhanden] | [E-Mail eintragen] |

---

## Erkennungs-Checkliste

Mögliche Anzeichen einer Datenpanne:

- [ ] Ungewöhnliche Datenbankzugriffe in den Logs
- [ ] API-Key-Rotation ausgelöst
- [ ] Nutzerbeschwerde über unbekannte Datenweitergabe
- [ ] Sicherheitsscanner meldet Anomalie
- [ ] Multi-Tenant-Fehler im Log (studio_id-Leck)

---

## Reaktionsplan

### Schritt 1: Sofortmaßnahmen (0–4 Stunden)
1. System oder betroffene Komponente abschalten (is_active = False)
2. Umfang des Lecks ermitteln: Welche Daten? Wie viele Betroffene?
3. Logs sichern (unveränderlich)
4. Internes Team informieren

### Schritt 2: Bewertung (4–24 Stunden)
1. Risikoklassifizierung: Hoch / Mittel / Niedrig
2. Entscheidung: Meldepflicht ja/nein?
3. Beweise dokumentieren

### Schritt 3: Meldung (bis 72 Stunden nach Erkenntnis)
Meldung an Aufsichtsbehörde mit:
- Beschreibung der Panne
- Kategorien und ungefähre Anzahl Betroffener
- Wahrscheinliche Folgen
- Ergriffene und geplante Maßnahmen

### Schritt 4: Nachbereitung
1. Ursache beheben
2. Betroffene informieren (falls Hochrisiko)
3. Prozess dokumentieren
4. DPIA aktualisieren

---

## Meldeformular-Template

```
DATENPANNE-MELDUNG — [Datum]

1. Datum und Uhrzeit der Entdeckung: ___________
2. Art der Panne: ___________
3. Betroffene Datenkategorien: ___________
4. Anzahl betroffener Personen (geschätzt): ___________
5. Wahrscheinliche Folgen: ___________
6. Ergriffene Maßnahmen: ___________
7. Kontakt: ___________
```
