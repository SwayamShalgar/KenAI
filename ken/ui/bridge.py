from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

from ken.app.router import handle_input
from ken.app.state import SessionState
from ken.config import get_mode_profile, resolve_model_name
from ken.services.llm_service import LlmService
from ken.services.memory_service import MemoryService
from ken.services.voice_service import VoiceService
from ken.ui.animations import clamp


@dataclass
class ConversationItem:
    role: str
    text: str


class AssistantBridge(QObject):
    user_message = pyqtSignal(str)
    assistant_started = pyqtSignal()
    assistant_chunk = pyqtSignal(str)
    assistant_finished = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    state_changed = pyqtSignal(str)
    level_changed = pyqtSignal(float)
    error_occurred = pyqtSignal(str)
    conversation_cleared = pyqtSignal()

    def __init__(self, *, voice_mode: bool = False, mode: str | None = None, model: str | None = None, benchmark: bool = False):
        super().__init__()
        self.memory_service = MemoryService()
        self.llm_service = LlmService()
        self.voice_service = VoiceService()
        self.state = SessionState(
            voice_mode=voice_mode,
            active_mode=get_mode_profile(mode).name,
            active_model=resolve_model_name(model),
            benchmark=benchmark,
        )
        self._turn_lock = threading.Lock()
        self._voice_listening = threading.Event()
        self._shutdown = threading.Event()
        self._voice_thread: threading.Thread | None = None
        self._mic_thread: threading.Thread | None = None
        self._conversation: list[ConversationItem] = []

    @property
    def conversation(self) -> list[ConversationItem]:
        return list(self._conversation)

    def set_session(self, *, mode: str, model: str, benchmark: bool):
        self.state.active_mode = get_mode_profile(mode).name
        self.state.active_model = resolve_model_name(model)
        self.state.benchmark = benchmark

    def submit_text(self, text: str, *, source: str = "typed"):
        text = text.strip()
        if not text:
            return
        threading.Thread(target=self._process_turn, args=(text, source), daemon=True).start()

    def clear_chat(self):
        self._conversation.clear()
        self.conversation_cleared.emit()

    def start_listening(self):
        if self._voice_listening.is_set():
            return
        self.voice_service.init_stt()
        self._voice_listening.set()
        self.state.voice_mode = True
        self.state_changed.emit("listening")
        self.status_changed.emit("Listening...")
        self._voice_thread = threading.Thread(target=self._voice_loop, daemon=True)
        self._voice_thread.start()
        # self._mic_thread = threading.Thread(target=self._mic_level_loop, daemon=True)
        # self._mic_thread.start()

    def stop_listening(self):
        self._voice_listening.clear()
        self.state.voice_mode = False
        self.state_changed.emit("idle")
        self.status_changed.emit("Idle")
        self.voice_service.stop_audio_playback()

    def shutdown(self):
        self._shutdown.set()
        self.stop_listening()
        self.voice_service.cleanup_audio()

    def _record(self, role: str, text: str):
        self._conversation.append(ConversationItem(role=role, text=text))

    def _process_turn(self, text: str, source: str):
        if not self._turn_lock.acquire(blocking=False):
            self.error_occurred.emit("Assistant is already processing a turn.")
            return
        try:
            self.user_message.emit(text)
            self._record("user", text)

            outcome = handle_input(text, self.state, self.memory_service, self.voice_service)
            if outcome.handled:
                if outcome.message:
                    self._record("assistant", outcome.message)
                    self.assistant_started.emit()
                    self.assistant_chunk.emit(outcome.message)
                    self.assistant_finished.emit(outcome.message)
                if outcome.speak_text and self.state.voice_mode:
                    self.state_changed.emit("speaking")
                    asyncio.run(self.voice_service.generate_and_play_tts(outcome.speak_text))
                self.status_changed.emit("Idle")
                self.state_changed.emit("idle")
                return

            self.state_changed.emit("processing")
            self.status_changed.emit("Processing...")
            asyncio.run(self._stream_response(text, prompt=outcome.modified_prompt))
            self.state_changed.emit("idle")
            self.status_changed.emit("Idle")
        except Exception as exc:
            self.state_changed.emit("error")
            self.status_changed.emit("Error")
            self.error_occurred.emit(str(exc))
        finally:
            self._turn_lock.release()

    async def _stream_response(self, text: str, prompt: str | None = None):
        full_response = ""
        self.assistant_started.emit()
        actual_prompt = prompt or text
        try:
            async for chunk in self.llm_service.stream_chat(
                actual_prompt,
                self.memory_service.memory,
                mode=self.state.active_mode,
                model=self.state.active_model,
                benchmark=self.state.benchmark,
            ):
                full_response += chunk
                self.assistant_chunk.emit(chunk)
            self._record("assistant", full_response)
            self.assistant_finished.emit(full_response)
            if self.state.voice_mode and full_response.strip():
                self.state_changed.emit("speaking")
                self.status_changed.emit("Speaking...")
                await self.voice_service.generate_and_play_tts(full_response)
        except Exception as exc:
            self.state_changed.emit("error")
            self.error_occurred.emit(str(exc))
            raise

    def _voice_loop(self):
        while self._voice_listening.is_set() and not self._shutdown.is_set():
            self.status_changed.emit("Listening...")
            self.state_changed.emit("listening")
            text = self.voice_service.listen_for_speech()
            if not self._voice_listening.is_set() or self._shutdown.is_set():
                break
            if text:
                self._process_turn(text.strip(), "voice")

    def _mic_level_loop(self):
        try:
            import numpy as np
            import sounddevice as sd
        except Exception:
            return

        def callback(indata, frames, time_info, status):
            if status:
                return
            level = float(np.sqrt(np.mean(np.square(indata))))
            self.level_changed.emit(clamp(level * 8.0))

        try:
            with sd.InputStream(callback=callback, channels=1, samplerate=16000):
                while self._voice_listening.is_set() and not self._shutdown.is_set():
                    time.sleep(0.05)
        except Exception:
            return


__all__ = ["AssistantBridge", "ConversationItem"]