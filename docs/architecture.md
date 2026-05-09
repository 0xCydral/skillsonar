# Architecture

`opencode-router` is a thin orchestration layer over OpenCode's existing
agent + Task tool primitives. Nothing about it is magic — it's three
pieces wired together.

## Three pieces

### 1. The router agent (a primary agent)

A normal OpenCode agent in `mode: primary`, dropped into your agents
directory as `router.md`. Its system prompt instructs it to:

1. Identify whether the user's request needs routing (real work) or can
   be handled inline (small talk).
2. Frame the task as one short sentence.
3. Run `bash: opencode-router route --top-1 "<task>"` to get the best
   specialist agent name.
4. Dispatch to that agent via OpenCode's `task` tool.
5. Relay the result back to the user with no editorialising.

The router never reads the agent catalog into its own context.

### 2. The CLI

`opencode-router` — a single Python entry point that wraps:

- **`init`** — register all `.md` files in your agents directory into
  `opencode.json`, apply model assignments per profile, build the
  embedding index. Idempotent.
- **`route <query>`** — embed the query, retrieve top-N from the index,
  rerank with a small LLM, return the top match.
- **`profile {list|current|show|set}`** — manage provider profiles.
- **`models apply`** — re-run model assignments for the current profile.
- **`index build`** — rebuild the embedding index.
- **`doctor`** — diagnose configuration issues.

### 3. The two-stage retrieval pipeline

```
user task
   │
   ▼
embed via mxbai-embed-large (Ollama)        ~50 ms
   │
   ▼
cosine top-10 over agent index               ~10 ms
   │
   ▼
rerank top-10 with qwen3.5:4b (Ollama)      ~2 s
   │  ── strict JSON output
   │  ── role+domain rules in the prompt
   ▼
chosen agent name
```

The embedding stage gets us into the right neighbourhood cheaply. The
LLM rerank stage applies semantic understanding (output-type matching,
domain rules, surface-keyword rejection) over a manageable shortlist.
Validated 8/8 on a diverse battery of tasks ranging from Django ORM bug
fixes to LinkedIn post writing.

Both stages run on Ollama. No network call leaves your machine for a
routing decision.

## Why two stages, not one

**Embeddings alone** mis-route on surface keywords. Example: a SQL
migration on a `users.email` column embeds close to an
"email-intelligence" agent. The cosine score wins; the routing fails.

**LLM-only** (as in OpenCode's built-in primary agent over a 200-agent
catalog) needs every agent description in one prompt. Long, expensive,
and accuracy degrades as agents blur together.

**Hybrid:** embeddings narrow to 10 candidates, the LLM picks among
them with full descriptions visible and explicit role rules in the
prompt. Best of both.

## What's deliberate, what's swappable

**Deliberate (don't change unless you know why):**
- `router.md` is the sole entry point — there's only ever one router.
- The bucket abstraction (`pro`, `flash`, `coding`, `visual`, `chinese`,
  `translation`) — used by both rules and profiles.
- Two-stage retrieval (embed → rerank) — neither stage alone reaches
  required accuracy.
- Index excludes `mode: primary` agents (otherwise the router could
  recommend itself).

**Swappable:**
- Embedding model — set `OPENCODE_ROUTER_EMBED_MODEL`.
- Rerank model — set `OPENCODE_ROUTER_RERANK_MODEL`.
- Ollama URL — set `OPENCODE_ROUTER_OLLAMA_URL`.
- Routing rules — write your own at
  `~/.config/opencode/orchestration-rules.json`.
- Provider profiles — edit
  `~/.config/opencode/orchestration-profile.json`.
- Bucket names — write your own profile and matching rules.
- Router prompt — copy `examples/router-prompts/default.md`, edit, drop
  into your agents dir.

## What about Claude Code, not OpenCode?

Claude Code uses the same primary/subagent + Task tool pattern. The
mechanics carry over: a router subagent + a `route-agent`-style CLI
called via `Bash`. The opencode.json patcher in this package
specifically targets OpenCode's config schema; for Claude Code the
agent registration step looks different (subagent files alone, no
config block to patch). PRs welcome.
