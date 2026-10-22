# 🤖 Antigravity Personal AI Desktop Agent (Windows)

A production-quality, local-first personal AI assistant built in Python for Windows 10/11. It understands goals in plain English, autonomously breaks tasks into steps, uses secure tools, and reports results clearly.

---

## 🌟 Key Features

* **Swappable LLM Providers:** Switch between **Google Gemini** (`google-genai` SDK) and **Anthropic Claude** (`anthropic` SDK) via a single line in `config.yaml` without changing code.
* **Strict Security Sandbox:** File operations are restricted to approved directories (default: `sandbox/`). Blocks directory traversal tricks like `..`, `../../Windows`, or drive hops.
* **Human-in-the-Loop Confirmation:** Prompts `[y/N]` before overwriting files, deleting files, or executing shell commands.
* **Web Search & Article Extractor:** Free web search via DuckDuckGo and clean HTML text extraction via BeautifulSoup with context safeguards.
* **Persistent SQLite Long-Term Memory:** Remembers facts, user preferences, project details, and manages to-do tasks across terminal restarts in a local SQLite database (`data/memory.db`).
* **Safe Shell Execution:** PowerShell command execution disabled by default; gated by a config killswitch and explicit user confirmation.
* **Action Audit Logging:** Clean, human-readable audit trail of every turn, tool invocation, and security block in `data/agent.log`.
* **Rich Terminal UI:** Formatted startup dashboard, real-time tool badges, and Markdown rendering powered by `Rich`.

---

## 📁 Project Structure

```text
C:\Users\mohan\Projects\desktop-agent\
├── .env.example             # Template for API keys
├── .env                     # Real secrets (git-ignored)
├── .gitignore               # Protects secrets, cache, logs, and sandbox
├── config.yaml              # User configuration (provider, model, paths, limits)
├── requirements.txt         # Python dependencies
├── pytest.ini               # Pytest configuration
├── README.md                # Documentation & user manual
│
├── sandbox/                 # Approved workspace for agent file operations
│
├── data/                    # Persistent storage
│   ├── memory.db            # SQLite database (memories & todos)
│   └── agent.log            # Human-readable action audit trail
│
├── agent/                   # Core Python package
│   ├── config.py            # Loads config.yaml and .env
│   ├── core.py              # Autonomous ReAct agent loop
│   ├── logger.py            # Action audit logger
│   ├── prompt.py            # System prompt & behavioral guidelines
│   ├── providers/           # Swappable LLM backends (Gemini, Claude)
│   ├── safety/              # Path guardrails & [y/N] confirmation prompts
│   ├── memory/              # SQLite database manager
│   └── tools/               # Modular tool plugins (Files, Web, Memory, Shell)
│
└── tests/                   # 43 automated unit tests
    ├── test_files.py        # File CRUD & path traversal defense tests
    ├── test_logger.py       # Action audit logging tests
    ├── test_memory.py       # SQLite memory & task tests
    ├── test_milestone1.py   # ReAct loop & provider conversion tests
    ├── test_shell.py        # PowerShell execution & killswitch tests
    └── test_web.py          # Web search & page extraction tests
```

---

## 🚀 Windows Setup Guide

### 1. Prerequisites
* **Windows 10 or 11**
* **Python 3.11+** installed (check with `python --version` in PowerShell)

### 2. Open PowerShell in Project Directory
```powershell
cd C:\Users\mohan\Projects\desktop-agent
```

### 3. Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Configure Your API Key
Copy `.env.example` to `.env` if not already present:
```powershell
Copy-Item .env.example .env
notepad .env
```
Paste your Google Gemini API key (or Anthropic API key), then save (`Ctrl + S`):
```text
GEMINI_API_KEY=AIzaSy...your_actual_key_here
ANTHROPIC_API_KEY=your_claude_key_here
```

### 6. Start the Agent
You can run the agent either in the **Terminal** or as a **Desktop Window**:

* **Option A: Modern Desktop Window (GUI)**
  ```powershell
  python gui.py
  ```

