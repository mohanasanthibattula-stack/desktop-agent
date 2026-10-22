"""
Core Agent Loop
Orchestrates reasoning, tool execution, safety checks, and step/timeout limits.
"""
import time
from typing import Any, Callable, Dict, List, Optional

from .config import AppConfig
from .logger import ActionLogger
from .prompt import get_system_prompt
from .providers.base import BaseProvider
from .safety.confirmation import get_tool_confirmation_callback
from .tools.registry import ToolRegistry


class Agent:
    """Autonomous ReAct agent loop."""

    def __init__(
        self,
        config: AppConfig,
        provider: BaseProvider,
        tools: ToolRegistry,
        logger: Optional[ActionLogger] = None,
    ):
        self.config = config
        self.provider = provider
        self.tools = tools
        self.logger = logger or ActionLogger(config.log_path)
        self.system_prompt = get_system_prompt(config.allowed_folders)
        self.messages: List[Dict[str, Any]] = []
        self.confirmation_callback = (
            get_tool_confirmation_callback() if config.require_confirmation else None
        )

    def chat(
        self,
        user_input: str,
        on_status_update: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Run the ReAct agent loop for a user request.
        
        Args:
            user_input: The text prompt from the user.
            on_status_update: Optional callback to notify UI about tool calls or progress.
        """
        # Append user message to conversation history
        self.messages.append({"role": "user", "content": user_input})
        if self.logger:
            self.logger.log_user_message(user_input)

        step_count = 0
        start_time = time.time()

        while True:
            # Check maximum step limit
            if step_count >= self.config.max_steps:
                warning = f"\n⚠️ [Stopped] Reached maximum limit of {self.config.max_steps} steps."
                self.messages.append({"role": "assistant", "content": warning})
                if self.logger:
                    self.logger.log_system_event(f"Reached step limit ({self.config.max_steps})")
                return warning

            # Check timeout limit
            elapsed = time.time() - start_time
            if elapsed > self.config.timeout_seconds:
                warning = f"\n⚠️ [Stopped] Task timed out after {int(elapsed)} seconds."
                self.messages.append({"role": "assistant", "content": warning})
                if self.logger:
                    self.logger.log_system_event(f"Task timed out after {int(elapsed)}s")
                return warning

            if on_status_update:
                on_status_update("Thinking...")

            # Query the active provider
            try:
                response = self.provider.generate(
                    messages=self.messages,
                    tools=self.tools.get_schemas(),
                    system_prompt=self.system_prompt,
                )
            except Exception as e:
                err_msg = f"Model provider error: {str(e)}"
                self.messages.append({"role": "assistant", "content": err_msg})
                if self.logger:
                    self.logger.log_system_event(f"Provider error: {str(e)}")
                return err_msg

            # If the model requested tool calls, execute them
            if response.has_tool_calls:
                # Save assistant's intent and tool calls to history
                self.messages.append({
                    "role": "assistant",
                    "content": response.text or "",
                    "tool_calls": [
                        {"name": tc.name, "args": tc.args, "call_id": tc.call_id}
                        for tc in response.tool_calls
                    ],
                    "raw_response": response.raw_response,
                })

                for tc in response.tool_calls:
                    if on_status_update:
                        args_preview = ", ".join(f"{k}={v}" for k, v in tc.args.items())
                        on_status_update(f"Running tool: {tc.name}({args_preview})")

                    if self.logger:
                        self.logger.log_tool_call(tc.name, tc.args)

                    # Execute tool via registry (with confirmation check if required)
                    tool_output = self.tools.execute(
                        name=tc.name,
                        args=tc.args,
                        confirm_callback=self.confirmation_callback,
                    )

                    if self.logger:
                        self.logger.log_tool_result(tc.name, tool_output)

                    # Feed tool output back into history
                    self.messages.append({
                        "role": "tool",
                        "tool_name": tc.name,
                        "content": tool_output,
                        "call_id": tc.call_id,
                    })

                step_count += 1
                # Loop continues so model can observe tool outputs
            else:
                # No tool calls: model has provided its final response
                final_text = response.text or "Task completed."
                self.messages.append({
                    "role": "assistant",
                    "content": final_text,
                    "raw_response": response.raw_response,
                })
                if self.logger:
                    self.logger.log_assistant_response(final_text)
                return final_text
