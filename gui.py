"""
Desktop Agent Modern GUI Window
Native Windows desktop application for your personal AI assistant.
Runs background threads to keep the interface smooth and responsive.
"""
from datetime import datetime
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import font, messagebox, ttk

# Add project root to sys.path so 'agent' package imports work cleanly
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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


# Modern color palette
BG_DARK = "#181825"
BG_PANEL = "#1e1e2e"
BG_INPUT = "#313244"
TEXT_MAIN = "#cdd6f4"
TEXT_MUTED = "#a6adc8"
ACCENT_BLUE = "#89b4fa"
ACCENT_GREEN = "#a6e3a1"
ACCENT_YELLOW = "#f9e2af"
ACCENT_RED = "#f38ba8"
USER_TAG_COLOR = "#89dceb"
AGENT_TAG_COLOR = "#cba6f7"
STATUS_TAG_COLOR = "#fab387"


class DesktopAgentApp:
    """Main Desktop GUI Window for the Personal AI Agent."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🤖 Antigravity Desktop AI Agent")
        self.root.geometry("920x720")
        self.root.minsize(720, 520)
        self.root.configure(bg=BG_DARK)

        # Message communication queue for background thread
        self.msg_queue: queue.Queue = queue.Queue()

        # Load config and agent
        self.config = load_config()
        self.agent = self._initialize_agent()

        # Build UI layout
        self._setup_styles()
        self._build_header()
        self._build_chat_display()
        self._build_input_bar()
        self._build_status_bar()

        # Start periodic queue polling
        self.root.after(100, self._process_queue)

        # Welcome message
        self._append_message(
            "Agent",
            f"Hello! I am your personal desktop assistant running on Windows.\n"
            f"• Active Model: {self._get_model_name()}\n"
            f"• Sandbox: {self.config.allowed_folders[0]}\n\n"
            f"How can I assist you today? You can ask me to research topics, manage to-dos, "
            f"organize folders, or work with files.",
        )

    def _get_model_name(self) -> str:
        return self.config.gemini_model if self.config.provider == "gemini" else self.config.claude_model

    def _gui_confirmation_callback(self, tool, args) -> bool:
        """Pops up a native Windows modal dialog for approvals when required."""
        details = ", ".join(f"{k}='{v}'" for k, v in args.items())
        msg = (
            f"The agent is requesting approval to execute action:\n\n"
            f"Tool: {tool.name}\n"
            f"Arguments: {details}\n\n"
            f"Do you want to proceed?"
        )
        return messagebox.askyesno("Approval Required", msg, parent=self.root)

    def _initialize_agent(self) -> Agent:
        """Initialize the model provider, memory, and tools."""
        try:
            api_key = get_api_key(self.config.provider)
        except ValueError as e:
            messagebox.showerror("Configuration Error", f"{str(e)}\nPlease check your .env file.")
            sys.exit(1)

        if self.config.provider == "gemini":
            provider = GeminiProvider(
                api_key=api_key,
                model_name=self.config.gemini_model,
                temperature=self.config.gemini_temperature,
            )
        else:
            provider = ClaudeProvider(
                api_key=api_key,
                model_name=self.config.claude_model,
                temperature=self.config.claude_temperature,
            )

        memory_mgr = MemoryManager(self.config.database_path)

        registry = ToolRegistry()
        registry.register(GetCurrentTimeTool())
        registry.register(ReadFileTool(self.config.allowed_folders))
        registry.register(WriteFileTool(self.config.allowed_folders))
        registry.register(ListDirectoryTool(self.config.allowed_folders))
        registry.register(SearchFilesTool(self.config.allowed_folders))
        registry.register(DeleteFileTool(self.config.allowed_folders))
        registry.register(WebSearchTool())
        registry.register(FetchWebpageTool())
        registry.register(RememberFactTool(memory_mgr))
        registry.register(RecallMemoriesTool(memory_mgr))
        registry.register(DeleteMemoryTool(memory_mgr))
        registry.register(ManageTodosTool(memory_mgr))
        registry.register(ExecuteCommandTool(enabled=self.config.shell_enabled, allowed_folders=self.config.allowed_folders))
        registry.register(OrganizeFolderTool(self.config.allowed_folders))

        agent = Agent(config=self.config, provider=provider, tools=registry)
        # Use native GUI popup for confirmations
        agent.confirmation_callback = self._gui_confirmation_callback
        return agent

    def _setup_styles(self) -> None:
        self.default_font = font.Font(family="Segoe UI", size=10)
        self.bold_font = font.Font(family="Segoe UI", size=10, weight="bold")
        self.title_font = font.Font(family="Segoe UI", size=12, weight="bold")
        self.code_font = font.Font(family="Consolas", size=9)

    def _build_header(self) -> None:
        header_frame = tk.Frame(self.root, bg=BG_PANEL, height=55, padx=15, pady=8)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header_frame,
            text="🤖 Antigravity Desktop Agent",
            font=self.title_font,
            fg=ACCENT_BLUE,
            bg=BG_PANEL,
        )
        title_lbl.pack(side=tk.LEFT)

        model_badge = tk.Label(
            header_frame,
            text=f"  ● {self.config.provider.upper()}: {self._get_model_name()}  ",
            font=self.default_font,
            fg=ACCENT_GREEN,
            bg=BG_INPUT,
            padx=8,
            pady=2,
        )
        model_badge.pack(side=tk.LEFT, padx=15)

        # Action shortcuts
        actions_frame = tk.Frame(header_frame, bg=BG_PANEL)
        actions_frame.pack(side=tk.RIGHT)

        clean_btn = tk.Button(
            actions_frame,
            text="Clear Chat",
            font=self.default_font,
            fg=TEXT_MUTED,
            bg=BG_INPUT,
            activebackground=BG_DARK,
            activeforeground=TEXT_MAIN,
            relief=tk.FLAT,
            command=self._clear_chat,
            cursor="hand2",
            padx=8,
            pady=2,
        )
        clean_btn.pack(side=tk.LEFT, padx=4)

        todos_btn = tk.Button(
            actions_frame,
            text="Tasks",
            font=self.default_font,
            fg=TEXT_MUTED,
            bg=BG_INPUT,
            activebackground=BG_DARK,
            activeforeground=TEXT_MAIN,
            relief=tk.FLAT,
            command=self._quick_show_tasks,
            cursor="hand2",
            padx=8,
            pady=2,
        )
        todos_btn.pack(side=tk.LEFT, padx=4)

        org_btn = tk.Button(
            actions_frame,
            text="Organize Sandbox",
            font=self.default_font,
            fg=TEXT_MUTED,
            bg=BG_INPUT,
            activebackground=BG_DARK,
            activeforeground=TEXT_MAIN,
            relief=tk.FLAT,
            command=self._quick_organize_sandbox,
            cursor="hand2",
            padx=8,
            pady=2,
        )
        org_btn.pack(side=tk.LEFT, padx=4)

    def _build_chat_display(self) -> None:
        chat_frame = tk.Frame(self.root, bg=BG_DARK, padx=10, pady=8)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self.chat_text = tk.Text(
            chat_frame,
            bg=BG_DARK,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=self.default_font,
            relief=tk.FLAT,
            wrap=tk.WORD,
            padx=12,
            pady=10,
        )
        scrollbar = tk.Scrollbar(chat_frame, command=self.chat_text.yview, bg=BG_PANEL)
        self.chat_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Style tags
        self.chat_text.tag_config("user_tag", foreground=USER_TAG_COLOR, font=self.bold_font)
        self.chat_text.tag_config("agent_tag", foreground=AGENT_TAG_COLOR, font=self.bold_font)
        self.chat_text.tag_config("status_tag", foreground=STATUS_TAG_COLOR, font=self.code_font)
        self.chat_text.tag_config("timestamp", foreground=TEXT_MUTED, font=self.code_font)
        self.chat_text.tag_config("normal_text", foreground=TEXT_MAIN, font=self.default_font)

        self.chat_text.configure(state=tk.DISABLED)

    def _build_input_bar(self) -> None:
        input_frame = tk.Frame(self.root, bg=BG_PANEL, padx=15, pady=10)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.entry_var,
            bg=BG_INPUT,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=self.default_font,
            relief=tk.FLAT,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        self.entry.bind("<Return>", lambda event: self._send_user_message())
        self.entry.focus_set()

        self.send_btn = tk.Button(
            input_frame,
            text="Send  ➤",
            font=self.bold_font,
            fg=BG_DARK,
            bg=ACCENT_BLUE,
            activebackground=ACCENT_GREEN,
            activeforeground=BG_DARK,
            relief=tk.FLAT,
            command=self._send_user_message,
            cursor="hand2",
            padx=15,
            pady=6,
        )
        self.send_btn.pack(side=tk.RIGHT)

    def _build_status_bar(self) -> None:
        self.status_frame = tk.Frame(self.root, bg=BG_DARK, height=22, padx=15)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, before=self.chat_text.master)

        self.status_lbl = tk.Label(
            self.status_frame,
            text="🟢 Ready",
            font=self.code_font,
            fg=TEXT_MUTED,
            bg=BG_DARK,
        )
        self.status_lbl.pack(side=tk.LEFT)

    def _append_message(self, sender: str, text: str) -> None:
        self.chat_text.configure(state=tk.NORMAL)
        time_str = datetime.now().strftime("%I:%M %p")

        tag = "user_tag" if sender == "You" else "agent_tag"
        self.chat_text.insert(tk.END, f"\n{sender} ", tag)
        self.chat_text.insert(tk.END, f"({time_str})\n", "timestamp")
        self.chat_text.insert(tk.END, f"{text.strip()}\n", "normal_text")
        self.chat_text.see(tk.END)
        self.chat_text.configure(state=tk.DISABLED)

    def _append_status_line(self, status_msg: str) -> None:
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"  ⚙️  {status_msg}\n", "status_tag")
        self.chat_text.see(tk.END)
        self.chat_text.configure(state=tk.DISABLED)

    def _send_user_message(self) -> None:
        msg = self.entry_var.get().strip()
        if not msg:
            return

        self.entry_var.set("")
        self._append_message("You", msg)
        self._set_busy(True, "Thinking...")

        # Run ReAct agent loop in background thread
        threading.Thread(
            target=self._run_agent_thread,
            args=(msg,),
            daemon=True,
        ).start()

    def _run_agent_thread(self, user_prompt: str) -> None:
        def on_update(status_text: str):
            self.msg_queue.put(("status", status_text))

        try:
            response = self.agent.chat(user_prompt, on_status_update=on_update)
            self.msg_queue.put(("response", response))
        except Exception as e:
            self.msg_queue.put(("response", f"Error: {type(e).__name__}: {str(e)}"))

    def _process_queue(self) -> None:
        """Process notifications arriving from background worker thread."""
        try:
            while True:
                msg_type, content = self.msg_queue.get_nowait()
                if msg_type == "status":
                    self.status_lbl.configure(text=f"⏳ {content}", fg=STATUS_TAG_COLOR)
                    if "Running tool" in content:
                        self._append_status_line(content)
                elif msg_type == "response":
                    self._append_message("Agent", content)
                    self._set_busy(False, "🟢 Ready")
        except queue.Empty:
            pass

        self.root.after(100, self._process_queue)

    def _set_busy(self, is_busy: bool, status_text: str) -> None:
        self.status_lbl.configure(text=status_text)
        if is_busy:
            self.send_btn.configure(state=tk.DISABLED, bg=BG_INPUT)
            self.entry.configure(state=tk.DISABLED)
        else:
            self.send_btn.configure(state=tk.NORMAL, bg=ACCENT_BLUE)
            self.entry.configure(state=tk.NORMAL)
            self.entry.focus_set()

    def _clear_chat(self) -> None:
        self.chat_text.configure(state=tk.NORMAL)
        self.chat_text.delete("1.0", tk.END)
        self.chat_text.configure(state=tk.DISABLED)
        self._append_message("Agent", "Chat history cleared. How can I help you?")

    def _quick_show_tasks(self) -> None:
        self.entry_var.set("Show my pending to-do tasks")
        self._send_user_message()

    def _quick_organize_sandbox(self) -> None:
        self.entry_var.set("Please organize my sandbox folder")
        self._send_user_message()


def main():
    root = tk.Tk()
    app = DesktopAgentApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
