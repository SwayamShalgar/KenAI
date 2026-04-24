import json
from pathlib import Path
from typing import List, Dict, Any
from ken.config import config

class Memory:
    def __init__(self):
        self.memory_file = config.data_dir / "memory.json"
        self.messages: List[Dict[str, Any]] = self.load()

    def load(self) -> List[Dict[str, Any]]:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.messages[-50:], f)  # Keep last 50 messages to stay lightweight

    def add_user(self, text: str):
        self.messages.append({"role": "user", "content": text})
        self.save()

    def add_assistant(self, text: str):
        self.messages.append({"role": "assistant", "content": text})
        self.save()
        
    def add_system(self, text: str):
        pass
        
    def get_context(self) -> List[Dict[str, Any]]:
        return self.messages[-10:] # send last 10 messages for context
    
    def clear(self):
        self.messages = []
        self.save()
