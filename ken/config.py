from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal

from pydantic_settings import BaseSettings

ModeName = Literal["linux", "coding", "tutor", "fast", "think"]


@dataclass(frozen=True)
class ModeProfile:
    name: ModeName
    description: str
    temperature: float
    top_p: float
    repeat_penalty: float
    num_predict: int
    num_ctx: int
    style_instruction: str


MODE_PROFILES: Dict[ModeName, ModeProfile] = {
    "linux": ModeProfile(
        name="linux",
        description="Concise Linux troubleshooting and command-first guidance.",
        temperature=0.2,
        top_p=0.9,
        repeat_penalty=1.15,
        num_predict=220,
        num_ctx=2048,
        style_instruction=(
            "Prioritize terminal-first Linux troubleshooting. Provide safe, verified commands "
            "with short explanations and expected output checks."
        ),
    ),
    "coding": ModeProfile(
        name="coding",
        description="Debugging and implementation support with practical code snippets.",
        temperature=0.25,
        top_p=0.92,
        repeat_penalty=1.12,
        num_predict=420,
        num_ctx=3072,
        style_instruction=(
            "Focus on debugging logic, clear code examples, and concrete implementation steps."
        ),
    ),
    "tutor": ModeProfile(
        name="tutor",
        description="Stepwise educational explanations with checks for understanding.",
        temperature=0.45,
        top_p=0.95,
        repeat_penalty=1.1,
        num_predict=520,
        num_ctx=3072,
        style_instruction=(
            "Teach step by step, explain tradeoffs, and keep explanations beginner-friendly "
            "without being vague."
        ),
    ),
    "fast": ModeProfile(
        name="fast",
        description="Lowest-latency short answers.",
        temperature=0.15,
        top_p=0.88,
        repeat_penalty=1.08,
        num_predict=120,
        num_ctx=1536,
        style_instruction=(
            "Return the shortest useful answer. Prefer one to three bullets max."
        ),
    ),
    "think": ModeProfile(
        name="think",
        description="Higher-depth reasoning mode for non-trivial tasks.",
        temperature=0.35,
        top_p=0.93,
        repeat_penalty=1.14,
        num_predict=700,
        num_ctx=4096,
        style_instruction=(
            "Reason carefully before answering. Offer assumptions, edge cases, and a robust plan."
        ),
    ),
}


MODEL_ALIASES = {
    "llama": "llama3.2:3b",
    "llama3": "llama3.2:3b",
    "llama3.2": "llama3.2:3b",
    "qwen": "qwen2.5:4b",
    "qwen2.5": "qwen2.5:4b",
    "mistral": "mistral:latest",
}


class KenConfig(BaseSettings):
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2:3b"
    default_mode: ModeName = "linux"
    request_timeout_s: float = 60.0
    ollama_keep_alive: str = "15m"

    # CPU-safe defaults; override with KEN_OLLAMA_NUM_GPU and KEN_OLLAMA_NUM_THREAD as needed.
    ollama_num_gpu: int = 0
    ollama_num_thread: int = 6

    memory_recent_window: int = 12
    memory_summary_trigger: int = 40
    memory_keep_after_summary: int = 12
    memory_summary_char_limit: int = 2200

    data_dir: Path = Path.home() / ".local" / "share" / "ken"

    class Config:
        env_prefix = "KEN_"


def get_mode_profile(mode: str | None) -> ModeProfile:
    if not mode:
        return MODE_PROFILES[config.default_mode]
    normalized = mode.strip().lower()
    if normalized not in MODE_PROFILES:
        return MODE_PROFILES[config.default_mode]
    return MODE_PROFILES[normalized]  # type: ignore[index]


def resolve_model_name(model_name: str | None) -> str:
    if not model_name:
        return config.model
    cleaned = model_name.strip()
    if not cleaned:
        return config.model
    alias = MODEL_ALIASES.get(cleaned.lower())
    return alias or cleaned


config = KenConfig()
config.data_dir.mkdir(parents=True, exist_ok=True)
