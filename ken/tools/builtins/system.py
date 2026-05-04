from ken.tools.base import ToolResult


def handle_shutdown() -> ToolResult:
    return ToolResult(ok=True, message="Shutdown requested.")
