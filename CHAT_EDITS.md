# Chat Edit Log

This file contains the exact unified diffs for edits made during this chat session.

## Files Included
- README.md
- ken/config.py
- ken/llm.py
- ken/main.py
- ken/memory.py
- ken/utils.py

## Unified Diff

diff --git a/README.md b/README.md
index 14478c9..73e2128 100644
--- a/README.md
+++ b/README.md
@@ -72,6 +72,34 @@ pip install -r requirements.txt
 python -m ken.main
 ```
 
+## Assistant Modes and Model Switching
+
+Ken now supports tuned assistant modes and direct model selection from CLI:
+
+```bash
+uv run ken --mode linux
+uv run ken --mode coding
+uv run ken --mode tutor
+uv run ken --mode fast
+uv run ken --mode think
+
+uv run ken --model llama3.2:3b
+uv run ken --model qwen2.5:4b
+uv run ken --model mistral:latest
+
+uv run ken --mode think --model qwen2.5:4b --benchmark
+```
+
+Inside an active session, you can switch instantly:
+
+```text
+/mode linux
+/mode coding
+/model qwen2.5:4b
+/bench on
+/status
+```
+
 ### 3. Pulling Models (Requires Ollama)
 
 Ken relies on [Ollama](https://ollama.com) for local AI execution. Make sure it's installed and running.
diff --git a/ken/config.py b/ken/config.py
index 6cf16d3..399aa3e 100644
--- a/ken/config.py
+++ b/ken/config.py
@@ -1,13 +1,140 @@
+from dataclasses import dataclass
 from pathlib import Path
+from typing import Dict, Literal
+
 from pydantic_settings import BaseSettings
 
+ModeName = Literal["linux", "coding", "tutor", "fast", "think"]
+
+
+@dataclass(frozen=True)
+class ModeProfile:
+    name: ModeName
+    description: str
+    temperature: float
+    top_p: float
+    repeat_penalty: float
+    num_predict: int
+    num_ctx: int
+    style_instruction: str
+
+
+MODE_PROFILES: Dict[ModeName, ModeProfile] = {
+    "linux": ModeProfile(
+        name="linux",
+        description="Concise Linux troubleshooting and command-first guidance.",
+        temperature=0.2,
+        top_p=0.9,
+        repeat_penalty=1.15,
+        num_predict=220,
+        num_ctx=2048,
+        style_instruction=(
+            "Prioritize terminal-first Linux troubleshooting. Provide safe, verified commands "
+            "with short explanations and expected output checks."
+        ),
+    ),
+    "coding": ModeProfile(
+        name="coding",
+        description="Debugging and implementation support with practical code snippets.",
+        temperature=0.25,
+        top_p=0.92,
+        repeat_penalty=1.12,
+        num_predict=420,
+        num_ctx=3072,
+        style_instruction=(
+            "Focus on debugging logic, clear code examples, and concrete implementation steps."
+        ),
+    ),
+    "tutor": ModeProfile(
+        name="tutor",
+        description="Stepwise educational explanations with checks for understanding.",
+        temperature=0.45,
+        top_p=0.95,
+        repeat_penalty=1.1,
+        num_predict=520,
+        num_ctx=3072,
+        style_instruction=(
+            "Teach step by step, explain tradeoffs, and keep explanations beginner-friendly "
+            "without being vague."
+        ),
+    ),
+    "fast": ModeProfile(
+        name="fast",
+        description="Lowest-latency short answers.",
+        temperature=0.15,
+        top_p=0.88,
+        repeat_penalty=1.08,
+        num_predict=120,
+        num_ctx=1536,
+        style_instruction=(
+            "Return the shortest useful answer. Prefer one to three bullets max."
+        ),
+    ),
+    "think": ModeProfile(
+        name="think",
+        description="Higher-depth reasoning mode for non-trivial tasks.",
+        temperature=0.35,
+        top_p=0.93,
+        repeat_penalty=1.14,
+        num_predict=700,
+        num_ctx=4096,
+        style_instruction=(
+            "Reason carefully before answering. Offer assumptions, edge cases, and a robust plan."
+        ),
+    ),
+}
+
+
+MODEL_ALIASES = {
+    "llama": "llama3.2:3b",
+    "llama3": "llama3.2:3b",
+    "llama3.2": "llama3.2:3b",
+    "qwen": "qwen2.5:4b",
+    "qwen2.5": "qwen2.5:4b",
+    "mistral": "mistral:latest",
+}
+
+
 class KenConfig(BaseSettings):
     ollama_url: str = "http://127.0.0.1:11434"
     model: str = "llama3.2:3b"
+    default_mode: ModeName = "linux"
+    request_timeout_s: float = 60.0
+    ollama_keep_alive: str = "15m"
+
+    # GTX 1650-oriented defaults: moderate context and token limits keep latency stable.
+    ollama_num_gpu: int = 24
+    ollama_num_thread: int = 6
+
+    memory_recent_window: int = 12
+    memory_summary_trigger: int = 40
+    memory_keep_after_summary: int = 12
+    memory_summary_char_limit: int = 2200
+
     data_dir: Path = Path.home() / ".local" / "share" / "ken"
-    
+
     class Config:
         env_prefix = "KEN_"
 
+
+def get_mode_profile(mode: str | None) -> ModeProfile:
+    if not mode:
+        return MODE_PROFILES[config.default_mode]
+    normalized = mode.strip().lower()
+    if normalized not in MODE_PROFILES:
+        return MODE_PROFILES[config.default_mode]
+    return MODE_PROFILES[normalized]  # type: ignore[index]
+
+
+def resolve_model_name(model_name: str | None) -> str:
+    if not model_name:
+        return config.model
+    cleaned = model_name.strip()
+    if not cleaned:
+        return config.model
+    alias = MODEL_ALIASES.get(cleaned.lower())
+    return alias or cleaned
+
+
 config = KenConfig()
 config.data_dir.mkdir(parents=True, exist_ok=True)
diff --git a/ken/llm.py b/ken/llm.py
index 54d949d..ca9c289 100644
--- a/ken/llm.py
+++ b/ken/llm.py
@@ -1,37 +1,117 @@
 import httpx
 import json
-from ken.config import config
+
+from ken.config import config, get_mode_profile, resolve_model_name
 from ken.memory import Memory
 
-async def stream_chat(prompt: str, memory: Memory):
+
+def _build_system_prompt(mode: str, memory: Memory) -> str:
+    profile = get_mode_profile(mode)
+    memory_hint = ""
+    if memory.user_preferences:
+        prefs = "; ".join(memory.user_preferences[-6:])
+        memory_hint = f"\nUser preferences to honor: {prefs}"
+
+    return (
+        "You are Ken, a local-first Linux AI assistant running on Ubuntu. "
+        "Be accurate, intentional, and practical.\n"
+        "Core operating rules:\n"
+        "1) If uncertain, explicitly say what is uncertain.\n"
+        "2) Never fabricate Linux commands, packages, files, logs, or tool output.\n"
+        "3) Ask a clarifying question when information is missing for a safe answer.\n"
+        "4) Prefer verified command patterns and explain risky commands before suggesting them.\n"
+        "5) Keep answers local-first and privacy-preserving unless user asks otherwise.\n"
+        f"Mode: {profile.name} - {profile.description}\n"
+        f"Mode behavior: {profile.style_instruction}"
+        f"{memory_hint}"
+    )
+
+
+def _quality_note(text: str, first_token_latency_s: float | None) -> str:
+    words = len(text.split())
+    low_confidence_markers = [
+        "not sure",
+        "uncertain",
+        "i don't know",
+        "might be",
+        "possibly",
+    ]
+    has_uncertainty = any(marker in text.lower() for marker in low_confidence_markers)
+
+    if not text.strip():
+        return "Empty response; likely model load or stream interruption."
+    if has_uncertainty:
+        return "Model signaled uncertainty; safer than guessing."
+    if words < 10:
+        return "Very concise answer; good for speed, may need follow-up depth."
+    if first_token_latency_s is not None and first_token_latency_s > 2.5:
+        return "Good content quality but first token latency was high."
+    return "Balanced response quality for local assistant use."
+
+
+async def stream_chat(
+    prompt: str,
+    memory: Memory,
+    *,
+    mode: str,
+    model: str | None = None,
+    benchmark: bool = False,
+    benchmark_report: dict | None = None,
+):
     """Yields tokens from the Ollama chat stream."""
+    profile = get_mode_profile(mode)
+    chosen_model = resolve_model_name(model)
+
     memory.add_user(prompt)
-    
-    # Prepend a lightweight system prompt
+
     system_msg = {
-        "role": "system", 
-        "content": "You are Ken, a concise, helpful Linux assistant. Give brief, direct answers."
+        "role": "system",
+        "content": _build_system_prompt(profile.name, memory),
     }
-    
+
     payload = {
-        "model": config.model,
+        "model": chosen_model,
         "messages": [system_msg] + memory.get_context(),
-        "stream": True
+        "stream": True,
+        "keep_alive": config.ollama_keep_alive,
+        "options": {
+            "temperature": profile.temperature,
+            "top_p": profile.top_p,
+            "repeat_penalty": profile.repeat_penalty,
+            "num_predict": profile.num_predict,
+            "num_ctx": profile.num_ctx,
+            "num_gpu": config.ollama_num_gpu,
+            "num_thread": config.ollama_num_thread,
+        },
     }
-    
+
+    started_at = None
+    first_token_latency_s = None
+    server_eval_count = None
+    server_eval_duration_ns = None
     full_response = ""
-    
+    loop = None
+
     try:
-        async with httpx.AsyncClient(timeout=30.0) as client:
+        import asyncio
+
+        loop = asyncio.get_running_loop()
+        started_at = loop.time()
+        async with httpx.AsyncClient(timeout=config.request_timeout_s) as client:
             async with client.stream("POST", f"{config.ollama_url}/api/chat", json=payload) as response:
                 response.raise_for_status()
                 async for chunk in response.aiter_lines():
                     if chunk:
                         try:
                             data = json.loads(chunk)
+                            if data.get("done"):
+                                server_eval_count = data.get("eval_count")
+                                server_eval_duration_ns = data.get("eval_duration")
                             if "message" in data and "content" in data["message"]:
                                 token = data["message"]["content"]
                                 full_response += token
+                                if first_token_latency_s is None and started_at is not None:
+                                    first_token_latency_s = round(loop.time() - started_at, 3)
                                 yield token
                         except json.JSONDecodeError:
                             continue
@@ -41,6 +121,31 @@ async def stream_chat(prompt: str, memory: Memory):
         yield "\n[Error] Ollama timed out. The model might be loading or the system is under heavy load."
     except Exception as e:
         yield f"\n[Error] Unexpected error from LLM: {str(e)}"
-        
+
     if full_response:
         memory.add_assistant(full_response)
+
+    if benchmark and benchmark_report is not None and loop is not None and started_at is not None:
+        total_latency_s = round(loop.time() - started_at, 3)
+        if server_eval_count and server_eval_duration_ns:
+            eval_secs = server_eval_duration_ns / 1_000_000_000
+            tokens_per_s = round(server_eval_count / eval_secs, 2) if eval_secs > 0 else 0.0
+            output_tokens = int(server_eval_count)
+        else:
+            output_tokens = max(1, int(len(full_response) / 4)) if full_response else 0
+            generation_time = max(total_latency_s - (first_token_latency_s or 0.0), 0.001)
+            tokens_per_s = round(output_tokens / generation_time, 2)
+
+        benchmark_report.update(
+            {
+                "mode": profile.name,
+                "model": chosen_model,
+                "prompt_chars": len(prompt),
+                "response_chars": len(full_response),
+                "output_tokens_est": output_tokens,
+                "first_token_latency_s": first_token_latency_s,
+                "total_latency_s": total_latency_s,
+                "tokens_per_s": tokens_per_s,
+                "quality_note": _quality_note(full_response, first_token_latency_s),
+            }
+        )
diff --git a/ken/main.py b/ken/main.py
index c46ee29..0b77541 100644
--- a/ken/main.py
+++ b/ken/main.py
@@ -1,9 +1,11 @@
 import asyncio
 import typer
 from rich.console import Console
+from rich.panel import Panel
 from prompt_toolkit import PromptSession
 from prompt_toolkit.styles import Style
 
+from ken.config import MODE_PROFILES, config, get_mode_profile, resolve_model_name
 from ken.utils import check_ollama_running, show_fallback_help
 from ken.memory import Memory
 from ken.commands import route_command
@@ -13,23 +15,53 @@ from ken.voice import generate_and_play_tts, listen_for_speech, init_stt
 app = typer.Typer(add_completion=False)
 console = Console()
 
-async def chat_loop(voice_mode: bool = False):
+
+def _render_benchmark(report: dict):
+    if not report:
+        return
+
+    lines = [
+        f"Model: {report.get('model', 'n/a')}",
+        f"Mode: {report.get('mode', 'n/a')}",
+        f"First token: {report.get('first_token_latency_s', 'n/a')}s",
+        f"Total latency: {report.get('total_latency_s', 'n/a')}s",
+        f"Output speed: {report.get('tokens_per_s', 'n/a')} tok/s",
+        f"Output tokens(est): {report.get('output_tokens_est', 'n/a')}",
+        f"Quality note: {report.get('quality_note', 'n/a')}",
+    ]
+    console.print(Panel("\n".join(lines), title="Benchmark", border_style="cyan"))
+
+
+async def chat_loop(
+    voice_mode: bool = False,
+    mode: str | None = None,
+    model: str | None = None,
+    benchmark: bool = False,
+):
+    active_mode = get_mode_profile(mode).name
+    active_model = resolve_model_name(model)
+
     console.clear()
     console.print("[bold blue]Ken - Personal Linux AI Assistant[/bold blue]")
-    console.print("Type 'exit' or 'quit' to close. Type 'clear' to reset memory. Type '/voice' to toggle voice.\n")
+    console.print(
+        "Type 'exit'/'quit' to close, 'clear' to reset memory, '/voice' to toggle voice.\n"
+        "Session controls: /mode <linux|coding|tutor|fast|think>, /model <ollama-model>, /bench on|off"
+    )
+    console.print(f"[dim]Mode={active_mode} | Model={active_model} | Benchmark={'on' if benchmark else 'off'}[/dim]\n")
+
     if voice_mode:
         console.print("[bold green]Voice Mode Active. Speak to Ken.[/bold green]\n")
         init_stt()
-    
+
     ollama_ready = await check_ollama_running()
     if not ollama_ready:
         show_fallback_help()
-        
+
     memory = Memory()
-    
+
     style = Style.from_dict({'prompt': 'ansicyan bold'})
     session = PromptSession()
-    
+
     while True:
         try:
             if voice_mode:
@@ -49,7 +81,7 @@ async def chat_loop(voice_mode: bool = False):
             if user_input.lower() in ["exit", "quit"]:
                 console.print("[blue]Goodbye![/blue]")
                 break
-                
+
             if user_input.lower() == "/voice":
                 voice_mode = not voice_mode
                 status = "enabled" if voice_mode else "disabled"
@@ -57,12 +89,46 @@ async def chat_loop(voice_mode: bool = False):
                 if voice_mode:
                     init_stt()
                 continue
-                
+
+            if user_input.lower().startswith("/mode "):
+                selected = user_input.split(maxsplit=1)[1].strip().lower()
+                if selected in MODE_PROFILES:
+                    active_mode = get_mode_profile(selected).name
+                    console.print(f"[green]Mode set to {active_mode}.[/green]")
+                else:
+                    allowed = ", ".join(MODE_PROFILES.keys())
+                    console.print(f"[yellow]Unknown mode. Use one of: {allowed}[/yellow]")
+                continue
+
+            if user_input.lower().startswith("/model "):
+                requested = user_input.split(maxsplit=1)[1].strip()
+                active_model = resolve_model_name(requested)
+                console.print(f"[green]Model set to {active_model}.[/green]")
+                continue
+
+            if user_input.lower().startswith("/bench "):
+                value = user_input.split(maxsplit=1)[1].strip().lower()
+                if value in {"on", "true", "1"}:
+                    benchmark = True
+                elif value in {"off", "false", "0"}:
+                    benchmark = False
+                else:
+                    console.print("[yellow]Use /bench on or /bench off[/yellow]")
+                    continue
+                console.print(f"[green]Benchmark {'enabled' if benchmark else 'disabled'}.[/green]")
+                continue
+
+            if user_input.lower() == "/status":
+                console.print(
+                    f"[cyan]Mode={active_mode} | Model={active_model} | Benchmark={'on' if benchmark else 'off'}[/cyan]"
+                )
+                continue
+
             if user_input.lower() == "clear":
                 memory.clear()
                 console.print("[green]Memory cleared.[/green]")
                 continue
-                
+
             # 1. Try local command routing first (fastest)
             handled, response = route_command(user_input)
             if handled:
@@ -73,24 +139,34 @@ async def chat_loop(voice_mode: bool = False):
                 if voice_mode:
                     await generate_and_play_tts(response)
                 continue
-                
+
             # 2. Check if Ollama is online before sending
             if not await check_ollama_running():
                 show_fallback_help()
                 continue
-                
+
             # 3. Stream from LLM
             console.print("")
             full_response = ""
-            async for chunk in stream_chat(user_input, memory):
+            benchmark_report = {}
+            async for chunk in stream_chat(
+                user_input,
+                memory,
+                mode=active_mode,
+                model=active_model,
+                benchmark=benchmark,
+                benchmark_report=benchmark_report,
+            ):
                 console.print(chunk, end="", highlight=False)
                 full_response += chunk
             console.print("\n")
-            
+
+            if benchmark:
+                _render_benchmark(benchmark_report)
+
             if voice_mode:
                 await generate_and_play_tts(full_response)
-            
-            
+
         except KeyboardInterrupt:
             continue
         except EOFError:
@@ -98,11 +174,26 @@ async def chat_loop(voice_mode: bool = False):
         except Exception as e:
             console.print(f"\n[red]Fatal Error: {e}[/red]")
 
+
 @app.command()
-def start(voice: bool = typer.Option(False, "--voice", "-v", help="Enable voice mode")):
+def start(
+    voice: bool = typer.Option(False, "--voice", "-v", help="Enable voice mode"),
+    mode: str = typer.Option(
+        config.default_mode,
+        "--mode",
+        "-m",
+        help="Assistant mode: linux, coding, tutor, fast, think",
+    ),
+    model: str = typer.Option(
+        config.model,
+        "--model",
+        help="Ollama model name (for example: llama3.2:3b, qwen2.5:4b, mistral:latest)",
+    ),
+    benchmark: bool = typer.Option(False, "--benchmark", help="Show latency and throughput metrics"),
+):
     """Start the Ken AI assistant."""
     try:
-        asyncio.run(chat_loop(voice_mode=voice))
+        asyncio.run(chat_loop(voice_mode=voice, mode=mode, model=model, benchmark=benchmark))
     except KeyboardInterrupt:
         console.print("\n[blue]Goodbye![/blue]")
         import os
diff --git a/ken/memory.py b/ken/memory.py
index 59e7fe2..1648895 100644
--- a/ken/memory.py
+++ b/ken/memory.py
@@ -1,14 +1,29 @@
 import json
-from pathlib import Path
 from typing import List, Dict, Any
+
 from ken.config import config
 
+
 class Memory:
     def __init__(self):
         self.memory_file = config.data_dir / "memory.json"
-        self.messages: List[Dict[str, Any]] = self.load()
+        self.messages: List[Dict[str, Any]] = []
+        self.summary: str = ""
+        self.user_preferences: List[str] = []
+        self._load_state()
+
+    def _load_state(self):
+        loaded = self.load()
+        if isinstance(loaded, list):
+            # Backward compatibility: old format stored a raw message list.
+            self.messages = loaded
+            return
+
+        self.messages = loaded.get("messages", [])
+        self.summary = loaded.get("summary", "")
+        self.user_preferences = loaded.get("user_preferences", [])
 
-    def load(self) -> List[Dict[str, Any]]:
+    def load(self) -> List[Dict[str, Any]] | Dict[str, Any]:
         if self.memory_file.exists():
             try:
                 with open(self.memory_file, "r", encoding="utf-8") as f:
@@ -19,22 +34,123 @@ class Memory:
 
     def save(self):
         with open(self.memory_file, "w", encoding="utf-8") as f:
-            json.dump(self.messages[-50:], f)  # Keep last 50 messages to stay lightweight
+            payload = {
+                "summary": self.summary,
+                "user_preferences": self.user_preferences[-12:],
+                "messages": self.messages[-120:],
+            }
+            json.dump(payload, f, ensure_ascii=True, indent=2)
 
     def add_user(self, text: str):
         self.messages.append({"role": "user", "content": text})
+        self._capture_preferences(text)
+        self._compact_if_needed()
         self.save()
 
     def add_assistant(self, text: str):
         self.messages.append({"role": "assistant", "content": text})
+        self._compact_if_needed()
         self.save()
-        
+
     def add_system(self, text: str):
-        pass
-        
+        self.messages.append({"role": "system", "content": text})
+        self._compact_if_needed()
+        self.save()
+
     def get_context(self) -> List[Dict[str, Any]]:
-        return self.messages[-10:] # send last 10 messages for context
-    
+        context: List[Dict[str, Any]] = []
+
+        if self.summary.strip():
+            context.append(
+                {
+                    "role": "system",
+                    "content": "Conversation summary so far:\n" + self.summary.strip(),
+                }
+            )
+
+        if self.user_preferences:
+            pref_text = "\n".join(f"- {item}" for item in self.user_preferences[-8:])
+            context.append(
+                {
+                    "role": "system",
+                    "content": "Known user preferences:\n" + pref_text,
+                }
+            )
+
+        context.extend(self.messages[-config.memory_recent_window :])
+        return context
+
     def clear(self):
         self.messages = []
+        self.summary = ""
+        self.user_preferences = []
         self.save()
+
+    def _capture_preferences(self, text: str):
+        lowered = text.lower().strip()
+        candidate: str | None = None
+
+        if lowered.startswith("my name is "):
+            candidate = text.strip()
+        elif "i prefer" in lowered:
+            candidate = text.strip()
+        elif "please keep" in lowered:
+            candidate = text.strip()
+        elif "always" in lowered and len(text.split()) <= 14:
+            candidate = text.strip()
+
+        if not candidate:
+            return
+
+        cleaned = candidate[:160]
+        if cleaned not in self.user_preferences:
+            self.user_preferences.append(cleaned)
+            self.user_preferences = self.user_preferences[-16:]
+
+    def _compact_if_needed(self):
+        trigger = config.memory_summary_trigger
+        keep = config.memory_keep_after_summary
+        if len(self.messages) <= trigger:
+            return
+
+        older = self.messages[:-keep]
+        if not older:
+            return
+
+        rollup = self._summarize_messages(older)
+        if not rollup:
+            self.messages = self.messages[-keep:]
+            return
+
+        if self.summary.strip():
+            merged = self.summary.strip() + "\n" + rollup
+        else:
+            merged = rollup
+
+        self.summary = merged[-config.memory_summary_char_limit :]
+        self.messages = self.messages[-keep:]
+
+    def _summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
+        lines: List[str] = []
+        for msg in messages:
+            role = msg.get("role", "")
+            content = str(msg.get("content", "")).strip()
+            if not content:
+                continue
+
+            one_line = " ".join(content.split())
+            if len(one_line) > 160:
+                one_line = one_line[:157] + "..."
+
+            if role == "user":
+                lines.append(f"User asked: {one_line}")
+            elif role == "assistant":
+                lines.append(f"Ken answered: {one_line}")
+
+            if len(lines) >= 18:
+                break
+
+        if not lines:
+            return ""
+
+        return "\n".join(lines)
diff --git a/ken/utils.py b/ken/utils.py
index f72e7c4..a24d853 100644
--- a/ken/utils.py
+++ b/ken/utils.py
@@ -8,7 +8,7 @@ console = Console()
 async def check_ollama_running() -> bool:
     try:
         async with httpx.AsyncClient(timeout=2.0) as client:
-            resp = await client.get(config.ollama_url)
+            resp = await client.get(f"{config.ollama_url}/api/tags")
             return resp.status_code == 200
     except Exception:
         return False
