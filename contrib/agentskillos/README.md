# AgentSkillOS Router Engine

An [AgentSkillOS](https://github.com/ynulihao/AgentSkillOS) orchestrator
engine that replaces generic skill execution with
[opencode-router](https://github.com/AdrianCsT/opencode-router)'s
specialist agent dispatch.

## How it works

```
AgentSkillOS DAG pipeline
    │
    ▼
Task: "Generate a bug diagnosis report for this React app"
    │
    ▼
Router engine:
    ├── opencode-router route --top-1 "generate bug diagnosis report"
    │   → "qa-automation"
    ├── Load: ~/.config/opencode/agents/qa-automation.md
    │   → specialist prompt injected into the task
    └── Execute via Claude SDK with agent's domain expertise
    │
    ▼
Output: report saved, summary returned to DAG
```

For every node in a multi-step DAG workflow, the router picks the best
specialist agent from your catalog and injects its expertise before
execution.

## Install

```bash
cd opencode-router
bash contrib/agentskillos/install.sh                 # auto-detect AgentSkillOS
bash contrib/agentskillos/install.sh ~/AgentSkillOS   # or specify path
```

Restart AgentSkillOS. "Router (Agent Dispatch)" appears in the engine
selector.

## Prerequisites

- [AgentSkillOS](https://github.com/ynulihao/AgentSkillOS) installed
- [opencode-router](https://github.com/AdrianCsT/opencode-router) installed
- `~/.config/opencode/agents/` populated with specialist agents
- `opencode-router index build` run (embedding index built)

## How to use

1. Start AgentSkillOS: `agent-skillos webui`
2. Select **Router (Agent Dispatch)** as the execution engine
3. Enter your task — no need to pick skills manually
4. The router picks the right agent for each step
5. Results land in the project workspace

## Architecture

```
contrib/agentskillos/
├── router_engine/
│   └── engine.py      # @register_engine("router") class
├── install.sh          # symlink installer
└── README.md           # this file
```

The engine follows AgentSkillOS's `ExecutionEngine` protocol. It
inherits the DAG planning from AgentSkillOS's dag engine — this
engine replaces only the *execution* phase.

## Uninstall

```bash
rm ~/AgentSkillOS/src/orchestrator/router_engine
```
