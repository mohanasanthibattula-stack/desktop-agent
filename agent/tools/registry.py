"""
Tool Registry
Central hub for registering, discovering, and executing tools.
"""
from typing import Any, Callable, Dict, List, Optional
from .base import BaseTool


class ToolRegistry:
    """Manages the collection of available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool instance."""
        if not tool.name:
            raise ValueError("Tool name cannot be empty.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return list of JSON schemas for all registered tools."""
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(
        self,
        name: str,
        args: Dict[str, Any],
        confirm_callback: Optional[Callable[[BaseTool, Dict[str, Any]], bool]] = None,
    ) -> str:
        """
        Execute a tool safely, handling errors and confirmation checks.
        """
        tool = self.get(name)
        if not tool:
            return f"Error: Tool '{name}' is not registered."

        # Check for user confirmation if required
        if tool.requires_confirmation and confirm_callback:
            allowed = confirm_callback(tool, args)
            if not allowed:
                return f"Action '{name}' was cancelled by the user."

        try:
            return str(tool.execute(**args))
        except TypeError as te:
            return f"Error executing tool '{name}': invalid arguments provided ({te})."
        except Exception as e:
            return f"Error executing tool '{name}': {type(e).__name__}: {str(e)}"
