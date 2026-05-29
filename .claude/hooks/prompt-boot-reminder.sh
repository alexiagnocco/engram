#!/usr/bin/env bash
# UserPromptSubmit: one-time reminder to run /boot at session start
SENTINEL=/tmp/vault-boot-reminded
if [ ! -f "$SENTINEL" ]; then
  echo "SESSION START: Run /boot to load full vault context (health + recall + project memory). End with /wrap."
  touch "$SENTINEL"
fi
