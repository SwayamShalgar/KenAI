from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ToolResult:
    ok: bool
    message: str
    data: Dict[str, Any] | None = None


class Tool:
    name: str
    description: str

    async def execute(self, text: str) -> ToolResult:
        raise NotImplementedError
