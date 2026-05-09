"""Filesystem paths used across the package.

All paths live under the user's OpenCode config directory so the user
can override by symlinking or moving files. Environment variables can
override individual paths for testing or alternate setups.
"""

from __future__ import annotations

import os
from pathlib import Path


def _env_path(var: str, default: Path) -> Path:
    value = os.environ.get(var)
    return Path(value).expanduser() if value else default


OPENCODE_DIR = _env_path(
    "OPENCODE_ROUTER_OPENCODE_DIR",
    Path.home() / ".config" / "opencode",
)

AGENTS_DIR = _env_path(
    "OPENCODE_ROUTER_AGENTS_DIR",
    OPENCODE_DIR / "agents",
)

CONFIG_FILE = _env_path(
    "OPENCODE_ROUTER_CONFIG",
    OPENCODE_DIR / "opencode.json",
)

INDEX_FILE = _env_path(
    "OPENCODE_ROUTER_INDEX",
    OPENCODE_DIR / "agent-index.json",
)

PROFILE_FILE = _env_path(
    "OPENCODE_ROUTER_PROFILE",
    OPENCODE_DIR / "orchestration-profile.json",
)

RULES_FILE = _env_path(
    "OPENCODE_ROUTER_RULES",
    OPENCODE_DIR / "orchestration-rules.json",
)
