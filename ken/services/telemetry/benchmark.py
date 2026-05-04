from dataclasses import dataclass


@dataclass
class BenchmarkReport:
    mode: str
    model: str
    prompt_chars: int
    response_chars: int
    output_tokens_est: int
    first_token_latency_s: float | None
    total_latency_s: float
    tokens_per_s: float
    quality_note: str
