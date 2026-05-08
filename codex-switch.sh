#!/bin/bash
# Mac / Linux launcher for codex-switch
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/codex-switch.py" "$@"
