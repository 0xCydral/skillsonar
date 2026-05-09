#!/usr/bin/env bash
#
# Import a starter agent catalog from open-source collections.
#
# Sources:
#   agency-agents  — 180+ specialists across 14 divisions (MIT)
#   ECC agents     — ~50 engineering-focused agents (MIT)
#
# Usage:
#   bash scripts/import-agents.sh              # all collections
#   bash scripts/import-agents.sh agency       # agency-agents only
#   bash scripts/import-agents.sh --dry-run    # show what would be copied

set -euo pipefail

AGENTS_DIR="${OPENCODE_ROUTER_AGENTS_DIR:-$HOME/.config/opencode/agents}"
CLONE_DIR="$HOME/.local/share/opencode-router-collections"
DRY_RUN=false
COLLECTIONS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    agency|ecc|all) COLLECTIONS="$COLLECTIONS $1"; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

COLLECTIONS="${COLLECTIONS:-all}"

color() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
log()  { color "1;34" "→ $*"; }
ok()   { color "1;32" "✓ $*"; }

mkdir -p "$AGENTS_DIR"

import_agency() {
  local src="$CLONE_DIR/agency-agents/agents"
  if [ ! -d "$src" ]; then
    log "Cloning agency-agents…"
    mkdir -p "$CLONE_DIR"
    git clone --depth 1 https://github.com/msitarzewski/agency-agents.git "$CLONE_DIR/agency-agents"
  else
    log "Updating agency-agents…"
    (cd "$CLONE_DIR/agency-agents" && git pull --ff-only) || true
  fi
  local count=0
  for f in "$src"/*.md; do
    local name
    name="$(basename "$f")"
    if $DRY_RUN; then
      echo "  would copy: $name"
    else
      cp -f "$f" "$AGENTS_DIR/$name"
    fi
    ((count++))
  done
  ok "agency-agents: $count agents"
}

import_ecc() {
  local ecc_dir
  ecc_dir="$(npm root -g 2>/dev/null)/ecc-universal/agents" || true
  if [ ! -d "$ecc_dir" ]; then
    log "ECC not found globally. Install with: npm install -g ecc-universal"
    log "Skipping ECC agents."
    return
  fi
  local count=0
  for f in "$ecc_dir"/*.md; do
    local name
    name="$(basename "$f")"
    if $DRY_RUN; then
      echo "  would copy: $name (ECC)"
    else
      cp -f "$f" "$AGENTS_DIR/$name"
    fi
    ((count++))
  done
  ok "ECC: $count agents"
}

echo
log "Target: $AGENTS_DIR"
if $DRY_RUN; then log "(dry run — no files will be copied)"; fi
echo

case "$COLLECTIONS" in
  *all*|*agency*) import_agency ;;
esac
case "$COLLECTIONS" in
  *all*|*ecc*) import_ecc ;;
esac

echo
ok "Done. Run 'opencode-router init' to register the new agents."
