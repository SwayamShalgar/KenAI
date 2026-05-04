from ken.tools.base import ToolResult


def handle_open_url(url: str) -> ToolResult:
    return ToolResult(ok=True, message=f"Opening {url} in your browser...")
