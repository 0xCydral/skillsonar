# opencode-router

Local-first agent routing for [OpenCode](https://opencode.ai). Two-stage
semantic dispatch (embeddings + LLM rerank) that picks the right
specialist agent for any task. Multi-step DAG orchestration that
decomposes complex work across agents with dependency ordering. 105K
curated skills for task enrichment.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/AdrianCsT/opencode-router/actions/workflows/test.yml/badge.svg)](https://github.com/AdrianCsT/opencode-router/actions/workflows/test.yml)

## What it does

Open `opencode`, type a task, and the **router agent** handles everything
else.

```
> fix N+1 queries in Django ORM
  → routes to database-optimizer → done

> build a Kubernetes CI/CD pipeline with security scanning
  → orchestrates a 5-step DAG across devops-automator, security-reviewer,
    technical-writer → each step runs on its assigned model → done
```

No `/agent` switching. No memorising 233 agent names. No wondering which
specialist fits.

## How it works

```
You type a task in OpenCode
  │
  ▼
Router agent (primary) — picks the right path
  │
  ├── Simple task → opencode-router route --top-1
  │     ├── Embed (mxbai-embed-large, Ollama, ~50ms)
  │     ├── Cosine top-10 over 233 agents
  │     ├── LLM rerank (qwen3.5:4b, ~2s, role rules)
  │     └── Returns: best agent name
  │
  └── Complex task → opencode-router orchestrate
        ├── Skill discovery: 118 tree seeds + 105K token index
        ├── Agent routing per step
        ├── DAG planning: LLM decomposes into ordered steps
        └── Returns: [{step, agent, depends_on}]
  │
  ▼
Router dispatches via OpenCode task tool (one per step)
  │
  ▼
Specialist agents do the work → files saved + summary relayed
```

[Full visual diagram → docs/architecture.md](docs/architecture.md)

## Install

```bash
git clone https://github.com/AdrianCsT/opencode-router.git
cd opencode-router
./install.sh
```

`install.sh` pulls Ollama models (~4 GB), installs the package, seeds
provider profiles, and prints next steps. Re-running is safe.

**Prerequisites:** OpenCode ≥ 1.14.20, Python ≥ 3.10, Ollama running
locally, `~/.local/bin` on `PATH`.

## Quick start

```bash
# 1. Get agents — write your own, import a collection, or use the helper
bash scripts/import-agents.sh       # 180+ from agency-agents
cp examples/agents/*.md ~/.config/opencode/agents/

# 2. Copy the router prompt
cp examples/router-prompts/default.md ~/.config/opencode/agents/router.md

# 3. Initialise — registers agents, applies models, builds index
opencode-router init

# 4. Open OpenCode and type a task
opencode
```

**Optional: skill catalog enrichment.** For richer multi-step planning,
set up AgentSkillOS and import the 105K skill catalog:

```bash
# Install AgentSkillOS
git clone https://github.com/ynulihao/AgentSkillOS ~/AgentSkillOS
cd ~/AgentSkillOS
cp .env.example .env   # edit with your API key (DeepSeek, Kimi, etc.)
pip install -e .

# Import the skill catalog
open-code-router doesn't bundle skills — clone the astra-skills dataset
and run the import pipeline (see docs/architecture.md).
```

## CLI

```text
opencode-router init              One-shot: register + apply models + build index
opencode-router register          Populate opencode.json agent block from agents/
opencode-router models apply      Apply role → bucket → model assignments
opencode-router route "<query>"   Find the best agent for a task (returns top-N)
opencode-router orchestrate "<t>" Plan a multi-step DAG with skill + agent routing
opencode-router profile list      Show available provider profiles
opencode-router profile set <n>   Switch providers + auto-reapply models
opencode-router index build       Re-embed all agents
opencode-router doctor            Diagnose configuration issues
```

## Configuration

| File | Purpose |
|---|---|
| `~/.config/opencode/orchestration-profile.json` | Provider profiles + active selection |
| `~/.config/opencode/orchestration-rules.json` | Role-pattern → bucket rules (optional) |
| `~/.config/opencode/agent-index.json` | Pre-computed embeddings |
| `~/.config/opencode/agents/router.md` | The router agent prompt |
| `~/.config/opencode/agents/*.md` | Your specialist agents (BYO) |

## Provider profiles

Switch all 233 agents to a new provider in one command:

```bash
opencode-router profile set ollama-cloud      # when other plans run out
opencode-router profile set nvidia-nim
opencode-router profile set deepseek-official
```

Shipped profiles: `ollama-local`, `ollama-local-multi`, `ollama-cloud`,
`nvidia-nim`, `deepseek-official`. Add your own at
`~/.config/opencode/orchestration-profile.json`.

## Design

- **Bring your own agents.** Zero bundled. Write `.md` files or import
  from open-source collections.
- **Bring your own provider.** Six abstract buckets map to real model
  paths. Switch in one command.
- **Bring your own rules.** Role patterns → bucket assignments are
  user-editable.
- **Local-first.** Routing runs on Ollama. No network call for dispatch
  decisions.
- **No lock-in.** Remove the router from `default_agent` to disable.

## Docs

[Architecture](docs/architecture.md) ·
[Installation](docs/installation.md) ·
[Configuration](docs/configuration.md) ·
[Creating agents](docs/creating-agents.md) ·
[Provider profiles](docs/profiles.md) ·
[Routing rules](docs/routing-rules.md) ·
[FAQ](docs/faq.md)

## License

[MIT](LICENSE)
