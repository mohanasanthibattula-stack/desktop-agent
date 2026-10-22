"""
Folder Organizer Tool
Automatically organizes messy directories by sorting files into categorized subfolders
(Documents, Images, Spreadsheets, Audio-Video, Code, Archives).
Restricted strictly to allowed sandbox directories.
"""
from collections import defaultdict
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List

from agent.safety.confirmation import ask_confirmation
from agent.safety.guardrails import SecurityError, resolve_and_validate_path
from .base import BaseTool

# File extension categorization mapping
CATEGORY_MAP: Dict[str, str] = {
    # Documents
    ".pdf": "Documents",
    ".docx": "Documents",
    ".doc": "Documents",
    ".txt": "Documents",
    ".md": "Documents",
    ".rtf": "Documents",
    ".odt": "Documents",
    ".epub": "Documents",
    # Images
    ".png": "Images",
    ".jpg": "Images",
    ".jpeg": "Images",
    ".gif": "Images",
    ".bmp": "Images",
    ".svg": "Images",
    ".webp": "Images",
    ".ico": "Images",
    # Spreadsheets & Data
    ".xlsx": "Spreadsheets",
    ".xls": "Spreadsheets",
    ".csv": "Spreadsheets",
    ".json": "Spreadsheets",
    ".parquet": "Spreadsheets",
    ".tsv": "Spreadsheets",
    # Code & Scripts
    ".py": "Code",
    ".js": "Code",
    ".ts": "Code",
    ".html": "Code",
    ".css": "Code",
    ".sql": "Code",
    ".ps1": "Code",
    ".sh": "Code",
    ".cpp": "Code",
    ".c": "Code",
    ".java": "Code",
    # Audio & Video
    ".mp4": "Media",
    ".mkv": "Media",
    ".avi": "Media",
    ".mov": "Media",
    ".mp3": "Media",
    ".wav": "Media",
    ".flac": "Media",
    # Archives & Compressed
    ".zip": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".7z": "Archives",
    ".rar": "Archives",
}


class OrganizeFolderTool(BaseTool):
    """Tool to automatically organize messy folders into categorized subdirectories."""

    name = "organize_folder"
    description = (
        "Automatically organizes files in a directory by sorting them into categorized subfolders: "
        "'Documents', 'Images', 'Spreadsheets', 'Code', 'Media', 'Archives'. "
        "Strictly restricted to allowed sandbox folders. Prompts for confirmation before moving files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the folder to organize (must be within allowed sandbox; defaults to sandbox root).",
            },
        },
        "required": [],
    }
    requires_confirmation = True

    def __init__(self, allowed_folders: List[Path]):
        self.allowed_folders = allowed_folders

    def execute(self, path: str = "", **kwargs: Any) -> str:
        try:
            target = resolve_and_validate_path(path or "", self.allowed_folders)
        except SecurityError as se:
            return f"Security Error: {str(se)}"

        if not target.exists() or not target.is_dir():
            return f"Error: Target path '{path}' does not exist or is not a directory."

        # Scan top-level loose files in directory (ignore existing subfolders and hidden files)
        loose_files = [f for f in target.iterdir() if f.is_file() and not f.name.startswith(".")]

        if not loose_files:
            return f"Directory '{target.name}' has no loose files that need organizing."

        # Group files into proposed categories
        plan: Dict[str, List[Path]] = defaultdict(list)
        for f in loose_files:
            ext = f.suffix.lower()
            category = CATEGORY_MAP.get(ext, "Other")
            plan[category].append(f)

        plan_summary = ", ".join(f"{len(files)} {cat}" for cat, files in plan.items())
        prompt_msg = (
            f"ORGANIZE FOLDER: Found {len(loose_files)} file(s) in '{target}'.\n"
            f"    Plan: Move files into subfolders: {plan_summary}."
        )

        confirmed = ask_confirmation(prompt_msg)
        if not confirmed:
            return f"Action cancelled: Organization of '{target.name}' was declined by the user."

        moved_count = 0
        details: List[str] = []

        try:
            for category, files in plan.items():
                cat_folder = target / category
                cat_folder.mkdir(exist_ok=True)

                for f in files:
                    dest = cat_folder / f.name
                    # If destination file already exists, avoid overwriting by renaming
                    if dest.exists():
                        stem = f.stem
                        suffix = f.suffix
                        dest = cat_folder / f"{stem}_copy{suffix}"

                    shutil.move(str(f), str(dest))
                    moved_count += 1
                details.append(f"  📁 {category}/ ({len(files)} files moved)")

            return (
                f"Successfully organized {moved_count} file(s) in '{target.name}':\n"
                + "\n".join(details)
            )

        except Exception as e:
            return f"Error while organizing files in '{target.name}': {type(e).__name__}: {str(e)}"
