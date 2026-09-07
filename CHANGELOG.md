# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [semver](https://semver.org/).

## 3.0.0 (unreleased)

SmartThink stops being an analysis command and becomes a **context arming engine**. It no longer
answers your question: it builds the session that will. Before you start the real work, it routes
your task through a Cynefin diagnosis, picks only the reference modules that task needs, shows you
the estimated cost at a gate, and assembles an **armory pack**: the selected reference text verbatim,
plus a task-fitted application layer and a researched domain synthesis on top. Then it prints a
briefing and ends its turn, so you decide what happens next.

### Added

- **Arming gate (HITL-1)**, the one required interaction. Shows the interpreted task, the Cynefin
  domain and classification, five recommended modules with three starred, the estimated cost in two
  units (what lands in the main context vs what the sub-agent burns), and the research on/off state.
  You can adjust modules, set a budget, or turn research off before anything expensive happens.
- **Armory pack**, a six-section artifact written to the vault as `pack.md` + `manifest.json`:
  arming briefing, task interpretation, research synthesis, per-module application layer, verbatim
  reference text, and past insights plus profile excerpt.
- **Verbatim integrity contract.** Reference text in the pack is wrapped in `MODULE-BEGIN` /
  `MODULE-END` markers carrying a SHA-256 of the source file, so `scripts/check-structure.py` can
  prove no module was summarized, reflowed, or truncated on its way into the pack.
- **`st-armorer` agent.** Reads references, researches, and synthesizes in its own window, writes
  the pack files, and returns only a manifest summary. Pack text never round-trips through the
  main context.
- **Inline path** for harnesses without an Agent tool. Same gate, same pack spec, same vault; the
  only difference is that reference loading and research spend main context, which the gate says
  out loud.
- **Lifecycle subcommands** `init`, `retain`, `status`, recognized only on an exact first-token
  match. `init` scans locally and runs a short six-question interview to imprint a profile;
  `retain` proposes routing-weight, insight/gap, and profile deltas for your approval; `status`
  summarizes state and diagnoses the environment (no separate doctor command).
- **Three-layer evolution**: user profile, routing weights plus insights and gaps, and a pack cache
  that `--pack` can reload.
- **New flags** `--digest` (distilled reference section, 10-20K), `--report` (the analysis-report
  path), `--budget N`, and `--pack <path>`.
- **Plugin packaging**: `.claude-plugin/plugin.json`, `commands/st.md` alias, `docs/ARCHITECTURE.md`,
  `scripts/build-index.py` (generates `references/index.json` with per-module sizes and hashes),
  a rewritten `scripts/check-structure.py`, and `tests/gates.md` with an evidence directory.
- **Graceful degradation table** fixing behavior when the Agent tool, an agent definition, search
  tools, `insane-search`, `index.json`, or the vault is missing, and when running headless
  (the gate auto-proceeds under a 120K cap).

### Changed

- **Default mode is arming, not answering.** The turn ends after the briefing. Starting the real
  work is your call, which is the point: it is the last cheap moment to change direction.
- **Packs carry reference text verbatim, not summaries.** Compression is a separate mode
  (`--digest`), never a silent degradation of the default path.
- **Research runs after arming, inside the sub-agent window.** References are read first so the
  queries are informed ones, and raw pages are digested there instead of in your session.
- **`--report` is now pack-driven.** `st-thinker` takes the pack file path as input rather than
  selecting and loading references itself, and still keeps the feedback loop and the
  confirm-before-recording rule.
- **`--lite` no longer spawns a search scout.** It is Cynefin plus first-principles analysis in
  context, and doubles as the fallback for environments without sub-agents.
- **Repository layout moved to the Claude Code plugin layout**: `skills/smartthink/`, `agents/`,
  `commands/`. The old top-level `skill/` directory is gone.
- **`install.sh` now links the skill, both agent definitions, and the `/st` command alias**, seeds
  `packs/` in the vault, and clears symlinks left over from v2 agent definitions that no longer
  exist. `uninstall.sh` removes the same set and leaves the vault untouched.
- **Documentation** states plainly that the nine reference modules are written in Korean, while
  synthesized output follows your language.

### Removed

- **`--deep` mode.** Its interactive checkpoints are covered by the single arming gate, and its
  in-main-context analysis is what the inline path does when the environment requires it.
- **Legacy prefix aliases** `agent <topic>`, `light <topic>`, `search <topic>`. The modes they
  named no longer exist. Text starting with those words is now treated as the topic itself.
- **The `st-searcher` agent definition** (`agents/st-searcher.md`), removed and folded into
  `st-armorer`. Research now happens in the same window that read the references, which is what
  makes the queries informed.
- **`effort` and `argument-hint` keys** from the skill frontmatter (neither is documented skill
  frontmatter). The briefing recommends `/effort xhigh` in prose instead.

### Breaking

- `--deep` is gone. Invocations using it must drop the flag.
- The prefix aliases `agent` / `light` / `search` are gone and are no longer stripped from input.
- `agents/st-searcher.md` is deleted. Anything that spawned `st-searcher` by name must target
  `st-armorer`, and a v2 install left a symlink to it that now dangles.
- The evolution state file changed from prose to a YAML header plus body (`routing_weights`,
  `sessions`, `diversity_h`). The first `retain` converts a v2 file automatically and backs the
  original up as `evolution-state.v2.bak.md`; the filename `evolution-state.md` does not change.
- The repository layout moved from `skill/` to `skills/smartthink/`. Anything pinned to the old
  path, including hand-made symlinks, breaks.
- Users who installed from a private organization mirror of this project must move to
  `Bkankim/smartthink`. The mirror is frozen at v1 and receives none of this.

### Migration from v2

1. `git pull` (or re-clone) and re-run `./install.sh`. It relinks everything and clears the stale
   agent symlink from v2 on its own.
2. Drop `--deep` from any saved invocation, and drop the `agent` / `light` / `search` prefixes.
3. Run `/st init` once to create the profile. Arming works without it, but routing does not adapt
   to you until it exists.
4. Run `/st retain` once in a session that used SmartThink. That is what converts an existing
   evolution state to the new format and writes the backup.
5. Expect the default path to end with a briefing instead of an answer. Give the work order after
   it, and prefer `/effort xhigh` for deep tasks.

## 2.0.0 - 2026-09-07

Sync of the July 2026 agent-topology rebuild (agent-default mode, `--deep`/`--lite`/`--nosearch`,
an analysis agent plus a search scout, vault kept outside the repo).

## 1.0.0 - 2026-03-26

Initial public release.
