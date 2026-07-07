# Language Matrix / Sprach-Matrix

🇩🇪 [Deutsch](LANGUAGE_MATRIX.md) | 🇬🇧 [English](LANGUAGE_MATRIX.en.md)

---

## Welche Sprache wird wo verwendet?

Diese Tabelle definiert klar, welche Sprache in welchem Kontext verwendet wird:

| Bereich | Sprache | Begründung |
| ------- | ------- | ---------- |
| **UI-Texte** (Widget) | 🇩🇪 Deutsch | Kundenseitig, deutschsprachige Zielgruppe |
| **Chat-Antworten** (Lisa, Max, Anna, Tom, Sara) | 🇩🇪 Deutsch | Kundenseitig, natürliche Konversation |
| **READMEs** | 🇩🇪 Deutsch + 🇬🇧 Englisch | Beide Versionen für internationale Zusammenarbeit |
| **Code** (Variablen, Funktionen, Klassen) | 🇬🇧 Englisch | Universell lesbar, Standard in der Softwareentwicklung |
| **Kommentare & Docstrings** | 🇬🇧 Englisch | Universell lesbar, internationale Entwickler |
| **Commit Messages** | 🇬🇧 Englisch | Conventional Commits Standard |
| **Log-Einträge** | 🇬🇧 Englisch | Tool-kompatibel, maschinenlesbar |
| **Error Messages** (API) | 🇬🇧 Englisch | Standard, internationale Clients |
| **Environment Variables** | 🇬🇧 Englisch | SCREAMING_SNAKE_CASE Standard |
| **Datenbank** (Tabellen, Spalten) | 🇬🇧 Englisch | Standard, SQL-Konventionen |
| **API Endpoints** | 🇬🇧 Englisch | REST-Standard, internationale Clients |

---

## Beispiele

### ✅ Richtig

```python
# NOTE: The customer's preferred_datetime is free text (e.g., "Wednesday 4pm").
# We map it to the next available business slot.
async def find_available_slot(preferred_datetime: str, berater_id: UUID) -> datetime:
    """
    Finds the next available appointment slot.
    
    Args:
        preferred_datetime: Customer's preferred time as free text
        berater_id: ID of the consultant
        
    Returns:
        Next available datetime slot
    """
    # Implementation...
```

**Chat-Antwort (Deutsch):**
```
Gerne! Ich habe für Sie einen Termin am Mittwoch, 15. Mai um 16:00 Uhr 
bei unserem Küchenplaner Max reserviert. Passt Ihnen das?
```

### ❌ Falsch

```python
# HINWEIS: Der bevorzugte_zeitpunkt des Kunden ist Freitext.
async def finde_verfuegbaren_slot(bevorzugter_zeitpunkt: str, berater_id: UUID) -> datetime:
    """
    Findet den nächsten verfügbaren Termin.
    """
    # Implementierung...
```

---

## Zweisprachige READMEs

Jede `README.md` (Deutsch) hat eine `README.en.md` (Englisch).

**Oben in jeder Datei:**
```markdown
🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md)
```

**Gilt für:**
- Projekt-Root: `README.md` + `README.en.md`
- Alle Unterverzeichnisse mit eigener README
- Dokumentationsdateien (z.B. `CLAUDE.md` → `CLAUDE.en.md`)

---

## Commit Messages (Conventional Commits)

**Format:** `<type>(<scope>): <description>`

**Immer auf Englisch:**

```bash
✅ feat(kea): add secure contact handoff
✅ fix(calendar): refresh token before creating event
✅ docs(readme): add bilingual setup instructions

❌ feat(kea): Füge sichere CRM Übergabe hinzu
❌ fix(kalender): Token vor Event-Erstellung erneuern
```

**Typen:**
- `feat:` — Neue Funktionalität
- `fix:` — Bugfix
- `docs:` — Nur Dokumentation
- `refactor:` — Kein neues Feature, kein Fix
- `test:` — Tests hinzugefügt/geändert
- `chore:` — Build, Dependencies, Config
- `style:` — Formatierung, keine Logik-Änderung
- `perf:` — Performance-Verbesserung

---

## Warum diese Aufteilung?

### Deutsch für Kundenkontakt
- **UI & Chat:** Deutsche Zielgruppe (Küchenstudios in Deutschland/Österreich/Schweiz)
- **Natürliche Sprache:** Kunden erwarten deutsche Konversation

### Englisch für Code & Technik
- **Internationale Standards:** Code ist universell lesbar
- **Open Source Ready:** Projekt kann international geteilt werden
- **Tool-Kompatibilität:** Linter, Debugger, CI/CD erwarten englische Logs
- **Entwickler-Community:** Internationale Zusammenarbeit möglich

### Beide Sprachen für Dokumentation
- **README:** Deutsche Version für lokale Partner, englische für internationale Entwickler
- **Flexibilität:** Projekt kann in beide Richtungen wachsen

---

## Konfiguration

### Git Commit Template aktivieren

```bash
git config commit.template .gitmessage
```

Jetzt öffnet `git commit` automatisch die Vorlage mit Conventional Commits Beispielen.

---

## Fragen?

Bei Unklarheiten: Siehe `CLAUDE.md` Regel 4 oder frage im Team.
