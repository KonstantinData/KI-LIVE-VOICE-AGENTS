"""
Tool Registry and Discovery
===========================
What:    Registry for all agent tools; provides tool discovery and definition export.
Does:    Registers tools, retrieves them by name, exports definitions in Claude's tool format.
Why:     Centralizes tool management; allows agents to dynamically register and use tools.
Who:     BaseAgent, ToolRunner, all concrete agents.
Depends: structlog
"""


import structlog

log = structlog.get_logger()


class BaseTool:
    """
    Base class for all agent tools.
    
    Subclasses must define:
    - name: Unique tool identifier
    - description: What the tool does (shown to Claude)
    - input_schema: JSON schema for parameters
    - execute(): Async method that performs the tool's action
    """

    name: str = ""
    description: str = ""
    input_schema: dict = {}

    async def execute(self, **kwargs) -> dict:
        """
        Executes the tool. Must be implemented by subclasses.
        
        Args:
            **kwargs: Tool parameters as defined in input_schema
            
        Returns:
            Tool result as dict
        """
        raise NotImplementedError


class ToolRegistry:
    """
    Registers and manages all available tools.

    Each agent registers its own tools at startup.
    Tools are looked up by name during execution.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Registers a tool.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        log.debug("tool_registry.registered", tool=tool.name)

    def get(self, name: str) -> BaseTool | None:
        """
        Returns a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_definitions(self) -> list[dict]:
        """
        Returns all tool definitions in Claude's format.
        
        Returns:
            List of dicts with name, description, input_schema
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    @property
    def names(self) -> list[str]:
        """
        Returns all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
