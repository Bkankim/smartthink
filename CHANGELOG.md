# Changelog

## [Unreleased] - 3.0.0

Context arming engine. Breaking: repository moves to the Claude Code plugin layout (`skills/smartthink/`, `agents/`, `commands/`); `skill/` is gone. `install.sh` still works for non-plugin installs.

- Plugin skeleton: `.claude-plugin/plugin.json`, `commands/st.md` alias, `tests/`.
- Everything else lands via the v3 work packages (see `docs/ARCHITECTURE.md` once written).

## 2.0.0 - 2026-09-07

Sync of the July 2026 agent-topology rebuild (agent-default mode, `--deep/--lite/--nosearch`, st-thinker + st-searcher, vault outside the repo). Commit bc31268.

## 1.0.0 - 2026-03-26

Initial public release at bkan-hq/smartthink.
