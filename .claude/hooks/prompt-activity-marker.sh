#!/usr/bin/env bash
# UserPromptSubmit: mark session activity boundary
VAULT_ROOT="${VAULT_PATH:-$HOME/vault}"
echo "--- SESSION $(date -Iseconds) | $(pwd) ---" >> "$VAULT_ROOT/_meta/session-activity.log"
