# KEN Architecture

This document explains the final package architecture, module boundaries, and dependency flow for KEN.

## Goals

- One authoritative source of truth per subsystem.
- Clear dependency flow that supports new interfaces (CLI, GUI, API).
- Easy extension for tools, integrations, and new LLM providers.
- Stable public API surfaces via package exports.

## High-Level Dependency Flow

interfaces
  -> runtime
     -> services
        -> integrations

config, core are shared foundations and must not depend on higher layers.

tools depend on services and integrations, but not on interfaces or runtime.

## Package Map

ken/
├── __main__.py
├── app/
│   ├── bootstrap.py
│   ├── router.py
│   ├── session.py
│   └── state.py
├── config/
│   ├── __init__.py
│   ├── modes.py
│   └── settings.py
├── core/
│   ├── __init__.py
│   ├── errors.py
│   ├── exceptions.py
│   └── utils.py
├── integrations/
│   ├── __init__.py
│   ├── devices/
│   ├── files/
│   ├── filesystem.py
│   └── ollama.py
├── interfaces/
│   ├── __init__.py
│   ├── api/
│   ├── cli/
│   ├── cli.py
│   ├── gui.py
│   └── ui.py
├── runtime/
│   ├── __init__.py
│   ├── bootstrap.py
│   ├── health.py
│   ├── lifecycle.py
│   ├── logging.py
│   ├── router.py
│   └── session.py
├── services/
│   ├── __init__.py
│   ├── llm/
│   ├── memory/
│   ├── telemetry/
│   └── voice/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── tools/
    ├── __init__.py
    ├── builtins/
    ├── command_router.py
    ├── commands.py
    └── registry.py

## Module Responsibilities

### app/
- Orchestration logic for the assistant runtime.
- Owns session loop, state management, and routing coordination.

### config/
- Settings and mode profiles.
- Exports the stable config API for other layers.

### core/
- Cross-cutting primitives and exceptions.
- Contains shared utilities that should stay dependency-free.

### integrations/
- External adapters (web, filesystem, devices).
- No core logic here; only glue to external systems.

### interfaces/
- User-facing interfaces (CLI, future API, GUI).
- Render and input concerns only; no business logic.

### runtime/
- Bootstrapping and lifecycle helpers.
- Thin wrappers that enforce dependency flow and standard startup behavior.

### services/
- Domain services: LLM, memory, voice, telemetry.
- The primary engine layer used by runtime and tools.

### tools/
- Built-in commands and tool routing.
- Can depend on services and integrations, but not on interfaces.

### tests/
- Unit: pure logic tests.
- Integration: service + integration boundary tests.
- E2E: CLI or full runtime tests.

## Public API Guidelines

- Package-level __init__.py files expose stable public APIs.
- Root legacy files remain thin wrappers for backward compatibility.
- New development should import from final packages, not legacy shims.

## Typical Request Flow

1. CLI receives user input (interfaces/cli).
2. Runtime session handles routing (app/session + app/router).
3. Tools or services are invoked (tools, services).
4. Integrations are used as needed (integrations/*).
5. Output renders through UI (interfaces/cli/ui).

## Where New Features Go

- GUI: interfaces/gui.py or interfaces/gui/
- Web API: interfaces/api/
- Wake word: services/voice/
- New LLM provider: services/llm/
- Semantic memory: services/memory/
- Web search: integrations/web/ + tools
- File tools: integrations/files/ + tools
- Mobile companion: integrations/devices/

## Backward Compatibility

Legacy root modules (ken/voice.py, ken/llm.py, ken/memory.py, etc.) exist as wrappers.
They delegate to the authoritative modules to avoid breaking existing imports.

## Editing Rules

- Add new behavior in app/, services/, tools/, or integrations.
- Do not add logic to wrapper modules.
- Keep dependencies flowing downward only.
