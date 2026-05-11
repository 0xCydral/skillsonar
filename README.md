# opencode-router

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/AdrianCsT/opencode-router/actions/workflows/test.yml/badge.svg)](https://github.com/AdrianCsT/opencode-router/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Version](https://img.shields.io/badge/version-0.3.3-blue)](https://github.com/AdrianCsT/opencode-router/releases)

> Open `opencode`, type a task, and the router dispatches it to the right
> specialist from a catalog of 233 agents. Two-stage semantic routing
> (embeddings + LLM rerank). Multi-step DAG orchestration with 105K skills.
> Project memory so agents skip exploration. **Local-first, zero config.**

---

## For your agent

Paste this block into Claude Code, OpenCode, or any LLM agent. Let the
agent do it — humans fat-finger configs.

```
Install and configure opencode-router by reading the setup guide at
https://raw.githubusercontent.com/AdrianCsT/opencode-router/main/AGENTS.md

Then verify with:
  opencode-router doctor
  opencode-router memory rebuild --force
```

**Agents reading this directly:** fetch the full setup guide.

```bash
curl -s https://raw.githubusercontent.com/AdrianCsT/opencode-router/main/AGENTS.md
```

[AGENTS.md](AGENTS.md) covers the full dev environment: Python, Ollama,
OpenCode, Claude Code, Hermes, agent import, provider profiles, project
memory, and AgentSkillOS.

---

## What it does

```
> fix N+1 queries in Django ORM
  → routes to database-optimizer → done

> build a Kubernetes CI/CD pipeline with security scanning
  → orchestrates a 5-step DAG across devops-automator, security-reviewer,
    technical-writer → done
```

No `/agent` switching. No memorising agent names. The router picks the
right specialist, injects project context so the agent already knows the
codebase, and records the dispatch so future runs learn from past work.

## Quick install

If you're setting up by hand instead of using an agent. macOS, Linux, and
Windows are all supported.

```bash
# Prerequisites (pick your platform)
brew install python@3.12 ollama                         # macOS
sudo apt install -y python3.12 python3-pip && curl -fsSL https://ollama.com/install.sh | sh  # Linux
winget install Python.Python.3.12 Ollama.Ollama          # Windows

# Start Ollama + pull models
ollama serve &>/dev/null &
ollama pull mxbai-embed-large qwen3.5:4b

# Install opencode-router
git clone https://github.com/AdrianCsT/opencode-router.git ~/opencode-router
cd ~/opencode-router && python3 -m pip install -e ".[dev]"
bash scripts/import-agents.sh
cp examples/router-prompts/default.md ~/.config/opencode/agents/router.md
opencode-router init
```

**Prerequisites:** OpenCode ≥ 1.14.20, Python ≥ 3.10, Ollama running.

[Full installation guide →](docs/installation.md) ·
[Configuration reference →](docs/configuration.md)

## How it works

```
You type a task in OpenCode
  │
  ▼
Router agent picks the right path
  │
  ├── Simple task → route --top-1 --json --with-memory
  │     ├── Embed task (mxbai-embed-large, Ollama, ~50ms)
  │     ├── Cosine top-10 over 233 agents (~10ms)
  │     ├── LLM rerank (qwen3.5:4b, ~2s, role rules)
  │     └── Returns {agent, memory_brief}
  │
  └── Complex task → orchestrate
        ├── Skill discovery (AgentSkillOS tree + 105K token index)
        ├── Agent routing per step
        ├── DAG planning (LLM decomposes into ordered steps)
        └── Returns [{step, agent, depends_on}]
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
| **Two-stage routing** | Embedding retrieval + LLM rerank. Neither stage alone is accurate enough. |
| **Local-first** | Routing runs on Ollama. No network call for dispatch. |
| **Project memory** | Agents receive file tree, symbols, conventions — skip exploration on every dispatch. |
| **Episodic distillation** | Dispatch logs are LLM-distilled into reusable patterns for future agents. |
| **Retrieval injection** | Large projects get header + top-5 relevant chunks via cosine search. ~89% token savings. |
| **Provider profiles** | Switch all 233 agents between providers in one command. |
| **Multi-step orchestration** | DAG planning with dependency ordering, 105K skill catalog. |
| **Bring your own agents** | Zero bundled. Write `.md` files or import from open-source collections. |
| **No lock-in** | Remove the router from `default_agent` to disable. Everything in opencode.json. |

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

## Provider profiles

```bash
opencode-router profile list          # ollama-local, ollama-cloud, nvidia-nim, deepseek-official
opencode-router profile set <name>    # switch all 233 agents + re-apply models
opencode-router profile current       # show active
```

Add your own at `~/.config/opencode/orchestration-profile.json`.
[Profile docs →](docs/profiles.md)

## Project memory

```bash
opencode-router memory rebuild --force   # build now
opencode-router memory inject "fix bug"  # debug: what gets injected
opencode-router memory log --tail 10     # dispatch history
opencode-router memory clear             # start fresh
```

Memory auto-rebuilds when ≥10 files change, git HEAD moves, or 24h elapse.

## Configuration

| File | Purpose |
|---|---|
| `~/.config/opencode/opencode.json` | Agent registry + model assignments |
| `~/.config/opencode/agents/router.md` | Router primary agent prompt |
| `~/.config/opencode/agents/*.md` | Specialist subagents (BYO) |
| `~/.config/opencode/agent-index.json` | Pre-computed embeddings |
| `~/.config/opencode/orchestration-profile.json` | Provider profiles |
| `~/.config/opencode/orchestration-rules.json` | Role-pattern → bucket rules |
| `<project>/.opencode-router/memory.md` | Project memory (auto-generated) |

[Routing rules →](docs/routing-rules.md) ·
[Creating agents →](docs/creating-agents.md) ·
[FAQ →](docs/faq.md)

## Design

- **Bring your own agents.** Zero bundled. Write or import.
- **Bring your own provider.** Six buckets map to real model paths.
- **Bring your own rules.** Role-pattern → bucket assignments are user-editable.
- **Local-first.** Routing runs on Ollama. No network call for dispatch.
- **No lock-in.** Remove the router to disable. No migration needed.

## License

[MIT](LICENSE)
