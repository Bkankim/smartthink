#!/usr/bin/env bash
set -euo pipefail

SKILL_TARGET="$HOME/.claude/skills/smartthink"
AGENTS_TARGET="$HOME/.claude/agents"
VAULT="${SMARTTHINK_VAULT:-$HOME/.claude/smartthink-vault}"
AGENT_FILES=(st-thinker.md st-searcher.md)

echo "SmartThink Uninstaller"
echo "======================"
echo ""

# Skill symlink
if [ -L "$SKILL_TARGET" ]; then
  rm "$SKILL_TARGET"
  echo "Skill symlink removed: $SKILL_TARGET"
elif [ -d "$SKILL_TARGET" ]; then
  echo "WARNING: $SKILL_TARGET is a directory, not a symlink. Skipping."
else
  echo "Skill symlink not found: $SKILL_TARGET (already removed?)"
fi

# Agent symlinks
for f in "${AGENT_FILES[@]}"; do
  target="$AGENTS_TARGET/$f"
  if [ -L "$target" ]; then
    rm "$target"
    echo "Agent symlink removed: $target"
  elif [ -e "$target" ]; then
    echo "WARNING: $target is a regular file, not a symlink. Skipping."
  fi
done

echo ""
echo "Uninstall complete."
echo "Your evolution state is preserved in $VAULT"
echo "Delete that directory manually if you want a full reset."
