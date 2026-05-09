# Contributing

Thanks for your interest. Pull requests, issues, and discussions are
all welcome.

## Quick start

```bash
git clone https://github.com/AdrianCsT/opencode-router.git
cd opencode-router
python3 -m pip install --user -e ".[dev]"
python3 -m unittest discover -s tests
```

## What needs work

A non-exhaustive list:

- **Wider provider coverage** — additional starter profiles for
  providers we don't yet ship (Anthropic, OpenAI, Together, etc.).
- **Claude Code adapter** — equivalent of the `register` command for
  Claude Code's subagent format.
- **Additional embedding/rerank models** — verified working
  combinations, with notes on accuracy/latency tradeoffs.
- **Bigger test suite** — particularly route-level integration tests
  that mock Ollama.
- **Better defaults** — more sensible default rules without becoming
  opinionated about specific agent collections.

## Pull request guidelines

1. **One concern per PR.** Don't bundle a feature with an unrelated
   refactor.
2. **Tests for new logic.** Use `unittest` from the stdlib — no extra
   test deps. Mock Ollama when needed.
3. **No new runtime dependencies** without strong justification. The
   package is stdlib-only by design.
4. **Backwards-compatible config schemas.** If you add a field, make
   it optional and document the default.
5. **Follow existing style.** `ruff check src/` should pass.

## Reporting issues

Include:

- OpenCode version (`opencode --version`)
- Python version (`python3 --version`)
- Ollama version (`ollama --version`) and whether the daemon is running
- The exact `opencode-router` command you ran
- Full error output (or last 30 lines)
- Output of `opencode-router doctor`

## Code organisation

```
src/opencode_router/
├── __init__.py            # version
├── __main__.py            # python -m opencode_router
├── cli.py                 # arg parser + subcommand dispatch
├── paths.py               # filesystem paths (env-var overridable)
├── ollama.py              # tiny stdlib HTTP client
├── agents.py              # parse .md frontmatter + body
├── index.py               # build/search the embedding index
├── route.py               # two-stage routing (retrieve + rerank)
├── rules.py               # role-pattern → bucket
├── profile.py             # provider profile load/save/set
└── opencode.py            # opencode.json patcher
```

Each module is small and focused. Keep it that way.

## License

By contributing, you agree your contributions are licensed under the
[MIT License](LICENSE).
