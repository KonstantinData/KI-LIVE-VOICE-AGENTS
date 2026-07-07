"""
Beispiel-Tool als Vorlage für eigene Tools.

So erstellst du ein neues Tool:
1. Kopiere diese Datei und benenne sie nach dem Tool.
2. Benenne die Klasse um
3. Setze name, description und input_schema
4. Implementiere die execute()-Methode
5. Registriere das Tool in agent.py: registry.register(MeinTool())
"""

from typing import Any

from src.core.tool_registry import BaseTool


class ExampleTool(BaseTool):
    """
    Beispiel-Tool: Gibt eine einfache Begrüßung zurück.

    In echten Tools würde hier z.B. eine DB-Abfrage,
    ein API-Call oder eine Kalender-Operation stehen.
    """

    name = "example_tool"
    description = "Gibt eine Begrüßung für den angegebenen Namen zurück."
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Der Name der Person, die gegrüßt werden soll.",
            }
        },
        "required": ["name"],
    }

    async def execute(self, **kwargs: Any) -> dict:
        """Führt das Tool aus und gibt das Ergebnis zurück."""
        name = str(kwargs.get("name", "Gast"))
        return {
            "success": True,
            "message": f"Hallo {name}! Willkommen bei uns.",
        }
