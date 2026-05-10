"""Tests for memory.__init__ — public API: rebuild, inject, clear."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router import memory


class TestMemoryAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "src").mkdir()
        (self.project / "src" / "main.py").write_text("def main():\n    pass\nclass App:\n    pass\n")
        (self.project / "pyproject.toml").write_text('[project]\nname = "testapp"\n')

    def test_rebuild_creates_memory(self) -> None:
        result = memory.rebuild(self.project, force=True)
        self.assertEqual(result["status"], "built")
        self.assertTrue(result["size_bytes"] > 0)
        self.assertTrue(memory.storage.memory_file(self.project).exists())

    def test_rebuild_has_required_sections(self) -> None:
        memory.rebuild(self.project, force=True)
        content = memory.storage.memory_file(self.project).read_text()
        self.assertIn("## Anatomy", content)
        self.assertIn("## Conventions", content)

    def test_rebuild_includes_symbols(self) -> None:
        memory.rebuild(self.project, force=True)
        content = memory.storage.memory_file(self.project).read_text()
        self.assertIn("main", content)
        self.assertIn("App", content)

    def test_rebuild_skips_unchanged(self) -> None:
        memory.rebuild(self.project, force=True)
        result = memory.rebuild(self.project)
        self.assertEqual(result["status"], "skipped")

    def test_inject_empty_when_no_memory(self) -> None:
        self.assertEqual(memory.inject("fix bug", self.project), "")

    def test_inject_returns_content(self) -> None:
        memory.rebuild(self.project, force=True)
        brief = memory.inject("fix bug", self.project)
        self.assertIn("## Anatomy", brief)

    def test_clear_removes_dir(self) -> None:
        memory.rebuild(self.project, force=True)
        self.assertTrue(memory.storage.memory_dir(self.project).exists())
        memory.clear(self.project)
        self.assertFalse(memory.storage.memory_dir(self.project).exists())

    def test_rebuild_preserves_user_notes(self) -> None:
        memory.rebuild(self.project, force=True)
        mem_path = memory.storage.memory_file(self.project)
        mem_path.write_text(mem_path.read_text() + "\n\n<!-- user-notes -->\nCustom notes\n")
        memory.rebuild(self.project, force=True)
        self.assertIn("Custom notes", mem_path.read_text())

    def test_rebuild_preserves_episodic(self) -> None:
        memory.rebuild(self.project, force=True)
        mem_path = memory.storage.memory_file(self.project)
        mem_path.write_text(mem_path.read_text() + "\n\n## Episodic\n\n- Auth uses JWT in middleware/auth.py\n")
        memory.rebuild(self.project, force=True)
        self.assertIn("Auth uses JWT", mem_path.read_text())


if __name__ == "__main__":
    unittest.main()
