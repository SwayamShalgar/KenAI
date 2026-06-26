import asyncio
import typer

from ken.app.session import chat_loop
from ken.config import config
from ken.interfaces.cli.ui import print_message
from ken.interfaces.gui import run_gui

app = typer.Typer(add_completion=False)


@app.command()
def start(
    voice: bool = typer.Option(False, "--voice", "-v", help="Enable voice mode"),
    mode: str = typer.Option(
        config.default_mode,
        "--mode",
        "-m",
        help="Assistant mode: linux, coding, tutor, fast, think",
    ),
    model: str = typer.Option(
        config.model,
        "--model",
        help="Ollama model name (for example: llama3.2:3b, qwen2.5:4b, mistral:latest)",
    ),
    benchmark: bool = typer.Option(
        False,
        "--benchmark",
        help="Show latency and throughput metrics",
    ),
):
    """Start the Ken AI assistant."""
    try:
        asyncio.run(chat_loop(voice_mode=voice, mode=mode, model=model, benchmark=benchmark))
    except KeyboardInterrupt:
        print_message("Goodbye!", style="blue")
        import os
        os._exit(0)


@app.command()
def gui():
    """Start the Ken GUI assistant."""
    run_gui()
