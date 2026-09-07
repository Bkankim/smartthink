English | [한국어](README.ko.md)

# SmartThink

**A context arming engine for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).**

SmartThink does not answer your question. It builds the session that will.

Before you start the real work, it deliberately spends tokens to turn the session into a specialist
for that specific task. This is not fine-tuning. It is in-context arming, and it lives only inside
the session. When it is done it prints a briefing and ends its turn, and you give the work order.

```
/st 사내 문서 검색 도구를 새로 만들지 기존 것을 개선할지 결정
```

---

## Why this is different

Most thinking-framework tools hand you a summary. SmartThink loads the **verbatim source**.

- **Verbatim, not summarized.** The selected reference modules go into the pack without a single
  character changed, and a SHA-256 contract proves it. On top of that text sits a task-fitted
  application layer and a research synthesis. A pack is the source, amplified, not compressed.
- **Routed, not everything.** The nine reference modules total roughly 200K tokens. Loading them
  all is not arming, it is drowning. A Cynefin diagnosis and a classification tree pick five
  candidates and star three, and you approve the selection at a gate before anything is read.
- **Research after arming.** References are read first, so the search queries are written by
  something that already knows which frames it is feeding. Raw pages are digested inside the
  sub-agent window, never in yours.
- **The turn ends at the briefing.** Arming is preparation, not a conclusion. Ending there is the
  last cheap moment for you to change direction.

---

## Install

The plugin is the canonical path.

```bash
# from a marketplace
/plugin marketplace add Bkankim/bkankim-plugins
/plugin install smartthink

# or straight from a local clone
git clone https://github.com/Bkankim/smartthink.git
claude --plugin-dir ./smartthink
```

> **Check the invocation name after installing.** Depending on your Claude Code version and how the
> plugin was loaded, the skill may appear as `/smartthink` or under a namespaced form. Run `/skills`
> and use whatever name is listed there. We are not going to guess it for you.

### Alternative: `install.sh`

If you would rather not use the plugin system, or you specifically want the short `/st` command
without a namespace, use the installer. It symlinks into `~/.claude/`:

```bash
git clone https://github.com/Bkankim/smartthink.git
cd smartthink
./install.sh
```

It installs one skill (`smartthink`), two agent definitions (`st-thinker`, `st-armorer`), and the
`/st` command alias, then seeds an empty vault at `~/.claude/smartthink-vault/`
(override with `SMARTTHINK_VAULT`). Upgrading from v2 also clears the symlink to the agent
definition that v3 deleted.

**Start a new Claude Code session afterwards.** Existing sessions do not pick up new skills or agents.

---

## Usage

### Subcommands

Recognized only when the **first token matches exactly**. `/st status page redesign` is a topic,
not the `status` subcommand.

| Subcommand | What it does |
|---|---|
| `/st init` | Local scan plus a short six-question interview, imprints your profile. Idempotent: an existing profile goes into update mode |
| `/st retain` | Infers from the session which frames actually changed your mind, proposes routing, insight and profile deltas, writes only what you approve |
| `/st status` | Profile summary, recent packs, evolution counts, environment diagnosis. Read-only |

### Flags

| Flag | What it does | When it earns its keep |
|---|---|---|
| `--digest` | Replaces the verbatim reference section with per-module distillations, 10-20K total | The frames matter but you cannot spare 100K of context for this task |
| `--report` | Feeds the pack to `st-thinker`, which writes an analysis report instead | You want the conclusion written for you, not the session armed |
| `--lite` | Cynefin plus first-principles analysis in context. No references, no pack, no gate | A quick read on a topic, or a harness where sub-agents are unavailable |
| `--nosearch` | Skips research; pack section 3 is omitted | The domain is one you already know, or the network is not worth the wait |
| `--budget N` | Caps the gate at N tokens and applies the trimming order | You know exactly how much context the rest of the session needs |
| `--pack <path>` | Reloads an existing pack and skips the gate | A new session on work you already armed for once |

**The topic is whatever text remains** after the subcommand and flags are stripped. Legacy prefixes
(`agent`, `light`, `search`) were removed in v3 and are now read as part of the topic.

---

## How a run goes

