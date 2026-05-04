from dataclasses import dataclass
from typing import Any, Dict, Literal

Role = Literal["system", "user", "assistant"]


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class ToolResult:
    ok: bool
    message: str
    data: Dict[str, Any] | None = None
