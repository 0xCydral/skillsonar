"""Agent file parsing — frontmatter extraction and embed-text construction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class Agent:
    """A parsed agent file."""

    name: str
    description: str
    mode: str
    raw_frontmatter: dict[str, str]


def parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fm: dict[str, str] = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ")


def parse_agent_file(path: Path) -> Agent:
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    name = path.stem
    return Agent(
        name=name,
        description=fm.get("description", f"Agent: {humanize(name).title()}"),
        mode=fm.get("mode", "subagent"),
        raw_frontmatter=fm,
    )


def embed_text_for(agent: Agent) -> str:
    """Return the canonical text used to embed this agent.

    We embed only humanized name + description. Body intros are
    formulaic across agent collections and add noise.
    """
    parts = [humanize(agent.name), agent.description]
    return "\n".join(p for p in parts if p)


def list_agent_files(agents_dir: Path) -> list[Path]:
    if not agents_dir.is_dir():
        return []
    return sorted(agents_dir.glob("*.md"))
