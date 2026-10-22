"""
Action Audit Logger
Maintains a clean, human-readable audit trail of all agent actions,
tool calls, user confirmations, and security events in data/agent.log.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class ActionLogger:
    """Logs agent events and tool operations to an audit file."""

    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_entry(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level.upper()}] {message}\n"
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            # Avoid crashing the agent if disk logging encounters an IO issue
            print(f"[Warning] Failed to write to audit log: {e}")

    def log_user_message(self, message: str) -> None:
        self._write_entry("USER", message.strip())

    def log_assistant_response(self, response: str) -> None:
        # Log clean first line or summary if response is long
        preview = response.strip().replace("\n", " ")[:200]
        self._write_entry("ASSISTANT", preview)

    def log_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        args_str = ", ".join(f"{k}='{v}'" for k, v in args.items())
        self._write_entry("TOOL_CALL", f"{tool_name}({args_str})")

    def log_tool_result(self, tool_name: str, result: str) -> None:
        result_preview = result.strip().replace("\n", " ")[:200]
        self._write_entry("TOOL_RESULT", f"{tool_name} -> {result_preview}")

    def log_security_event(self, event: str) -> None:
        self._write_entry("SECURITY", event)

    def log_system_event(self, message: str) -> None:
        self._write_entry("SYSTEM", message)
