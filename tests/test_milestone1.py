"""
Unit tests for Milestone 1 components.
Verifies config loading, tool registry, and agent loop mechanics with a mock provider.
"""
from pathlib import Path
from agent.config import load_config
from agent.tools.registry import ToolRegistry
from agent.tools.time_tool import GetCurrentTimeTool
from agent.providers.base import BaseProvider, ProviderResponse, ToolCall
from agent.core import Agent


class MockProvider(BaseProvider):
    """Mock provider to test the ReAct loop deterministically without external API calls."""

    def __init__(self):
        super().__init__(model_name="mock-model")
        self.call_count = 0

    def generate(self, messages, tools, system_prompt):
        self.call_count += 1
        if self.call_count == 1:
            # First turn: call get_current_time
            return ProviderResponse(
                text="Checking the clock for you...",
                tool_calls=[ToolCall(name="get_current_time", args={}, call_id="call_1")],
            )
        else:
            # Second turn: provide final answer based on tool output
            last_msg = messages[-1]
            return ProviderResponse(
                text=f"The current time was successfully fetched: {last_msg.get('content')}",
                tool_calls=[],
            )


def test_config_loads_defaults():
    config = load_config()
    assert config.provider in ("gemini", "claude")
    assert config.max_steps > 0
    assert len(config.allowed_folders) >= 1
    assert all(isinstance(f, Path) for f in config.allowed_folders)


def test_time_tool_execution():
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    
    schemas = registry.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "get_current_time"

    output = registry.execute("get_current_time", {})
    assert "Current local time:" in output


def test_agent_loop_with_tool_call():
    config = load_config()
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    mock_provider = MockProvider()

    agent = Agent(config=config, provider=mock_provider, tools=registry)
    result = agent.chat("What time is it?")

    assert mock_provider.call_count == 2
    assert "The current time was successfully fetched" in result
    assert "Current local time:" in result


def test_claude_tool_conversion():
    from agent.providers.claude import ClaudeProvider
    claude = ClaudeProvider(api_key="dummy_key")
    tool = GetCurrentTimeTool()
    schemas = [tool.to_schema()]
    converted = claude._convert_tool_schemas(schemas)
    assert len(converted) == 1
    assert converted[0]["name"] == "get_current_time"
    assert "input_schema" in converted[0]


def test_gemini_tool_conversion():
    from agent.providers.gemini import GeminiProvider
    gemini = GeminiProvider(api_key="dummy_key")
    tool = GetCurrentTimeTool()
    schemas = [tool.to_schema()]
    converted = gemini._convert_tool_schemas(schemas)
    assert len(converted) == 1


def test_gemini_thought_signature_preservation():
    from google.genai import types
    from agent.providers.gemini import GeminiProvider

    gemini = GeminiProvider(api_key="dummy_key")

    # Simulate a Gemini model turn with a thought and a function call carrying a thought_signature
    mock_part_thought = types.Part(thought=True, text="Let me check the time.")
    mock_part_call = types.Part(
        thought_signature=b"test_thought_signature_bytes",
        function_call=types.FunctionCall(name="get_current_time", args={})
    )
    mock_content = types.Content(role="model", parts=[mock_part_thought, mock_part_call])
    mock_candidate = types.Candidate(content=mock_content)
    mock_response = types.GenerateContentResponse(candidates=[mock_candidate])

    messages = [
        {"role": "user", "content": "What time is it?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"name": "get_current_time", "args": {}, "call_id": "call_1"}],
            "raw_response": mock_response,
        },
        {"role": "tool", "tool_name": "get_current_time", "content": "12:00 PM", "call_id": "call_1"},
    ]

    converted = gemini._convert_messages(messages)

    # Converted turns: 1 user, 1 model (with original parts/signatures intact), 1 user (with function_response)
    assert len(converted) == 3
    assert converted[0].role == "user"
    assert converted[1].role == "model"
    assert converted[1].parts[1].thought_signature == b"test_thought_signature_bytes"
    assert converted[2].role == "user"
    assert converted[2].parts[0].function_response.name == "get_current_time"


