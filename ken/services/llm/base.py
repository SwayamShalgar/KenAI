from collections.abc import AsyncIterator
from typing import Protocol

from ken.services.memory.store import Memory


class LlmProvider(Protocol):
    async def stream_chat(
        self,
        prompt: str,
        memory: Memory,
        *,
        mode: str,
        model: str | None = None,
        benchmark: bool = False,
        benchmark_report: dict | None = None,
    ) -> AsyncIterator[str]:
        ...
