# Architecture

`opencode-router` is a local-first orchestration layer that combines
**skill discovery** (105K+ catalog + AgentSkillOS tree), **agent
routing** (two-stage semantic dispatch), and **DAG planning** into a
single pipeline triggered from within OpenCode.

## Full pipeline

```mermaid
flowchart TB
    subgraph User["User"]
        TASK["Type any task into OpenCode<br/>'build a Kubernetes CI/CD pipeline<br/>with security scanning'"]
    end

    subgraph Router["Router Agent (OpenCode primary)"]
        DETECT{"Single-step<br/>or multi-step?"}
        ROUTE["opencode-router route --top-1"]
        ORCH["opencode-router orchestrate"]
    end

    subgraph SkillLayer["Skill Discovery (105K catalog)"]
        TREESEARCH["AgentSkillOS tree search<br/>118 curated seeds<br/>LLM-guided capability tree"]
        IDXSEARCH["Tokenized index search<br/>105K imported skills<br/>44 MB pre-built index"]
        SKILLS["Matched skills<br/>cicd-workflow, minikube-deploy,<br/>gitlab-ci, ssdt-best-practices"]
    end

    subgraph AgentLayer["Agent Routing (233 specialists)"]
        EMBED["Embed task<br/>mxbai-embed-large<br/>Ollama, ~50ms"]
        COSINE["Cosine top-10<br/>over agent index<br/>~10ms"]
        RERANK["LLM rerank top-10<br/>qwen3.5:4b, ~2s<br/>strict role rules"]
        AGENTS["Best agent per step<br/>devops-automator,<br/>security-reviewer,<br/>technical-writer"]
    end

    subgraph Plan["DAG Planning"]
        PLANNER["LLM decomposes task<br/>into ordered steps<br/>with dependencies"]
        DAG["Execution plan"]
    end

    subgraph Execute["OpenCode Task Tool"]
        STEP1["Step 1: devops-automator<br/>Provision cluster"]
        STEP2["Step 2: security-reviewer<br/>Audit pipeline<br/>waits for step 1"]
        STEP3["Step 3: technical-writer<br/>Write runbook<br/>waits for step 2"]
    end

    subgraph Output["Result"]
        FILES["Multiple focused files<br/>saved to project<br/>3-line summary"]
    end

    TASK --> DETECT
    DETECT -->|simple task| ROUTE
    DETECT -->|complex task| ORCH
    ROUTE --> EMBED
    ORCH --> TREESEARCH
    ORCH --> IDXSEARCH
    TREESEARCH --> SKILLS
    IDXSEARCH --> SKILLS
    SKILLS --> EMBED
    EMBED --> COSINE
    COSINE --> RERANK
    RERANK --> AGENTS
    AGENTS --> PLANNER
    PLANNER --> DAG
    DAG --> STEP1
    STEP1 --> STEP2
    STEP2 --> STEP3
    STEP3 --> FILES
```

## Three layers

### 1. Skill discovery (105K+ catalog)

Before routing to agents, the pipeline searches the skill catalog to
find relevant capabilities. Two search strategies run in parallel:

- **AgentSkillOS tree search** — LLM-guided traversal of a pre-built
  capability tree over 118 curated seed skills. Finds skills by
  navigating a hierarchy rather than keyword matching.
- **Tokenized index search** — tokenized pre-built index over 105K
  imported skills (44 MB JSON, cached in memory after first load).
  Matches skill names and descriptions against task query tokens.

Combined results feed into agent routing to expand the candidate pool.

### 2. Agent routing (233 specialists)

A two-stage pipeline that picks the right specialist for each step:

1. **Embed** the task with `mxbai-embed-large` (Ollama, ~50ms).
2. **Cosine search** over the pre-built 1024-dim agent index (~10ms).
3. **LLM rerank** — top-10 candidates go to `qwen3.5:4b` which applies
   explicit role+domain rules and strict JSON output (~2s).

This avoids both embedding-only surface-word traps (e.g. `users.email`
matching `email-intelligence-engineer` instead of `database-optimizer`)
and the cost of putting 200+ agent descriptions in one prompt.

### 3. DAG planning

For complex tasks, an LLM decomposes the work into ordered steps with
dependencies. Each step is assigned to the best agent from the routing
stage. The result is a directed acyclic graph: "step-1 → step-2 (waits
for step-1), step-3 (waits for step-2)".

## What's deliberate, what's swappable

**Deliberate:**
- Two-stage retrieval (embed → rerank) — neither stage alone reaches
  required accuracy.
- The bucket abstraction (`pro`, `flash`, `coding`, `visual`, `chinese`,
  `translation`) separates role logic from provider details.
- Index excludes `mode: primary` agents (otherwise the router
  recommends itself).

**Swappable:**
- Embedding / rerank models — set `OPENCODE_ROUTER_EMBED_MODEL` and
  `OPENCODE_ROUTER_RERANK_MODEL`.
- Ollama URL — set `OPENCODE_ROUTER_OLLAMA_URL`.
- Routing rules — write `~/.config/opencode/orchestration-rules.json`.
- Provider profiles — edit `~/.config/opencode/orchestration-profile.json`.
- Router prompt — copy `examples/router-prompts/default.md`, edit, drop in.
- Skill catalog — run `scripts/import-skills.py` to refresh.
