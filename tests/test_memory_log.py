"""Tests for memory.log — dispatch entry recording and reading."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router.memory import log, storage


class TestLog(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        storage.ensure(self.project)

    def test_record_writes_file(self) -> None:
        path = log.record_entry(
            self.project,
            agent="database-optimizer",
            task="fix N+1 queries",
            files_touched=["src/users/views.py"],
            summary="Replaced N+1 with select_related. Query count: 51 → 2.",
            duration_seconds=45.2,
        )
        self.assertTrue(path.exists())
        self.assertEqual(path.suffix, ".yaml")

    def test_read_entries_returns_data(self) -> None:
        log.record_entry(
            self.project,
            agent="test-agent",
            task="do a thing",
            files_touched=["src/a.py"],
            summary="Done.",
            duration_seconds=1.0,
        )
        entries = log.read_entries(self.project)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["agent"], "test-agent")
        self.assertEqual(entries[0]["task"], "do a thing")
        self.assertIn("src/a.py", entries[0]["files_touched"])
        self.assertEqual(entries[0]["summary"], "Done.")

    def test_read_entries_newest_first(self) -> None:
        import time
        log.record_entry(self.project, agent="first", task="a", files_touched=[], summary="", duration_seconds=0)
        time.sleep(0.01)
        log.record_entry(self.project, agent="second", task="b", files_touched=[], summary="", duration_seconds=0)
        entries = log.read_entries(self.project)
        self.assertEqual(entries[0]["agent"], "second")

    def test_read_entries_empty_when_no_logs(self) -> None:
        entries = log.read_entries(self.project)
        self.assertEqual(entries, [])

    def test_archive_moves_files(self) -> None:
        log.record_entry(self.project, agent="test", task="x", files_touched=[], summary="", duration_seconds=0)
        all_yaml = sorted(storage.log_dir(self.project).glob("*.yaml"))
        count = log.archive(self.project, all_yaml)
        self.assertEqual(count, 1)
        archived = sorted((storage.log_dir(self.project) / ".archived").glob("*.yaml"))
        self.assertEqual(len(archived), 1)
        # Unarchived should be empty now
        self.assertEqual(len(log.read_entries(self.project)), 0)

    def test_summary_with_newlines_roundtrips(self) -> None:
        summary = "Line one.\nLine two.\nLine three."
        log.record_entry(
            self.project,
            agent="test",
            task="multi-line summary",
            files_touched=[],
            summary=summary,
            duration_seconds=0,
        )
        entries = log.read_entries(self.project)
        self.assertIn("Line one.", entries[0]["summary"])
        self.assertIn("Line two.", entries[0]["summary"])


if __name__ == "__main__":
    unittest.main()
