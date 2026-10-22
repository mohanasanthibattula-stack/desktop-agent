"""
Base Tool Definition
All agent tools inherit from BaseTool.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    requires_confirmation: bool = False

    def to_schema(self) -> Dict[str, Any]:
        """Return the JSON schema definition for the LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Execute the tool logic and return string output."""
        pass
