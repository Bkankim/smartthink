#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SKILL_SOURCE="$SCRIPT_DIR/skills/smartthink"
AGENTS_SOURCE="$SCRIPT_DIR/agents"
COMMANDS_SOURCE="$SCRIPT_DIR/commands"
SKILL_TARGET="$HOME/.claude/skills/smartthink"
AGENTS_TARGET="$HOME/.claude/agents"
COMMANDS_TARGET="$HOME/.claude/commands"
RESOLVER="$SCRIPT_DIR/scripts/resolve-vault.py"
AGENT_FILES=(st-thinker.md st-armorer.md)
COMMAND_FILES=(st.md)
LEGACY="$SCRIPT_DIR/scripts/legacy-install.py"

MIGRATE_LEGACY=0
for arg in "$@"; do
  case "$arg" in
    --migrate-legacy) MIGRATE_LEGACY=1 ;;
    *) echo "usage: ./install.sh [--migrate-legacy]"; exit 2 ;;
  esac
done

echo "SmartThink Installer"
echo "===================="
echo ""
echo "Skill source   : $SKILL_SOURCE"
echo "Skill target   : $SKILL_TARGET"
echo "Agents target  : $AGENTS_TARGET"
echo "Commands target: $COMMANDS_TARGET"
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

# 0. Leftovers from a copy install (real files instead of symlinks) shadow the bare names and
# block the links below. scripts/legacy-install.py recognizes them by content; they are moved to
# a backup, never deleted, and only when asked.
if ! LEFTOVERS="$(python3 "$LEGACY" detect --blocking)"; then
  echo "ERROR: could not check for leftovers of an earlier install (see the message above). Nothing was changed."
  exit 1
fi
if [ -n "$LEFTOVERS" ]; then
  if [ "$MIGRATE_LEGACY" -eq 0 ]; then
    echo "ERROR: an earlier SmartThink install left real files that shadow this one:"
    printf '%s\n' "$LEFTOVERS" | sed 's/^/  /'
    echo ""
    echo "Nothing was changed. To move them to ~/.claude/.backup/ and install, run:"
    echo "  ./install.sh --migrate-legacy"
    exit 1
  fi
fi

# A detected leftover is about to be moved, so it does not block its target.
is_leftover() {
  # No pipe into grep -q: under pipefail an early grep exit can fail the writer with SIGPIPE.
  [ -n "$LEFTOVERS" ] && grep -qxF "$1" <<<"$(cut -f1 <<<"$LEFTOVERS")"
}

# 1. Preflight: every target is checked before anything changes (leftovers are moved only
# after it passes), so a blocked target can never leave a half-finished install behind.
BLOCKED=()
if [ -e "$SKILL_TARGET" ] && [ ! -L "$SKILL_TARGET" ] && ! is_leftover "$SKILL_TARGET"; then
  BLOCKED+=("$SKILL_TARGET exists as a directory (not a symlink)")
fi
for f in "${AGENT_FILES[@]}"; do
  target="$AGENTS_TARGET/$f"
  if [ -e "$target" ] && [ ! -L "$target" ] && ! is_leftover "$target"; then
    BLOCKED+=("$target exists as a regular file (not a symlink)")
  fi
done
if [ "${#BLOCKED[@]}" -gt 0 ]; then
  for reason in "${BLOCKED[@]}"; do
    echo "ERROR: $reason"
  done
  echo "They were not recognized as leftovers of an earlier SmartThink install, so they were not"
  echo "moved. Nothing was changed."
  echo "Back them up or remove them manually, then re-run install.sh."
  exit 1
fi

# A regular /st command that is not a SmartThink leftover is the user's own. It does not block
# the install (the skill still opens as /smartthink), but say so before anything changes.
for f in "${COMMAND_FILES[@]}"; do
  target="$COMMANDS_TARGET/$f"
  if [ -e "$target" ] && [ ! -L "$target" ] && ! is_leftover "$target"; then
    echo "WARNING: $target exists as a regular file and will be left alone."
    echo "         The /st alias will not be installed; use /smartthink instead."
  fi
done

# Vault, checked before any link is created so an unwritable vault stops the install cleanly.
# It lives OUTSIDE the repo so your profile and insights never get committed. The folder itself is
# NOT created here: /st init step 5 picks it (maybe an existing note store), and seeding the default
# first would leave an unused folder behind. The first run creates the resolved vault instead.
# scripts/resolve-vault.py owns the path rules; this script only checks and reports.
if ! VAULT_JSON="$(python3 "$RESOLVER")"; then
  echo "ERROR: could not resolve the vault (see the message above)."
  exit 1
fi
VAULT="$(printf '%s' "$VAULT_JSON" | python3 -c 'import json, sys; print(json.load(sys.stdin)["path"])')"
VAULT_SOURCE="$(printf '%s' "$VAULT_JSON" | python3 -c 'import json, sys; print(json.load(sys.stdin)["source"])')"
# The vault, or the nearest part of its path that already exists, must be a writable directory.
VAULT_BASE="$(python3 -c 'import os, sys; p = sys.argv[1]
while not os.path.lexists(p): p = os.path.dirname(p)
print(p)' "$VAULT")"
if [ ! -d "$VAULT_BASE" ] || [ ! -w "$VAULT_BASE" ]; then
  echo "ERROR: the vault $VAULT cannot be created or written ($VAULT_BASE is not a writable directory)."
  exit 1
fi
echo "Vault          : $VAULT (from $VAULT_SOURCE)"
if [ -d "$VAULT" ]; then
  echo "Packs dir      : $VAULT/packs"
else
  echo "Packs dir      : $VAULT/packs (created on first use; /st init can pick another vault)"
fi

if [ -n "$LEFTOVERS" ]; then
  echo "Moving leftovers of an earlier install to a backup:"
  if ! MOVED="$(python3 "$LEGACY" migrate --blocking)"; then
    echo "ERROR: moving the leftovers failed (see the message above). Check ~/.claude/.backup/ before re-running."
    exit 1
  fi
  printf '%s\n' "$MOVED" | sed 's/^/  /'
  echo ""
fi

mkdir -p "$HOME/.claude/skills" "$AGENTS_TARGET" "$COMMANDS_TARGET"

# 2. Skill symlink (SKILL.md + references/ + references/index.json + .data/ seeds)
if [ -L "$SKILL_TARGET" ]; then
  echo "Existing skill symlink found. Replacing..."
  rm "$SKILL_TARGET"
fi
ln -s "$SKILL_SOURCE" "$SKILL_TARGET"
echo "Skill linked   : $SKILL_TARGET -> $SKILL_SOURCE"

# 3. Agent definitions (st-thinker = report path, st-armorer = arming path)
for f in "${AGENT_FILES[@]}"; do
  target="$AGENTS_TARGET/$f"
  if [ -L "$target" ]; then
    rm "$target"
  fi
  ln -s "$AGENTS_SOURCE/$f" "$target"
  echo "Agent linked   : $target -> $AGENTS_SOURCE/$f"
done

# 3b. An older release installed agent definitions this version no longer ships. Those
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

# 4. /st command alias (the skill itself is invoked as /smartthink)
for f in "${COMMAND_FILES[@]}"; do
  target="$COMMANDS_TARGET/$f"
  if [ -L "$target" ]; then
    rm "$target"
  elif [ -e "$target" ]; then
    continue  # the user's own command, announced in the preflight
  fi
  ln -s "$COMMANDS_SOURCE/$f" "$target"
  echo "Command linked : $target -> $COMMANDS_SOURCE/$f"
done

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
