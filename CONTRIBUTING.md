# Contributing

Issues and pull requests are welcome.

## Set up

```bash
git clone https://github.com/0xCydral/skillsonar.git
cd skillsonar
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
```

## Pull requests

1. One concern per pull request.
2. Add tests for new logic. Tests use pytest and never touch the network: stub `OllamaClient` and
   `RerankClient` (see `tests/conftest.py`).
3. No new runtime dependencies. The core is standard library only.
4. Keep every outside service behind its one client class (`ollama.py`, `rerank.py`). Other
   modules ask for embeddings or a ranking, and never build a URL or read a key.
5. Run `python -m ruff check .` before pushing.

## Where to start

- Ranking quality: new queries for `evals/queries.jsonl`, or fixture skills that expose a weakness.
- Skill folders used by other agents that `skillsonar build` should look in by default.
- Measurements of `--rerank` with a real model, reported with the model and the query set.

## Reporting issues

Include the output of `skillsonar --version`, your Python version and operating system, the exact
command, and the full error. For embeddings problems, add the output of `ollama list`.

## Code layout

```
src/skillsonar/
  cli.py        argument parsing and output
  index.py      SKILL.md parsing, scanning, keyword scoring
  semantic.py   embedding index and cosine ranking
  search.py     keyword, semantic and hybrid modes, rerank pipeline
  evaluate.py   recall@k
  ollama.py     OllamaClient, the only code that talks to Ollama
  rerank.py     RerankClient, the only code that talks to the rerank model
  paths.py      default skill folders and the cache directory
```

## License

By contributing, you agree your contributions are licensed under the [MIT License](LICENSE).