* **Option B: Terminal CLI**
  ```powershell
  python main.py
  ```

---

## ⚙️ Configuration (`config.yaml`)

Edit `config.yaml` to customize your setup:

```yaml
# Active Provider: 'gemini' or 'claude'
provider: gemini

providers:
  gemini:
    model: gemini-flash-lite-latest   # or gemini-3.5-flash
    temperature: 0.2
  claude:
    model: claude-3-5-sonnet-latest
    temperature: 0.2

agent:
  max_steps: 15          # Max tool calls per user turn to prevent infinite loops
  timeout_seconds: 300   # 5-minute timeout per turn

security:
  allowed_folders:
    - sandbox            # Only files inside these folders can be touched
  shell_enabled: false   # Set to true to allow PowerShell command execution
  require_confirmation: true # Require [y/N] before overwriting or deleting
```

---

## 🛠️ Built-in Tools Reference

| Tool Name | Description | Requires Confirmation? |
| :--- | :--- | :---: |
| `get_current_time` | Returns the local Windows time, date, and day of week. | No |
| `read_file` | Reads text from a file inside the sandbox folder. | No |
| `write_file` | Creates or overwrites files inside the sandbox. | **Yes** (if overwriting) |
| `list_directory` | Lists files, sizes, and timestamps inside the sandbox. | No |
| `search_files` | Finds files matching wildcard patterns (`*.md`) or text content. | No |
| `delete_file` | Permanently deletes a file inside the sandbox. | **Yes** |
| `organize_folder` | Automatically sorts files into categorized subfolders (`Documents/`, `Images/`, `Spreadsheets/`, `Code/`). | **Yes** |
| `web_search` | Searches DuckDuckGo for live facts, documentation, or news. | No |
| `fetch_webpage` | Downloads and strips HTML from a webpage URL to extract clean text. | No |
| `remember_fact` | Saves personal facts or preferences to `data/memory.db`. | No |
| `recall_memories` | Searches or lists stored long-term memories. | No |
| `delete_memory` | Deletes a stored memory item by its numeric ID. | No |
| `manage_todos` | Adds, lists, completes, or deletes tasks in SQLite to-do manager. | No |
| `execute_command` | Runs a PowerShell command within the sandbox. | **Yes** (and disabled by default) |

---

## 🧪 Running Automated Tests

Run the full automated test suite (48 tests):
```powershell
.\venv\Scripts\pytest -v tests
```

---

## 🔒 Production Security Checklist

* [x] **Path Traversal Defense:** Every file path is normalized using `resolve()`. Any path with `..` or targeting outside `allowed_folders` is blocked with `SecurityError`.
* [x] **Gated Shell Execution:** PowerShell commands are disabled by default (`security.shell_enabled: false`). Even when enabled, every command pauses for explicit `[y/N]` confirmation.
* [x] **Irreversible Action Prompts:** Deleting files, overwriting existing files, or executing terminal commands prompts the user with `[y/N]`. Pressing `Enter` defaults to **No**.
* [x] **Secret Isolation:** API keys are never stored in source code or `config.yaml`. They reside strictly in `.env`, which is excluded by `.gitignore`.
* [x] **Runaway Execution Protection:** A strict step counter (default 15) and timeout (default 300s) guarantee the agent never enters an infinite loop.
* [x] **Action Audit Logging:** Every user request, tool call, tool result, and security exception is written to `data/agent.log`.

---

## 🚀 Ideas to Extend Your Agent

1. **Desktop GUI Window:** Wrap `Agent.chat()` in a native PyQt6 or Tkinter desktop chat window with system tray minimization.
2. **Email Assistant:** Add an `email_tool` using Python's `imaplib` and `smtplib` to draft and summarize emails (with confirmation before sending).
3. **Calendar Integration:** Connect to Google Calendar API to schedule meetings and check upcoming events.
4. **Local Offline LLMs:** Add an `OllamaProvider` pointing to `http://localhost:11434` for 100% offline private local model execution (e.g. Llama 3 or Mistral).
