"""
Abstract Base Provider
Defines a unified interface for LLM backends (Gemini, Claude, etc.)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """Represents a request from the model to execute a tool."""
    name: str
    args: Dict[str, Any]
    call_id: str = ""


@dataclass
class ProviderResponse:
    """Normalized response from any model provider."""
    text: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Any = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseProvider(ABC):
    """Abstract interface all model providers must implement."""

    def __init__(self, model_name: str, temperature: float = 0.2):
        self.model_name = model_name
        self.temperature = temperature

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str,
    ) -> ProviderResponse:
        """
        Send messages and tool definitions to the LLM and return a standardized response.
        
        Args:
            messages: List of message dictionaries with 'role' ('user', 'assistant', 'tool') 
                      and 'content'.
            tools: List of tool schemas in standard JSON Schema format.
            system_prompt: System instruction for the model.
        """
        pass
