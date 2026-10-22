"""
Long-Term SQLite Memory Subsystem
Manages persistent storage for facts, user preferences, projects, and to-dos.
"""
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional


class MemoryManager:
    """Manages SQLite persistent storage for long-term agent memory."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Create tables for memories and to-dos if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Memories table (facts, preferences, project context)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL DEFAULT 'general',
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Todos table (task management)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            conn.commit()

    # =================================================================
    # Memories CRUD
    # =================================================================

    def add_memory(self, content: str, category: str = "general") -> int:
        """Store a new fact, preference, or note."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (category, content, created_at) VALUES (?, ?, ?)",
                (category.lower().strip(), content.strip(), now_str),
            )
            conn.commit()
            return cursor.lastrowid

    def search_memories(self, query: str = "") -> List[Dict[str, Any]]:
        """Search memories by keyword, or return all if query is empty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if query.strip():
                wildcard = f"%{query.strip().lower()}%"
                cursor.execute(
                    "SELECT * FROM memories WHERE LOWER(content) LIKE ? OR LOWER(category) LIKE ? ORDER BY id DESC",
                    (wildcard, wildcard),
                )
            else:
                cursor.execute("SELECT * FROM memories ORDER BY id DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_memory(self, memory_id: int) -> bool:
        """Delete a memory item by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    # =================================================================
    # To-Do Task CRUD
    # =================================================================

    def add_todo(self, title: str, priority: str = "medium") -> int:
        """Add a new task to the to-do list."""
        valid_priorities = ("low", "medium", "high")
        pri = priority.lower().strip() if priority.lower().strip() in valid_priorities else "medium"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO todos (title, priority, status, created_at) VALUES (?, ?, 'pending', ?)",
                (title.strip(), pri, now_str),
            )
            conn.commit()
            return cursor.lastrowid

    def list_todos(self, status: str = "pending") -> List[Dict[str, Any]]:
        """List tasks filtered by status ('pending', 'completed', or 'all')."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            st = status.lower().strip()
            if st in ("pending", "completed"):
                cursor.execute("SELECT * FROM todos WHERE status = ? ORDER BY id ASC", (st,))
            else:
                cursor.execute("SELECT * FROM todos ORDER BY status DESC, id ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def complete_todo(self, todo_id: int) -> bool:
        """Mark a task as completed."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE todos SET status = 'completed', completed_at = ? WHERE id = ?",
                (now_str, todo_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_todo(self, todo_id: int) -> bool:
        """Permanently delete a task by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()
            return cursor.rowcount > 0
