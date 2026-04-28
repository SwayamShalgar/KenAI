# Ken — Personal Linux AI Assistant

<div align="center">

```
 ██╗  ██╗███████╗███╗   ██╗
 ██║ ██╔╝██╔════╝████╗  ██║
 █████╔╝ █████╗  ██╔██╗ ██║
 ██╔═██╗ ██╔══╝  ██║╚██╗██║
 ██║  ██╗███████╗██║ ╚████║
 ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝
```

**Fast · Modular · Private · Expandable**

</div>

---

## What is Ken?

Ken is your personal Linux AI assistant. It runs entirely on your machine using local LLMs via [Ollama](https://ollama.com). No data leaves your system.

## Features

- 🧠 **Conversational AI** — Persistent sessions with context memory
- 🔧 **Skills system** — Modular plugins: shell, files, web search, system info, notes
- 🖥️ **Beautiful CLI** — Rich terminal UI with streaming responses
- ⚡ **Fast** — Async throughout, streaming from first token
- 🔒 **Private** — 100% local inference, zero telemetry
- 🔌 **Expandable** — Drop a Python file in `skills/` to add new capabilities

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com) running locally
- `uv` package manager (recommended)

## Quick Start & Running Guide

We highly recommend using `uv` to run Ken, as it seamlessly isolates dependencies. We have provided scripts that automatically install `uv` if missing.

### Option 1: Using the provided scripts (Recommended)

1. **Run the test/smoke script:**
   This script will automatically install `uv` if it isn't found on your system, and then it will run the tests.
   ```bash
   bash run_test.sh
   ```

2. **Run Ken directly with `uv`:**
   If `run_test.sh` ran successfully, `uv` is installed.
   ```bash
   uv run python -m ken.main
   # or
   uv run ken
   ```

### Option 2: Standard Python Virtual Environment

If you prefer not to use `uv`, you can use standard Python:

```bash
# 1. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run Ken
python -m ken.main
```

## Assistant Modes and Model Switching

Ken now supports tuned assistant modes and direct model selection from CLI:

```bash
uv run ken --mode linux
uv run ken --mode coding
uv run ken --mode tutor
uv run ken --mode fast
uv run ken --mode think

uv run ken --model llama3.2:3b
uv run ken --model qwen2.5:4b
uv run ken --model mistral:latest

uv run ken --mode think --model qwen2.5:4b --benchmark
```

Inside an active session, you can switch instantly:

```text
/mode linux
/mode coding
/model qwen2.5:4b
/bench on
/status
```

### 3. Pulling Models (Requires Ollama)

Ken relies on [Ollama](https://ollama.com) for local AI execution. Make sure it's installed and running.
```bash
ollama pull llama3.2:3b
ollama serve
```

---

## Troubleshooting

- **`uv: command not found`**: If you get this error when running manually, you can automatically install `uv` by running `bash run_test.sh` first. Or run: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Ken says "Ollama is not running"**: Ensure the `ollama serve` process is active in another terminal.
- **Python module not found**: If running via standard Python, make sure you activated the `.venv` and ran `pip install -r requirements.txt`.

## Configuration

Ken's config lives at `~/.config/ken/config.yaml`. It's created automatically on first run.

```yaml
llm:
  provider: ollama
  model: llama3.2:3b      # change to any Ollama model
  temperature: 0.7

skills:
  shell_require_confirmation: true  # ask before running shell commands
```

## Skills

| Skill | What it does |
|-------|-------------|
| `shell` | Run bash commands with optional confirmation |
| `file_manager` | Read, write, search files |
| `web_search` | Search the web via DuckDuckGo |
| `system_info` | CPU, RAM, disk, processes |
| `notes` | Personal notes with full-text search |
| `calculator` | Math expressions and unit conversions |

## CLI Commands

Inside Ken:
```
/help          — Show available commands and skills
/skills        — List all loaded skills
/clear         — Clear conversation history
/model <name>  — Switch LLM model on the fly
/save          — Save conversation to file
/exit          — Quit Ken
```

## Adding Your Own Skills

Create a file in `ken/skills/myskill.py`:

```python
from ken.skills import Skill, skill_result

class MySkill(Skill):
    name = "myskill"
    description = "Does something awesome"
    
    def get_tools(self):
        return [{"name": "my_tool", "description": "...", "parameters": {...}}]
    
    async def execute(self, tool_name: str, params: dict) -> str:
        return skill_result("Done!", data={"result": "..."})
```

That's it — Ken auto-discovers it on next startup.

## Architecture

```
ken/
├── core/           # Conversation engine, memory, planner
├── llm/            # LLM provider abstraction (Ollama, OpenAI-compat)
├── skills/         # Plugin system — each skill is self-contained
├── ui/             # CLI interface (Rich + prompt-toolkit)
└── main.py         # Entry point
```
# KenAI
