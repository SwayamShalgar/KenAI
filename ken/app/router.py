from dataclasses import dataclass

from ken.tools.command_router import route_command
from ken.config import MODE_PROFILES, get_mode_profile, resolve_model_name
from ken.services.memory_service import MemoryService
from ken.services.voice_service import VoiceService
from ken.app.state import SessionState


@dataclass
class RouteOutcome:
    handled: bool
    should_exit: bool = False
    message: str | None = None
    message_style: str | None = None
    speak_text: str | None = None
    trailing_newline: bool = False
    modified_prompt: str | None = None


def handle_input(
    user_input: str,
    state: SessionState,
    memory_service: MemoryService,
    voice_service: VoiceService,
) -> RouteOutcome:
    text = user_input.strip()
    text_lower = text.lower()

    if text_lower in ["exit", "quit"]:
        return RouteOutcome(handled=True, should_exit=True)

    if text_lower == "/voice":
        state.voice_mode = not state.voice_mode
        status = "enabled" if state.voice_mode else "disabled"
        if state.voice_mode:
            voice_service.init_stt()
        return RouteOutcome(
            handled=True,
            message=f"Voice mode {status}.",
            message_style="green",
        )

    if text_lower.startswith("/mode "):
        selected = text.split(maxsplit=1)[1].strip().lower()
        if selected in MODE_PROFILES:
            state.active_mode = get_mode_profile(selected).name
            return RouteOutcome(
                handled=True,
                message=f"Mode set to {state.active_mode}.",
                message_style="green",
            )
        allowed = ", ".join(MODE_PROFILES.keys())
        return RouteOutcome(
            handled=True,
            message=f"Unknown mode. Use one of: {allowed}",
            message_style="yellow",
        )

    if text_lower.startswith("/model "):
        requested = text.split(maxsplit=1)[1].strip()
        state.active_model = resolve_model_name(requested)
        return RouteOutcome(
            handled=True,
            message=f"Model set to {state.active_model}.",
            message_style="green",
        )

    if text_lower.startswith("/bench "):
        value = text.split(maxsplit=1)[1].strip().lower()
        if value in {"on", "true", "1"}:
            state.benchmark = True
        elif value in {"off", "false", "0"}:
            state.benchmark = False
        else:
            return RouteOutcome(
                handled=True,
                message="Use /bench on or /bench off",
                message_style="yellow",
            )
        return RouteOutcome(
            handled=True,
            message=f"Benchmark {'enabled' if state.benchmark else 'disabled'}.",
            message_style="green",
        )

    if text_lower == "/status":
        status_line = (
            f"Mode={state.active_mode} | Model={state.active_model} | "
            f"Benchmark={'on' if state.benchmark else 'off'}"
        )
        return RouteOutcome(
            handled=True,
            message=status_line,
            message_style="cyan",
        )

    if text_lower == "clear":
        memory_service.clear()
        return RouteOutcome(
            handled=True,
            message="Memory cleared.",
            message_style="green",
        )

    import re
    weather_match = re.match(r"^(?:what is the )?weather(?: like)?(?: in| for)?\s+(.+)$", text_lower)
    if weather_match:
        city = weather_match.group(1).strip().rstrip("?")
        if city:
            import httpx
            try:
                r = httpx.get(f"https://wttr.in/{city}?format=%C+%t,+%w,+%h+humidity,+%P+pressure", timeout=4.0)
                if r.status_code == 200 and r.text and "Unknown location" not in r.text:
                    modified = f"Question: {text}\n\nI have fetched the real-time weather data for {city}: {r.text}\nSynthesize this into a natural, conversational response."
                    return RouteOutcome(handled=False, modified_prompt=modified)
            except Exception:
                pass
                
    search_prefixes = ["search ", "search for ", "look up ", "who is ", "what is the current ", "latest news "]
    for prefix in search_prefixes:
        if text_lower.startswith(prefix):
            query = text[len(prefix):].strip()
            if prefix in ["who is ", "what is the current ", "latest news "]:
                query = text.strip()
            
            from ken.integrations.web.search import search_web
            context = search_web(query)
            if context:
                modified = f"Question: {text}\n\nI have fetched these latest web results to help you answer. Synthesize them into a natural, conversational response:\n\n{context}"
                return RouteOutcome(handled=False, modified_prompt=modified)
            break

    handled, response = route_command(text)
    if handled and response:
        memory_service.add_user(text)
        memory_service.add_assistant(response)
        return RouteOutcome(
            handled=True,
            message=response,
            message_style="green",
            speak_text=response,
            trailing_newline=True,
        )

    return RouteOutcome(handled=False)
