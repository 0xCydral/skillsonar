import zlib
from pathlib import Path

import pytest

from skillsonar.index import tokenize

SKILLS = Path(__file__).parent / "fixtures" / "skills"
QUERIES = Path(__file__).parent.parent / "evals" / "queries.jsonl"


class FakeOllama:
    """Stands in for OllamaClient: hashes word tokens into a small vector, no network."""

    model = "fake-embed"
    DIM = 4096

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        vectors = []
        for text in texts:
            vec = [0.0] * self.DIM
            for token in tokenize(text):
                vec[zlib.crc32(token.encode()) % self.DIM] += 1.0
            vectors.append(vec)
        return vectors


class FakeReranker:
    """Stands in for RerankClient: picks the candidates whose line contains a chosen word."""

    def __init__(self, word):
        self.word = word
        self.seen = []

    def rank(self, query, candidates, k):
        self.seen.append(candidates)
        hits = [i for i, line in enumerate(candidates) if self.word in line]
        return hits[:k]


@pytest.fixture
def skills_dir():
    return SKILLS


@pytest.fixture
def queries_file():
    return QUERIES


@pytest.fixture
def fake_ollama(monkeypatch):
    fake = FakeOllama()
    monkeypatch.setattr("skillsonar.cli.OllamaClient", type("C", (), {"from_env": staticmethod(lambda: fake)}))
    return fake


@pytest.fixture
def index_dir(tmp_path, skills_dir):
    from skillsonar.cli import main

    target = tmp_path / "idx"
    assert main(["build", "--path", str(skills_dir), "--index", str(target)]) == 0
    return target
