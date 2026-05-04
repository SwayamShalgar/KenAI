from ken.services.memory.store import Memory


class MemoryService:
    def __init__(self):
        self._memory = Memory()

    @property
    def memory(self) -> Memory:
        return self._memory

    def clear(self):
        self._memory.clear()

    def add_user(self, text: str):
        self._memory.add_user(text)

    def add_assistant(self, text: str):
        self._memory.add_assistant(text)
