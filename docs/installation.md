# Installation

## Prerequisites

| Requirement | Why | Verify |
|---|---|---|
| Python ≥ 3.10 | Core runtime | `python3 --version` |
| pip | Install the package | `pip3 --version` |
| OpenCode ≥ 1.14.20 | Host agent system | `opencode --version` |
| Ollama | Local embedding + rerank | `ollama --version` && daemon running |
| `~/.local/bin` on `$PATH` | Console scripts land there | `echo "$PATH"` |

### Ollama

Install from <https://ollama.com>. Start the daemon (or open the
desktop app). Verify:

```bash
curl -sf http://localhost:11434/api/tags
```

The installer pulls two models on first run (~4 GB total):

| Model | Purpose | Size |
|---|---|---|
| `mxbai-embed-large` | Embedding (retrieval stage) | 669 MB |
| `qwen3.5:4b` | LLM rerank | 3.4 GB |

Override either with environment variables:

```bash
export OPENCODE_ROUTER_EMBED_MODEL=nomic-embed-text   # smaller
export OPENCODE_ROUTER_RERANK_MODEL=qwen3.5:9b        # stronger
```

## Install from source

```bash
git clone https://github.com/AdrianCsT/opencode-router.git
cd opencode-router
./install.sh
```

What the installer does, in order:

1. `pip install --user -e .` — package becomes importable AND the
   `opencode-router` console script lands on `PATH`.
2. `ollama pull` for the embedding + rerank models (skipped if Ollama
   isn't running).
3. Seeds `~/.config/opencode/orchestration-profile.json` from
   `examples/profiles/starter-profile.json` (if absent — never
   overwrites).
4. Warns if `~/.config/opencode/agents/router.md` is missing and tells
   you the command to copy it.

Re-running `install.sh` is safe — it only adds, never overwrites.

## Pip install (when published)

```bash
pip install --user opencode-router
```

Not yet on PyPI — install from source for now.

## First-time setup after install

```bash
# 1. Copy the router prompt into your agents dir
cp examples/router-prompts/default.md ~/.config/opencode/agents/router.md

# 2. Add at least one specialist agent (or import a collection)
cp examples/agents/*.md ~/.config/opencode/agents/

# 3. Edit the active profile + bucket models to match your providers
$EDITOR ~/.config/opencode/orchestration-profile.json

# 4. Initialise — registers agents, applies models, builds index
opencode-router init

# 5. Sanity-check
opencode-router doctor
opencode-router route "review TypeScript code"
```

## Uninstall

```bash
pip uninstall opencode-router
```

Then in `~/.config/opencode/opencode.json`, change `default_agent` away
from `"router"` (or remove the key) and optionally drop the bundled
agents from the `agent` block. The router's CLI tools disappear from
`PATH` after `pip uninstall`.

The Ollama models stay around. Remove them with:

```bash
ollama rm mxbai-embed-large qwen3.5:4b
```
