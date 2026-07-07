# Language Matrix / Sprach-Matrix

🇩🇪 [Deutsch](LANGUAGE_MATRIX.md) | 🇬🇧 [English](LANGUAGE_MATRIX.en.md)

---

## Which language is used where?

This table clearly defines which language is used in which context:

| Area | Language | Rationale |
| ---- | -------- | --------- |
| **UI Text** (Widget) | 🇩🇪 German | Customer-facing, German-speaking target audience |
| **Chat Responses** (Lisa, Max, Anna, Tom, Sara) | 🇩🇪 German | Customer-facing, natural conversation |
| **READMEs** | 🇩🇪 German + 🇬🇧 English | Both versions for international collaboration |
| **Code** (Variables, Functions, Classes) | 🇬🇧 English | Universally readable, software development standard |
| **Comments & Docstrings** | 🇬🇧 English | Universally readable, international developers |
| **Commit Messages** | 🇬🇧 English | Conventional Commits standard |
| **Log Entries** | 🇬🇧 English | Tool-compatible, machine-readable |
| **Error Messages** (API) | 🇬🇧 English | Standard, international clients |
| **Environment Variables** | 🇬🇧 English | SCREAMING_SNAKE_CASE standard |
| **Database** (Tables, Columns) | 🇬🇧 English | Standard, SQL conventions |
| **API Endpoints** | 🇬🇧 English | REST standard, international clients |

---

## Examples

### ✅ Correct

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

**Chat Response (German):**
```
Gerne! Ich habe für Sie einen Termin am Mittwoch, 15. Mai um 16:00 Uhr 
bei unserem Küchenplaner Max reserviert. Passt Ihnen das?
```

### ❌ Wrong

```python
# HINWEIS: Der bevorzugte_zeitpunkt des Kunden ist Freitext.
async def finde_verfuegbaren_slot(bevorzugter_zeitpunkt: str, berater_id: UUID) -> datetime:
    """
    Findet den nächsten verfügbaren Termin.
    """
    # Implementierung...
```

---

## Bilingual READMEs

Every `README.md` (German) has a `README.en.md` (English).

**At the top of each file:**
```markdown
🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md)
```

**Applies to:**
- Project root: `README.md` + `README.en.md`
- All subdirectories with their own README
- Documentation files (e.g., `CLAUDE.md` → `CLAUDE.en.md`)

---

## Commit Messages (Conventional Commits)

**Format:** `<type>(<scope>): <description>`

**Always in English:**

```bash
✅ feat(kea): add secure contact handoff
✅ fix(calendar): refresh token before creating event
✅ docs(readme): add bilingual setup instructions

❌ feat(kea): Füge sichere CRM Übergabe hinzu
❌ fix(kalender): Token vor Event-Erstellung erneuern
```

**Types:**
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `refactor:` — Code change that neither fixes a bug nor adds a feature
- `test:` — Adding or modifying tests
- `chore:` — Build, dependencies, config changes
- `style:` — Formatting, no logic change
- `perf:` — Performance improvement

---

## Why this division?

### German for customer contact
- **UI & Chat:** German target audience (kitchen studios in Germany/Austria/Switzerland)
- **Natural language:** Customers expect German conversation

### English for code & technology
- **International standards:** Code is universally readable
- **Open source ready:** Project can be shared internationally
- **Tool compatibility:** Linters, debuggers, CI/CD expect English logs
- **Developer community:** International collaboration possible

### Both languages for documentation
- **README:** German version for local partners, English for international developers
- **Flexibility:** Project can grow in both directions

---

## Configuration

### Activate Git Commit Template

```bash
git config commit.template .gitmessage
```

Now `git commit` automatically opens the template with Conventional Commits examples.

---

## Questions?

If unclear: See `CLAUDE.md` Rule 4 or ask the team.
