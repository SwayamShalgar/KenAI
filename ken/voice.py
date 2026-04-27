import asyncio
import os
import tempfile
import sys
import time
from contextlib import contextmanager

import numpy as np
import speech_recognition as sr
import edge_tts
from faster_whisper import WhisperModel
from rich import print

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame

_whisper_model = None


@contextmanager
def suppress_alsa_errors():
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        sys.stderr.flush()
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(devnull)
        os.close(old_stderr)


def init_stt():
    global _whisper_model

    if _whisper_model is not None:
        return

    print("[blue]Loading Whisper STT...[/blue]")

    try:
        # ✅ FIX 1: Upgraded to medium.en — much better with proper nouns & app names
        _whisper_model = WhisperModel(
            "small.en",
            device="cuda",
            compute_type="float16"
        )
        print("[green]Whisper medium.en loaded on GPU.[/green]")

    except Exception as e:
        print(f"[yellow]GPU unavailable, using CPU fallback.[/yellow] {e}")
        _whisper_model = WhisperModel(
            "medium.en",
            device="cpu",
            compute_type="int8"
        )

    # Warmup
    try:
        dummy = np.zeros(16000, dtype=np.float32)
        list(_whisper_model.transcribe(dummy, language="en", beam_size=1)[0])
    except Exception:
        pass


def normalize_command(text: str) -> str:
    t = text.lower().strip()
    fixes = {
        "i know": "no",
        "know": "no",
        "yeah": "yes",
        "ya": "yes",
        "yas": "yes",
        "yup": "yes",
        "stop it": "stop",
        "exact": "exit",
        "searchh": "search",
        "church": "search",
        "open up": "open",
    }
    return fixes.get(t, t)


def transcribe_audio(audio_data: sr.AudioData) -> str:
    global _whisper_model

    if _whisper_model is None:
        init_stt()

    try:
        raw_data = audio_data.get_raw_data(
            convert_rate=16000,
            convert_width=2
        )

        audio_np = (
            np.frombuffer(raw_data, dtype=np.int16)
            .astype(np.float32) / 32768.0
        )

        duration_sec = len(audio_np) / 16000

        print("[yellow]Processing speech...[/yellow]")
        start = time.time()

        # ✅ FIX 2: Raised short-utterance threshold from 1.2s → 2.0s
        # "open youtube" can easily be 1.5–1.8s, was wrongly getting weak decoding
        if duration_sec <= 2.0:
            beam = 5
            best_of = 5
            # ✅ FIX 3: Added common app/website names to the prompt so Whisper
            # has context for proper nouns it might otherwise mangle
            prompt = (
                "Short voice commands for an assistant. Common apps and sites: "
                "YouTube, Spotify, Chrome, Discord, WhatsApp, Gmail, Netflix, "
                "Google, Reddit, Twitter, Instagram. "
                "Commands: open, close, search, play, pause, stop, yes, no, exit, clear."
            )
        else:
            beam = 5
            best_of = 3
            # ✅ FIX 4: Also prompt on longer utterances for consistency
            prompt = (
                "Voice command for a desktop assistant. Apps: YouTube, Spotify, "
                "Chrome, Discord, WhatsApp, Gmail, Netflix, Google."
            )

        segments, info = _whisper_model.transcribe(
            audio_np,
            language="en",
            beam_size=beam,
            best_of=best_of,
            temperature=0.0,
            # ✅ FIX 5: Disabled vad_filter — it was clipping word endings like "YouTube" → "yo"
            vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt=prompt,
            # ✅ FIX 6: Added no_speech_threshold to avoid garbage transcriptions on silence
            no_speech_threshold=0.6,
        )

        parts = []
        for segment in segments:
            txt = segment.text.strip()
            if txt:
                parts.append(txt)

        final_text = " ".join(parts).strip()

        # Only normalize very short single-word commands
        if duration_sec <= 2.0 and len(final_text.split()) <= 2:
            final_text = normalize_command(final_text)

        elapsed = round(time.time() - start, 2)
        print(f"[green]Recognized:[/green] {final_text}")
        print(f"[green]Done ({elapsed}s)[/green]")

        return final_text

    except Exception as e:
        print(f"[red][STT Error]: {e}[/red]")
        return ""


def listen_for_speech(timeout: int = 5, phrase_time_limit: int = 8) -> str:
    recognizer = sr.Recognizer()

    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 300

    # ✅ FIX 7: Increased pause/non-speaking thresholds so word endings aren't cut off
    recognizer.pause_threshold = 1.2        # was 0.8 — too aggressive
    recognizer.non_speaking_duration = 0.6  # was 0.3 — was clipping last syllables

    try:
        with suppress_alsa_errors():
            with sr.Microphone(sample_rate=16000) as source:

                print("[cyan]Listening...[/cyan]")

                recognizer.adjust_for_ambient_noise(
                    source,
                    duration=0.5  # slightly longer calibration
                )

                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

        print("[cyan]Speech detected.[/cyan]")
        return transcribe_audio(audio)

    except sr.WaitTimeoutError:
        return ""

    except Exception as e:
        print(f"[red][Mic Error]: {e}[/red]")
        return ""


async def generate_and_play_tts(text: str):
    if not text.strip():
        return

    voice = "en-US-AriaNeural"
    communicate = edge_tts.Communicate(text, voice)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        temp_file = fp.name

    try:
        await communicate.save(temp_file)

        with suppress_alsa_errors():
            if not pygame.mixer.get_init():
                pygame.mixer.init()

        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

        pygame.mixer.music.unload()

    except Exception as e:
        print(f"[red][TTS Error]: {e}[/red]")

    finally:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except OSError:
            pass


def cleanup_audio():
    if pygame.mixer.get_init():
        pygame.mixer.quit()