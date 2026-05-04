import asyncio

from ken.services.voice.engine import (
    cleanup_audio,
    generate_and_play_tts,
    init_stt,
    listen_for_interrupt,
    listen_for_speech,
    stop_audio_playback,
)


class VoiceService:
    def __init__(self):
        self.interrupt_event = asyncio.Event()
        self.speaking_event = asyncio.Event()

    def init_stt(self):
        init_stt()

    def listen_for_speech(self, timeout: int = 5, phrase_time_limit: int = 8) -> str:
        return listen_for_speech(timeout=timeout, phrase_time_limit=phrase_time_limit)

    async def generate_and_play_tts(
        self,
        text: str,
        interrupt_event: asyncio.Event | None = None,
    ):
        await generate_and_play_tts(
            text,
            interrupt_event=interrupt_event or self.interrupt_event,
            speaking_event=self.speaking_event,
        )

    async def listen_for_interrupt(
        self,
        interrupt_event: asyncio.Event | None = None,
    ) -> str:
        return await listen_for_interrupt(interrupt_event or self.interrupt_event)

    def stop_audio_playback(self):
        stop_audio_playback()

    def cleanup_audio(self):
        cleanup_audio()
