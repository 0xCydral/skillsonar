# Example agents

These are minimal example agent definitions to help you get started.
The repo deliberately ships only two — the goal is to illustrate the
file format, not to provide a curated catalog.

## Where to find more agents

- [agency-agents](https://github.com/msitarzewski/agency-agents) — 180+
  agents across 14 divisions
- [Everything Claude Code (ECC)](https://github.com/everything-claude-code) —
  ~50 engineering-focused agents
- Write your own — see [docs/creating-agents.md](../../docs/creating-agents.md)

## Adding agents to your setup

Drop `.md` files into `~/.config/opencode/agents/` (or wherever
`OPENCODE_ROUTER_AGENTS_DIR` points) and run:

```bash
opencode-router init
```

That registers them in `opencode.json`, applies model assignments based
on your active profile, and rebuilds the embedding index.
