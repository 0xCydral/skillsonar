"""Manipulate ~/.config/opencode/opencode.json safely.

We touch only:
  - the `agent` key (registering all .md files in agents/)
  - the `default_agent` key (set to "router" if a router.md exists)

Everything else (plugin, mcp, provider, permission, custom keys) is
preserved verbatim. Backups are written before each change.
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import agents, profile, rules
from .paths import AGENTS_DIR, CONFIG_FILE


def _to_tilde(path: Path) -> str:
    """Render a path with `~` for the user home, opencode-style."""
    home = str(Path.home())
    p = path.as_posix()
    if p.startswith(home):
        return "~" + p[len(home):]
    return p


PLACEHOLDER_MODEL_BUCKET = "pro"


def _backup() -> str:
    if not CONFIG_FILE.exists():
        return ""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = CONFIG_FILE.with_suffix(f".json.backup-{ts}")
    shutil.copyfile(CONFIG_FILE, target)
    return str(target)


def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        # Minimal valid config so callers can write to it.
        return {"$schema": "https://opencode.ai/config.json"}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def _save_config(data: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def register() -> tuple[int, str]:
    """Populate the `agent` block from agents/ directory. Sets
    default_agent="router" if a router.md is present. Returns the count
    of agents registered and the backup path (empty if no prior config).
    Models are set to a placeholder; call apply_models() next."""
    files = agents.list_agent_files(AGENTS_DIR)
    if not files:
        raise SystemExit(f"No agent .md files in {AGENTS_DIR}")

    backup = _backup()
    config = _load_config()

    # Resolve placeholder model from active profile, fallback to a literal
    # if no profile is set (so first-time install still produces a valid
    # config — the user fixes models with `models apply` after).
    try:
        active = profile.get_active()
        placeholder = active.buckets[PLACEHOLDER_MODEL_BUCKET]
    except SystemExit:
        placeholder = "PLACEHOLDER_MODEL_NEEDS_PROFILE"

    block: dict[str, dict] = {}
    has_router = False
    for path in files:
        agent = agents.parse_agent_file(path)
        desc = agent.description
        if len(desc) > 500:
            desc = desc[:497] + "..."
        block[agent.name] = {
            "description": desc,
            "model": placeholder,
            "prompt": f"{{file:{_to_tilde(path)}}}",
        }
        if agent.name == "router":
            has_router = True

    config["agent"] = dict(sorted(block.items()))
    if has_router:
        config["default_agent"] = "router"

    _save_config(config)
    return len(block), backup


def apply_models(*, profile_name: str | None = None) -> dict:
    """Re-pick the model field for every agent in opencode.json based on
    the rules engine and the chosen profile. Returns a summary dict with
    counts."""
    if profile_name:
        prof = profile.get(profile_name)
    else:
        prof = profile.get_active()

    ruleset = rules.load()
    config = _load_config()
    agent_block = config.get("agent", {})
    if not agent_block:
        raise SystemExit("No agents in opencode.json. Run: opencode-router register")

    bucket_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    changed = 0

    for name, cfg in agent_block.items():
        if name == "router":
            bucket = "coding"  # router needs strong tool-use discipline
        else:
            bucket = ruleset.pick(name, cfg.get("description", ""))
        new_model = prof.buckets.get(bucket, prof.buckets["pro"])
        if cfg.get("model") != new_model:
            cfg["model"] = new_model
            changed += 1
        bucket_counts[bucket] += 1
        model_counts[new_model] += 1

    config["agent"] = dict(sorted(agent_block.items()))
    _save_config(config)

    return {
        "profile": prof.name,
        "changed": changed,
        "total": len(agent_block),
        "buckets": dict(bucket_counts),
        "models": dict(model_counts),
    }
