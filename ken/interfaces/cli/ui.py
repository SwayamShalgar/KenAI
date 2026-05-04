from rich.console import Console
from rich.panel import Panel

console = Console()


def format_status_line(active_mode: str, active_model: str, benchmark: bool) -> str:
    return (
        f"Mode={active_mode} | Model={active_model} | "
        f"Benchmark={'on' if benchmark else 'off'}"
    )


def render_startup(active_mode: str, active_model: str, benchmark: bool):
    console.clear()
    console.print("[bold blue]Ken - Personal Linux AI Assistant[/bold blue]")
    console.print(
        "Type 'exit'/'quit' to close, 'clear' to reset memory, '/voice' to toggle voice.\n"
        "Session controls: /mode <linux|coding|tutor|fast|think>, /model <ollama-model>, "
        "/bench on|off"
    )
    console.print(
        f"[dim]{format_status_line(active_mode, active_model, benchmark)}[/dim]\n"
    )


def render_voice_active():
    console.print("[bold green]Voice Mode Active. Speak to Ken.[/bold green]\n")


def render_status(active_mode: str, active_model: str, benchmark: bool):
    console.print(
        f"[cyan]{format_status_line(active_mode, active_model, benchmark)}[/cyan]"
    )


def render_benchmark(report: dict):
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


def print_message(text: str, *, style: str | None = None):
    if style:
        console.print(f"[{style}]{text}[/{style}]")
    else:
        console.print(text)
