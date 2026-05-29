#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

unset VIRTUAL_ENV

if [ -z "${OBSIDIAN_API_KEY:-}" ]; then
    OBSIDIAN_API_KEY="$(python3 -c "
import keyring
k = keyring.get_password('engram', 'obsidian-rest')
if k:
    print(k, end='')
" 2>/dev/null || true)"
fi

if [ -n "${OBSIDIAN_API_KEY:-}" ]; then
    export OBSIDIAN_API_KEY
fi

cd "$PROJECT_DIR"
exec uv run python -m engram
