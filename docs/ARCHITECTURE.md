# SmartThink Architecture

Why the system is shaped this way. For how to use it see [README](../README.md); for how to change
it safely see [CONTRIBUTING](../CONTRIBUTING.md).

---

## 1. The problem

A session starts ignorant of the work it is about to do. It has general competence and no particular
preparation, and it commits to an approach in the first few sentences, before anything has told it
which frames the problem deserves.

There is a body of material that would help: mental models, thinking engines, strategy frameworks.
Two obvious ways to use it both fail.

**Load everything.** The nine reference modules total roughly 200K tokens. Loading them all leaves
no room for the work itself, and burying three relevant frames under thirty irrelevant ones is not
preparation, it is noise. Relevance does not come free with volume.

**Load summaries.** A summary of a mental model is a label for it. It tells a session that
"barbell strategy" exists without conveying the reasoning that makes it operational: the conditions
it assumes, the failure modes it warns about, the worked examples that show what counts as one arm
of the barbell. A session armed with labels produces text that names frameworks. A session armed
with the source produces judgments that use them.

So: neither everything nor a digest of everything. The material has to be **routed**, and what
survives the routing has to arrive **intact**.

---

## 2. Design principles

**(a) Route, do not load everything.** A Cynefin diagnosis and a classification tree pick five
candidate modules and star three. Past routing weights nudge the ranking but never override topic
fit. Everything downstream operates on that selection.

**(b) Verbatim, not summarized.** Selected modules enter the pack unchanged, byte for byte. The
application layer, the research, and the briefing are **added on top** as separate sections rather
than mixed into the source. A pack is the source amplified. This is the load-bearing decision of
the whole system; most of the mechanism below exists to keep it true.

**(c) Research after arming.** Search runs *after* the references are read, in the same window that
read them. A query written by something that already knows which frames it is feeding is a different
query: it goes looking for the specific numbers, players, and counter-signals those frames need,
rather than for a general overview. Reversing the order turns informed research back into ordinary
search.

**(d) A gate before the expensive commit.** Reading references and running research is the moment
cost becomes unrecoverable. Immediately before it, and only there, the system stops and shows the
user the interpreted task, the diagnosis, the selected modules, and the estimated cost in two units:
what will land in the main context, and what the sub-agent will burn. The user can adjust modules,
set a budget, or turn research off. This is the one required interaction in the system, and its
placement is the whole point: it is the last cheap moment before an expensive commitment.

**(e) End the turn at the briefing.** Arming is preparation, not a conclusion. When the pack is
loaded the system prints the briefing and stops. Continuing straight into the work would pour a
fully armed context into whatever direction was guessed at, and the guess is only as good as a
one-line topic. Stopping hands the direction back to the person who has the rest of the context.

**(f) Degrade predictably.** Environments differ: no sub-agent tool, no search, no agent definition,
no vault, no terminal. Every one of those has a fixed, documented behavior. A tool that improvises
under degradation is a tool whose output you cannot trust, because you cannot tell which version of
it produced any given result.

---

## 3. Components and ownership

Each fact lives in exactly one place. Everything else references it.

| Component | Responsibility | Source of truth for |
|---|---|---|
| `skills/smartthink/SKILL.md` | The pipeline: capability detection, profile load, diagnosis, routing, gate, spawn or inline execution, briefing, turn end | Syntax (subcommands and flags), the routing tables, the gate format, the cost formula, the degradation matrix |
| `agents/st-armorer.md` | Reads the selected references, researches, synthesizes, writes the pack, returns a manifest summary | The pack authoring procedure and the research fallback chain |
| `agents/st-thinker.md` | The `--report` path: takes a pack as input and writes an analysis report; keeps the feedback loop alive | Report-path behavior and the confirm-before-recording rule |
| `references/analysis-method.md` | The analysis pipeline itself | Methodology, the self-audit step, verbatim-integrity rules, the evolution-state schema and merge protocol |
| `references/lifecycle.md` | `init`, `retain`, `status` procedures | What is scanned, what is asked, what is proposed, what requires approval |
| `references/thinker-prompt.md` | The report path when the agent definition is absent | Nothing. It is a deliberate duplicate of the agent definition and must be kept in sync with it |
| `.data/README.md` | Ships blank seed templates | Vault layout, pack retention, permissions, privacy |
| The vault | All user state: profile, evolution state, packs | Lives outside the repository. Nothing personal is ever committed |

Two duplications are deliberate, because each side must work when the other is missing: the pack
section titles and manifest fields, shared by `SKILL.md` and the armorer; and the thinker's static
instructions, shared with the fallback prompt. Both are checked mechanically by
`scripts/check-structure.py`, because a duplicate that drifts is worse than no duplicate at all.

---

## 4. Two paths, one specification

```
                   /st <task or topic>
                            |
                   capability detection
                            |
              +-------------+-------------+
              |                           |
        Agent tool present          no Agent tool
              |                           |
        ARMORER PATH                 INLINE PATH
              |                           |
   spawn st-armorer (clean,      main session does the
   synchronous, inherits         same work in its own
   the session model)            context
              |                           |
   reads references              reads references
   researches                    researches
   writes pack.md +              writes pack.md +
   manifest.json                 manifest.json
              |                           |
   returns manifest summary               |
   only, never pack text                  |
              +-------------+-------------+
                            |
              main reads pack.md, prints
              section 1, ends the turn
```

