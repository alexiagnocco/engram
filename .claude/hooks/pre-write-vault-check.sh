#!/usr/bin/env bash
# PreToolUse (Write): remind to search the vault before creating new notes
INPUT="$(cat)"
file=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')
[ -z "$file" ] && exit 0
if echo "$file" | grep -qE '/(00-inbox|10-projects|20-areas|30-resources)/.*\.md$' && [ ! -f "$file" ]; then
  echo 'REMINDER: Search the vault before creating. Use vault_search or /recall to check for existing notes on this topic.'
fi
