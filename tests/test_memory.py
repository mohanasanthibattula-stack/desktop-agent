"""
Unit tests for Milestone 4: Long-Term SQLite Memory & Task Manager.
Tests database persistence, memory CRUD, to-do management, and tool integration.
"""
from pathlib import Path
import pytest

from agent.memory.sqlite_mem import MemoryManager
from agent.tools.memory import (
    DeleteMemoryTool,
    ManageTodosTool,
    RecallMemoriesTool,
    RememberFactTool,
)
from agent.tools.registry import ToolRegistry


@pytest.fixture
def memory_mgr(tmp_path: Path):
    """Create an isolated test database in a temporary directory."""
    db_path = tmp_path / "test_memory.db"
    return MemoryManager(db_path)


# =====================================================================
# 1. SQLite MemoryManager Core Tests
# =====================================================================

def test_database_initialization(memory_mgr):
    assert memory_mgr.db_path.exists()
    # Confirm tables were created
    memories = memory_mgr.search_memories()
    assert memories == []
    todos = memory_mgr.list_todos()
    assert todos == []


def test_add_and_search_memories(memory_mgr):
    id1 = memory_mgr.add_memory("Favorite coffee: Cold brew", category="preference")
    id2 = memory_mgr.add_memory("Work laptop is a Dell XPS 15", category="fact")
    id3 = memory_mgr.add_memory("Project Alpha launching in Q4", category="project")

    assert id1 == 1
    assert id2 == 2
    assert id3 == 3

    # List all
    all_mem = memory_mgr.search_memories()
    assert len(all_mem) == 3

    # Keyword search
    coffee_res = memory_mgr.search_memories("coffee")
    assert len(coffee_res) == 1
    assert coffee_res[0]["content"] == "Favorite coffee: Cold brew"

    # Category search
    project_res = memory_mgr.search_memories("project")
    assert any("Project Alpha" in m["content"] for m in project_res)


def test_delete_memory(memory_mgr):
    mid = memory_mgr.add_memory("Temporary reminder to clean desk")
    assert len(memory_mgr.search_memories()) == 1

    # Successful delete
    deleted = memory_mgr.delete_memory(mid)
    assert deleted is True
    assert len(memory_mgr.search_memories()) == 0

    # Non-existent delete
    deleted_again = memory_mgr.delete_memory(999)
    assert deleted_again is False


# =====================================================================
# 2. To-Do Management Tests
# =====================================================================

def test_todo_crud_lifecycle(memory_mgr):
    # Add tasks
    t1 = memory_mgr.add_todo("Buy groceries", priority="low")
    t2 = memory_mgr.add_todo("Prepare quarterly presentation", priority="high")

    # List pending
    pending = memory_mgr.list_todos("pending")
    assert len(pending) == 2
    assert pending[1]["priority"] == "high"

    # Complete a task
    assert memory_mgr.complete_todo(t1) is True

    # Check pending vs completed
    pending_after = memory_mgr.list_todos("pending")
    assert len(pending_after) == 1
    assert pending_after[0]["id"] == t2

    completed = memory_mgr.list_todos("completed")
    assert len(completed) == 1
    assert completed[0]["id"] == t1
    assert completed[0]["completed_at"] is not None

    # Delete task
    assert memory_mgr.delete_todo(t2) is True
    assert len(memory_mgr.list_todos("all")) == 1


# =====================================================================
# 3. Memory & Task Agent Tools Tests
# =====================================================================

def test_remember_and_recall_tools(memory_mgr):
    remember_tool = RememberFactTool(memory_mgr)
    recall_tool = RecallMemoriesTool(memory_mgr)

    # Empty recall
    assert "No long-term memories" in recall_tool.execute()

    # Save preference
    save_res = remember_tool.execute(
        content="Prefers Python over JavaScript for backend",
        category="preference",
    )
    assert "Successfully saved to memory (ID #1" in save_res

    # Recall preference
    recall_res = recall_tool.execute(query="Python")
    assert "Found 1 memory item(s)" in recall_res
    assert "Prefers Python over JavaScript" in recall_res


def test_delete_memory_tool(memory_mgr):
    remember_tool = RememberFactTool(memory_mgr)
    del_tool = DeleteMemoryTool(memory_mgr)

    remember_tool.execute("Fact to be removed")
    res = del_tool.execute(memory_id=1)
    assert "permanently deleted" in res

    # Bad ID
    err_res = del_tool.execute(memory_id=99)
    assert "Error: No memory found" in err_res


def test_manage_todos_tool_actions(memory_mgr):
    todo_tool = ManageTodosTool(memory_mgr)

    # Add task
    add_res = todo_tool.execute(action="add", title="File taxes", priority="high")
    assert "Added to-do [Task #1]" in add_res

    # List tasks
    list_res = todo_tool.execute(action="list", status="pending")
    assert "File taxes" in list_res
    assert "[HIGH]" in list_res

    # Complete task
    comp_res = todo_tool.execute(action="complete", todo_id=1)
    assert "marked as COMPLETED" in comp_res

    # Delete task
    del_res = todo_tool.execute(action="delete", todo_id=1)
    assert "Task #1 deleted" in del_res


def test_tool_registry_with_memory_tools(memory_mgr):
    registry = ToolRegistry()
    registry.register(RememberFactTool(memory_mgr))
    registry.register(RecallMemoriesTool(memory_mgr))
    registry.register(DeleteMemoryTool(memory_mgr))
    registry.register(ManageTodosTool(memory_mgr))

    schemas = registry.get_schemas()
    names = [s["name"] for s in schemas]
    assert "remember_fact" in names
    assert "recall_memories" in names
    assert "delete_memory" in names
    assert "manage_todos" in names
