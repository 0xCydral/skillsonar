"""Retrieval-augmented injection for large project memories.

When memory.md exceeds ~3k tokens we stop injecting verbatim and
instead return a small always-on header plus top-K chunks most
relevant to the task, found via cosine search over embeddings.

Embedding model: same mxbai-embed-large used for agent routing.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from opencode_router import ollama

from . import storage

_VERBATIM_THRESHOLD_CHARS = 9_000  # ~3k tokens
_HEADER_SECTIONS = frozenset({"# Project Memory", "## Conventions"})
_TOP_K = 5
_CHUNK_MAX_LINES = 25


def inject(task: str, project: Path) -> str:
    """Return memory context for a task dispatch.

    Small projects get verbatim injection. Large projects get
    header plus top-K relevant chunks.
    """
    path = storage.memory_file(project)
    if not path.exists():
        return ""

    content = path.read_text(encoding="utf-8")
    if len(content) < _VERBATIM_THRESHOLD_CHARS:
        return content.strip()

    idx = _load_index(project)
    if idx is None:
        return content[:_VERBATIM_THRESHOLD_CHARS].strip()

    header = _extract_header(content)
    chunks = _search_chunks(task, idx, k=_TOP_K)
    return (header + "\n\n" + chunks).strip()


def build_index(project: Path) -> dict | None:
    """Chunk memory.md and build an embedding index."""
    path = storage.memory_file(project)
    if not path.exists() or path.stat().st_size < _VERBATIM_THRESHOLD_CHARS:
        return None

    content = path.read_text(encoding="utf-8")
    chunks = _chunk(content)

    if len(chunks) < 3:
        return None

    entries: list[dict] = []
    for _i, c in enumerate(chunks):
        try:
            vec = ollama.embed(c)
            entries.append({"text": c, "embedding": vec})
        except Exception:
            continue  # skip chunks that fail to embed

    if len(entries) < 3:
        return None

    idx = {
        "model": ollama.DEFAULT_EMBED_MODEL,
        "chunks": entries,
    }
    _save_index(project, idx)
    return idx


# ---------------------------------------------------------------- internals


def _chunk(content: str) -> list[str]:
    sections = _split_sections(content)
    chunks: list[str] = []
    for title, body in sections:
        if title in _HEADER_SECTIONS:
            continue
        if title in ("## Anatomy", "## Episodic"):
            chunks.extend(_sub_chunk(body))
        else:
            chunks.append(f"{title}\n{body}".strip())
    return [c for c in chunks if len(c) > 50]


def _split_sections(content: str) -> list[tuple[str, str]]:
    parts = content.split("\n## ")
    sections: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("#"):
            lines = part.split("\n", 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
        else:
            title = "## " + part.split("\n", 1)[0].strip()
            body = part.split("\n", 1)[1].strip() if "\n" in part else ""
        sections.append((title, body))
    return sections


def _sub_chunk(body: str) -> list[str]:
    lines = body.splitlines()
    chunks: list[str] = []
    for i in range(0, len(lines), _CHUNK_MAX_LINES):
        chunk = "\n".join(lines[i : i + _CHUNK_MAX_LINES]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _extract_header(content: str) -> str:
    sections = _split_sections(content)
    lines: list[str] = []
    for title, body in sections:
        if title in _HEADER_SECTIONS or title.startswith("# Project Memory"):
            lines.append(f"{title}\n{body}".strip())
    return "\n\n".join(lines).strip()


def _load_index(project: Path) -> dict | None:
    path = storage.index_file(project)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_index(project: Path, idx: dict) -> None:
    storage.ensure(project)
    storage.index_file(project).write_text(
        json.dumps(idx, ensure_ascii=False), encoding="utf-8"
    )


def _search_chunks(task: str, idx: dict, *, k: int) -> str:
    qvec = ollama.embed(task, model=idx.get("model"))
    scored: list[tuple[float, str]] = []
    for entry in idx["chunks"]:
        score = _cosine(qvec, entry["embedding"])
        scored.append((score, entry["text"]))
    scored.sort(key=lambda x: -x[0])

    lines: list[str] = []
    for score, text in scored[:k]:
        if score < 0.15:
            continue
        if len(text) > 600:
            text = text[:597] + "..."
        lines.append(f"<!-- score={score:.3f} -->\n{text}")
    return "\n\n".join(lines)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
