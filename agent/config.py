"""
Configuration Manager
Loads settings from config.yaml and API keys from .env.
"""
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from .env in project root
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


@dataclass
class AppConfig:
    provider: str = "gemini"
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.2
    claude_model: str = "claude-3-5-sonnet-latest"
    claude_temperature: float = 0.2
    max_steps: int = 15
    timeout_seconds: int = 120
    allowed_folders: List[Path] = field(default_factory=list)
    shell_enabled: bool = False
    require_confirmation: bool = True
    database_path: Path = PROJECT_ROOT / "data" / "memory.db"
    log_path: Path = PROJECT_ROOT / "data" / "agent.log"


def load_config() -> AppConfig:
    """Load configuration from config.yaml with sensible fallbacks."""
    config_file = PROJECT_ROOT / "config.yaml"
    raw_data: Dict[str, Any] = {}

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[Warning] Error reading config.yaml: {e}. Using defaults.")

    provider = raw_data.get("provider", "gemini").lower()
    
    # Model provider configs
    providers_cfg = raw_data.get("providers", {})
    gemini_cfg = providers_cfg.get("gemini", {})
    claude_cfg = providers_cfg.get("claude", {})

    # Agent loop boundaries
    agent_cfg = raw_data.get("agent", {})
    max_steps = int(agent_cfg.get("max_steps", 15))
    timeout_seconds = int(agent_cfg.get("timeout_seconds", 120))

    # Security settings
    security_cfg = raw_data.get("security", {})
    raw_folders = security_cfg.get("allowed_folders", ["sandbox"])
    allowed_folders: List[Path] = []
    for f in raw_folders:
        p = Path(f)
        if not p.is_absolute():
            p = (PROJECT_ROOT / p).resolve()
        else:
            p = p.resolve()
        allowed_folders.append(p)

    shell_enabled = bool(security_cfg.get("shell_enabled", False))
    require_confirmation = bool(security_cfg.get("require_confirmation", True))

    # File paths
    paths_cfg = raw_data.get("paths", {})
    db_raw = paths_cfg.get("database_path", "data/memory.db")
    db_path = Path(db_raw)
    if not db_path.is_absolute():
        db_path = (PROJECT_ROOT / db_path).resolve()

    log_raw = paths_cfg.get("log_path", "data/agent.log")
    log_path = Path(log_raw)
    if not log_path.is_absolute():
        log_path = (PROJECT_ROOT / log_path).resolve()

    # Ensure parent directories exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    return AppConfig(
        provider=provider,
        gemini_model=gemini_cfg.get("model", "gemini-2.5-flash"),
        gemini_temperature=float(gemini_cfg.get("temperature", 0.2)),
        claude_model=claude_cfg.get("model", "claude-3-5-sonnet-latest"),
        claude_temperature=float(claude_cfg.get("temperature", 0.2)),
        max_steps=max_steps,
        timeout_seconds=timeout_seconds,
        allowed_folders=allowed_folders,
        shell_enabled=shell_enabled,
        require_confirmation=require_confirmation,
        database_path=db_path,
        log_path=log_path,
    )


def get_api_key(provider: str) -> str:
    """Retrieve the API key for a specified provider from environment."""
    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise ValueError(
                "Missing GEMINI_API_KEY. Please set GEMINI_API_KEY in your .env file."
            )
        return key
    elif provider == "claude":
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise ValueError(
                "Missing ANTHROPIC_API_KEY. Please set ANTHROPIC_API_KEY in your .env file."
            )
        return key
    else:
        raise ValueError(f"Unknown provider '{provider}'. Supported: 'gemini', 'claude'.")
