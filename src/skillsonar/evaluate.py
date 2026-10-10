"""recall@k over a JSONL file of {"query": ..., "expected": [skill names]} lines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from skillsonar.errors import SkillIndexError
from skillsonar.search import Searcher


@dataclass
class Miss:
    query: str
    expected: list[str]
    got: list[str]


@dataclass
class Report:
    k: int
    mode: str
    queries: int
    recall: float
    first_hits: int
    misses: list[Miss]


def load_queries(path: Path) -> list[tuple[str, list[str]]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SkillIndexError(f"cannot read {path} ({exc})") from exc
    out = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            expected = row["expected"]
            out.append((row["query"], [expected] if isinstance(expected, str) else list(expected)))
        except (ValueError, KeyError, TypeError) as exc:
            raise SkillIndexError(f"{path}:{number}: need a JSON object with query and expected") from exc
    return out


def evaluate(searcher: Searcher, queries: list[tuple[str, list[str]]], k: int, mode: str) -> Report:
    """recall@k per query is the share of its expected skills found in the top k; the report averages it."""
    known = {e["name"] for e in searcher.all_entries}
    unknown = sorted({n for _, expected in queries for n in expected} - known)
    if unknown:
        raise SkillIndexError(f"expected skills not in the index: {', '.join(unknown)}")
    total, first, misses = 0.0, 0, []
    for query, expected in queries:
        got = [e["name"] for e, _ in searcher.rank(query, mode)[:k]]
        found = [n for n in expected if n in got]
        total += len(found) / len(expected)
        first += bool(got) and got[0] in expected
        if len(found) < len(expected):
            misses.append(Miss(query, expected, got))
    count = len(queries)
    return Report(k, mode, count, total / count if count else 0.0, first, misses)
