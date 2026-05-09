"""Build and query the agent embedding index."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from . import agents, ollama
from .paths import AGENTS_DIR, INDEX_FILE


@dataclass(frozen=True)
class Hit:
    name: str
    score: float
    description: str
    mode: str


def build(*, verbose: bool = True) -> int:
    """Embed every agent file in AGENTS_DIR and write the index. Returns
    the count of agents indexed (primary-mode agents are skipped to
    avoid the router recommending itself)."""
    files = agents.list_agent_files(AGENTS_DIR)
    if not files:
        raise SystemExit(f"No agent files found in {AGENTS_DIR}")

    indexed: list[dict] = []
    skipped: list[str] = []
    started = time.time()

    for i, path in enumerate(files, 1):
        agent = agents.parse_agent_file(path)
        if agent.mode.lower() == "primary":
            skipped.append(agent.name)
            continue
        try:
            vec = ollama.embed(agents.embed_text_for(agent))
        except Exception as exc:
            if verbose:
                print(f"[{i}/{len(files)}] FAIL {agent.name}: {exc}")
            continue
        indexed.append(
            {
                "name": agent.name,
                "description": agent.description,
                "mode": agent.mode,
                "embedding": vec,
            }
        )
        if verbose and (i % 25 == 0 or i == len(files)):
            print(f"[{i}/{len(files)}] embedded ({time.time() - started:.1f}s)")

    payload = {
        "model": ollama.DEFAULT_EMBED_MODEL,
        "dim": len(indexed[0]["embedding"]) if indexed else 0,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(indexed),
        "agents": indexed,
    }
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(payload), encoding="utf-8")

    if verbose:
        size_mb = INDEX_FILE.stat().st_size / (1024 * 1024)
        print(f"\nWrote {len(indexed)} agents, {payload['dim']}-dim, {size_mb:.2f} MB → {INDEX_FILE}")
        if skipped:
            print(f"Skipped {len(skipped)} primary agent(s): {', '.join(skipped)}")
    return len(indexed)


def load() -> dict:
    if not INDEX_FILE.exists():
        raise SystemExit(
            f"Index not found at {INDEX_FILE}\n"
            f"Run: opencode-router index build"
        )
    return json.loads(INDEX_FILE.read_text(encoding="utf-8"))


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def search(query: str, *, k: int) -> list[Hit]:
    idx = load()
    qvec = ollama.embed(query, model=idx.get("model"))
    scored: list[Hit] = []
    for entry in idx["agents"]:
        score = cosine(qvec, entry["embedding"])
        scored.append(
            Hit(
                name=entry["name"],
                score=score,
                description=entry.get("description", ""),
                mode=entry.get("mode", "subagent"),
            )
        )
    scored.sort(key=lambda h: h.score, reverse=True)
    return scored[:k]
