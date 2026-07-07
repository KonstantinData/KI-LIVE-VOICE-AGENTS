# Quick Setup for Developers

🇩🇪 [Deutsch](DEVELOPER_SETUP.md) | 🇬🇧 [English](DEVELOPER_SETUP.en.md)

---

## Activate Git Commit Template

To use the Conventional Commits template:

```bash
git config commit.template .gitmessage
```

From now on, `git commit` will automatically open the template with examples.

---

## Documentation Rules

This project follows 5 documentation rules from `CLAUDE.md`:

### 1️⃣ Bilingual READMEs
- Every `README.md` (German) has a `README.en.md` (English)
- At the top of each file: `🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md)`

### 2️⃣ Script Headers
Every Python file starts with:
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

### 3️⃣ Inline Documentation
- Every function: English docstring with Args, Returns
- Complex sections: `# NOTE:` comments for business logic

### 4️⃣ Language Matrix
- **German:** UI text, chat responses
- **English:** Code, comments, docstrings, commits, logs, API

See `LANGUAGE_MATRIX.md` for details.

### 5️⃣ Commit Messages
Format: `<type>(<scope>): <description>`

Examples:
```bash
feat(kea): add secure contact handoff
fix(calendar): refresh token before event
docs(readme): add setup instructions
```

---

## Checklist for New Files

- [ ] Python file has extended module docstring (Rule 2)
- [ ] All functions have English docstrings (Rule 3)
- [ ] Complex sections have `# NOTE:` comments (Rule 3)
- [ ] Code in English, UI text in German (Rule 4)
- [ ] README files in both languages (Rule 1)
- [ ] Commit message follows Conventional Commits (Rule 5)

---

## More Info

- `CLAUDE.md` — Complete rule definitions
- `LANGUAGE_MATRIX.md` — Detailed language matrix
- `RULES_APPLIED.md` — What has been implemented
- `.gitmessage` — Commit message template
