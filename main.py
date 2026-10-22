"""
Desktop Agent CLI Entry Point
Interactive terminal chat with rich formatting, live status, and modular tools.
"""
import sys
from pathlib import Path

# Configure UTF-8 encoding on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path so 'agent' package imports work cleanly
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from agent.config import load_config, get_api_key
from agent.core import Agent
from agent.providers.gemini import GeminiProvider
from agent.providers.claude import ClaudeProvider
from agent.tools.registry import ToolRegistry
from agent.tools.time_tool import GetCurrentTimeTool
from agent.tools.files import (
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
    SearchFilesTool,
    DeleteFileTool,
)
from agent.tools.web import WebSearchTool, FetchWebpageTool
from agent.memory.sqlite_mem import MemoryManager
from agent.tools.memory import (
    RememberFactTool,
    RecallMemoriesTool,
    DeleteMemoryTool,
    ManageTodosTool,
)
from agent.tools.shell import ExecuteCommandTool
from agent.tools.organize import OrganizeFolderTool

console = Console()


def print_banner(config) -> None:
    """Display a clean, formatted startup dashboard using Rich."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")

    model_name = config.gemini_model if config.provider == "gemini" else config.claude_model
    shell_status = "[green]ENABLED (prompts on run)[/green]" if config.shell_enabled else "[red]DISABLED (safety default)[/red]"

    table.add_row("Provider :", f"[bold green]{config.provider.upper()}[/bold green]")
    table.add_row("Model    :", f"[yellow]{model_name}[/yellow]")
    table.add_row("Sandbox  :", f"[dim]{[str(p) for p in config.allowed_folders]}[/dim]")
    table.add_row("Shell    :", shell_status)
    table.add_row("Limits   :", f"{config.max_steps} max steps | {config.timeout_seconds}s timeout")

    panel = Panel(
        table,
        title="[bold blue]🤖 Antigravity Personal Desktop Agent (Windows)[/bold blue]",
        subtitle="[dim]Type your message below. Type 'exit' or 'quit' to close.[/dim]",
        border_style="cyan",
    )
    console.print(panel)


def setup_provider(config):
    """Initialize the configured model provider."""
    try:
        api_key = get_api_key(config.provider)
    except ValueError as e:
        console.print(f"\n[bold red]Configuration Error:[/bold red] {e}")
        console.print("Please open the .env file in the project folder and paste your API key.")
        sys.exit(1)

    if config.provider == "gemini":
        return GeminiProvider(
            api_key=api_key,
            model_name=config.gemini_model,
            temperature=config.gemini_temperature,
        )
    elif config.provider == "claude":
        return ClaudeProvider(
            api_key=api_key,
            model_name=config.claude_model,
            temperature=config.claude_temperature,
        )
    else:
        console.print(f"\n[bold red]Unsupported provider:[/bold red] '{config.provider}' in config.yaml.")
        sys.exit(1)


def main():
    config = load_config()
    print_banner(config)

    # Initialize model provider
    provider = setup_provider(config)

    # Initialize memory subsystem
    memory_mgr = MemoryManager(config.database_path)

    # Register all available tools
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    registry.register(ReadFileTool(config.allowed_folders))
    registry.register(WriteFileTool(config.allowed_folders))
    registry.register(ListDirectoryTool(config.allowed_folders))
    registry.register(SearchFilesTool(config.allowed_folders))
    registry.register(DeleteFileTool(config.allowed_folders))
    registry.register(WebSearchTool())
    registry.register(FetchWebpageTool())
    registry.register(RememberFactTool(memory_mgr))
    registry.register(RecallMemoriesTool(memory_mgr))
    registry.register(DeleteMemoryTool(memory_mgr))
    registry.register(ManageTodosTool(memory_mgr))
    registry.register(ExecuteCommandTool(enabled=config.shell_enabled, allowed_folders=config.allowed_folders))
    registry.register(OrganizeFolderTool(config.allowed_folders))

    # Build agent
    agent = Agent(config=config, provider=provider, tools=registry)

    # Live status updater callback
    def status_callback(status_msg: str):
        if "Running tool" in status_msg:
            console.print(f"   [bold yellow]⚙️ {status_msg}[/bold yellow]")
        else:
            console.print(f"   [dim cyan]⚙️ {status_msg}[/dim cyan]")

    # Interactive chat loop
    while True:
        try:
            console.print("\n[bold green]You > [/bold green]", end="")
            user_input = input().strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[bold cyan]Goodbye! Have a great day. 👋[/bold cyan]\n")
                break

            console.print()
            response = agent.chat(user_input, on_status_update=status_callback)

            # Render model markdown response beautifully
            console.print("\n[bold magenta]Agent >[/bold magenta]")
            console.print(Markdown(response))

        except KeyboardInterrupt:
            console.print("\n\n[dim]Session interrupted. Exiting...[/dim]")
            break
        except Exception as ex:
            console.print(f"\n[bold red]Unexpected error:[/bold red] {ex}\n")


if __name__ == "__main__":
    main()
