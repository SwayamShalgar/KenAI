import json
from typing import Any, Dict, List

from ken.config import config


class Memory:
    def __init__(self):
        self.memory_file = config.data_dir / "memory.json"
        self.messages: List[Dict[str, Any]] = []
        self.summary: str = ""
        self.user_preferences: List[str] = []
        self._load_state()

    def _load_state(self):
        loaded = self.load()
        if isinstance(loaded, list):
            # Backward compatibility: old format stored a raw message list.
            self.messages = loaded
            return

        self.messages = loaded.get("messages", [])
        self.summary = loaded.get("summary", "")
        self.user_preferences = loaded.get("user_preferences", [])

    def load(self) -> List[Dict[str, Any]] | Dict[str, Any]:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            payload = {
                "summary": self.summary,
                "user_preferences": self.user_preferences[-12:],
                "messages": self.messages[-120:],
            }
            json.dump(payload, f, ensure_ascii=True, indent=2)

    def add_user(self, text: str):
        self.messages.append({"role": "user", "content": text})
        self._capture_preferences(text)
        self._compact_if_needed()
        self.save()

    def add_assistant(self, text: str):
        self.messages.append({"role": "assistant", "content": text})
        self._compact_if_needed()
        self.save()

    def add_system(self, text: str):
        self.messages.append({"role": "system", "content": text})
        self._compact_if_needed()
        self.save()

    def get_context(self) -> List[Dict[str, Any]]:
        context: List[Dict[str, Any]] = []

        if self.summary.strip():
            context.append(
                {
                    "role": "system",
                    "content": "Conversation summary so far:\n" + self.summary.strip(),
                }
            )

        if self.user_preferences:
            pref_text = "\n".join(f"- {item}" for item in self.user_preferences[-8:])
            context.append(
                {
                    "role": "system",
                    "content": "Known user preferences:\n" + pref_text,
                }
            )

        context.extend(self.messages[-config.memory_recent_window :])
        return context

    def clear(self):
        self.messages = []
        self.summary = ""
        self.user_preferences = []
        self.save()

    def _capture_preferences(self, text: str):
        lowered = text.lower().strip()
        candidate: str | None = None

        if lowered.startswith("my name is "):
            candidate = text.strip()
        elif "i prefer" in lowered:
            candidate = text.strip()
        elif "please keep" in lowered:
            candidate = text.strip()
        elif "always" in lowered and len(text.split()) <= 14:
            candidate = text.strip()

        if not candidate:
            return

        cleaned = candidate[:160]
        if cleaned not in self.user_preferences:
            self.user_preferences.append(cleaned)
            self.user_preferences = self.user_preferences[-16:]

    def _compact_if_needed(self):
        trigger = config.memory_summary_trigger
        keep = config.memory_keep_after_summary
        if len(self.messages) <= trigger:
            return

        older = self.messages[:-keep]
        if not older:
            return

        rollup = self._summarize_messages(older)
        if not rollup:
            self.messages = self.messages[-keep:]
            return

        if self.summary.strip():
            merged = self.summary.strip() + "\n" + rollup
        else:
            merged = rollup

        self.summary = merged[-config.memory_summary_char_limit :]
        self.messages = self.messages[-keep:]

    def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = str(msg.get("content", "")).strip()
            if not content:
                continue

            one_line = " ".join(content.split())
            if len(one_line) > 160:
                one_line = one_line[:157] + "..."

            if role == "user":
                lines.append(f"User asked: {one_line}")
            elif role == "assistant":
                lines.append(f"Ken answered: {one_line}")

            if len(lines) >= 18:
                break

        if not lines:
            return ""

        return "\n".join(lines)
