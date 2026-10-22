"""
File Operations Tools
Provides read, write, list, search, and delete tools strictly confined to allowed folders.
Enforces user confirmation [y/N] before overwriting or deleting any file.
"""
from datetime import datetime
import fnmatch
import os
from pathlib import Path
from typing import Any, List, Optional

from agent.safety.confirmation import ask_confirmation
from agent.safety.guardrails import SecurityError, resolve_and_validate_path
from .base import BaseTool


class ReadFileTool(BaseTool):
    """Tool to read content of a file within allowed sandbox folders."""

    name = "read_file"
    description = "Reads and returns the text content of a file located inside the allowed sandbox directory."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative or absolute path of the file to read (must be inside allowed sandbox).",
            },
        },
        "required": ["path"],
    }
    requires_confirmation = False

    def __init__(self, allowed_folders: List[Path]):
        self.allowed_folders = allowed_folders

    def execute(self, path: str, **kwargs: Any) -> str:
        try:
            target = resolve_and_validate_path(path, self.allowed_folders)
        except SecurityError as se:
            return f"Security Error: {str(se)}"

        if not target.exists():
            return f"Error: File does not exist at '{path}'."
        if not target.is_file():
            return f"Error: Path '{path}' is a directory, not a file. Use 'list_directory' instead."

        try:
            # Read with UTF-8 first, fallback to latin-1
            try:
                content = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = target.read_text(encoding="latin-1")

            lines = content.splitlines()
            total_lines = len(lines)

            # Safeguard against huge files
            max_lines = 300
            if total_lines > max_lines:
                preview = "\n".join(lines[:max_lines])
                return (
                    f"Content of '{target.name}' ({total_lines} total lines, showing first {max_lines}):\n\n"
                    f"{preview}\n\n[... Truncated remainder of file ...]"
                )

            return f"Content of '{target.name}' ({total_lines} lines):\n\n{content}"
        except Exception as e:
            return f"Error reading file '{path}': {type(e).__name__}: {str(e)}"


class WriteFileTool(BaseTool):
    """Tool to create or overwrite a file in allowed sandbox folders."""

    name = "write_file"
    description = (
        "Creates a new file or overwrites an existing file in the allowed sandbox directory. "
        "Overwriting an existing file will prompt the user for confirmation."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path where the file should be saved (must be inside allowed sandbox).",
            },
            "content": {
                "type": "string",
                "description": "Text content to write into the file.",
            },
            "overwrite": {
                "type": "boolean",
                "description": "Set to true if you explicitly intend to overwrite an existing file.",
            },
        },
        "required": ["path", "content"],
    }
    requires_confirmation = False  # Confirmation is evaluated conditionally if file exists

    def __init__(self, allowed_folders: List[Path]):
        self.allowed_folders = allowed_folders

    def execute(self, path: str, content: str, overwrite: bool = False, **kwargs: Any) -> str:
        try:
            target = resolve_and_validate_path(path, self.allowed_folders)
        except SecurityError as se:
            return f"Security Error: {str(se)}"

        # If file exists, require explicit confirmation before overwriting
        if target.exists():
            if not overwrite:
                return (
                    f"File already exists at '{target.name}'. "
                    f"To replace it, please request user permission or specify overwrite=true."
                )

            confirmed = ask_confirmation(
                f"OVERWRITE EXISTING FILE: The agent wants to overwrite '{target}'. "
                f"This will replace its current contents ({target.stat().st_size} bytes)."
            )
            if not confirmed:
                return f"Action cancelled: Overwriting file '{target.name}' was declined by the user."

        try:
            # Ensure parent directories exist
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            status = "overwrote" if target.exists() and overwrite else "created"
            return f"Successfully {status} file '{target.name}' ({len(content)} characters written)."
        except Exception as e:
            return f"Error writing file '{path}': {type(e).__name__}: {str(e)}"


