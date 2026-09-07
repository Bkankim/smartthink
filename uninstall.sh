#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
AGENTS_SOURCE="$SCRIPT_DIR/agents"
SKILL_TARGET="$HOME/.claude/skills/smartthink"
AGENTS_TARGET="$HOME/.claude/agents"
COMMANDS_TARGET="$HOME/.claude/commands"
VAULT="${SMARTTHINK_VAULT:-$HOME/.claude/smartthink-vault}"
AGENT_FILES=(st-thinker.md st-armorer.md)
COMMAND_FILES=(st.md)

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

# Agent symlinks this version installs
for f in "${AGENT_FILES[@]}"; do
  target="$AGENTS_TARGET/$f"
  if [ -L "$target" ]; then
    rm "$target"
    echo "Agent symlink removed: $target"
  elif [ -e "$target" ]; then
    echo "WARNING: $target is a regular file, not a symlink. Skipping."
  fi
done

# Agent symlinks left by earlier releases that shipped definitions this version does not.
# Only links pointing into this repo are touched; anything else is left alone.
for target in "$AGENTS_TARGET"/*.md; do
  [ -L "$target" ] || continue
  case "$(readlink "$target")" in
    "$AGENTS_SOURCE"/*)
      rm "$target"
      echo "Agent symlink removed: $target (installed by an earlier version)"
      ;;
  esac
done

# Command alias symlink
for f in "${COMMAND_FILES[@]}"; do
  target="$COMMANDS_TARGET/$f"
  if [ -L "$target" ]; then
    rm "$target"
    echo "Command symlink removed: $target"
  elif [ -e "$target" ]; then
    echo "WARNING: $target is a regular file, not a symlink. Skipping."
  fi
done

echo ""
echo "Uninstall complete."
echo "Your profile, evolution state and packs are preserved in $VAULT"
echo "Delete that directory manually if you want a full reset."
