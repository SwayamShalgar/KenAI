import httpx
import json

from ken.config import config, get_mode_profile, resolve_model_name
from ken.services.memory.store import Memory


def _build_system_prompt(mode: str, memory: Memory) -> str:
    profile = get_mode_profile(mode)
    memory_hint = ""
    if memory.user_preferences:
        prefs = "; ".join(memory.user_preferences[-6:])
        memory_hint = f"\nUser preferences to honor: {prefs}"

    return (
        "You are Ken, a local-first Linux AI assistant running on Ubuntu. "
        "Be accurate, intentional, and practical.\n"
        "Core operating rules:\n"
        "1) If uncertain, explicitly say what is uncertain.\n"
        "2) Never fabricate Linux commands, packages, files, logs, or tool output.\n"
        "3) Ask a clarifying question when information is missing for a safe answer.\n"
        "4) Prefer verified command patterns and explain risky commands before suggesting them.\n"
        "5) Keep answers local-first and privacy-preserving unless user asks otherwise.\n"
        f"Mode: {profile.name} - {profile.description}\n"
        f"Mode behavior: {profile.style_instruction}"
        f"{memory_hint}"
    )


def _quality_note(text: str, first_token_latency_s: float | None) -> str:
    words = len(text.split())
    low_confidence_markers = [
        "not sure",
        "uncertain",
        "i don't know",
        "might be",
        "possibly",
    ]
    has_uncertainty = any(marker in text.lower() for marker in low_confidence_markers)

    if not text.strip():
        return "Empty response; likely model load or stream interruption."
    if has_uncertainty:
        return "Model signaled uncertainty; safer than guessing."
    if words < 10:
        return "Very concise answer; good for speed, may need follow-up depth."
    if first_token_latency_s is not None and first_token_latency_s > 2.5:
        return "Good content quality but first token latency was high."
    return "Balanced response quality for local assistant use."


async def stream_chat(
    prompt: str,
    memory: Memory,
    *,
    mode: str,
    model: str | None = None,
    benchmark: bool = False,
    benchmark_report: dict | None = None,
):
    """Yields tokens from the Ollama chat stream."""
    profile = get_mode_profile(mode)
    chosen_model = resolve_model_name(model)

    memory.add_user(prompt)

    system_msg = {
        "role": "system",
        "content": _build_system_prompt(profile.name, memory),
    }

    payload = {
        "model": chosen_model,
        "messages": [system_msg] + memory.get_context(),
        "stream": True,
        "keep_alive": config.ollama_keep_alive,
        "options": {
            "temperature": profile.temperature,
            "top_p": profile.top_p,
            "repeat_penalty": profile.repeat_penalty,
            "num_predict": profile.num_predict,
            "num_ctx": profile.num_ctx,
            "num_gpu": config.ollama_num_gpu,
            "num_thread": config.ollama_num_thread,
        },
    }

    started_at = None
    first_token_latency_s = None
    server_eval_count = None
    server_eval_duration_ns = None
    full_response = ""
    loop = None

    try:
        import asyncio

        loop = asyncio.get_running_loop()
        started_at = loop.time()
        timeout = httpx.Timeout(connect=10.0, read=None, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{config.ollama_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if chunk:
                        try:
                            data = json.loads(chunk)
                            if data.get("done"):
                                server_eval_count = data.get("eval_count")
                                server_eval_duration_ns = data.get("eval_duration")
                            if "message" in data and "content" in data["message"]:
                                token = data["message"]["content"]
                                full_response += token
                                if first_token_latency_s is None and started_at is not None:
                                    first_token_latency_s = round(loop.time() - started_at, 3)
                                yield token
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
        yield "\n[Error] Unable to connect to Ollama. Is it running?"
    except httpx.ReadTimeout:
        yield "\n[Error] Ollama timed out. The model might be loading or the system is under heavy load."
    except Exception as e:
        yield f"\n[Error] Unexpected error from LLM: {str(e)}"

    if full_response:
        memory.add_assistant(full_response)

    if benchmark and benchmark_report is not None and loop is not None and started_at is not None:
        total_latency_s = round(loop.time() - started_at, 3)
        if server_eval_count and server_eval_duration_ns:
            eval_secs = server_eval_duration_ns / 1_000_000_000
            tokens_per_s = round(server_eval_count / eval_secs, 2) if eval_secs > 0 else 0.0
            output_tokens = int(server_eval_count)
        else:
            output_tokens = max(1, int(len(full_response) / 4)) if full_response else 0
            generation_time = max(total_latency_s - (first_token_latency_s or 0.0), 0.001)
            tokens_per_s = round(output_tokens / generation_time, 2)

        benchmark_report.update(
            {
                "mode": profile.name,
                "model": chosen_model,
                "prompt_chars": len(prompt),
                "response_chars": len(full_response),
                "output_tokens_est": output_tokens,
                "first_token_latency_s": first_token_latency_s,
                "total_latency_s": total_latency_s,
                "tokens_per_s": tokens_per_s,
                "quality_note": _quality_note(full_response, first_token_latency_s),
            }
        )
