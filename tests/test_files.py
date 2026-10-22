"""
Unit tests for Milestone 2: File Tools & Sandbox Security Guardrails.
Tests path canonicalization, directory traversal defense, file CRUD, and confirmation prompts.
"""
from pathlib import Path
import pytest
from unittest.mock import patch

from agent.safety.guardrails import SecurityError, resolve_and_validate_path
from agent.tools.files import (
    DeleteFileTool,
    ListDirectoryTool,
    ReadFileTool,
    SearchFilesTool,
    WriteFileTool,
)


@pytest.fixture
def sandbox_env(tmp_path: Path):
    """Create an isolated test sandbox environment."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    allowed_folders = [sandbox]
    return sandbox, allowed_folders


# =====================================================================
# 1. Path Security & Guardrails Tests
# =====================================================================

def test_resolve_valid_path_inside_sandbox(sandbox_env):
    sandbox, allowed = sandbox_env
    resolved = resolve_and_validate_path("notes.txt", allowed)
    assert resolved == (sandbox / "notes.txt").resolve()


def test_resolve_nested_subfolder_inside_sandbox(sandbox_env):
    sandbox, allowed = sandbox_env
    resolved = resolve_and_validate_path("reports/2026/summary.md", allowed)
    assert resolved == (sandbox / "reports" / "2026" / "summary.md").resolve()


def test_block_directory_traversal_dot_dot(sandbox_env):
    sandbox, allowed = sandbox_env
    # Attempting to escape sandbox via ..
    with pytest.raises(SecurityError) as exc_info:
        resolve_and_validate_path("../../secret.txt", allowed)
    assert "outside the approved sandbox" in str(exc_info.value)


def test_block_directory_traversal_sneaky(sandbox_env):
    sandbox, allowed = sandbox_env
    with pytest.raises(SecurityError):
        resolve_and_validate_path("subfolder/../../outside.txt", allowed)


def test_block_absolute_path_outside_sandbox(sandbox_env):
    sandbox, allowed = sandbox_env
    outside_file = "C:\\Windows\\System32\\drivers\\etc\\hosts"
    with pytest.raises(SecurityError):
        resolve_and_validate_path(outside_file, allowed)


# =====================================================================
# 2. File Tools Operations Tests
# =====================================================================

def test_write_and_read_file(sandbox_env):
    sandbox, allowed = sandbox_env
    write_tool = WriteFileTool(allowed)
    read_tool = ReadFileTool(allowed)

    # Write new file
    res = write_tool.execute("hello.txt", "Hello, Antigravity!")
    assert "created file 'hello.txt'" in res.lower()
    assert (sandbox / "hello.txt").exists()

    # Read the file
    content = read_tool.execute("hello.txt")
    assert "Hello, Antigravity!" in content


def test_read_file_outside_sandbox_blocked(sandbox_env):
    sandbox, allowed = sandbox_env
    read_tool = ReadFileTool(allowed)

    # Try to read outside sandbox
    result = read_tool.execute("..\\..\\Windows\\win.ini")
    assert "Security Error:" in result
    assert "outside the approved sandbox" in result


def test_write_file_overwrite_without_flag_fails(sandbox_env):
    sandbox, allowed = sandbox_env
    write_tool = WriteFileTool(allowed)

    # First write
    write_tool.execute("doc.txt", "Version 1")
    # Second write with overwrite=False
    res = write_tool.execute("doc.txt", "Version 2", overwrite=False)
    assert "already exists" in res
    assert (sandbox / "doc.txt").read_text() == "Version 1"


def test_write_file_overwrite_with_user_confirmation(sandbox_env):
    sandbox, allowed = sandbox_env
    write_tool = WriteFileTool(allowed)

    write_tool.execute("doc.txt", "Original Content")

    # Simulate user typing 'y'
    with patch("builtins.input", return_value="y"):
        res = write_tool.execute("doc.txt", "Updated Content", overwrite=True)
        assert "overwrote file 'doc.txt'" in res.lower()
        assert (sandbox / "doc.txt").read_text() == "Updated Content"


def test_write_file_overwrite_declined_by_user(sandbox_env):
    sandbox, allowed = sandbox_env
    write_tool = WriteFileTool(allowed)

    write_tool.execute("doc.txt", "Protected Content")

    # Simulate user pressing Enter (No)
    with patch("builtins.input", return_value=""):
        res = write_tool.execute("doc.txt", "Malicious Overwrite", overwrite=True)
        assert "declined by the user" in res.lower()
        assert (sandbox / "doc.txt").read_text() == "Protected Content"


def test_list_and_search_files(sandbox_env):
    sandbox, allowed = sandbox_env
    write_tool = WriteFileTool(allowed)
    list_tool = ListDirectoryTool(allowed)
    search_tool = SearchFilesTool(allowed)

    write_tool.execute("project_a.txt", "First project notes")
    write_tool.execute("project_b.md", "Second project details")

    # Test listing
    listed = list_tool.execute("")
    assert "project_a.txt" in listed
    assert "project_b.md" in listed

    # Test searching by wildcard
    searched = search_tool.execute(pattern="*.md")
    assert "project_b.md" in searched
    assert "project_a.txt" not in searched

    # Test searching by content query
    searched_content = search_tool.execute(pattern="*", content_query="First project")
    assert "project_a.txt" in searched_content


def test_delete_file_with_confirmation(sandbox_env):
    sandbox, allowed = sandbox_env
    write_tool = WriteFileTool(allowed)
    delete_tool = DeleteFileTool(allowed)

    write_tool.execute("temporary.txt", "delete me")
    assert (sandbox / "temporary.txt").exists()

    # User confirms deletion
    with patch("builtins.input", return_value="yes"):
        res = delete_tool.execute("temporary.txt")
        assert "permanently deleted" in res.lower()
        assert not (sandbox / "temporary.txt").exists()


def test_delete_file_declined_by_user(sandbox_env):
    sandbox, allowed = sandbox_env
    write_tool = WriteFileTool(allowed)
    delete_tool = DeleteFileTool(allowed)

    write_tool.execute("important.txt", "keep me")
    assert (sandbox / "important.txt").exists()

    # User declines deletion
    with patch("builtins.input", return_value="n"):
        res = delete_tool.execute("important.txt")
        assert "declined by the user" in res.lower()
        assert (sandbox / "important.txt").exists()


def test_delete_outside_sandbox_blocked(sandbox_env):
    sandbox, allowed = sandbox_env
    delete_tool = DeleteFileTool(allowed)

    res = delete_tool.execute("..\\..\\some_system_file.txt")
    assert "Security Error:" in res
