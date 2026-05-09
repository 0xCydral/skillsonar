# Configuration

All paths are configurable via environment variables. Defaults assume
the standard OpenCode layout.

| Env var | Default | Purpose |
|---|---|---|
| `OPENCODE_ROUTER_OPENCODE_DIR` | `~/.config/opencode` | Root of OpenCode config |
| `OPENCODE_ROUTER_AGENTS_DIR` | `${OPENCODE_DIR}/agents` | Agent `.md` files |
| `OPENCODE_ROUTER_CONFIG` | `${OPENCODE_DIR}/opencode.json` | OpenCode main config |
| `OPENCODE_ROUTER_INDEX` | `${OPENCODE_DIR}/agent-index.json` | Embedding index |
| `OPENCODE_ROUTER_PROFILE` | `${OPENCODE_DIR}/orchestration-profile.json` | Provider profiles |
| `OPENCODE_ROUTER_RULES` | `${OPENCODE_DIR}/orchestration-rules.json` | Role-pattern rules (optional) |
| `OPENCODE_ROUTER_OLLAMA_URL` | `http://localhost:11434` | Ollama daemon URL |
| `OPENCODE_ROUTER_EMBED_MODEL` | `mxbai-embed-large` | Embedding model |
| `OPENCODE_ROUTER_RERANK_MODEL` | `qwen3.5:4b` | Rerank model |

## File schemas

### `orchestration-profile.json`

```jsonc
{
  "active": "<profile name>",
  "profiles": {
    "<name>": {
      "description": "Short human-readable description",
      "buckets": {
        "pro":         "<provider/model>",
        "flash":       "<provider/model>",
        "coding":      "<provider/model>",
        "visual":      "<provider/model>",
        "chinese":     "<provider/model>",
        "translation": "<provider/model>"
      }
    }
  }
}
```

- `active` selects which profile is in effect.
- Buckets missing from a profile fall back to that profile's `pro`
  bucket. Only `pro` is strictly required.
- See `examples/profiles/starter-profile.json` for a complete example
  with four profiles wired up.

### `orchestration-rules.json` (optional)

If absent, built-in defaults are used (see
`src/opencode_router/rules.py`). To override, write:

```jsonc
{
  "rules": [
    ["<substring pattern>", "<bucket name>"],
    ["security-reviewer",   "pro"],
    ["sales-coach",         "flash"],
    ["my-internal-agent",   "coding"]
  ],
  "default_bucket": "pro"
}
```

- Order matters — first match wins. Specific patterns BEFORE general.
- Matched against `lowercase(<agent name> + " " + <description>)`.
- The `default_bucket` is used when no rule matches.

### `agent-index.json` (auto-generated)

Built by `opencode-router index build`. Don't edit by hand.

## OpenCode config (`opencode.json`)

`opencode-router` writes to two keys:

- `agent` — the registry. One entry per `.md` file in your agents
  directory.
- `default_agent` — set to `"router"` if a `router.md` exists in your
  agents directory.

**Everything else is preserved verbatim** across runs (your `plugin`
list, MCP servers, providers, permissions, custom keys). Each write
creates a timestamped backup at
`~/.config/opencode/opencode.json.backup-YYYYMMDD-HHMMSS`.

## Bucket names

The default rules use six conventional buckets: `pro`, `flash`,
`coding`, `visual`, `chinese`, `translation`. You can rename or replace
them — just keep your rules file's right-hand sides in sync with your
profile's `buckets` keys.

## Custom embedding / rerank models

Any Ollama-served model with `/api/embeddings` or `/api/generate`
support works:

```bash
# Lightweight footprint
export OPENCODE_ROUTER_EMBED_MODEL=nomic-embed-text  # 137M params
export OPENCODE_ROUTER_RERANK_MODEL=qwen3.5:1.7b     # 1.0 GB

# Heavier, more accurate
export OPENCODE_ROUTER_RERANK_MODEL=qwen3.5:9b
```

After changing the embedding model, **always rebuild the index** — old
embeddings won't match the new model's vector space:

```bash
opencode-router index build
```
