.PHONY: setup dev test lint format migration migrate seed compliance compliance-fix

# Komplettes Setup
setup:
	chmod +x setup.sh && ./setup.sh

# venv aktivieren (muss mit 'source' aufgerufen werden)
# Nutze: source venv/bin/activate

# Entwicklungsserver starten
dev:
	source venv/bin/activate && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Tests
test:
	source venv/bin/activate && pytest tests/ -v --cov=src

# Linting
lint:
	source venv/bin/activate && ruff check src/ tests/

# Format
format:
	source venv/bin/activate && ruff format src/ tests/

# Datenbank-Migration erstellen
migration:
	source venv/bin/activate && alembic revision --autogenerate -m "$(msg)"

# Migration ausführen
migrate:
	source venv/bin/activate && alembic upgrade head

# Seed-Daten laden
seed:
	source venv/bin/activate && python -m src.db.seed

# Governance / Compliance-Scan (DSGVO + EU AI Act)
compliance:
	source venv/bin/activate && python -m src.agents.governance.agent --scan-all --report

# Governance auto-fix (nur auto-fixable findings)
compliance-fix:
	source venv/bin/activate && python -m src.agents.governance.agent --auto-fix
