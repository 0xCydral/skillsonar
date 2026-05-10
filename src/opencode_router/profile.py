"""Provider profile management.

A profile maps abstract role buckets to concrete model paths. The
on-disk schema is JSON:

    {
      "active": "<profile name>",
      "profiles": {
        "<name>": {
          "description": "...",
          "buckets": {
            "pro": "<model path>",
            "flash": "<model path>",
            ...
          }
        }
      }
    }

Buckets are conventional names used by the rules engine (`pro`,
`flash`, `coding`, `visual`, `chinese`, `translation`). Missing buckets
fall back to `pro`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .paths import PROFILE_FILE

CONVENTIONAL_BUCKETS = ("pro", "flash", "coding", "visual", "chinese", "translation")


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    buckets: dict[str, str]


def _empty_config() -> dict:
    return {"active": None, "profiles": {}}


def load() -> dict:
    if not PROFILE_FILE.exists():
        return _empty_config()
    return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def list_profiles() -> dict:
    return load().get("profiles", {})


def active_name() -> str | None:
    return load().get("active")


def get(name: str) -> Profile:
    data = load()
    profiles = data.get("profiles", {})
    if name not in profiles:
        raise SystemExit(
            f"Profile '{name}' not found. Available: {sorted(profiles)}"
        )
    p = profiles[name]
    buckets = dict(p.get("buckets", {}))
    pro = buckets.get("pro")
    if not pro:
        raise SystemExit(f"Profile '{name}' is missing the required 'pro' bucket")
    for b in CONVENTIONAL_BUCKETS:
        buckets.setdefault(b, pro)
    return Profile(name=name, description=p.get("description", ""), buckets=buckets)


def get_active() -> Profile:
    name = active_name()
    if not name:
        raise SystemExit(
            "No active profile set. Run: opencode-router profile set <name>"
        )
    return get(name)


def set_active(name: str) -> None:
    data = load()
    if name not in data.get("profiles", {}):
        raise SystemExit(
            f"Profile '{name}' not found. Available: {sorted(data.get('profiles', {}))}"
        )
    data["active"] = name
    save(data)
