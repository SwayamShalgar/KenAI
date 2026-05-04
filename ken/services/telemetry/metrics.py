from dataclasses import dataclass


@dataclass
class Counter:
    name: str
    value: int = 0

    def inc(self, delta: int = 1):
        self.value += delta