```
  capability detection      Agent tool available? -> armorer path, else inline path
          |
  profile + evolution       read from the vault, if they exist
          |
  Cynefin diagnosis         Clear domain? answer briefly and stop, no arming
          |
  module recommendation     5 candidates, 3 starred, routing weights applied
          |
  === GATE ===              interpretation, diagnosis, modules, estimated cost, research state
          |                 you can adjust modules, set a budget, or turn research off
  arming                    read references -> research -> synthesize -> write the pack
          |
  briefing                  section 1 of the pack, printed as written
          |
  turn ends                 you give the work order
```

The **gate is the core UX of this tool.** It is the last cheap moment before an expensive commit,
so it shows you the bill before you pay it:

```
━━ SmartThink 무장 게이트 ━━

1. 입력 해석
   사내 문서 검색 도구를 새로 만들지 기존 것을 개선할지 결정한다.
   판단 대상은 빌드 대 개선이며, 성공 기준은 아직 미확정이다.

2. 진단
   Cynefin: Complicated  |  분류: 의사 결정

3. 추천 모듈 (5개, ★ = 주력)
   ★ 인지 무기고     - 매몰 비용과 가용성 편향이 "새로 짓자"를 부풀리는 지점을 짚는다
   ★ 실행 속도       - 되돌릴 수 있는 결정과 없는 결정을 갈라 판단 속도를 정한다
   ★ 안티프래질 전략 - 기존 개선을 기본값으로 두고 신규 구축을 작은 옵션으로 사는 바벨 배치
     패턴 합성       - 같은 선택을 한 다른 팀들의 사후 신호를 찾는다
     메타인지        - 이 결정이 실제로는 조직 문제인지 되짚는다

4. 예상 비용 (추정치)
   메인에 실릴 팩      ≈ 123K 토큰
   서브에이전트 작업    ≈ 136K 토큰
   ※ 두 값 모두 추정이며 실제와 다를 수 있습니다.

5. 리서치: ON (기본)

6. 조작
   Enter    진행
   숫자     예산 상한 지정 (예: 60000)
   모듈 ±   추가·제거 (예: "메타인지 빼고 유니콘 플레이북 넣어")
   --nosearch  리서치 끄기
```

Typing `60000` there trims in a fixed order: shrink research first, then drop whole low-priority
modules, then compress the application layer. **A module is never cut in half.** Truncating source
text turns the pack back into a summary, which is the one thing this tool exists to avoid.

Running headless, the gate auto-proceeds under a 120K cap and reports what it trimmed.

---

## What a pack is

A pack is a directory in your vault holding two files:

```
{VAULT}/packs/2026-03-14-team-onboarding-redesign/
├── pack.md
└── manifest.json
```

`pack.md` always has these six sections, in this order:

| Section | Contents |
|---|---|
| 1. 무장 브리핑 | Active frames, the rules to follow for this task, relevant past insights, biases to watch, what to do next. 30-50 lines. This is what gets printed |
| 2. 작업 해석 | The task restated. If you gave only a topic, three concrete candidate tasks instead |
| 3. 리서치 합성 | Domain state, figures paired with sources, players, at least one contrary signal, source URLs. Omitted with `--nosearch` or when search is unavailable |
| 4. 작업 적용 레이어 | Per module, 20-40 lines of "use this frame on this task like so", including conflicts between frames and which to follow when |
| 5. 레퍼런스 원문 | The selected modules verbatim, wrapped in `MODULE-BEGIN` / `MODULE-END` markers carrying the source SHA-256 |
| 6. 과거 인사이트와 프로필 | The insights and profile fields that actually bear on this task |

`manifest.json` records the task, interpretation, Cynefin domain, classification, modules, budget,
research flag, profile version, token estimates, creation time, and harness. Packs are kept 20 deep;
past that SmartThink tells you which are oldest and lets **you** decide. It never deletes one, because
`--pack` can reload it.

---

## Evolution

SmartThink adapts to you across three layers.

| Layer | What it holds | Who writes it |
|---|---|---|
| Profile | Identity, current goals, style, defaults, sources, history summary | `/st init`, and you: it is meant to be hand-edited |
| Routing weights, insights, gaps | Which modules actually work for which kind of thinking, plus insight and gap slots | `/st retain`, only what you approve |
| Pack cache | Every pack ever built, reloadable with `--pack` | Each arming run |

- **`/st init`** scans locally (project root instruction files, `~/.claude`, 50 git log entries, and
  a notes directory if you name one), shows you what it inferred, asks six short questions you can
  skip entirely, and writes the profile. It reads only; nothing is transmitted anywhere.