The inline path is **not a lesser fallback.** Same gate, same pack specification, same vault, same
output quality bar. Exactly one thing differs: in the armorer path, reference text and raw search
pages are digested in a separate window, while inline they are spent from the main context. That is
a cost difference, and the gate states it rather than hiding it. The default is not changed on the
user's behalf.

Two properties keep the armorer path honest:

- **It spawns clean, never forked.** The armorer must read reference source into an empty window.
  Inheriting the main context would defeat the purpose of delegating.
- **It returns a manifest summary, never pack text.** If the pack came back as a return value, the
  source the armorer was supposed to absorb would land in the main context twice. The main session
  reads the file itself.

---

## 5. Pack structure and verbatim integrity

A pack is a directory holding `pack.md` and `manifest.json`. The section titles are fixed strings,
because the checker and the main session parse them:

```
## 1. 무장 브리핑            written last, printed as-is, ends the turn
## 2. 작업 해석              the task restated, or three candidate tasks from a bare topic
## 3. 리서치 합성            figures paired with sources, players, contrary signals, URLs
## 4. 작업 적용 레이어        per module: use this frame on this task, like so
## 5. 레퍼런스 원문           the selected modules, unchanged
## 6. 과거 인사이트와 프로필    what actually bears on this task
```

The order matters more than it looks. Sections 3 through 5 are written first; **the briefing is
written last**, so it describes what actually went into the pack rather than what was planned. And
the briefing is printed exactly as written, not re-synthesized by the main session: it was written
by something in an armed state, and rewriting it from an unarmed one dilutes it.

Section 5 carries the load-bearing guarantee, so it is enforced mechanically rather than by
instruction. Each module is wrapped:

```
<!-- MODULE-BEGIN: core-engines.md sha256=<64 hex chars> -->
(source text, unchanged)
<!-- MODULE-END: core-engines.md -->
```

The checker compares three values: the hash of the actual source file, the hash declared in the
marker, and the hash of the block copied into the pack. The only tolerated difference is a single
separator newline before the closing marker. Any other byte difference fails.

That covers a specific failure. Summarizing, reflowing, fixing a typo, normalizing whitespace,
adjusting a heading level, or translating are all edits a helpful writer makes without noticing,
and each of them quietly converts the pack back into the summary the design rejected. A hash makes
that unrepresentable instead of merely discouraged.

Two consequences follow. Trimming under a budget removes **whole modules**, never part of one:
a half-loaded module is a summary with extra steps. And `--digest`, which does ship distillations,
is a **separate mode** with a distinct marker (`MODULE-DIGEST`, no hash) rather than a quiet
degradation of the default. A pack is entirely verbatim or entirely distilled, never a mix, so
reading one tells you which kind you have.

---

## 6. Evolution

Three layers, each with different write rules, because they carry different kinds of truth.

| Layer | Contents | Written by | Rule |
|---|---|---|---|
| Profile | Identity, current goals, style, defaults, sources, history summary | `init`, and the user directly | Hand-editable by design. `retain` may only *propose* deltas |
| Routing weights, insights, gaps | Which modules work for which kind of thinking; insight and gap slots | `retain` | Nothing is written without explicit approval |
| Pack cache | Every pack built, reloadable | Each arming run | Retained 20 deep, never auto-deleted |

Both state files are a **YAML header plus a body**. The header is authoritative and machine-owned
(`routing_weights`, `sessions`, `diversity_h`); the body is the human-readable version. When they
disagree, the header wins. Earlier versions stored this as prose only, which meant every consumer
re-parsed sentences and disagreed about what a number was. Converting a prose file happens once, on
the first `retain`, after the original is backed up.

The feedback loop closes at routing. `retain` distinguishes frames that **actually changed a
decision** from frames that were merely loaded, and only the former raise a module's weight for that
kind of thinking. Unused modules decay. At the next arming those weights nudge the recommendation
ranking, but they never outrank topic fit and never outrank the Cynefin diagnosis, and a diversity
measure forces under-represented modules into the supplementary slots when one framework starts
dominating. A system that learns purely from its own recommendations converges on its own habits;
the ordering rule and the diversity check are what stop that.

Everything approval-gated is gated for the same reason: an evolution record written from a
conclusion the user later reversed teaches the system the wrong lesson permanently, and nothing
downstream can tell a confident wrong weight from a correct one. That is also why the report path
updates state only after an explicit confirmation, not when the first draft is returned.

---

## 7. Deliberately not done

Not oversights. Each is a real capability that was scoped out, with a reason.

- **Memory-server adapters.** Persisting evolution state through an external memory service instead
  of files. Files are inspectable, diffable, and have no runtime dependency, which is worth more
  while the schema is still settling.
- **English translations of the reference modules.** Translation is not an edit but a fork of the
  content, and it breaks every hash in the index and in every existing pack. Doing it properly means
  a parallel indexed module set, not a rewrite in place.
- **Cross-pack learning.** Packs are currently independent artifacts. Mining them collectively for
  patterns is a genuinely different system with its own failure modes, starting with reinforcing
  whatever the user already does.
- **Automatic retain hooks.** Recording evolution at session end without asking. The approval
  requirement is the thing keeping wrong conclusions out of the state, and an automatic hook removes
  exactly that.

---

## 8. Reading order

- `skills/smartthink/SKILL.md` for the pipeline, the syntax, and the degradation matrix
- `skills/smartthink/references/analysis-method.md` for the methodology and the integrity rules
- `agents/st-armorer.md` for how a pack is actually built
- `skills/smartthink/references/lifecycle.md` for `init`, `retain`, and `status`
- `scripts/check-structure.py` for every contract stated above, expressed as an executable check
