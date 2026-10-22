"""
Shell Command Execution Tool
Enables the agent to run PowerShell commands on Windows when explicitly enabled in config.yaml.
Strictly gated by default: disabled unless security.shell_enabled is True,
and ALWAYS prompts the user with [y/N] confirmation before executing any command.
"""
from pathlib import Path
import subprocess
from typing import Any, List, Optional

from agent.safety.confirmation import ask_confirmation
from agent.safety.guardrails import SecurityError, resolve_and_validate_path
from .base import BaseTool


class ExecuteCommandTool(BaseTool):
    """Tool to run PowerShell commands on the host Windows machine."""

    name = "execute_command"
    description = (
        "Executes a PowerShell command in the terminal on the user's Windows machine. "
        "DISABLED by default for safety. Only available if 'shell_enabled: true' is set in config.yaml. "
        "ALWAYS requires explicit user confirmation [y/N] before running."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The exact PowerShell command line to execute.",
            },
            "working_directory": {
                "type": "string",
                "description": "Directory to execute the command within (must be inside allowed sandbox; defaults to sandbox root).",
            },
        },
        "required": ["command"],
    }
    requires_confirmation = True

    def __init__(self, enabled: bool, allowed_folders: List[Path]):
        self.enabled = enabled
        self.allowed_folders = allowed_folders

    def execute(self, command: str, working_directory: str = "", **kwargs: Any) -> str:
        # Check global killswitch
        if not self.enabled:
            return (
                "Execution Blocked: Shell execution is currently DISABLED in config.yaml "
                "('security.shell_enabled: false'). The user must change this setting to true "
                "in config.yaml to allow command execution."
            )

        clean_cmd = command.strip()
        if not clean_cmd:
            return "Error: Command cannot be empty."

        # Validate working directory is within allowed sandbox
        try:
            cwd_path = resolve_and_validate_path(working_directory or "", self.allowed_folders)
        except SecurityError as se:
            return f"Security Error: {str(se)}"

        # Explicit user confirmation [y/N]
        prompt_msg = (
            f"EXECUTE SHELL COMMAND:\n"
            f"    Command: {clean_cmd}\n"
            f"    Folder : {cwd_path}\n"
            f"    System : Windows PowerShell"
        )
        confirmed = ask_confirmation(prompt_msg)
        if not confirmed:
            return f"Action cancelled: Execution of command '{clean_cmd}' was declined by the user."

        try:
            # Execute command using PowerShell with 30s timeout
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", clean_cmd],
                cwd=str(cwd_path),
                capture_output=True,
                text=True,
                timeout=30,
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            exit_code = result.returncode

            output_lines = [f"Command finished with exit code {exit_code}"]
            if stdout:
                output_lines.append(f"\n[Standard Output]:\n{stdout}")
            if stderr:
                output_lines.append(f"\n[Standard Error]:\n{stderr}")
            if not stdout and not stderr:
                output_lines.append("\n(No output produced)")

            return "\n".join(output_lines)

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after 30 seconds."
        except Exception as e:
            return f"Error executing shell command: {type(e).__name__}: {str(e)}"
