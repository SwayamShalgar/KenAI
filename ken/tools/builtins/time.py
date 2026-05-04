import datetime

from ken.tools.base import ToolResult


def handle_time() -> ToolResult:
    now = datetime.datetime.now().strftime("%I:%M %p, %A, %B %d")
    return ToolResult(ok=True, message=f"The current time is {now}.")
