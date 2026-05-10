"""Tests for memory.episodic — distillation prompt and parsing."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router.memory import episodic, log, storage


class TestEpisodicParsing(unittest.TestCase):
    def test_parse_json_array(self) -> None:
        raw = '["Use JWT in auth.py", "Prefer select_related over prefetch"]'
        result = episodic._parse_distill_output(raw)
        self.assertEqual(len(result), 2)
        self.assertIn("Use JWT", result[0])

    def test_parse_json_object_with_bullets_key(self) -> None:
        raw = '{"bullets": ["Pattern A", "Pattern B"], "other": 123}'
        result = episodic._parse_distill_output(raw)
        self.assertEqual(len(result), 2)

    def test_parse_fallback_bullet_lines(self) -> None:
        raw = "Some text\n- first pattern here\n- second pattern here\nmore text"
        result = episodic._parse_distill_output(raw)
        self.assertEqual(len(result), 2)

    def test_parse_empty_returns_empty_list(self) -> None:
        result = episodic._parse_distill_output("no bullets here at all")
        self.assertEqual(result, [])

    def test_parse_short_bullets_filtered(self) -> None:
        raw = "- ok\n- short\n- long enough pattern right here"
        result = episodic._parse_distill_output(raw)
        # Only "long enough pattern right here" is > 10 chars
        self.assertGreaterEqual(len(result), 1)


class TestEpisodicFormatting(unittest.TestCase):
    def test_format_includes_section_header(self) -> None:
        result = episodic._format_section(["Use JWT in auth.py"])
        self.assertIn("## Episodic", result)

    def test_format_caps_at_max_bullets(self) -> None:
        many = [f"Pattern number {i}" for i in range(100)]
        result = episodic._format_section(many)
        lines = [line for line in result.splitlines() if line.startswith("- ")]
        self.assertLessEqual(len(lines), 50)

    def test_empty_bullets_minimal_section(self) -> None:
        result = episodic._format_section([])
        self.assertIn("## Episodic", result)


class TestEpisodicDistill(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        storage.ensure(self.project)

    def test_distill_returns_none_with_few_entries(self) -> None:
        # Only 1 entry, below _MIN_ENTRIES (5)
        log.record_entry(
            self.project,
            agent="test",
            task="fix bug",
            files_touched=["src/a.py"],
            summary="Fixed a bug in the routing pipeline.",
            duration_seconds=10,
        )
        result = episodic.distill(self.project)
        self.assertIsNone(result)

    def test_build_prompt_includes_agent_and_task(self) -> None:
        entries = [
            {"agent": "db-optimizer", "task": "fix N+1", "summary": "Done", "files_touched": ["a.py"]},
        ]
        prompt = episodic._build_prompt(entries)
        self.assertIn("db-optimizer", prompt)
        self.assertIn("fix N+1", prompt)
        self.assertIn("Done", prompt)

    def test_build_prompt_truncates_long_summaries(self) -> None:
        entries = [{"agent": "x", "task": "y", "summary": "A" * 500, "files_touched": []}]
        prompt = episodic._build_prompt(entries)
        self.assertIn("A" * 297 + "...", prompt)

    def test_estimate_tokens(self) -> None:
        t = episodic.estimate_tokens("hello world")
        self.assertGreater(t, 0)


if __name__ == "__main__":
    unittest.main()
