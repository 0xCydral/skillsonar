# AGENTS.md — Developer setup for coding agents

Instructions for LLM agents working on or with this project. Humans: paste
this into your agent or point it at this file.

## Quick install (paste this)

```bash
# 1. Prerequisites
brew install python@3.12 ollama          # macOS
# Ubuntu: sudo apt install python3.12 pipx && pipx install ollama

# 2. Ollama models (~4 GB, one-time)
ollama pull mxbai-embed-large
ollama pull qwen3.5:4b

# 3. opencode-router
git clone https://github.com/AdrianCsT/opencode-router.git ~/opencode-router
cd ~/opencode-router
python3 -m pip install -e ".[dev]"

# 4. Import agents + configure
# If you already have agents, back up your config first:
cp ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.bak 2>/dev/null || true
bash scripts/import-agents.sh
cp examples/router-prompts/default.md ~/.config/opencode/agents/router.md
opencode-router init   # also auto-creates opencode.json.backup-<timestamp>

# 5. Verify
opencode-router doctor
python3 -m unittest discover -s tests -v
```

## Toolchain

| Tool | Version | Install | Purpose |
|------|---------|---------|---------|
| Python | ≥ 3.10 | `brew install python@3.12` | Runtime |
| Ollama | latest | `brew install ollama` | Local embeddings + LLM rerank |
| OpenCode | ≥ 1.14.20 | `npm i -g opencode` or [opencode.ai](https://opencode.ai) | Agent TUI |
| Claude Code | latest | `npm i -g @anthropic-ai/claude-code` | CLI agent (optional) |
| Hermes | latest | [ECC plugin](https://github.com/everything-claude-code/everything-claude-code) | Agent orchestration (optional) |

### Ollama models

```bash
ollama pull mxbai-embed-large   # 1024-dim embeddings, ~670 MB
ollama pull qwen3.5:4b          # LLM rerank, ~2.4 GB
```

### OpenCode config

opencode-router writes to `~/.config/opencode/`:
- `opencode.json` — agent registry + model assignments
- `agents/router.md` — the router primary agent prompt
- `agents/*.md` — specialist subagents
- `agent-index.json` — pre-built 1024-dim embeddings
- `orchestration-profile.json` — provider profiles
- `orchestration-rules.json` — role-pattern → bucket rules

## Provider profiles

Switch all agents to a new provider:

```bash
opencode-router profile list          # see available
opencode-router profile set <name>    # switch + re-apply models
opencode-router profile current       # show active
```

Shipped profiles: `ollama-local`, `ollama-local-multi`, `ollama-cloud`,
`nvidia-nim`, `deepseek-official`.

## Project memory

Every project gets `.opencode-router/memory.md` built on first dispatch:

```bash
opencode-router memory rebuild --force
opencode-router memory show
opencode-router memory log --tail 10
opencode-router memory inject "fix auth bug"
opencode-router memory clear
```

Memory is auto-rebuilt when files change (≥10), git HEAD moves, or
24h elapse.

## AgentSkillOS (optional — for orchestrate)

```bash
git clone https://github.com/ynulihao/AgentSkillOS ~/AgentSkillOS
cd ~/AgentSkillOS
cp .env.example .env   # add your API key
pip install -e .
```

The `orchestrate` subcommand uses AgentSkillOS for skill discovery.
Without it, orchestrate still works but skips the skill catalog.

## Development

```bash
# Install dev deps
pip install -e ".[dev]"

# Lint
python3 -m ruff check src/ tests/

# Auto-fix
python3 -m ruff check --fix src/ tests/

# Tests
python3 -m unittest discover -s tests -v

# Single test file
python3 -m unittest tests.test_memory_storage -v
```

### Module map

```
src/opencode_router/
├── cli.py           # CLI entry point (argparse)
├── route.py         # Two-stage routing: embed → cosine → LLM rerank
├── orchestrate.py   # Multi-step DAG planning + AgentSkillOS
├── index.py         # Agent embedding index (build/search)
├── agents.py        # Parse agent .md frontmatter
├── opencode.py      # Patch opencode.json (register agents, apply models)
├── profile.py       # Provider profile management
├── rules.py         # Role-pattern → bucket assignments
├── ollama.py        # Stdlib-only Ollama HTTP client
├── paths.py         # Configurable filesystem paths
├── memory/
│   ├── __init__.py   # Public API: inject, rebuild, clear, record
│   ├── storage.py    # .opencode-router/ layout
│   ├── walk.py       # File listing (git ls-files or os.walk)
│   ├── anatomy.py    # File tree + symbol detection (7 languages)
│   ├── conventions.py# Manifest parsing (8 types)
│   ├── trigger.py    # Rebuild decision logic
│   ├── episodic.py   # Log distillation via LLM
│   ├── log.py        # Dispatch log (YAML read/write)
│   └── retrieval.py  # Chunk + embed + cosine search (large projects)
└── tests/
```

### Code conventions

- **No dependencies.** Stdlib-only except for `ollama` (our own HTTP client).
- **Python 3.10+** with `from __future__ import annotations`.
- **dataclass(frozen=True)** for all data types.
- **Ruff** for linting (I001, E, F, B, UP rules). Line length 100.
- **unittest** (not pytest) for tests. `tempfile.TemporaryDirectory` for isolation.
- **Public API only.** All memory modules export through `memory/__init__.py`.

### Before committing

```bash
python3 -m ruff check src/ tests/     # must pass
python3 -m unittest discover -s tests  # must pass
```

CI runs on macOS + Ubuntu × Python 3.10, 3.11, 3.12.
