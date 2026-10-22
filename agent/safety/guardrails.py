"""
Security Guardrails & Path Validation
Ensures all file operations are strictly confined within allowed directories.
Prevents directory traversal (e.g. '..'), drive jumps, and symlink escapes.
"""
import os
from pathlib import Path
from typing import List, Optional


class SecurityError(PermissionError):
    """Raised when an operation attempts to breach security guardrails."""
    pass


def resolve_and_validate_path(
    user_path: str,
    allowed_folders: List[Path],
    default_base: Optional[Path] = None,
) -> Path:
    """
    Safely resolve a target path and verify it resides strictly inside an allowed folder.
    
    Args:
        user_path: The path string provided by user or model (relative or absolute).
        allowed_folders: List of approved root directories.
        default_base: The default directory to resolve relative paths against (defaults to first allowed folder).
    
    Returns:
        The canonical, validated absolute Path.
        
    Raises:
        SecurityError: If the resolved path attempts to escape the allowed sandbox.
    """
    if not allowed_folders:
        raise SecurityError("Security error: No allowed folders are configured in security settings.")

    base_dir = default_base if default_base is not None else allowed_folders[0]
    base_dir = base_dir.resolve()

    # Clean input
    clean_path = user_path.strip()
    if not clean_path or clean_path in (".", "./", ".\\"):
        return base_dir

    raw_path = Path(clean_path)

    # If relative, anchor to base_dir
    if not raw_path.is_absolute():
        target = (base_dir / raw_path).resolve()
    else:
        target = raw_path.resolve()

    # Check if target resides within at least one allowed directory
    target_str_lower = str(target).lower()
    for allowed in allowed_folders:
        allowed_resolved = allowed.resolve()
        allowed_str_lower = str(allowed_resolved).lower()

        # Check if identical to allowed root or a child within it
        if target == allowed_resolved or allowed_resolved in target.parents:
            return target
        
        # Windows case-insensitive check
        if target_str_lower == allowed_str_lower or target_str_lower.startswith(allowed_str_lower + os.sep.lower()):
            return target

    raise SecurityError(
        f"Access Denied: Path '{user_path}' resolves to '{target}', which is outside the approved sandbox folders: "
        f"{[str(p) for p in allowed_folders]}."
    )
