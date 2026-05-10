"""Tests for memory.trigger — rebuild decision logic."""

from __future__ import annotations

import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router.memory import storage, trigger


class TestTrigger(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "src").mkdir()
        (self.project / "src" / "main.py").write_text("def main(): pass")
        (self.project / "pyproject.toml").write_text("[project]\nname='test'")

    def _seed(self) -> None:
        storage.ensure(self.project)
        storage.memory_file(self.project).write_text("# Project Memory\n\n## Anatomy\n\ntest\n")
        snapshot = {
            str(p): int((self.project / p).stat().st_mtime)
            for p in [Path("src/main.py"), Path("pyproject.toml")]
        }
        storage.write_state(self.project, {
            "last_build": datetime.now(timezone.utc).isoformat(),
            "file_mtime_hash": trigger._mtime_hash(self.project),
            "git_head": "",
            "mtime_snapshot": snapshot,
        })

    def test_cold_start_true(self) -> None:
        self.assertTrue(trigger.should_rebuild(self.project))

    def test_force_true(self) -> None:
        self._seed()
        self.assertTrue(trigger.should_rebuild(self.project, force=True))

    def test_no_changes_false(self) -> None:
        self._seed()
        self.assertFalse(trigger.should_rebuild(self.project))

    def test_few_changes_false(self) -> None:
        self._seed()
        (self.project / "src" / "main.py").write_text("def main(): return 1")
        self.assertFalse(trigger.should_rebuild(self.project))

    def test_many_changes_true(self) -> None:
        self._seed()
        for i in range(15):
            (self.project / "src" / f"mod_{i}.py").write_text(f"# module {i}")
            time.sleep(0.01)
        self.assertTrue(trigger.should_rebuild(self.project))

    def test_capture_snapshot_keys(self) -> None:
        snap = trigger.capture_snapshot(self.project)
        self.assertIn("file_mtime_hash", snap)
        self.assertIn("git_head", snap)
        self.assertIn("mtime_snapshot", snap)
        self.assertIn("src/main.py", snap["mtime_snapshot"])

    def test_mtime_hash_changes(self) -> None:
        h1 = trigger._mtime_hash(self.project)
        time.sleep(0.02)
        (self.project / "src" / "main.py").write_text("def main(): return 2")
        h2 = trigger._mtime_hash(self.project)
        self.assertNotEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()
