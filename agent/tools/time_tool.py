"""
Time Tool
Allows the agent to fetch the current local time and date.
"""
from datetime import datetime
from typing import Any
from .base import BaseTool


class GetCurrentTimeTool(BaseTool):
    """Tool to retrieve current local date and time."""

    name = "get_current_time"
    description = "Returns the current local date, time, and day of the week on the host Windows machine."
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    requires_confirmation = False

    def execute(self, **kwargs: Any) -> str:
        now = datetime.now()
        return now.strftime("Current local time: %A, %B %d, %Y at %I:%M:%S %p")
