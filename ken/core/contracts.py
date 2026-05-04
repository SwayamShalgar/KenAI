from collections.abc import AsyncIterator
from typing import Protocol

from ken.core.models import Message, ToolResult


class MemoryStore(Protocol):
    def add_user(self, text: str):
        ...

    def add_assistant(self, text: str):
        ...

    def get_context(self) -> list[dict]:
        ...


class LlmProvider(Protocol):
    async def stream_chat(
        self,
        prompt: str,
        memory: MemoryStore,
        *,
        mode: str,
        model: str | None = None,
        benchmark: bool = False,
        benchmark_report: dict | None = None,
    ) -> AsyncIterator[str]:
        ...


class Tool(Protocol):
    name: str
    description: str

    async def execute(self, text: str) -> ToolResult:
        ...
