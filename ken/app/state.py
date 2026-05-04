from dataclasses import dataclass


@dataclass
class SessionState:
    voice_mode: bool
    active_mode: str
    active_model: str
    benchmark: bool
