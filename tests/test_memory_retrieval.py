"""Tests for memory.retrieval — chunking, header extraction, injection."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router.memory import retrieval, storage

_SMALL_MEMORY = """# Project Memory
_Last built: 2026-05-10T00:00:00Z_

## Anatomy

### File Tree
  src/
    main.py
    utils.py

### Key Symbols
  src/main.py: main, App

## Conventions

### Languages
Primary: Python

## Episodic
- Use JWT in middleware/auth.py
- prefer select_related over prefetch for 1:1
"""


class TestRetrievalChunking(unittest.TestCase):
    def test_split_sections(self) -> None:
        sections = retrieval._split_sections(_SMALL_MEMORY)
        titles = [t for t, _ in sections]
        self.assertIn("# Project Memory", titles)
        self.assertIn("## Anatomy", titles)
        self.assertIn("## Conventions", titles)
        self.assertIn("## Episodic", titles)

    def test_chunk_excludes_header(self) -> None:
        chunks = retrieval._chunk(_SMALL_MEMORY)
        chunk_text = "\n".join(chunks)
        self.assertNotIn("# Project Memory", chunk_text)

    def test_chunk_includes_anatomy(self) -> None:
        chunks = retrieval._chunk(_SMALL_MEMORY)
        chunk_text = "\n".join(chunks)
        self.assertIn("main.py", chunk_text)

    def test_extract_header(self) -> None:
        header = retrieval._extract_header(_SMALL_MEMORY)
        self.assertIn("Project Memory", header)
        self.assertIn("## Conventions", header)
        self.assertNotIn("## Anatomy", header)


class TestRetrievalInjection(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        storage.ensure(self.project)

    def test_small_returns_verbatim(self) -> None:
        storage.memory_file(self.project).write_text(_SMALL_MEMORY, encoding="utf-8")
        brief = retrieval.inject("fix a bug", self.project)
        self.assertIn("## Anatomy", brief)

    def test_no_memory_returns_empty(self) -> None:
        self.assertEqual(retrieval.inject("fix a bug", self.project), "")

    def test_large_truncates_when_no_index(self) -> None:
        content = _SMALL_MEMORY + "\n" + ("x" * 10_000)
        storage.memory_file(self.project).write_text(content, encoding="utf-8")
        brief = retrieval.inject("fix a bug", self.project)
        self.assertLess(len(brief), len(content))
        self.assertIn("Project Memory", brief)

    def test_build_index_none_for_small(self) -> None:
        storage.memory_file(self.project).write_text(_SMALL_MEMORY, encoding="utf-8")
        self.assertIsNone(retrieval.build_index(self.project))

    def test_cosine_identical(self) -> None:
        v = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(retrieval._cosine(v, v), 1.0, places=5)

    def test_cosine_zero(self) -> None:
        self.assertEqual(retrieval._cosine([0.0, 0.0], [1.0, 2.0]), 0.0)


class TestRetrievalSubChunk(unittest.TestCase):
    def test_long_body_multi(self) -> None:
        body = "\n".join(f"line {i}" for i in range(80))
        self.assertGreater(len(retrieval._sub_chunk(body)), 1)

    def test_short_body_single(self) -> None:
        self.assertEqual(len(retrieval._sub_chunk("one\ntwo\nthree")), 1)


if __name__ == "__main__":
    unittest.main()
