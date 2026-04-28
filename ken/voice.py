import asyncio
import os
import tempfile
import sys
import time
from contextlib import contextmanager
from typing import List, Tuple

import numpy as np
import speech_recognition as sr
import edge_tts
from faster_whisper import WhisperModel
from rich import print

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame

_whisper_model = None


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

def _env_flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _candidate_whisper_models() -> List[str]:
    preferred = os.getenv("KEN_WHISPER_MODEL", "medium.en").strip()  # ✅ default to medium.en
    fallbacks = [preferred, "small.en", "base.en", "tiny.en"]
    seen = set()
    unique = []
    for name in fallbacks:
        if name and name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def _candidate_whisper_runtime() -> List[Tuple[str, str]]:
    device = os.getenv("KEN_WHISPER_DEVICE", "auto").strip().lower()
    compute = os.getenv("KEN_WHISPER_COMPUTE_TYPE", "").strip()

    if device in {"cpu", "cuda"}:
        return [(device, compute or ("int8" if device == "cpu" else "float16"))]

    # ✅ Try CUDA first, fall back to CPU
    return [("cuda", "float16"), ("cpu", "int8")]


# ---------------------------------------------------------------------------
# ALSA noise suppression (Linux)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# STT init
# ---------------------------------------------------------------------------

def init_stt():
    global _whisper_model

    if _whisper_model is not None:
        return

    print("[blue]Loading Whisper STT...[/blue]")
    print("[dim]First run may take time while the model downloads.[/dim]")

    cache_dir = os.getenv("KEN_WHISPER_CACHE_DIR")
    local_only = _env_flag("KEN_WHISPER_LOCAL_ONLY", default=False)

    errors = []
    for model_name in _candidate_whisper_models():
        for device, compute_type in _candidate_whisper_runtime():
            try:
                print(
                    f"[cyan]Trying Whisper model={model_name} "
                    f"device={device} compute={compute_type}[/cyan]"
                )
                _whisper_model = WhisperModel(
                    model_name,
                    device=device,
                    compute_type=compute_type,
                    download_root=cache_dir,
                    local_files_only=local_only,
                )
                print(
                    f"[green]Whisper ready: model={model_name}, "
                    f"device={device}, compute={compute_type}[/green]"
                )
                break
            except Exception as e:
                errors.append(f"{model_name}/{device}/{compute_type}: {e}")
                _whisper_model = None

        if _whisper_model is not None:
            break

    if _whisper_model is None:
        print("[red]Failed to initialize Whisper STT.[/red]")
        for err in errors:
            print(f"[red]  - {err}[/red]")
        raise RuntimeError(
            "Whisper STT init failed. "
            "Try: KEN_WHISPER_MODEL=tiny.en or KEN_WHISPER_DEVICE=cpu"
        )

    # Warmup pass — reduces lag on first real transcription
    try:
        dummy = np.zeros(16000, dtype=np.float32)
        list(_whisper_model.transcribe(dummy, language="en", beam_size=1)[0])
        print("[dim]Whisper warmup done.[/dim]")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Command normalizer
# ---------------------------------------------------------------------------

