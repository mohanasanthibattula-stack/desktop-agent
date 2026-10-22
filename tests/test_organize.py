"""
Unit tests for Smart Folder Organizer Tool.
Tests file categorization, subfolder creation, user confirmation, and sandbox security.
"""
from pathlib import Path
from unittest.mock import patch
import pytest

from agent.tools.organize import OrganizeFolderTool
from agent.tools.registry import ToolRegistry


@pytest.fixture
def sandbox_env(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    return sandbox, [sandbox]


def test_organize_empty_folder(sandbox_env):
    sandbox, allowed = sandbox_env
    tool = OrganizeFolderTool(allowed)

    res = tool.execute("")
    assert "no loose files that need organizing" in res


def test_organize_outside_sandbox_blocked(sandbox_env):
    sandbox, allowed = sandbox_env
    tool = OrganizeFolderTool(allowed)

    res = tool.execute("..\\..\\Windows")
    assert "Security Error:" in res
    assert "outside the approved sandbox" in res


def test_organize_declined_by_user(sandbox_env):
    sandbox, allowed = sandbox_env
    tool = OrganizeFolderTool(allowed)

    # Create dummy files
    (sandbox / "doc.pdf").write_text("dummy")
    (sandbox / "photo.jpg").write_text("dummy")

    with patch("builtins.input", return_value="n"):
        res = tool.execute("")
        assert "declined by the user" in res.lower()
        # Ensure files were NOT moved
        assert (sandbox / "doc.pdf").exists()
        assert (sandbox / "photo.jpg").exists()


def test_organize_approved_moves_into_categories(sandbox_env):
    sandbox, allowed = sandbox_env
    tool = OrganizeFolderTool(allowed)

    # Create mixed files
    (sandbox / "report.pdf").write_text("report content")
    (sandbox / "notes.txt").write_text("notes content")
    (sandbox / "sunset.png").write_text("image content")
    (sandbox / "data.csv").write_text("data content")
    (sandbox / "script.py").write_text("code content")

    with patch("builtins.input", return_value="yes"):
        res = tool.execute("")
        assert "Successfully organized 5 file(s)" in res
        assert "Documents/" in res
        assert "Images/" in res
        assert "Spreadsheets/" in res
        assert "Code/" in res

        # Verify target files moved to proper subdirectories
        assert (sandbox / "Documents" / "report.pdf").exists()
        assert (sandbox / "Documents" / "notes.txt").exists()
        assert (sandbox / "Images" / "sunset.png").exists()
        assert (sandbox / "Spreadsheets" / "data.csv").exists()
        assert (sandbox / "Code" / "script.py").exists()

        # Verify root no longer has the loose files
        assert not (sandbox / "report.pdf").exists()


def test_organize_tool_registry():
    registry = ToolRegistry()
    registry.register(OrganizeFolderTool([Path("sandbox")]))

    schemas = registry.get_schemas()
    names = [s["name"] for s in schemas]
    assert "organize_folder" in names
