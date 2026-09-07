# Contributing to SmartThink

Thanks for your interest. This document covers the parts of the repo that will bite you if you
change them without knowing what they are wired to.

## How to Contribute

### Bug Reports

Open an [issue](https://github.com/Bkankim/smartthink/issues) with:

- The exact invocation, flags included (`/st --digest --nosearch <topic>`)
- Which path ran: armorer (sub-agent) or inline (main context). The gate and the briefing say which
- What you expected vs what happened
- Claude Code version (`claude --version`), and whether you installed as a plugin or via `install.sh`
- If a pack was produced, its `manifest.json`. Do not paste `pack.md`: it contains your task and
  your profile excerpt

### Feature Requests

Open an issue with the `enhancement` label. Describe the problem, your proposed solution, and which
component it touches (routing, gate, pack spec, an agent, lifecycle, or the vault schema).

### Pull Requests

1. Fork and branch from the default branch
2. Make the change
3. Update **both** `README.md` and `README.ko.md` if user-facing text changes. They are a language
   pair: a section that exists in one must exist in the other
4. Run the development loop below until it is green
5. Submit the PR, and say in the description what you verified and what you did not

---

## Development loop

```bash
git clone https://github.com/Bkankim/smartthink.git
cd smartthink

python3 scripts/build-index.py        # only if you touched references/
python3 scripts/check-structure.py    # must be green
python3 scripts/check-structure.py --strict   # the final gate before a release
```

`check-structure.py` is the wiring checker. It verifies the plugin layout, agent frontmatter,
the shared pack contract, the reference index, the vault schemas, document hygiene, and, when you
pass `--pack <path>`, a real pack including the verbatim hashes.

`--strict` is the release gate. It promotes checks that are deliberately skipped during parallel
work into failures, so a PR that leaves a placeholder behind cannot ship.

To exercise the real thing, install into a session and run `/st --lite <topic>` first (fastest
feedback), then `/st <topic>` to drive the gate, the armorer, and the pack.

---

## The nine reference modules are frozen

`skills/smartthink/references/` contains nine mental-model modules: `core-engines.md`,
`cognitive-arsenal.md`, `unicorn-playbook.md`, `reality-distortion.md`, `pattern-synthesis.md`,
`execution-velocity.md`, `anti-fragile-strategy.md`, `triz-innovation.md`, `meta-cognition.md`.

**Their content is frozen. Editing one has consequences beyond the file:**

- `references/index.json` stores a SHA-256 per module. Change a byte and the stored hash is wrong.
- Every pack ever built embeds the module text inside `MODULE-BEGIN ... MODULE-END` markers carrying
  that same hash. Existing packs still on disk become unverifiable, and `--pack` reloads of them
  will fail the integrity check.

If a module genuinely must change, **regenerating the index is part of the same change, not a
follow-up**:

```bash
python3 scripts/build-index.py
python3 scripts/check-structure.py
```

Commit `references/index.json` alongside the module edit. A PR that edits a module without the
regenerated index will be rejected by the checker before anyone reads it.

Two things follow from the freeze:

- **The modules stay in Korean.** Translating them is a fork of the content, not an edit, and it
  breaks every hash. It is tracked as future work, not as a PR you can open today.
- The other files under `references/` (`analysis-method.md`, `lifecycle.md`, `thinker-prompt.md`)
  are **procedure documents, not modules.** They are not indexed and not hashed, and you may edit
  them normally.

---

## Wiring contracts

Some instructions are deliberately duplicated across files so each side works standalone. When a
contract is duplicated, **both sides must be edited together.** The checker catches drift, but only
after you have already written half a change.

| Contract | Files | What is shared |
|---|---|---|
| Pack contract | `skills/smartthink/SKILL.md`, `agents/st-armorer.md` | The six pack section titles, verbatim, and the `manifest.json` field names. The main session parses what the armorer writes; a renamed section title silently breaks the briefing |
| Report fallback | `agents/st-thinker.md`, `skills/smartthink/references/thinker-prompt.md` | The full static instruction set. The prompt file is the fallback used when the agent definition is missing, so drift means the fallback silently behaves differently |
| Methodology | `skills/smartthink/references/analysis-method.md` | The single source of truth for the analysis pipeline, the verbatim-integrity rules, the evolution-state schema, and the merge protocol. Other files reference it; **do not restate a formula or schema elsewhere** |
| Vault layout | `skills/smartthink/.data/README.md` | Vault paths, pack retention, permissions, privacy. `lifecycle.md` points here rather than repeating it |

`skills/smartthink/.data/` ships **blank seed templates only.** Real user state lives in the vault.
Never commit a filled-in `profile.md` or `evolution-state.md`.

---

## Documentation rules

- **No em dashes.** Use a hyphen. The checker scans every editable `.md` and `.py` for them; the
  nine frozen modules are exempt because fixing them would break their hashes.
- **No private information.** This is a public repository. No private host or organization names,
  no absolute home paths, no personal vault paths. The checker scans for these patterns too.
- Reference the public repository as `https://github.com/Bkankim/smartthink`.
- Keep `README.md` and `README.ko.md` structurally identical.
- Document what the code actually does. If something is unverified, say it is unverified rather
  than writing it as fact.

---

## Testing

There is no automated end-to-end suite: the pipeline runs inside a live agent session, and the
things worth testing are behavioral (does the gate appear, does the turn actually end, does the
fallback engage when an agent definition is missing).

`tests/gates.md` holds the scenarios, their pass criteria, and the evidence each one requires. Run
them by hand and drop the evidence in `tests/evidence/` as files, named for the scenario. A PR that
changes routing, the gate, an agent, or the vault schema should say which scenarios were run and
link the evidence.

---

## Code of Conduct

Be respectful and constructive. We follow the
[Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
