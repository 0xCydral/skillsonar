#!/usr/bin/env bash
#
# opencode-router installer.
#
# Idempotent. Safe to re-run. Does not touch any opencode.json keys
# beyond `agent` and `default_agent` (and only the latter if a router
# agent file is present).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCODE_DIR="$HOME/.config/opencode"
AGENTS_DIR="$OPENCODE_DIR/agents"
PROFILE_FILE="$OPENCODE_DIR/orchestration-profile.json"
EMBED_MODEL="${OPENCODE_ROUTER_EMBED_MODEL:-mxbai-embed-large}"
RERANK_MODEL="${OPENCODE_ROUTER_RERANK_MODEL:-qwen3.5:4b}"

color() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
log()  { color "1;34" "→ $*"; }
ok()   { color "1;32" "✓ $*"; }
warn() { color "1;33" "⚠ $*"; }
fail() { color "1;31" "✗ $*" >&2; exit 1; }

# Prereqs
log "Checking prerequisites…"
command -v python3 >/dev/null || fail "python3 not found"
command -v pip3    >/dev/null || command -v pip >/dev/null || fail "pip not found"
command -v ollama  >/dev/null || warn "ollama not found — install from https://ollama.com"
command -v opencode >/dev/null || warn "opencode not found — install from https://opencode.ai"

# Install package
log "Installing opencode-router…"
python3 -m pip install --user -e "$REPO_ROOT"
ok "Installed"

# Pull models
if command -v ollama >/dev/null; then
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        for model in "$EMBED_MODEL" "$RERANK_MODEL"; do
            if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$model"; then
                ok "$model already pulled"
            else
                log "Pulling $model…"
                ollama pull "$model"
            fi
        done
    else
        warn "Ollama daemon not running — start it before running opencode-router init"
    fi
fi

# Seed profile config
mkdir -p "$OPENCODE_DIR" "$AGENTS_DIR"
if [ ! -f "$PROFILE_FILE" ]; then
    cp "$REPO_ROOT/examples/profiles/starter-profile.json" "$PROFILE_FILE"
    ok "Seeded $PROFILE_FILE — edit the active profile and bucket models to match your setup"
else
    ok "Profile config already exists at $PROFILE_FILE"
fi

# Suggest router prompt copy if missing
if [ ! -f "$AGENTS_DIR/router.md" ]; then
    warn "No router.md found in $AGENTS_DIR"
    warn "Run: cp $REPO_ROOT/examples/router-prompts/default.md $AGENTS_DIR/router.md"
fi

cat <<EOF

$(color "1;32" "Installation complete.")

Next steps:

  1. Add agent .md files to: $AGENTS_DIR
     (see examples/agents/ for the format)

  2. Copy the router prompt:
       cp $REPO_ROOT/examples/router-prompts/default.md $AGENTS_DIR/router.md

  3. Edit profile/buckets to match your providers:
       \$EDITOR $PROFILE_FILE

  4. Initialise:
       opencode-router init

  5. Open opencode and try a real task.

EOF
