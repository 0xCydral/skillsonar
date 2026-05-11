# opencode-router

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/AdrianCsT/opencode-router/actions/workflows/test.yml/badge.svg)](https://github.com/AdrianCsT/opencode-router/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Version](https://img.shields.io/badge/version-0.3.3-blue)](https://github.com/AdrianCsT/opencode-router/releases)

> Open `opencode`, type a task, the router dispatches it to the right
> specialist. 233 agents. Two-stage semantic routing. Local-first.
> Multi-step DAG orchestration. 105K curated skills.

## What it does

```
> fix N+1 queries in Django ORM
  → routes to database-optimizer → done

> build a Kubernetes CI/CD pipeline with security scanning
  → orchestrates a 5-step DAG across devops-automator, security-reviewer,
    technical-writer → done
```

No `/agent` switching. No memorising 233 agent names. No wondering which
specialist fits. The router picks the right agent, injects project memory
so the agent already knows the codebase, and records the dispatch so
future runs learn from past work.

## Setup (paste this into your agent)

```bash
# 1. Prerequisites — one-time
brew install python@3.12 ollama          # macOS
ollama pull mxbai-embed-large            # embeddings, ~670 MB
ollama pull qwen3.5:4b                   # LLM rerank, ~2.4 GB

# 2. opencode-router
git clone https://github.com/AdrianCsT/opencode-router.git ~/opencode-router
cd ~/opencode-router
python3 -m pip install -e ".[dev]"

# 3. Agents + router prompt
bash scripts/import-agents.sh
cp examples/router-prompts/default.md ~/.config/opencode/agents/router.md
opencode-router init

# 4. Verify
opencode-router doctor
opencode-router memory rebuild --force
```

**Prerequisites:** OpenCode ≥ 1.14.20, Python ≥ 3.10, Ollama running
locally, `~/.local/bin` on `PATH`. [Full install guide →](docs/installation.md)

After setup, open `opencode` and type a task. The router handles everything.

### Switching providers

```bash
opencode-router profile list          # see available
opencode-router profile set <name>    # switch all 233 agents to a new provider
```

Shipped: `ollama-local`, `ollama-cloud`, `nvidia-nim`, `deepseek-official`.
Add your own at `~/.config/opencode/orchestration-profile.json`.

### Project memory

Every project gets context auto-injected on dispatch:

```bash
opencode-router memory rebuild --force   # build now
opencode-router memory log --tail 10     # dispatch history
opencode-router memory inject "fix bug"  # debug: what gets injected
```

Memory is rebuilt when files change (≥10), git HEAD moves, or 24h elapse.
[Full memory docs →](#docs)

## How it works

```
You type a task in OpenCode
  │
  ▼
Router agent picks the right path
  │
  ├── Simple task → opencode-router route --top-1 --json --with-memory
  │     ├── Embed task (mxbai-embed-large, Ollama, ~50ms)
  │     ├── Cosine top-10 over 233 agents (~10ms)
  │     ├── LLM rerank top-10 (qwen3.5:4b, ~2s, role rules)
  │     └── Returns: {agent, memory_brief}
  │
  └── Complex task → opencode-router orchestrate
        ├── Skill discovery (AgentSkillOS tree + 105K token index)
        ├── Agent routing per step
        ├── DAG planning (LLM decomposes into ordered steps)
        └── Returns: [{step, agent, depends_on}]
  │
  ▼
Router dispatches via OpenCode task tool (one per step)
  │
  ▼
Agent receives project memory + task → skips exploration → delivers
  │
  ▼
Dispatch recorded → future runs learn from past patterns
```

[Architecture diagram →](docs/architecture.md)

## Highlights

| | |
|---|---|
| **Two-stage routing** | Embedding retrieval + LLM rerank. Neither stage alone reaches required accuracy. |
| **Local-first** | Routing runs on Ollama. No network call for dispatch decisions. |
| **Bring your own agents** | Zero bundled. Write `.md` files or import from open-source collections. |
| **Bring your own provider** | Six abstract buckets map to real model paths. Switch in one command. |
| **Project memory** | Agents receive file tree, symbols, conventions, and distilled patterns — skip exploration. |
| **Multi-step orchestration** | DAG planning with dependency ordering. Skill catalog of 105K patterns. |
| **Episodic distillation** | Dispatch logs are LLM-distilled into reusable patterns for future agents. |
| **Retrieval injection** | Large projects get header + top-5 relevant chunks via cosine search. |
| **Provider profiles** | Switch all 233 agents to a new provider in one command. |
| **No lock-in** | Remove the router from `default_agent` to disable. Everything lives in opencode.json. |

## CLI

```text
opencode-router init                 One-shot: register + apply models + build index
opencode-router route "<query>"      Find the best agent (--top-1, --json, --with-memory)
opencode-router orchestrate "<t>"    Plan a multi-step DAG
opencode-router profile {list,set,current,show}    Manage providers
opencode-router models apply         Re-apply role → bucket → model assignments
opencode-router index build          Re-embed all agents
opencode-router doctor               Diagnose configuration
opencode-router memory {show,rebuild,clear,inject,log,record}   Project memory
```

## Configuration

| File | Purpose |
|---|---|
| `~/.config/opencode/opencode.json` | Agent registry + model assignments (managed by init) |
| `~/.config/opencode/agents/router.md` | Router primary agent prompt |
| `~/.config/opencode/agents/*.md` | Specialist subagents (BYO) |
| `~/.config/opencode/agent-index.json` | Pre-computed embeddings |
| `~/.config/opencode/orchestration-profile.json` | Provider profiles |
| `~/.config/opencode/orchestration-rules.json` | Role-pattern → bucket rules (optional) |
| `<project>/.opencode-router/memory.md` | Project memory (auto-generated) |

## Design

- **Bring your own agents.** Zero bundled. Write or import.
- **Bring your own provider.** Six buckets. Switch in one command.
- **Bring your own rules.** Role patterns → bucket assignments are user-editable.
- **Local-first.** Routing runs on Ollama. No network for dispatch.
- **No lock-in.** Remove the router to disable. No migration needed.

## Docs

[Installation](docs/installation.md) ·
[Architecture](docs/architecture.md) ·
[Configuration](docs/configuration.md) ·
[Creating agents](docs/creating-agents.md) ·
[Provider profiles](docs/profiles.md) ·
[Routing rules](docs/routing-rules.md) ·
[FAQ](docs/faq.md) ·
[AGENTS.md](AGENTS.md) (dev environment for coding agents)

## License

[MIT](LICENSE)
