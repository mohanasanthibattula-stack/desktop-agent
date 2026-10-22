"""
Anthropic Claude Model Provider
Integrates with the official anthropic SDK.
"""
import time
from typing import Any, Dict, List, Optional

from .base import BaseProvider, ProviderResponse, ToolCall


class ClaudeProvider(BaseProvider):
    """Anthropic Claude provider implementing BaseProvider."""

    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-latest", temperature: float = 0.2):
        super().__init__(model_name=model_name, temperature=temperature)
        self.api_key = api_key
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError(
                "The 'anthropic' package is required. "
                "Install it using: pip install anthropic"
            )

    def _convert_tool_schemas(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert standard JSON schemas into Anthropic tool format."""
        claude_tools = []
        for t in tools:
            claude_tools.append({
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
            })
        return claude_tools

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert universal message history into Anthropic format."""
        anthropic_messages: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")

            if role == "tool":
                # In Anthropic, tool results are sent as a user turn containing tool_result blocks
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("call_id", "default_id"),
                            "content": str(msg.get("content", "")),
                        }
                    ],
                })
            elif role == "assistant":
                content_blocks = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": str(msg["content"])})
                
                if "tool_calls" in msg and msg["tool_calls"]:
                    for tc in msg["tool_calls"]:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc.get("call_id", f"call_{tc['name']}"),
                            "name": tc["name"],
                            "input": tc.get("args", {}),
                        })

                anthropic_messages.append({
                    "role": "assistant",
                    "content": content_blocks if content_blocks else [{"type": "text", "text": ""}],
                })
            else:
                # Normal user message
                anthropic_messages.append({
                    "role": "user",
                    "content": str(msg.get("content", "")),
                })

        return anthropic_messages

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str,
    ) -> ProviderResponse:
        """Call Claude API with retries on rate limits."""
        claude_tools = self._convert_tool_schemas(tools)
        anthropic_messages = self._convert_messages(messages)

        max_retries = 4
        delay = 2.0

        for attempt in range(max_retries):
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "max_tokens": 4096,
                    "temperature": self.temperature,
                    "system": system_prompt,
                    "messages": anthropic_messages,
                }
                if claude_tools:
                    kwargs["tools"] = claude_tools

                response = self.client.messages.create(**kwargs)

                extracted_text: Optional[str] = None
                tool_calls: List[ToolCall] = []

                for block in response.content:
                    if block.type == "text":
                        extracted_text = (extracted_text or "") + block.text
                    elif block.type == "tool_use":
                        tool_calls.append(
                            ToolCall(
                                name=block.name,
                                args=block.input,
                                call_id=block.id,
                            )
                        )

                return ProviderResponse(
                    text=extracted_text,
                    tool_calls=tool_calls,
                    raw_response=response,
                )

            except Exception as e:
                err_str = str(e)
                is_transient = any(
                    token in err_str
                    for token in ["429", "rate_limit", "529", "overloaded", "503", "500"]
                )
                if is_transient and attempt < max_retries - 1:
                    print(
                        f"\n   [Notice] Claude temporarily busy. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise RuntimeError(f"Claude API error: {err_str}") from e

        raise RuntimeError("Failed to generate response from Claude after maximum retries.")
