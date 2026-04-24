import asyncio
import typer
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

from ken.utils import check_ollama_running, show_fallback_help
from ken.memory import Memory
from ken.commands import route_command
from ken.llm import stream_chat
from ken.voice import generate_and_play_tts, listen_for_speech, init_stt

app = typer.Typer(add_completion=False)
console = Console()

async def chat_loop(voice_mode: bool = False):
    console.clear()
    console.print("[bold blue]Ken - Personal Linux AI Assistant[/bold blue]")
    console.print("Type 'exit' or 'quit' to close. Type 'clear' to reset memory. Type '/voice' to toggle voice.\n")
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
            async for chunk in stream_chat(user_input, memory):
                console.print(chunk, end="", highlight=False)
                full_response += chunk
            console.print("\n")
            
            if voice_mode:
                await generate_and_play_tts(full_response)
            
            
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"\n[red]Fatal Error: {e}[/red]")

@app.command()
def start(voice: bool = typer.Option(False, "--voice", "-v", help="Enable voice mode")):
    """Start the Ken AI assistant."""
    try:
        asyncio.run(chat_loop(voice_mode=voice))
    except KeyboardInterrupt:
        console.print("\n[blue]Goodbye![/blue]")
        import os
        os._exit(0)

if __name__ == "__main__":
    app()
