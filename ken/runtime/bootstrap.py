from ken.services.llm_service import LlmService
from ken.services.memory_service import MemoryService
from ken.services.voice_service import VoiceService


def build_services():
    return {
        "llm": LlmService(),
        "memory": MemoryService(),
        "voice": VoiceService(),
    }
