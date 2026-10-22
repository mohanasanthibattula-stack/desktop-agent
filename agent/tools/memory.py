"""
Long-Term Memory and To-Do Tools
Enables the agent to remember facts/preferences, recall past knowledge, and manage tasks.
"""
from typing import Any, Optional
from agent.memory.sqlite_mem import MemoryManager
from .base import BaseTool


class RememberFactTool(BaseTool):
    """Tool to save a user preference, personal fact, or project note to long-term memory."""

    name = "remember_fact"
    description = (
        "Saves a personal fact, preference, contact detail, or project note into permanent long-term memory. "
        "Use this whenever the user says 'remember that...', 'my favorite...', or shares ongoing project details."
    )
    parameters = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The exact fact, preference, or information to remember.",
            },
            "category": {
                "type": "string",
                "enum": ["preference", "fact", "project", "general"],
                "description": "Category for organizing the memory (default: general).",
            },
        },
        "required": ["content"],
    }
    requires_confirmation = False

    def __init__(self, memory_mgr: MemoryManager):
        self.memory_mgr = memory_mgr

    def execute(self, content: str, category: str = "general", **kwargs: Any) -> str:
        clean_content = content.strip()
        if not clean_content:
            return "Error: Memory content cannot be empty."

        mem_id = self.memory_mgr.add_memory(content=clean_content, category=category)
        return f"Successfully saved to memory (ID #{mem_id}, Category: {category}): '{clean_content}'"


class RecallMemoriesTool(BaseTool):
    """Tool to search or retrieve stored memories from SQLite."""

    name = "recall_memories"
    description = (
        "Searches or lists facts, preferences, and project details stored in the user's long-term memory. "
        "Leave query empty to list all stored memories."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keyword to search memories for (optional; leave empty to retrieve all).",
            },
        },
        "required": [],
    }
    requires_confirmation = False

    def __init__(self, memory_mgr: MemoryManager):
        self.memory_mgr = memory_mgr

    def execute(self, query: str = "", **kwargs: Any) -> str:
        results = self.memory_mgr.search_memories(query=query)
        if not results:
            if query.strip():
                return f"No memories found matching keyword '{query}'."
            return "No long-term memories have been saved yet."

        header = f"Found {len(results)} memory item(s)" + (f" matching '{query}':" if query.strip() else ":")
        lines = [header]
        for item in results:
            lines.append(
                f"  • [ID #{item['id']}] ({item['category'].upper()}) {item['content']}  (Saved: {item['created_at']})"
            )
        return "\n".join(lines)


class DeleteMemoryTool(BaseTool):
    """Tool to delete a stored memory by ID."""

    name = "delete_memory"
    description = "Permanently deletes a specific memory item from long-term memory using its ID number."
    parameters = {
        "type": "object",
        "properties": {
            "memory_id": {
                "type": "integer",
                "description": "The numeric ID of the memory item to delete.",
            },
        },
        "required": ["memory_id"],
    }
    requires_confirmation = False

    def __init__(self, memory_mgr: MemoryManager):
        self.memory_mgr = memory_mgr

    def execute(self, memory_id: int, **kwargs: Any) -> str:
        try:
            mid = int(memory_id)
        except (ValueError, TypeError):
            return f"Error: Invalid memory ID '{memory_id}'. Must be an integer."

        success = self.memory_mgr.delete_memory(mid)
        if success:
            return f"Memory item [ID #{mid}] was permanently deleted."
        return f"Error: No memory found with ID #{mid}."


class ManageTodosTool(BaseTool):
    """Tool to add, list, complete, and delete to-do tasks in local SQLite."""

    name = "manage_todos"
    description = (
        "Manages your local to-do task list. Actions supported: "
        "'add' (add task), 'list' (view tasks), 'complete' (mark done), 'delete' (remove task)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "complete", "delete"],
                "description": "The task action to perform.",
            },
            "title": {
                "type": "string",
                "description": "The task title/description (required for 'add').",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Task priority level (optional, default: medium).",
            },
            "todo_id": {
                "type": "integer",
                "description": "Numeric ID of the task (required for 'complete' or 'delete').",
            },
            "status": {
                "type": "string",
                "enum": ["pending", "completed", "all"],
                "description": "Filter tasks by status when listing (default: pending).",
            },
        },
        "required": ["action"],
    }
    requires_confirmation = False

    def __init__(self, memory_mgr: MemoryManager):
        self.memory_mgr = memory_mgr

    def execute(
        self,
        action: str,
        title: Optional[str] = None,
        priority: str = "medium",
        todo_id: Optional[int] = None,
        status: str = "pending",
        **kwargs: Any,
    ) -> str:
        act = action.lower().strip()

        if act == "add":
            if not title or not title.strip():
                return "Error: A task title is required when adding a to-do."
            tid = self.memory_mgr.add_todo(title=title, priority=priority)
            return f"Added to-do [Task #{tid}]: '{title.strip()}' (Priority: {priority.upper()})"

        elif act == "list":
            todos = self.memory_mgr.list_todos(status=status)
            if not todos:
                return f"No {status} tasks found in your to-do list."

            lines = [f"Your To-Do List ({status.upper()}):"]
            for t in todos:
                status_icon = "☑" if t["status"] == "completed" else "☐"
                lines.append(
                    f"  {status_icon} [ID #{t['id']}] [{t['priority'].upper()}] {t['title']} (Status: {t['status']})"
                )
            return "\n".join(lines)

        elif act == "complete":
            if todo_id is None:
                return "Error: You must provide a 'todo_id' to complete a task."
            ok = self.memory_mgr.complete_todo(int(todo_id))
            if ok:
                return f"Task #{todo_id} marked as COMPLETED."
            return f"Error: Task #{todo_id} not found."

        elif act == "delete":
            if todo_id is None:
                return "Error: You must provide a 'todo_id' to delete a task."
            ok = self.memory_mgr.delete_todo(int(todo_id))
            if ok:
                return f"Task #{todo_id} deleted."
            return f"Error: Task #{todo_id} not found."

        return f"Error: Unknown action '{action}'. Supported: 'add', 'list', 'complete', 'delete'."
