#!/bin/bash
set -euo pipefail

# Check if uv is installed, if not, install it via the official script
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing it..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add common installation paths to PATH
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# Run the smoke test using uv for environment isolation
uv run python test_smoke.py
