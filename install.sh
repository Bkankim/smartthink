#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SKILL_SOURCE="$SCRIPT_DIR/skills/smartthink"
AGENTS_SOURCE="$SCRIPT_DIR/agents"
SKILL_TARGET="$HOME/.claude/skills/smartthink"
AGENTS_TARGET="$HOME/.claude/agents"
VAULT="${SMARTTHINK_VAULT:-$HOME/.claude/smartthink-vault}"
AGENT_FILES=(st-thinker.md st-searcher.md)

echo "SmartThink Installer"
echo "===================="
echo ""
echo "Skill source : $SKILL_SOURCE"
echo "Skill target : $SKILL_TARGET"
echo "Agents target: $AGENTS_TARGET"
echo "Vault        : $VAULT"
echo ""

# Check source exists
if [ ! -f "$SKILL_SOURCE/SKILL.md" ]; then
  echo "ERROR: SKILL.md not found in $SKILL_SOURCE"
  echo "Make sure you're running install.sh from the cloned smartthink repo."
  exit 1
fi

# Check Claude Code installation
if [ ! -d "$HOME/.claude" ]; then
  echo "WARNING: ~/.claude/ not found. Is Claude Code installed?"
  echo "Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code"
fi

mkdir -p "$HOME/.claude/skills" "$AGENTS_TARGET"

# 1. Skill symlink
if [ -L "$SKILL_TARGET" ]; then
  echo "Existing skill symlink found. Replacing..."
  rm "$SKILL_TARGET"
elif [ -d "$SKILL_TARGET" ]; then
  echo "ERROR: $SKILL_TARGET exists as a directory (not a symlink)."
  echo "Back it up or remove it manually, then re-run install.sh."
  exit 1
fi
ln -s "$SKILL_SOURCE" "$SKILL_TARGET"
echo "Skill linked : $SKILL_TARGET -> $SKILL_SOURCE"

# 2. Agent definition symlinks (st-thinker = analysis body, st-searcher = search scout)
for f in "${AGENT_FILES[@]}"; do
  target="$AGENTS_TARGET/$f"
  if [ -L "$target" ]; then
    rm "$target"
  elif [ -e "$target" ]; then
    echo "ERROR: $target exists as a regular file (not a symlink)."
    echo "Back it up or remove it manually, then re-run install.sh."
    exit 1
  fi
  ln -s "$AGENTS_SOURCE/$f" "$target"
  echo "Agent linked : $target -> $AGENTS_SOURCE/$f"
done

# 3. Evolution vault (lives OUTSIDE the repo so your insights never get committed)
mkdir -p "$VAULT"
if [ ! -f "$VAULT/evolution-state.md" ]; then
  cp "$SKILL_SOURCE/.data/evolution-state.md" "$VAULT/evolution-state.md"
  echo "Vault seeded : $VAULT/evolution-state.md (empty template)"
else
  echo "Vault kept   : $VAULT/evolution-state.md (existing insights preserved)"
fi

echo ""
echo "Installation complete!"
echo ""
echo "NOTE: Start a new Claude Code session for the skill and agents to be recognized."
if [ -n "${SMARTTHINK_VAULT:-}" ]; then
  echo "NOTE: SMARTTHINK_VAULT is set. Export it in your shell profile so every session finds the vault."
fi
echo ""
echo "Usage:"
echo "  In Claude Code, type: /smartthink <your topic>   (alias: /st)"
echo "  Example: /smartthink AI 스타트업 아이디어"
echo ""
echo "Modes:"
echo "  /smartthink <topic>            Agent analysis (default, sub-agent, web search on)"
echo "  /smartthink --deep <topic>     Deep analysis (interactive, in main context)"
echo "  /smartthink --lite <topic>     Light analysis (no reference modules)"
echo "  /smartthink --nosearch <topic> Skip web search (combinable with --deep/--lite)"
