import httpx
from ken.config import config
from rich.console import Console
from rich.panel import Panel

console = Console()

async def check_ollama_running() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(config.ollama_url)
            return resp.status_code == 200
    except Exception:
        return False

def show_fallback_help():
    help_text = """
[red bold]Ollama is not running or not reachable![/red bold]

Ken requires the local Ollama server to process natural language.

[bold]How to fix:[/bold]
1. Open a new terminal.
2. Run: [green]ollama serve[/green]
3. Alternatively, restart the system service: [green]sudo systemctl restart ollama[/green]

Ken can still execute basic local commands (like 'tell time' or 'open youtube') 
but natural chat is currently disabled.
"""
    console.print(Panel(help_text, title="System Offline", border_style="red"))