- **`/st retain`** works out which frames actually changed a decision and which were loaded but
  never mattered, then shows three separate proposals: routing weight deltas, insight and gap
  changes, and profile deltas. Accept, reject, or edit each one independently. Nothing is written
  without approval.
- **`/st status`** prints the profile summary, the five most recent packs, evolution counts, and an
  environment diagnosis with one line per problem on how to fix it. It writes nothing.

All of it lives **outside the repository**, at `~/.claude/smartthink-vault/` by default, or wherever
you point `SMARTTHINK_VAULT` or your profile. Your insights are never committed.

---

## Environment differences (graceful degradation)

Behavior in a degraded environment is fixed, not improvised.

| Missing | Behavior |
|---|---|
| Agent tool (Codex and similar) | **Inline path**: the main session does the same work itself, with the same gate, the same pack spec, and the same vault. The only difference is that reference loading and research spend main context, and the gate says so |
| `st-armorer` definition | Falls back to a general-purpose agent briefed with the full pack spec; failing that, the inline path |
| `st-thinker` definition | `--report` falls back to a general-purpose agent driven by the bundled fallback prompt |
| Search tools, or search fails | Pack section 3 is omitted, `manifest.research=false`, and the briefing says so. A missing tool is reported differently from a user-chosen `--nosearch` |
| `insane-search` skill | Plain fetches only. Blocked sources are labeled "차단" and skipped rather than worked around |
| Vault | Seeded on the spot. With no profile, the briefing points you at `/st init` |
| v2-format evolution state | Read as-is. Converted on the first `retain`, with the original backed up |
| `references/index.json` | Module sizes are measured directly and the gate marks the estimate as measured rather than precomputed |
| Interactive terminal (headless) | The gate auto-proceeds under a 120K cap and reports what it trimmed |

---

## Reference modules

> **The nine reference modules are written in Korean.** They are loaded verbatim, so a pack's
> section 5 is Korean regardless of your interface language. The synthesized parts (briefing,
> interpretation, research, application layer) follow the language in your profile. If reading
> Korean source text is a problem for you, this tool will not work well for you today. Translation
> is a known gap, not a hidden one.

| Module | Role |
|---|---|
| 핵심 엔진 (Core Engines) | The 12 operating engines: first principles, asymmetric opportunity, network effects, market creation, moat building, contrarian validation, value capture, timing, compound advantage, ecosystem design, inversion, lollapalooza |
| 인지 무기고 (Cognitive Arsenal) | 81 mental models across nine domains, from physics and biology to game theory, psychology, and competitive advantage |
| 유니콘 플레이북 (Unicorn Playbook) | Zero-to-$1B business building in six phases, with the antipatterns |
| 현실 왜곡 (Reality Distortion) | Constraint inversion, category creation, temporal arbitrage, paradigm architecture, counterfactual thinking |
| 패턴 합성 (Pattern Synthesis) | Cross-domain pattern recognition, convergence detection, anomaly mining, weak-signal detection |
| 실행 속도 (Execution Velocity) | OODA loops, decision frameworks, judging when blitzscaling conditions actually hold |
| 안티프래질 전략 (Antifragile Strategy) | Barbell strategy, optionality, convexity, black-swan positioning, reflexivity |
| TRIZ 혁신 시스템 (TRIZ Innovation) | The 40 inventive principles, contradiction resolution, ideal final result, laws of technical evolution |
| 메타인지 (Meta-Cognition) | Recursive self-improvement, Cynefin diagnosis, Wardley mapping, inversion, lollapalooza detection |

---

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Sub-agent support gets you the
  armorer path; without it you get the inline path, which produces the same pack.
- Python 3 for `scripts/build-index.py` and `scripts/check-structure.py`. Neither is needed to
  *use* SmartThink, only to develop it.
- macOS or Linux for `install.sh` (on Windows use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/)).
  The plugin route has no such restriction.
- Optional: the `insane-search` skill, for sources that block plain fetches. Without it those
  sources are skipped and labeled.
- Codex and other non-Claude-Code harnesses are expected to work through the inline path, but that
  is not yet verified.

---

## Uninstall

```bash
cd smartthink
./uninstall.sh
```

Symlinks go, the vault stays. Delete `~/.claude/smartthink-vault/` yourself for a full reset.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Design rationale lives in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); the release history is in [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).
