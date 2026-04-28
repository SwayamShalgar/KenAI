import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from ken.config import MODE_PROFILES, config, get_mode_profile, resolve_model_name
from ken.utils import check_ollama_running, show_fallback_help
from ken.memory import Memory
from ken.commands import route_command
from ken.llm import stream_chat
from ken.voice import generate_and_play_tts, listen_for_speech, init_stt

app = typer.Typer(add_completion=False)
console = Console()


def _render_benchmark(report: dict):
    if not report:
        return

    lines = [
        f"Model: {report.get('model', 'n/a')}",
        f"Mode: {report.get('mode', 'n/a')}",
        f"First token: {report.get('first_token_latency_s', 'n/a')}s",
        f"Total latency: {report.get('total_latency_s', 'n/a')}s",
        f"Output speed: {report.get('tokens_per_s', 'n/a')} tok/s",
        f"Output tokens(est): {report.get('output_tokens_est', 'n/a')}",
        f"Quality note: {report.get('quality_note', 'n/a')}",
    ]
    console.print(Panel("\n".join(lines), title="Benchmark", border_style="cyan"))


async def chat_loop(
    voice_mode: bool = False,
    mode: str | None = None,
    model: str | None = None,
    benchmark: bool = False,
):
    active_mode = get_mode_profile(mode).name
    active_model = resolve_model_name(model)

    console.clear()
    console.print("[bold blue]Ken - Personal Linux AI Assistant[/bold blue]")
    console.print(
        "Type 'exit'/'quit' to close, 'clear' to reset memory, '/voice' to toggle voice.\n"
        "Session controls: /mode <linux|coding|tutor|fast|think>, /model <ollama-model>, /bench on|off"
    )
    console.print(f"[dim]Mode={active_mode} | Model={active_model} | Benchmark={'on' if benchmark else 'off'}[/dim]\n")

    if voice_mode:
        console.print("[bold green]Voice Mode Active. Speak to Ken.[/bold green]\n")
        init_stt()

    ollama_ready = await check_ollama_running()
    if not ollama_ready:
        show_fallback_help()

    memory = Memory()

    style = Style.from_dict({'prompt': 'ansicyan bold'})
    session = PromptSession()

    while True:
        try:
            if voice_mode:
                console.print("\n[blue]Listening...[/blue]", end="\r")
                user_input = await asyncio.to_thread(listen_for_speech)
                if not user_input:
                    continue
                console.print(f"Ken > [bold]{user_input}[/bold]")
            else:
                user_input = await session.prompt_async("Ken > ", style=style)
                
            user_input = user_input.strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["exit", "quit"]:
                console.print("[blue]Goodbye![/blue]")
                break

            if user_input.lower() == "/voice":
                voice_mode = not voice_mode
                status = "enabled" if voice_mode else "disabled"
                console.print(f"[green]Voice mode {status}.[/green]")
                if voice_mode:
                    init_stt()
                continue

            if user_input.lower().startswith("/mode "):
                selected = user_input.split(maxsplit=1)[1].strip().lower()
                if selected in MODE_PROFILES:
                    active_mode = get_mode_profile(selected).name
                    console.print(f"[green]Mode set to {active_mode}.[/green]")
                else:
                    allowed = ", ".join(MODE_PROFILES.keys())
                    console.print(f"[yellow]Unknown mode. Use one of: {allowed}[/yellow]")
                continue

            if user_input.lower().startswith("/model "):
                requested = user_input.split(maxsplit=1)[1].strip()
                active_model = resolve_model_name(requested)
                console.print(f"[green]Model set to {active_model}.[/green]")
                continue

            if user_input.lower().startswith("/bench "):
                value = user_input.split(maxsplit=1)[1].strip().lower()
                if value in {"on", "true", "1"}:
                    benchmark = True
                elif value in {"off", "false", "0"}:
                    benchmark = False
                else:
                    console.print("[yellow]Use /bench on or /bench off[/yellow]")
                    continue
                console.print(f"[green]Benchmark {'enabled' if benchmark else 'disabled'}.[/green]")
                continue

            if user_input.lower() == "/status":
                console.print(
                    f"[cyan]Mode={active_mode} | Model={active_model} | Benchmark={'on' if benchmark else 'off'}[/cyan]"
                )
                continue

            if user_input.lower() == "clear":
                memory.clear()
                console.print("[green]Memory cleared.[/green]")
                continue

            # 1. Try local command routing first (fastest)
            handled, response = route_command(user_input)
            if handled:
                console.print(f"[green]{response}[/green]\n")
                # optionally save to memory
                memory.add_user(user_input)
                memory.add_assistant(response)
                if voice_mode:
                    await generate_and_play_tts(response)
                continue

            # 2. Check if Ollama is online before sending
            if not await check_ollama_running():
                show_fallback_help()
                continue

            # 3. Stream from LLM
            console.print("")
            full_response = ""
            benchmark_report = {}
            async for chunk in stream_chat(
                user_input,
                memory,
                mode=active_mode,
                model=active_model,
                benchmark=benchmark,
                benchmark_report=benchmark_report,
            ):
                console.print(chunk, end="", highlight=False)
                full_response += chunk
            console.print("\n")

            if benchmark:
                _render_benchmark(benchmark_report)

            if voice_mode:
                await generate_and_play_tts(full_response)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"\n[red]Fatal Error: {e}[/red]")


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
    benchmark: bool = typer.Option(False, "--benchmark", help="Show latency and throughput metrics"),
):
    """Start the Ken AI assistant."""
    try:
        asyncio.run(chat_loop(voice_mode=voice, mode=mode, model=model, benchmark=benchmark))
    except KeyboardInterrupt:
        console.print("\n[blue]Goodbye![/blue]")
        import os
        os._exit(0)

if __name__ == "__main__":
    app()
