from dataclasses import dataclass


@dataclass
class SessionStarted:
    mode: str
    model: str


@dataclass
class SessionEnded:
    reason: str
