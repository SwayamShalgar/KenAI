from ken.tools.base import ToolResult


def handle_shell(command: str) -> ToolResult:
    return ToolResult(ok=True, message=f"Running shell: {command}")
