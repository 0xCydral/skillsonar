# opencode-router

Local-first agent routing for [OpenCode](https://opencode.ai). Two-stage
semantic dispatch (embeddings + LLM rerank) that picks the right
specialist agent for any task — without locking you into a specific
model provider, agent catalog, or routing taxonomy.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/AdrianCsT/opencode-router/actions/workflows/test.yml/badge.svg)](https://github.com/AdrianCsT/opencode-router/actions/workflows/test.yml)

## What problem does this solve?

OpenCode lets you register hundreds of file-based subagents, but its
built-in primary agent has to read every agent's description in one
prompt to choose between them. With a 200+ agent catalog, that's slow,
expensive, and inaccurate.

This package adds a **`router` primary agent** that:

1. Embeds your task with a local embedding model.
2. Retrieves the top-N candidate agents by cosine similarity.
3. Reranks the shortlist with a small local LLM, applying explicit
   role+domain rules.
4. Dispatches to the chosen agent via OpenCode's `Task` tool.

The router never reads the full catalog into context. The user just
opens OpenCode and types — the right specialist is selected
automatically.

## Design principles

- **Bring your own agents.** Nothing is bundled. You write your agent
  `.md` files (or import them from any agent collection) and point this
  tool at the directory.
- **Bring your own provider.** Models are organised into six abstract
  buckets (`pro`, `flash`, `coding`, `visual`, `chinese`, `translation`).
  Profiles map buckets to concrete model paths. Switch providers in one
  command when a plan runs out.
- **Bring your own rules.** Role-pattern → bucket mapping is a
  user-editable file. Default rules cover obvious patterns
  (`reviewer → flash`, `designer → visual`); add your own.
- **Local-first.** The retrieval stage runs entirely on Ollama. No
  network call needed for routing decisions.
- **No lock-in.** Pure Python stdlib + your existing OpenCode install.
  Disable any time by removing the router from your default agent.

## Install

### Prerequisites

- [OpenCode](https://opencode.ai) ≥ 1.14.20
- Python ≥ 3.10
- [Ollama](https://ollama.com) (running locally — used for the
  retrieval and rerank models)
- `~/.local/bin` on `PATH`

### From source

```bash
git clone https://github.com/AdrianCsT/opencode-router.git
cd opencode-router
./install.sh
```

`install.sh` will:
1. Install the package with `pip install --user -e .`
2. Pull the default Ollama models (`mxbai-embed-large` and `qwen3.5:4b` —
   ~4 GB total, override with env vars; see [docs/configuration.md](docs/configuration.md))
3. Seed `~/.config/opencode/orchestration-profile.json` from
   `examples/profiles/starter-profile.json`
4. Print next steps

### Pip

```bash
pip install --user opencode-router    # once published
```

(Not yet on PyPI — install from source for now.)

## Quick start

```bash
# 1. Make sure your agent directory has at least one .md file
#    (see examples/agents/ for the format — write your own or import a collection)
ls ~/.config/opencode/agents/

# 2. Copy the router prompt into your agents directory
cp examples/router-prompts/default.md ~/.config/opencode/agents/router.md

# 3. Initialise — registers all agents + builds the embedding index
opencode-router init

# 4. Open OpenCode (default_agent is now `router`)
opencode
> fix N+1 queries in apps/orders/views.py
# router auto-dispatches to whichever specialist your catalog has
```

Test routing without launching OpenCode:

```bash
opencode-router route "review TypeScript code for type safety bugs"
# → top match printed with score + alternatives
```

### Zero-config first run

The `starter-profile.json` ships with an active `ollama-local` profile
that uses `qwen3.5:4b` (the rerank model — already pulled by
`install.sh`) for every bucket. That gives you a working setup with
zero provider sign-ups, zero API keys.

It's a baseline, not a recommendation: a 4B local model handles
routing decisions fine but is undersized for serious coding,
long-form writing, or vision work. Swap to a real provider profile
(`ollama-cloud`, `nvidia-nim`, `deepseek-official`) or a multi-model
local setup (`ollama-local-multi`) once you decide what you want.

### Getting a starter agent catalog

The repo ships two example agents in `examples/agents/`. For a full
catalog (200+ specialists across engineering, design, content, security,
etc.), import from open-source collections:

```bash
# Import 180+ agents from agency-agents + ~50 from ECC
bash scripts/import-agents.sh

# Or pick one:
bash scripts/import-agents.sh agency    # agency-agents only
bash scripts/import-agents.sh --dry-run # preview before copying

# Then register everything:
opencode-router init
```

These collections are MIT-licensed and maintained independently. Write
your own agents by following the format in
[docs/creating-agents.md](docs/creating-agents.md).

## CLI

```text
opencode-router init                         One-shot: register agents + apply
                                             models + build index
opencode-router register                     Populate opencode.json `agent` block
                                             from your agents/ directory
opencode-router models apply [--profile X]   Apply role-pattern → bucket → model
                                             assignments
opencode-router profile list                 Show available provider profiles
opencode-router profile current              Show active profile + bucket map
opencode-router profile show <name>          Show one profile's bucket map
opencode-router profile set <name>           Switch active profile + reapply
opencode-router index build                  Re-embed all agents
opencode-router route "<query>"              Test the router (returns top-N)
opencode-router orchestrate "<task>"         Plan a multi-step DAG (skills + agents)
opencode-router doctor                       Diagnose configuration issues
```

## Configuration

| File | Purpose |
|---|---|
| `~/.config/opencode/orchestration-profile.json` | Provider profiles + active profile selection |
| `~/.config/opencode/orchestration-rules.json` | Role-pattern → bucket rules (optional override; defaults built in) |
| `~/.config/opencode/agent-index.json` | Pre-computed embeddings (auto-generated by `index build`) |
| `~/.config/opencode/agents/router.md` | The router agent prompt |
| `~/.config/opencode/agents/*.md` | Your specialist agents (BYO) |

See [docs/configuration.md](docs/configuration.md) for the full schema.

## Architecture

```
User opens OpenCode → types any task
    │
    ▼
Router agent detects: single-step or multi-step?
    │
    ├── Simple: opencode-router route --top-1 "task"
    │       │
    │       ├── Embed task (mxbai-embed-large, ~50ms)
    │       ├── Cosine top-10 over 233 agents (~10ms)
    │       ├── LLM rerank (qwen3.5:4b, ~2s, role rules)
    │       └── Returns: best agent name
    │
    └── Complex: opencode-router orchestrate "task"
            │
            ├── Skill discovery: 118 tree seeds + 105K token index
            ├── Agent routing: embed → cosine → rerank (per step)
            ├── DAG planning: LLM decomposes into ordered steps
            └── Returns: plan [{step, agent, depends_on}]
    │
    ▼
Router: task(subagent_type=<name>, description=<full request>)
    │  (one per step, chained by dependencies)
    ▼
Specialist agents do the work (each on their assigned model)
    ▼
Result → multiple focused files saved to project + 3-line summary
```

[Full diagram and deep dive → docs/architecture.md](docs/architecture.md)

## Buckets

The role → model assignment uses six abstract buckets:

| Bucket | Typical roles |
|---|---|
| `pro` | Heavy reasoning, writing, strategy, security audit, default |
| `flash` | Code review, debugging, customer support, the router itself |
| `coding` | Architects, engineers, developers, scripters |
| `visual` | UI/UX, design, brand, level designers, image work |
| `chinese` | Chinese consumer-platform agents (Douyin, Bilibili, Weibo, …) |
| `translation` | Translation, localization, cultural-cross |

You can extend or rename these in your profile file. See
[docs/profiles.md](docs/profiles.md).

## Provider profiles

Switch providers in one command when a plan runs out:

```bash
opencode-router profile set ollama-cloud      # all six buckets on Ollama Cloud
opencode-router profile set nvidia-nim        # NVIDIA NIM
opencode-router profile set deepseek-official # official DeepSeek API
```

The repo ships starter profiles in `examples/profiles/`. You define your
own at `~/.config/opencode/orchestration-profile.json`.

### Model recommendations per bucket

This is a non-prescriptive starting point — pick what you have access
to. See [docs/profiles.md](docs/profiles.md) for the full discussion.

| Bucket | Tier 1 (best quality) | Tier 2 (cost-effective) | Tier 3 (fully local) |
|---|---|---|---|
| `pro` | Claude Opus, GPT-4 Turbo, DeepSeek V4 Pro | DeepSeek V4 Pro, Qwen3.5-235B | Qwen3.5:9b, Llama-3.3-70b |
| `flash` | Claude Haiku, GPT-4o-mini | DeepSeek V4 Flash | Qwen3.5:4b |
| `coding` | Claude Sonnet, Kimi for Coding | Qwen3-Coder, Codestral | Qwen3-Coder:14b |
| `visual` | GPT-4o (vision), Claude Opus | Mimo Pro, Qwen3-VL-235B | Qwen3-VL:7b |
| `chinese` | GLM-5.1, Qwen3.5 | GLM-4.7 | Qwen3.5:9b |
| `translation` | Claude Sonnet, GPT-4 | Qwen3.5, Aya | Qwen3.5:9b |

## Bring your own agents

This repo ships **zero agents** by design. You can:

- Hand-write `.md` files (the format is just YAML frontmatter +
  markdown body — see [docs/creating-agents.md](docs/creating-agents.md))
- Use any open-source agent collection (e.g.
  [agency-agents](https://github.com/msitarzewski/agency-agents),
  [ECC](https://github.com/everything-claude-code))
- Convert from Claude Code subagent format

After adding agents:

```bash
opencode-router init        # register + build index
```

## Documentation

- [Architecture](docs/architecture.md) — How the two-stage routing works
- [Installation](docs/installation.md) — Detailed install + prerequisites
- [Configuration](docs/configuration.md) — All config files and schemas
- [Creating agents](docs/creating-agents.md) — Agent file format
- [Profiles](docs/profiles.md) — Provider profile schema
- [Routing rules](docs/routing-rules.md) — Customising role → bucket rules
- [FAQ](docs/faq.md) — Common questions and gotchas

## Contributing

Pull requests welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
