# Contributing to SmartThink

Thank you for your interest in contributing to SmartThink!

## How to Contribute

### Bug Reports

Open an [issue](https://github.com/Bkankim/smartthink/issues) with:
- SmartThink mode used (Deep / Agent / Light)
- What you expected vs what happened
- Claude Code version (`claude --version`)

### Feature Requests

Open an issue with the `enhancement` label. Describe:
- The problem you're trying to solve
- Your proposed solution
- Which thinking module it relates to (if any)

### Pull Requests

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Ensure both `README.md` and `README.ko.md` are updated if user-facing text changes
4. Submit a PR

#### What to contribute

- New thinking modules or mental models (add to `skill/references/`)
- Improvements to analysis methodology (`skill/references/analysis-method.md`)
- Bug fixes in skill routing or mode handling (`skill/SKILL.md`)
- Sub-agent behaviour (`agents/st-thinker.md`, `agents/st-searcher.md`)
- Documentation improvements

#### What NOT to change

- `skill/.data/evolution-state.md` - keep it an empty template; real data lives in the user's vault
- Evolution state format - changing the slot format breaks semantic merge across sessions
- The wiring contract between `skill/SKILL.md`, `skill/references/thinker-prompt.md` and `agents/` - if you must, update all sides and keep `scripts/check-structure.py` green

### Development Setup

```bash
git clone https://github.com/Bkankim/smartthink.git
cd smartthink
./install.sh
python3 scripts/check-structure.py   # must print 66/66 passed
```

Test your changes by running `/smartthink --lite <topic>` in a new Claude Code session (fastest feedback loop), then `/smartthink <topic>` to exercise the sub-agents.

## Code of Conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
