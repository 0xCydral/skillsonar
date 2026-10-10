"""Embedding index: one unit vector per skill, cosine search, no dependencies."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from skillsonar.errors import SkillIndexError
from skillsonar.index import read_head, split_frontmatter

EMBEDDINGS_FILE = "embeddings.json"
BATCH = 16
DOC_CAP = 2500
_HEADING = re.compile(r"^#{1,3}\s+(.+)$", re.M)


def document_for(entry: dict) -> str:
    """The text that gets embedded: name, description, H1-H3 headings, then the opening prose.

    Headings are the tasks a skill covers, written as tasks, so they carry the most signal per
    token. The whole document is capped because an embedding model dilutes a long tail of setup
    boilerplate into a vector that looks like every other skill.
    """
    body = split_frontmatter(read_head(Path(entry["path"]) / "SKILL.md", 20000))[1]
    headings = " ".join(h.strip() for h in _HEADING.findall(body)[:40])
    prose = " ".join(_HEADING.sub(" ", body).split())[:900]
    return f"{entry['name']}. {entry['desc']} {headings} {prose}".strip()[:DOC_CAP]


def unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def build_embeddings(entries: list[dict], client, progress=None) -> dict:
    """Embed every entry in batches. `client` is an OllamaClient or anything with embed()."""
    vectors: list[list[float]] = []
    for start in range(0, len(entries), BATCH):
        batch = entries[start : start + BATCH]
        vectors.extend(unit(v) for v in client.embed([document_for(e) for e in batch]))
        if progress:
            progress(len(vectors), len(entries))
    return {
        "model": client.model,
        "count": len(vectors),
        "paths": [e["path"] for e in entries],
        "vectors": [[round(x, 6) for x in v] for v in vectors],
    }


def save_embeddings(directory: Path, payload: dict) -> Path:
    target = directory / EMBEDDINGS_FILE
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def load_embeddings(directory: Path, entries: list[dict]) -> dict[str, list[float]]:
    """Path to vector. Fails when the embeddings were built for a different set of skills."""
    target = directory / EMBEDDINGS_FILE
    if not target.is_file():
        raise SkillIndexError(f"no embeddings at {target}. Build them: skillsonar build --embed")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        vectors = dict(zip(payload["paths"], payload["vectors"], strict=True))
    except (OSError, ValueError, KeyError) as exc:
        raise SkillIndexError(f"cannot read {target} ({exc}); rebuild: skillsonar build --embed") from exc
    if any(e["path"] not in vectors for e in entries):
        raise SkillIndexError("embeddings are out of date for this index; run: skillsonar build --embed")
    return vectors


def semantic_rank(
    entries: list[dict], vectors: dict[str, list[float]], query_vector: list[float]
) -> list[tuple[dict, float]]:
    """Every entry, most similar first. Stored vectors are unit length, so a dot product is cosine."""
    query = unit(query_vector)
    scored = [(e, sum(a * b for a, b in zip(vectors[e["path"]], query, strict=True))) for e in entries]
    scored.sort(key=lambda pair: -pair[1])
    return scored
