"""
Tool Execution Engine
=====================
What:    Executes tool calls returned by OpenAI function calling.
Does:    Looks up tools in registry, executes them with parameters, returns results, logs execution.
Why:     Agents need to perform actions (book appointments, send emails, etc.) via tools.
Who:     BaseAgent (via process_message), all agents that use tools.
Depends: structlog, src.core.{tool_registry, types}
"""

from typing import Any

import structlog

from src.core.tool_registry import ToolRegistry
from src.core.types import ToolResult

log = structlog.get_logger()


class ToolRunner:
    """
    Führt Tool-Calls des LLM aus.

    Das LLM gibt Tool-Calls zurück. Der ToolRunner:
    1. Sucht das Tool in der Registry
    2. Führt die Tool-Funktion aus
    3. Gibt das Ergebnis an das LLM zurück
    4. Loggt die Ausführung
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> ToolResult:
        """
        Executes a single tool and returns the result.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters as dict
            
        Returns:
            ToolResult with success status and result/error
        """
        tool = self._registry.get(tool_name)

        if tool is None:
            log.warning("tool_runner.not_found", tool=tool_name)
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' nicht gefunden",
            )

        try:
            log.info("tool_runner.execute", tool=tool_name, params=list(parameters.keys()))
            result = await tool.execute(**parameters)
            log.info("tool_runner.success", tool=tool_name)
            return ToolResult(tool_name=tool_name, success=True, result=result)
        except Exception as e:
            log.error("tool_runner.error", tool=tool_name, error=str(e))
            return ToolResult(tool_name=tool_name, success=False, error=str(e))

    async def execute_all(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Executes all tool calls and formats results for the next OpenAI call.
        
        Args:
            tool_calls: List of tool calls with id, name, input
            
        Returns:
            List of OpenAI tool response messages
        """
        results = []
        for call in tool_calls:
            result = await self.execute(call["name"], call["input"])
            content = result.result if result.success else f"Fehler: {result.error}"
            results.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": str(content),
            })
        return results

    def get_tool_definitions(self) -> list[dict]:
        """
        Returns tool definitions in OpenAI's format.
        
        Returns:
            List of tool definitions with name, description, and input_schema
        """
        return self._registry.get_definitions()