class ListDirectoryTool(BaseTool):
    """Tool to inspect directories within allowed sandbox folders."""

    name = "list_directory"
    description = "Lists files and subdirectories located within the allowed sandbox directory."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (defaults to root of allowed sandbox).",
            },
        },
        "required": [],
    }
    requires_confirmation = False

    def __init__(self, allowed_folders: List[Path]):
        self.allowed_folders = allowed_folders

    def execute(self, path: str = "", **kwargs: Any) -> str:
        try:
            target = resolve_and_validate_path(path or "", self.allowed_folders)
        except SecurityError as se:
            return f"Security Error: {str(se)}"

        if not target.exists():
            return f"Error: Directory '{path}' does not exist."
        if not target.is_dir():
            return f"Error: Path '{path}' is a file, not a directory. Use 'read_file' instead."

        try:
            entries = sorted(list(target.iterdir()), key=lambda p: (not p.is_dir(), p.name.lower()))
            if not entries:
                return f"Directory '{target.name}' is empty."

            lines = [f"Contents of directory '{target}':"]
            for entry in entries:
                try:
                    stats = entry.stat()
                    mod_time = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
                    if entry.is_dir():
                        lines.append(f"  📁 [DIR]  {entry.name}/  (Modified: {mod_time})")
                    else:
                        size_kb = max(1, round(stats.st_size / 1024))
                        lines.append(f"  📄 [FILE] {entry.name}  ({size_kb} KB, Modified: {mod_time})")
                except Exception:
                    lines.append(f"  • {entry.name}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error listing directory '{path}': {type(e).__name__}: {str(e)}"


class SearchFilesTool(BaseTool):
    """Tool to search for files matching patterns or text within sandbox."""

    name = "search_files"
    description = (
        "Searches for files by filename pattern (e.g. '*.txt', '*notes*') "
        "or content within the allowed sandbox directory."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Wildcard pattern to match filenames (e.g. '*.txt', '*.md', '*report*').",
            },
            "path": {
                "type": "string",
                "description": "Directory to search within (defaults to root of allowed sandbox).",
            },
            "content_query": {
                "type": "string",
                "description": "Optional text to search for inside file contents.",
            },
        },
        "required": ["pattern"],
    }
    requires_confirmation = False

    def __init__(self, allowed_folders: List[Path]):
        self.allowed_folders = allowed_folders

    def execute(self, pattern: str, path: str = "", content_query: Optional[str] = None, **kwargs: Any) -> str:
        try:
            target = resolve_and_validate_path(path or "", self.allowed_folders)
        except SecurityError as se:
            return f"Security Error: {str(se)}"

        if not target.exists() or not target.is_dir():
            return f"Error: Search base directory '{path}' does not exist or is not a directory."

        try:
            matches = []
            for root, _, files in os.walk(target):
                for filename in files:
                    if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                        full_path = Path(root) / filename
                        rel_path = full_path.relative_to(target)

                        # If content search is requested, check file contents
                        if content_query:
                            try:
                                text = full_path.read_text(encoding="utf-8", errors="ignore")
                                if content_query.lower() in text.lower():
                                    matches.append(f"  📄 {rel_path} (matched content '{content_query}')")
                            except Exception:
                                pass
                        else:
                            matches.append(f"  📄 {rel_path}")

            if not matches:
                filter_desc = f" matching pattern '{pattern}'" + (f" and text '{content_query}'" if content_query else "")
                return f"No files found{filter_desc} in '{target}'."

            return f"Found {len(matches)} matching file(s) in '{target}':\n" + "\n".join(matches)
        except Exception as e:
            return f"Error searching files: {type(e).__name__}: {str(e)}"


class DeleteFileTool(BaseTool):
    """Tool to permanently delete a file within allowed sandbox folders."""

    name = "delete_file"
    description = (
        "Permanently deletes a file within the allowed sandbox directory. "
        "Always prompts the user for confirmation before deletion."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to delete (must be inside allowed sandbox).",
            },
        },
        "required": ["path"],
    }
    requires_confirmation = True

    def __init__(self, allowed_folders: List[Path]):
        self.allowed_folders = allowed_folders

    def execute(self, path: str, **kwargs: Any) -> str:
        try:
            target = resolve_and_validate_path(path, self.allowed_folders)
        except SecurityError as se:
            return f"Security Error: {str(se)}"

        if not target.exists():
            return f"Error: Cannot delete '{path}' because it does not exist."
        if not target.is_file():
            return f"Error: Path '{path}' is a directory. This tool only deletes individual files."

        # Prompt user explicitly with [y/N]
        confirmed = ask_confirmation(
            f"PERMANENTLY DELETE FILE: The agent wants to delete '{target}'. "
            f"This action cannot be undone."
        )
        if not confirmed:
            return f"Action cancelled: Deletion of '{target.name}' was declined by the user."

        try:
            target.unlink()
            return f"File '{target.name}' was permanently deleted."
        except Exception as e:
            return f"Error deleting file '{path}': {type(e).__name__}: {str(e)}"
