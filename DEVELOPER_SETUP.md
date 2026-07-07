# Quick Setup for Developers

🇩🇪 [Deutsch](DEVELOPER_SETUP.md) | 🇬🇧 [English](DEVELOPER_SETUP.en.md)

---

## Git Commit Template aktivieren

Um die Conventional Commits Vorlage zu nutzen:

```bash
git config commit.template .gitmessage
```

Ab jetzt öffnet `git commit` automatisch die Vorlage mit Beispielen.

---

## Dokumentationsregeln

Dieses Projekt folgt 5 Dokumentationsregeln aus `CLAUDE.md`:

### 1️⃣ Zweisprachige READMEs
- Jede `README.md` (Deutsch) hat eine `README.en.md` (Englisch)
- Oben in jeder Datei: `🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md)`

### 2️⃣ Script-Header
Jede Python-Datei beginnt mit:
```python
"""
Module Name
===========
What:    What is this file?
Does:    What does it do?
Why:     Why does it exist?
Who:     Who uses it?
Depends: What does it depend on?
"""
```

### 3️⃣ Inline-Dokumentation
- Jede Funktion: Englischer Docstring mit Args, Returns
- Komplexe Stellen: `# NOTE:` Kommentare für Business-Logik

### 4️⃣ Sprach-Matrix
- **Deutsch:** UI-Texte, Chat-Antworten
- **Englisch:** Code, Kommentare, Docstrings, Commits, Logs, API

Siehe `LANGUAGE_MATRIX.md` für Details.

### 5️⃣ Commit Messages
Format: `<type>(<scope>): <description>`

Beispiele:
```bash
feat(kea): add secure contact handoff
fix(calendar): refresh token before event
docs(readme): add setup instructions
```

---

## Checkliste für neue Dateien

- [ ] Python-Datei hat erweiterten Modul-Docstring (Regel 2)
- [ ] Alle Funktionen haben englische Docstrings (Regel 3)
- [ ] Komplexe Stellen haben `# NOTE:` Kommentare (Regel 3)
- [ ] Code auf Englisch, UI-Texte auf Deutsch (Regel 4)
- [ ] README-Dateien in beiden Sprachen (Regel 1)
- [ ] Commit-Message folgt Conventional Commits (Regel 5)

---

## Mehr Infos

- `CLAUDE.md` — Vollständige Regel-Definitionen
- `LANGUAGE_MATRIX.md` — Detaillierte Sprach-Matrix
- `RULES_APPLIED.md` — Was bereits umgesetzt wurde
- `.gitmessage` — Commit-Message-Template