def normalize_command(text: str) -> str:
    """Fix common Whisper mishears for short single-word commands."""
    t = text.lower().strip()
    fixes = {
        "i know":  "no",
        "know":    "no",
        "yeah":    "yes",
        "ya":      "yes",
        "yas":     "yes",
        "yup":     "yes",
        "stop it": "stop",
        "exact":   "exit",
        "searchh": "search",
        "church":  "search",
        "open up": "open",
    }
    return fixes.get(t, t)


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

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
        print(f"[dim]Audio duration: {duration_sec:.2f}s[/dim]")
        print("[yellow]Processing speech...[/yellow]")
        start = time.time()

        # ✅ Short utterance threshold raised to 2.0s
        # "open youtube" is ~1.5–1.8s and was getting weak beam decoding before
        if duration_sec <= 2.0:
            beam   = 5
            best_of = 5
            # ✅ Rich prompt gives Whisper vocabulary context for app names
            prompt = (
                "Short voice commands for a desktop assistant. "
                "Common apps and websites: YouTube, Spotify, Chrome, Discord, "
                "WhatsApp, Gmail, Netflix, Google, Reddit, Twitter, Instagram, VS Code. "
                "Commands: open, close, search, play, pause, stop, yes, no, exit, clear, next, back."
            )
        else:
            beam    = 5
            best_of = 3
            prompt = (
                "Voice command for a desktop assistant. "
                "Apps: YouTube, Spotify, Chrome, Discord, WhatsApp, Gmail, Netflix, Google."
            )

        segments, info = _whisper_model.transcribe(
            audio_np,
            language="en",
            beam_size=beam,
            best_of=best_of,
            temperature=0.0,
            vad_filter=False,               # ✅ OFF — was clipping word endings ("YouTube" → "yo")
            condition_on_previous_text=False,
            initial_prompt=prompt,
            no_speech_threshold=0.6,        # ✅ Avoids garbage output on near-silence
        )

        parts = []
        for segment in segments:
            txt = segment.text.strip()
            if txt:
                parts.append(txt)

        final_text = " ".join(parts).strip()

        # ✅ Only normalize very short single/two-word commands
        if duration_sec <= 2.0 and len(final_text.split()) <= 2:
            final_text = normalize_command(final_text)

        elapsed = round(time.time() - start, 2)
        print(f"[green]Recognized:[/green] {final_text}")
        print(f"[green]Done in {elapsed}s[/green]")

        return final_text

    except Exception as e:
        print(f"[red][STT Error]: {e}[/red]")
        return ""


# ---------------------------------------------------------------------------
# Microphone listener
# ---------------------------------------------------------------------------

def listen_for_speech(timeout: int = 5, phrase_time_limit: int = 8) -> str:
    recognizer = sr.Recognizer()

    # ✅ FIX: Dynamic threshold disabled — it overshoots badly in noisy rooms
    # and causes "stuck at Listening" because the bar keeps rising
    recognizer.dynamic_energy_threshold = False

    # ✅ FIX: Fixed threshold — adjust_for_ambient_noise will calibrate this
    # once, then we lock it. Raise manually to 500–800 if room is noisy.
    recognizer.energy_threshold = 400

    # ✅ FIX: Balanced pause values — responsive but won't clip last syllables
    recognizer.pause_threshold       = 0.9   # seconds of silence = end of phrase
    recognizer.non_speaking_duration = 0.5   # minimum trailing silence

    try:
        with suppress_alsa_errors():
            with sr.Microphone(sample_rate=16000) as source:

                print("[cyan]Calibrating mic...[/cyan]")

                # One-shot calibration to adapt to current room noise level
                recognizer.adjust_for_ambient_noise(source, duration=0.3)

                # ✅ Print threshold so you can tune it if needed
                print(
                    f"[dim]Energy threshold locked at: "
                    f"{int(recognizer.energy_threshold)}[/dim]"
                )
                print("[cyan]Listening...[/cyan]")

                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

        print("[cyan]Speech detected.[/cyan]")
        return transcribe_audio(audio)

    except sr.WaitTimeoutError:
        print("[yellow]Timeout — no speech detected.[/yellow]")
        return ""

    except Exception as e:
        print(f"[red][Mic Error]: {e}[/red]")
        return ""


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

async def generate_and_play_tts(text: str):
    if not text.strip():
        return

    voice     = "en-US-AriaNeural"
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


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_audio():
    """Call on shutdown to release pygame mixer."""
    if pygame.mixer.get_init():
        pygame.mixer.quit()


# ---------------------------------------------------------------------------
# Threshold finder utility — run this standalone to tune your mic
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("[bold]Mic threshold finder — speak normally after calibration[/bold]")
    r = sr.Recognizer()
    r.dynamic_energy_threshold = False
    with sr.Microphone(sample_rate=16000) as source:
        print("Calibrating for 2 seconds, stay quiet...")
        r.adjust_for_ambient_noise(source, duration=2)
        print(f"[green]Threshold: {int(r.energy_threshold)}[/green]")
        print("Now speak a command...")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=6)
            print("[green]Audio captured! Transcribing...[/green]")
            init_stt()
            result = transcribe_audio(audio)
            print(f"[bold]Result:[/bold] {result}")
        except sr.WaitTimeoutError:
            print("[yellow]No speech heard. Try raising energy_threshold.[/yellow]")