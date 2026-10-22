"""
Unit tests for Milestone 6: Action Audit Logger.
Tests log creation, timestamp formatting, event tags, and agent ReAct loop integration.
"""
from pathlib import Path
import pytest

from agent.logger import ActionLogger
from agent.config import load_config
from agent.core import Agent
from agent.providers.base import BaseProvider, ProviderResponse, ToolCall
from agent.tools.registry import ToolRegistry
from agent.tools.time_tool import GetCurrentTimeTool


class MockProvider(BaseProvider):
    def __init__(self):
        super().__init__(model_name="mock")
        self.turns = 0

    def generate(self, messages, tools, system_prompt):
        self.turns += 1
        if self.turns == 1:
            return ProviderResponse(
                text="Checking clock...",
                tool_calls=[ToolCall(name="get_current_time", args={})],
            )
        return ProviderResponse(text="The time is 10:00 AM.", tool_calls=[])


@pytest.fixture
def temp_log(tmp_path: Path):
    return tmp_path / "test_agent.log"


def test_action_logger_events(temp_log):
    logger = ActionLogger(temp_log)
    assert not temp_log.exists()

    logger.log_user_message("Hello Agent")
    logger.log_tool_call("web_search", {"query": "python"})
    logger.log_tool_result("web_search", "Found 3 results")
    logger.log_assistant_response("Here is what I found.")
    logger.log_security_event("Blocked access to C:\\Windows")

    assert temp_log.exists()
    content = temp_log.read_text(encoding="utf-8")

    assert "[USER] Hello Agent" in content
    assert "[TOOL_CALL] web_search(query='python')" in content
    assert "[TOOL_RESULT] web_search -> Found 3 results" in content
    assert "[ASSISTANT] Here is what I found." in content
    assert "[SECURITY] Blocked access to C:\\Windows" in content


def test_agent_loop_logs_automatically(temp_log):
    config = load_config()
    logger = ActionLogger(temp_log)
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    mock_provider = MockProvider()

    agent = Agent(config=config, provider=mock_provider, tools=registry, logger=logger)
    agent.chat("What time is it?")

    assert temp_log.exists()
    content = temp_log.read_text(encoding="utf-8")

    assert "[USER] What time is it?" in content
    assert "[TOOL_CALL] get_current_time()" in content
    assert "[TOOL_RESULT] get_current_time -> Current local time:" in content
    assert "[ASSISTANT] The time is 10:00 AM." in content
