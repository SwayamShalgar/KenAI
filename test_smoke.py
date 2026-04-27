#!/usr/bin/env python3
"""Quick smoke test for Ken modules."""
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("=== Ken Smoke Test ===")

# Test 1: Config
try:
    from ken.config import config
    print(f"[OK] Config: model={config.model}, ollama_url={config.ollama_url}")
except Exception as e:
    print(f"[FAIL] Config: {e}")

# Test 2: Memory
try:
    from ken.memory import Memory
    mem = Memory()
    print(f"[OK] Memory loaded. Current messages: {len(mem.messages)}")
except Exception as e:
    print(f"[FAIL] Memory: {e}")

# Test 3: Commands
try:
    from ken.commands import route_command
    handled, response = route_command("tell time")
    if handled:
        print(f"[OK] Commands: {response}")
    else:
        print("[FAIL] Commands: 'tell time' not handled")
except Exception as e:
    print(f"[FAIL] Commands: {e}")

# Test 3b: Voice normalization
try:
    from ken.voice import normalize_command
    if normalize_command("hello") != "hello":
        print("[FAIL] Voice normalization: 'hello' should not be rewritten")
    elif normalize_command("know") != "no":
        print("[FAIL] Voice normalization: 'know' should map to 'no'")
    else:
        print("[OK] Voice normalization checks passed")
except Exception as e:
    print(f"[FAIL] Voice normalization: {e}")

# Test 4: Utils (Ollama check)
try:
    from ken.utils import check_ollama_running
    is_running = asyncio.run(check_ollama_running())
    status = "running" if is_running else "not running"
    print(f"[OK] Utils: check_ollama_running -> {status}")
except Exception as e:
    print(f"[FAIL] Utils: {e}")

print("\n=== Done ===")
