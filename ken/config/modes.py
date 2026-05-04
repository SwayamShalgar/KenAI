from dataclasses import dataclass
from typing import Dict, Literal

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


def get_mode_profile(mode: str | None, default_mode: ModeName) -> ModeProfile:
    if not mode:
        return MODE_PROFILES[default_mode]
    normalized = mode.strip().lower()
    if normalized not in MODE_PROFILES:
        return MODE_PROFILES[default_mode]
    return MODE_PROFILES[normalized]  # type: ignore[index]


def resolve_model_name(model_name: str | None, default_model: str) -> str:
    if not model_name:
        return default_model
    cleaned = model_name.strip()
    if not cleaned:
        return default_model
    alias = MODEL_ALIASES.get(cleaned.lower())
    return alias or cleaned
