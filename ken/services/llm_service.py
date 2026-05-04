from collections.abc import AsyncIterator

from ken.services.llm.ollama import stream_chat
from ken.services.memory.store import Memory


class LlmService:
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
        async for chunk in stream_chat(
            prompt,
            memory,
            mode=mode,
            model=model,
            benchmark=benchmark,
            benchmark_report=benchmark_report,
        ):
            yield chunk
