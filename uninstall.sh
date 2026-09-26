#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
AGENTS_SOURCE="$SCRIPT_DIR/agents"
SKILL_TARGET="$HOME/.claude/skills/smartthink"
AGENTS_TARGET="$HOME/.claude/agents"
COMMANDS_TARGET="$HOME/.claude/commands"
if ! VAULT="$(python3 "$SCRIPT_DIR/scripts/resolve-vault.py" | python3 -c 'import json, sys; print(json.load(sys.stdin)["path"])')"; then
  echo "ERROR: could not resolve the vault path (see the message above). Nothing was changed."
  exit 1
fi
AGENT_FILES=(st-thinker.md st-armorer.md)
COMMAND_FILES=(st.md)
LEGACY="$SCRIPT_DIR/scripts/legacy-install.py"

MIGRATE_LEGACY=0
for arg in "$@"; do
  case "$arg" in
    --migrate-legacy) MIGRATE_LEGACY=1 ;;
    *) echo "usage: ./uninstall.sh [--migrate-legacy]"; exit 2 ;;
  esac
done

echo "SmartThink Uninstaller"
echo "======================"
echo ""

# Leftovers from a copy install are real files the symlink removal below would skip.
# scripts/legacy-install.py recognizes them by content and moves them to a backup on request.
if ! LEFTOVERS="$(python3 "$LEGACY" detect)"; then
  echo "ERROR: could not check for leftovers of an earlier install (see the message above). Nothing was changed."
  exit 1
fi
if [ -n "$LEFTOVERS" ]; then
  if [ "$MIGRATE_LEGACY" -eq 0 ]; then
    echo "ERROR: an earlier SmartThink install left real files that this uninstaller would skip:"
    printf '%s\n' "$LEFTOVERS" | sed 's/^/  /'
    echo ""
    echo "Nothing was changed. To move them to ~/.claude/.backup/ and uninstall, run:"
    echo "  ./uninstall.sh --migrate-legacy"
    exit 1
  fi
  echo "Moving leftovers of an earlier install to a backup:"
  if ! MOVED="$(python3 "$LEGACY" migrate)"; then
    echo "ERROR: moving the leftovers failed (see the message above). Check ~/.claude/.backup/ before re-running."
    exit 1
  fi
  printf '%s\n' "$MOVED" | sed 's/^/  /'
  echo ""
fi

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
