"""
Unit tests for Milestone 5: Shell Execution Tool.
Tests killswitch gating, working directory validation, user confirmation, and command execution.
"""
from pathlib import Path
from unittest.mock import patch
import pytest

from agent.tools.registry import ToolRegistry
from agent.tools.shell import ExecuteCommandTool


@pytest.fixture
def sandbox_env(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    allowed_folders = [sandbox]
    return sandbox, allowed_folders


def test_shell_tool_disabled_by_default(sandbox_env):
    sandbox, allowed = sandbox_env
    # enabled = False (default configuration)
    tool = ExecuteCommandTool(enabled=False, allowed_folders=allowed)

    res = tool.execute("dir")
    assert "Execution Blocked:" in res
    assert "DISABLED in config.yaml" in res


def test_shell_tool_outside_sandbox_blocked(sandbox_env):
    sandbox, allowed = sandbox_env
    tool = ExecuteCommandTool(enabled=True, allowed_folders=allowed)

    # Attempt to run inside an unapproved directory
    res = tool.execute("dir", working_directory="C:\\Windows\\System32")
    assert "Security Error:" in res
    assert "outside the approved sandbox" in res


def test_shell_tool_declined_by_user(sandbox_env):
    sandbox, allowed = sandbox_env
    tool = ExecuteCommandTool(enabled=True, allowed_folders=allowed)

    # User declines [y/N]
    with patch("builtins.input", return_value="n"):
        res = tool.execute("Get-Process")
        assert "declined by the user" in res.lower()


def test_shell_tool_approved_by_user(sandbox_env):
    sandbox, allowed = sandbox_env
    tool = ExecuteCommandTool(enabled=True, allowed_folders=allowed)

    # User approves [y/N]
    with patch("builtins.input", return_value="yes"):
        res = tool.execute("Write-Output 'Antigravity Shell Test'")
        assert "exit code 0" in res
        assert "Antigravity Shell Test" in res


def test_shell_tool_registration():
    registry = ToolRegistry()
    registry.register(ExecuteCommandTool(enabled=False, allowed_folders=[Path("sandbox")]))

    schemas = registry.get_schemas()
    names = [s["name"] for s in schemas]
    assert "execute_command" in names
