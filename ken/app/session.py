import asyncio

from ken.app.router import handle_input
from ken.app.state import SessionState
from ken.config import get_mode_profile, resolve_model_name
from ken.interfaces.cli.prompts import build_prompt_session
from ken.interfaces.cli.ui import (
    console,
    print_message,
    render_benchmark,
    render_startup,
    render_voice_active,
)
from ken.services.llm_service import LlmService
from ken.services.memory_service import MemoryService
from ken.services.voice_service import VoiceService
from ken.runtime.health import check_ollama_running, show_fallback_help


async def chat_loop(
    voice_mode: bool = False,
    mode: str | None = None,
    model: str | None = None,
    benchmark: bool = False,
):
    active_mode = get_mode_profile(mode).name
    active_model = resolve_model_name(model)

    state = SessionState(
        voice_mode=voice_mode,
        active_mode=active_mode,
        active_model=active_model,
        benchmark=benchmark,
    )

    render_startup(state.active_mode, state.active_model, state.benchmark)

    voice_service = VoiceService()
    if state.voice_mode:
        render_voice_active()
        voice_service.init_stt()

    async def speak_with_barge_in(text: str) -> str:
        interrupt_event = voice_service.interrupt_event
        interrupt_event.clear()

        tts_task = asyncio.create_task(
            voice_service.generate_and_play_tts(text, interrupt_event=interrupt_event)
        )
        interrupt_task = asyncio.create_task(
            voice_service.listen_for_interrupt(interrupt_event)
        )

        _, pending = await asyncio.wait(
            [tts_task, interrupt_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        if interrupt_event.is_set():
            tts_task.cancel()
            voice_service.stop_audio_playback()

        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        if interrupt_event.is_set():
            console.print("\n[blue]Listening...[/blue]", end="\r")
            barge_input = await asyncio.to_thread(voice_service.listen_for_speech)
            if barge_input:
                console.print(f"Ken > [bold]{barge_input}[/bold]")
                return barge_input.strip()
        return ""

    ollama_ready = await check_ollama_running()
    if not ollama_ready:
        show_fallback_help()

    memory_service = MemoryService()
    llm_service = LlmService()

    session, style = build_prompt_session()

    pending_input: str | None = None

    while True:
        try:
            if state.voice_mode:
                if pending_input is None:
                    console.print("\n[blue]Listening...[/blue]", end="\r")
                    user_input = await asyncio.to_thread(voice_service.listen_for_speech)
                    if not user_input:
                        continue
                    console.print(f"Ken > [bold]{user_input}[/bold]")
                else:
                    user_input = pending_input
                    pending_input = None
            else:
                user_input = await session.prompt_async("Ken > ", style=style)

            user_input = user_input.strip()

            if not user_input:
                continue

            outcome = handle_input(user_input, state, memory_service, voice_service)
            if outcome.handled:
                if outcome.should_exit:
                    print_message("Goodbye!", style="blue")
                    break
                if outcome.message:
                    print_message(outcome.message, style=outcome.message_style)
                if outcome.trailing_newline:
                    console.print("")
                if outcome.speak_text and state.voice_mode:
                    barge_input = await speak_with_barge_in(outcome.speak_text)
                    if barge_input:
                        pending_input = barge_input
                    continue
                continue

            if not await check_ollama_running():
                show_fallback_help()
                continue

            console.print("")
            full_response = ""
            benchmark_report: dict = {}
            async for chunk in llm_service.stream_chat(
                user_input,
                memory_service.memory,
                mode=state.active_mode,
                model=state.active_model,
                benchmark=state.benchmark,
                benchmark_report=benchmark_report,
            ):
                console.print(chunk, end="", highlight=False)
                full_response += chunk
            console.print("\n")

            if state.benchmark:
                render_benchmark(benchmark_report)

            if state.voice_mode:
                barge_input = await speak_with_barge_in(full_response)
                if barge_input:
                    pending_input = barge_input
                continue

        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"\n[red]Fatal Error: {e}[/red]")
