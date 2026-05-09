# FAQ

### The router agent calls `route-agent` as a tool and fails

The router prompt is explicit that `opencode-router` is a SHELL command
invoked via the `bash` tool, not an opencode tool. If you see
"Model tried to call unavailable tool", check that
`~/.config/opencode/agents/router.md` matches the version in
`examples/router-prompts/default.md` — older custom prompts may use
the wrong terminology.

### The router invents a constraint like "do not save to a file"

The default router prompt tells the router NEVER to fabricate
constraints, but smaller rerank models occasionally still do. If a
deliverable artifact didn't get saved, ask the user to check the
specialist agent's output policy and consider switching the router's
model to a stronger one (the router agent's `model` is set by the
`flash` bucket — bump that bucket to a smarter model).

### Routing accuracy looks bad

Run `opencode-router route --top 5 "<query>"` to see what the router
saw. Common causes:

1. **Index is stale.** Rebuild it: `opencode-router index build`.
2. **Catalog is too narrow.** No suitable agent exists — the router
   picks the closest, which may be wrong.
3. **Descriptions are weak.** Read [docs/creating-agents.md](creating-agents.md)
   on writing task-shaped descriptions.
4. **Rules are wrong.** A specific role isn't matched, so it falls
   into a generic bucket. Add a rule.

### `Model not found: <provider>/<model>`

OpenCode can't resolve the model in the active profile. Either:

- The provider isn't configured in your `opencode.json` (or its
  auth/keys are missing).
- The model path is wrong.

Run `opencode models <provider>` to see what's available, then either
fix the provider config or edit your profile to use a model that exists.

### `bad file reference: {file:~/.config/opencode/agents/X.md}`

OpenCode's `agent` block points to a file that no longer exists. Run
`opencode-router register` to rebuild the block from your current
`agents/` directory state.

### How do I add an agent without re-running everything?

```bash
# 1. Drop the .md file in
cp my-new-agent.md ~/.config/opencode/agents/

# 2. Re-register + re-index (skips models if you don't run apply)
opencode-router register
opencode-router index build
```

If you want the new agent to also have the right model assignment, add
`opencode-router models apply` between those two.

### What's the cost?

Routing is local-only via Ollama:

- Embedding (per query): ~50 ms, ~0 cost.
- LLM rerank (per query): ~2 s on `qwen3.5:4b`, ~0 cost (electricity).
- Index build (per agent): ~50 ms, one-time.

The actual *work* — the dispatched specialist agent's tokens — uses
whatever provider is mapped to that agent's bucket via your active
profile. That's the only outbound API cost.

### Can I disable the rerank stage?

Yes:

```bash
opencode-router route --no-rerank "<query>"
```

Embedding-only routing is faster (~50 ms total) but less accurate.
Useful for quick exploration; not recommended for the production
router agent.

### Why not just one giant LLM call with all 200 agents in the prompt?

That's how OpenCode's built-in primary agent does it. It works, but:

1. The prompt is enormous (50K+ tokens at 200 agents).
2. Accuracy degrades — agent descriptions blur together at scale.
3. Cost scales linearly with catalog size.

The two-stage retrieval keeps the LLM's view to 10 candidates
regardless of catalog size. Constant cost, higher accuracy.

### Does this work outside OpenCode?

The CLI parts (`route`, `index build`, `profile`, `rules`) work
anywhere — they're pure Python + Ollama.

The OpenCode-specific parts are:

- The router agent prompt — references `opencode-router` and the
  `task` tool by name.
- `opencode-router register` — patches `opencode.json` specifically.

For Claude Code or another agentic system, you'd write a different
"router agent" prompt that uses that system's dispatch mechanism, and
skip the `register` step. See [architecture.md](architecture.md).

### Can I contribute?

Yes — see [CONTRIBUTING.md](../CONTRIBUTING.md).
