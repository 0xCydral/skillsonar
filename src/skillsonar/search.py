"""Ranking modes: keyword, semantic, hybrid (reciprocal rank fusion), and the optional rerank."""

from __future__ import annotations

from pathlib import Path

from skillsonar.index import keyword_rank
from skillsonar.semantic import load_embeddings, semantic_rank

MODES = ("keyword", "semantic", "hybrid")
RRF_K = 60
POOL = 150
LINE_CHARS = 150


def rrf(rankings: list[list[dict]], k: int = RRF_K) -> list[tuple[dict, float]]:
    """Reciprocal rank fusion. An entry's score is the sum of 1/(k + rank) over each ranking it is in."""
    scores: dict[str, float] = {}
    by_path: dict[str, dict] = {}
    for ranking in rankings:
        for position, entry in enumerate(ranking, 1):
            by_path[entry["path"]] = entry
            scores[entry["path"]] = scores.get(entry["path"], 0.0) + 1.0 / (k + position)
    fused = sorted(scores.items(), key=lambda item: -item[1])
    return [(by_path[path], score) for path, score in fused]


class Searcher:
    """Ranks the entries of one index in any mode. Embedding services are only touched when needed."""

    def __init__(self, entries: list[dict], directory: Path, ollama=None, restrict=None):
        self.all_entries = entries
        self.entries = [e for e in entries if restrict is None or restrict(e)]
        self.directory = directory
        self.ollama = ollama
        self._vectors: dict[str, list[float]] | None = None

    def rank(self, query: str, mode: str = "keyword") -> list[tuple[dict, float]]:
        if mode == "keyword":
            return keyword_rank(self.entries, query)
        semantic = self._semantic(query)
        if mode == "semantic":
            return semantic
        keyword = keyword_rank(self.entries, query)
        return rrf([[e for e, _ in keyword], [e for e, _ in semantic[:POOL]]])

    def _semantic(self, query: str) -> list[tuple[dict, float]]:
        if self._vectors is None:
            self._vectors = load_embeddings(self.directory, self.all_entries)
        query_vector = self.ollama.embed([query])[0]
        return semantic_rank(self.entries, self._vectors, query_vector)

    def search(self, query: str, mode: str, top: int, reranker=None, pool: int = POOL):
        """Top results as (entry, first-stage score). With a reranker, it reorders the first-stage pool."""
        ranked = self.rank(query, mode)
        if reranker is None:
            return ranked[:top]
        shortlist = ranked[:pool]
        lines = [f"{e['name']}: {' '.join(e['desc'].split())[:LINE_CHARS]}" for e, _ in shortlist]
        order = reranker.rank(query, lines, top)
        return [shortlist[i] for i in order] or shortlist[:top]
