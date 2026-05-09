#!/usr/bin/env bash
#
# Install the opencode-router engine into AgentSkillOS.
#
# Symlinks the router_engine directory into AgentSkillOS's
# src/orchestrator/ so it is discovered by the plugin registry
# on next start.
#
# Usage:
#   bash contrib/agentskillos/install.sh
#   bash contrib/agentskillos/install.sh /path/to/AgentSkillOS
#
# Idempotent. Safe to re-run.

set -euo pipefail

SKILLOS_DIR="${1:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINE_SRC="$REPO_ROOT/contrib/agentskillos/router_engine"

if [ -z "$SKILLOS_DIR" ]; then
  for candidate in \
    "$HOME/AgentSkillOS" \
    "$HOME/agent-skillos" \
    "$HOME/agentskillos" \
    "$HOME/.local/share/AgentSkillOS"; do
    if [ -d "$candidate" ]; then
      SKILLOS_DIR="$candidate"
      break
    fi
  done
fi

if [ -z "$SKILLOS_DIR" ] || [ ! -d "$SKILLOS_DIR" ]; then
  echo "Error: AgentSkillOS directory not found." >&2
  echo "Usage: bash $0 /path/to/AgentSkillOS" >&2
  exit 1
fi

TARGET_DIR="$SKILLOS_DIR/src/orchestrator/router_engine"

if [ -L "$TARGET_DIR" ]; then
  echo "Router engine already symlinked at $TARGET_DIR"
elif [ -d "$TARGET_DIR" ]; then
  echo "Router engine dir already exists at $TARGET_DIR (not a symlink). Remove it first." >&2
  exit 1
else
  ln -s "$ENGINE_SRC" "$TARGET_DIR"
  echo "Symlinked: $TARGET_DIR → $ENGINE_SRC"
fi

echo "Done. Restart AgentSkillOS to see 'Router (Agent Dispatch)' in the engine list."
echo "Requires: opencode-router installed and ~/.config/opencode/agents/ populated."
