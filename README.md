English | [한국어](README.ko.md)

# SmartThink

**천재적 사고 엔진 시스템** - A genius-level thinking engine for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

SmartThink combines 9 thinking frameworks (81 mental models, 12 operating engines, TRIZ innovation principles, antifragile strategy, and more) with Cynefin-based situation diagnosis to deliver deep, creative analysis on any topic. It is a skill plus two dedicated sub-agents: the analysis body runs in its own context, and a search scout feeds it real-world data.

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/Bkankim/smartthink.git
cd smartthink
./install.sh
```

The installer creates three symlinks (`~/.claude/skills/smartthink`, `~/.claude/agents/st-thinker.md`, `~/.claude/agents/st-searcher.md`) and seeds an empty evolution vault at `~/.claude/smartthink-vault/`.

### 2. Open a new Claude Code session

```bash
claude
```

> **Important**: Start a **new** session after installation. Existing sessions won't recognize the skill or the agents.

### 3. Try it

```
/smartthink 1인 기업의 확장 전략
```

`/st` works as a short alias. SmartThink diagnoses your topic, picks the best frameworks, gathers search data, and returns a full analysis with 6-10 actionable ideas.

---

## Three Modes

| Flag | Mode | Where it runs | Interaction |
|------|------|---------------|-------------|
| (none) | **Agent** (default) | `st-thinker` sub-agent | none during analysis, feedback loop after |
| `--deep` | **Deep** | main agent | checkpoints at every decision point |
| `--lite` / `--light` | **Light** | main agent, no reference modules | none |

`--nosearch` skips web search in any mode. Web search is **on by default** in every mode.

### Agent Analysis (default)

The whole analysis is delegated to the `st-thinker` sub-agent (STSA). It loads the reference modules into its own context, so your main session stays lean. After it returns, the agent stays alive in the background: give feedback and it revises in place, say "확정" (confirm) and it writes the final insights to the evolution vault.

```
/smartthink AI 스타트업에서 네트워크 효과를 만드는 방법
```

### Deep Analysis

The main agent runs the analysis itself and checks in with you at each interaction point: Cynefin boundary, module selection, and the search data pack before the heavy reference load.

```
/smartthink --deep 1인 기업의 수익 모델 설계
```

### Light Analysis

Quick analysis using only Cynefin diagnosis plus first-principles decomposition, no reference modules loaded. Still runs the search scout unless `--nosearch` is given.

```
/smartthink --lite 사이드 프로젝트 아이디어
/smartthink --lite --nosearch 사이드 프로젝트 아이디어
```

Legacy prefixes (`agent <topic>`, `light <topic>`, `search <topic>`) are still accepted as aliases, but `--` flags are the canonical form.

---

## What Happens Behind the Scenes

```
You type: /smartthink [--deep|--lite] [--nosearch] 주제
         ↓
    ┌─────────────────────────────────────┐
    │  Main Agent                          │
    │  1. Cynefin diagnosis                │
    │  2. Topic classification + modules   │
    │  3. Spawn st-searcher ──► data pack  │  (≤2K tokens, sources paired)
    │  4. Mode branch                      │
    └──────────┬──────────────────────────┘
               ↓
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
  Agent       Deep          Light
  st-thinker  main agent    main agent
  (background (interactive) (no refs)
   + feedback
   loop)
```

- **st-searcher** (Sonnet) digests raw search results in its own window and returns only a compact data pack: quantified table with sources, player list, trends plus at least one contrary signal, and source URLs. Raw pages never enter the main context.
- **st-thinker** (inherits session model, 30-turn cap) runs the pipeline in `skill/references/analysis-method.md`: self-audit, module load, multi-layer analysis, cross-engine synthesis, idea generation, Top 3 with unicorn assessment, next steps.

---

## Evolution System

SmartThink learns from each session.

- Effective thinking patterns are saved as **insights** (up to 10 slots)
- Blind spots are tracked as **gaps** (up to 5 slots)
- Module diversity is monitored so you don't over-rely on one framework
- A self-audit step guards against the evolution state pre-deciding the conclusion

Evolution data lives **outside the repo** at `~/.claude/smartthink-vault/evolution-state.md` (override with `SMARTTHINK_VAULT`). Nothing personal is ever written into the cloned repo. The file `skill/.data/evolution-state.md` is only the empty template the installer seeds from.

In Agent mode the vault is updated only after you confirm the final version, so feedback-driven revisions never get stale insights recorded.

---

## Thinking Modules

| Module | Key Frameworks |
|--------|---------------|
| Core Engines | First Principles, Asymmetric Opportunity, Network Effects, Market Creation, Moat Building, Contrarian Validation, Value Capture, Timing Intelligence, Compound Advantage, Ecosystem Design, Inversion, Lollapalooza Detection |
| Unicorn Playbook | $0-to-$1B business building (6 phases) |
| Reality Distortion | Constraint Inversion, Category Creation, Temporal Arbitrage |
| Cognitive Arsenal | 81 mental models across 9 disciplines |
| Pattern Synthesis | Cross-domain pattern recognition, Weak signal detection |
| Execution Velocity | OODA Loop, Decision frameworks, Blitzscaling |
| Antifragile Strategy | Barbell Strategy, Optionality, Black Swan positioning |
| TRIZ Innovation | 40 Inventive Principles, Contradiction resolution |
| Meta-Cognition | Recursive self-improvement, Wardley Mapping, User frame bias detection |

SmartThink selects 2-3 modules based on your topic type (idea discovery, strategy, problem solving, decision, systematic invention, and so on).

---

## Repository Layout

```
skill/            the skill (SKILL.md + references/) - symlinked to ~/.claude/skills/smartthink
agents/           st-thinker.md, st-searcher.md     - symlinked into ~/.claude/agents/
scripts/          check-structure.py                - 66-point wiring check (skill <-> agents <-> prompt)
install.sh        creates the symlinks and seeds the vault
uninstall.sh      removes the symlinks, keeps the vault
```

Run the structure check after editing anything under `skill/` or `agents/`:

```bash
python3 scripts/check-structure.py             # checks the repo copy
python3 scripts/check-structure.py --installed # checks what Claude Code actually loads
```

---

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI with custom agents support
- macOS or Linux (Windows: use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/))
- Optional: the `insane-search` skill for reaching sites that block plain fetches. Without it, `st-searcher` simply skips blocked sources.

## Uninstallation

```bash
cd smartthink
./uninstall.sh
```

Your evolution vault stays in place. Delete `~/.claude/smartthink-vault/` for a full reset.

## License

MIT
