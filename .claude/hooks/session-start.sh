#!/usr/bin/env bash
# SessionStart: reset turn counter on startup/clear, preserve on resume

set -u

STATE_DIR="$HOME/.claude/hook-state"
mkdir -p "$STATE_DIR" 2>/dev/null

INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0

SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
SOURCE=$(printf '%s' "$INPUT" | jq -r '.source // empty' 2>/dev/null)

[ -z "$SESSION_ID" ] && exit 0

case "$SOURCE" in
  startup|clear)
    rm -f "$STATE_DIR/$SESSION_ID.state" 2>/dev/null
    ;;
  resume|*)
    # preserve existing state
    :
    ;;
esac

exit 0
