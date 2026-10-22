"""
User Confirmation Guardrails
Prompts the user for approval before risky actions execute.
"""
from typing import Any, Callable, Dict


def ask_confirmation(prompt_text: str) -> bool:
    """
    Prompt the user with standard [y/N] in the terminal.
    Defaults to No if Enter is pressed without typing 'y' or 'yes'.
    """
    print(f"\n[!] [ACTION REQUIRES APPROVAL]")
    print(f"    {prompt_text}")
    try:
        choice = input("    Proceed? [y/N]: ").strip().lower()
        if choice in ("y", "yes"):
            print("    [+] Approved.\n")
            return True
        else:
            print("    [-] Denied.\n")
            return False
    except (KeyboardInterrupt, EOFError):
        print("\n    [-] Cancelled.\n")
        return False


def get_tool_confirmation_callback() -> Callable[[Any, Dict[str, Any]], bool]:
    """Returns a callback function suitable for ToolRegistry."""
    def callback(tool: Any, args: Dict[str, Any]) -> bool:
        details = ", ".join(f"{k}='{v}'" for k, v in args.items())
        description = f"The agent wants to execute tool '{tool.name}' with arguments: ({details})"
        return ask_confirmation(description)
    return callback
