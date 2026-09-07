#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SKILL_SOURCE="$SCRIPT_DIR/skills/smartthink"
AGENTS_SOURCE="$SCRIPT_DIR/agents"
COMMANDS_SOURCE="$SCRIPT_DIR/commands"
SKILL_TARGET="$HOME/.claude/skills/smartthink"
AGENTS_TARGET="$HOME/.claude/agents"
COMMANDS_TARGET="$HOME/.claude/commands"
VAULT="${SMARTTHINK_VAULT:-$HOME/.claude/smartthink-vault}"
AGENT_FILES=(st-thinker.md st-armorer.md)
COMMAND_FILES=(st.md)

echo "SmartThink Installer"
echo "===================="
echo ""
echo "Skill source   : $SKILL_SOURCE"
echo "Skill target   : $SKILL_TARGET"
echo "Agents target  : $AGENTS_TARGET"
echo "Commands target: $COMMANDS_TARGET"
echo "Vault          : $VAULT"
echo ""

# Check source exists
if [ ! -f "$SKILL_SOURCE/SKILL.md" ]; then
  echo "ERROR: SKILL.md not found in $SKILL_SOURCE"
  echo "Make sure you're running install.sh from the cloned smartthink repo."
  exit 1
fi

# Every agent definition this installer links must actually exist in the repo.
for f in "${AGENT_FILES[@]}"; do
  if [ ! -f "$AGENTS_SOURCE/$f" ]; then
    echo "ERROR: agent definition not found: $AGENTS_SOURCE/$f"
    echo "The repo checkout looks incomplete. Re-clone or update it, then re-run install.sh."
    exit 1
  fi
done

# Check Claude Code installation
if [ ! -d "$HOME/.claude" ]; then
  echo "WARNING: ~/.claude/ not found. Is Claude Code installed?"
  echo "Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code"
fi

mkdir -p "$HOME/.claude/skills" "$AGENTS_TARGET" "$COMMANDS_TARGET"

# 1. Skill symlink (SKILL.md + references/ + references/index.json + .data/ seeds)
if [ -L "$SKILL_TARGET" ]; then
  echo "Existing skill symlink found. Replacing..."
  rm "$SKILL_TARGET"
elif [ -d "$SKILL_TARGET" ]; then
  echo "ERROR: $SKILL_TARGET exists as a directory (not a symlink)."
  echo "Back it up or remove it manually, then re-run install.sh."
  exit 1
fi
ln -s "$SKILL_SOURCE" "$SKILL_TARGET"
echo "Skill linked   : $SKILL_TARGET -> $SKILL_SOURCE"

# 2. Agent definitions (st-thinker = report path, st-armorer = arming path)
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
  echo "Agent linked   : $target -> $AGENTS_SOURCE/$f"
done

# 2b. An older release installed agent definitions this version no longer ships. Those
# symlinks now dangle. Clear the ones that point into this repo and no longer resolve;
# links owned by anything else are left alone.
for target in "$AGENTS_TARGET"/*.md; do
  [ -L "$target" ] || continue
  [ -e "$target" ] && continue
  case "$(readlink "$target")" in
    "$AGENTS_SOURCE"/*)
      rm "$target"
      echo "Stale link cleared: $target (this version ships no such agent definition)"
      ;;
  esac
done

# 3. /st command alias (the skill itself is invoked as /smartthink)
for f in "${COMMAND_FILES[@]}"; do
  target="$COMMANDS_TARGET/$f"
  if [ -L "$target" ]; then
    rm "$target"
  elif [ -e "$target" ]; then
    echo "WARNING: $target exists as a regular file. Leaving it alone."
    echo "         The /st alias will not be installed; use /smartthink instead."
    continue
  fi
  ln -s "$COMMANDS_SOURCE/$f" "$target"
  echo "Command linked : $target -> $COMMANDS_SOURCE/$f"
done

# 4. Vault (lives OUTSIDE the repo so your profile and insights never get committed)
mkdir -p "$VAULT/packs"
if [ ! -f "$VAULT/evolution-state.md" ]; then
  cp "$SKILL_SOURCE/.data/evolution-state.md" "$VAULT/evolution-state.md"
  echo "Vault seeded   : $VAULT/evolution-state.md (empty template)"
else
  echo "Vault kept     : $VAULT/evolution-state.md (existing insights preserved)"
fi
echo "Packs dir      : $VAULT/packs"
# profile.md is intentionally NOT seeded here. Its absence is the signal that tells
# SmartThink to suggest /st init, which is what actually fills the profile in.

echo ""
echo "Installation complete!"
echo ""
echo "Installed: 1 skill (smartthink), 2 agents (st-thinker, st-armorer), 1 command alias (/st)."
echo ""
echo "NOTE: Start a new Claude Code session for the skill and agents to be recognized."
if [ -n "${SMARTTHINK_VAULT:-}" ]; then
  echo "NOTE: SMARTTHINK_VAULT is set. Export it in your shell profile so every session finds the vault."
fi
echo ""
echo "First run:"
echo "  /st init                       Build your profile (scan + short interview)"
echo "  /st <task or topic>            Arm the session, then it hands the work back to you"
echo ""
echo "Flags:"
echo "  --digest        Distilled reference section instead of verbatim (10-20K pack)"
echo "  --report        st-thinker writes an analysis report from the pack"
echo "  --lite          Cynefin + first principles only, no references, no pack"
echo "  --nosearch      Skip research (pack section 3 is omitted)"
echo "  --budget N      Cap the arming gate at N tokens"
echo "  --pack <path>   Reload an existing pack, skipping the gate"
echo ""
echo "Lifecycle:"
echo "  /st init        Create or update the profile"
echo "  /st retain      Fold this session's lessons into the evolution state"
echo "  /st status      Profile summary, recent packs, evolution counts, environment check"
