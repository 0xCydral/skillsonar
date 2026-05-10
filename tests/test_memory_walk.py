"""Tests for memory.walk — file listing with deny-list filtering."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router.memory import walk


class TestWalk(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "src").mkdir()
        (self.project / "node_modules").mkdir()
        (self.project / "node_modules" / "lodash").mkdir(parents=True)
        (self.project / ".git").mkdir()
        (self.project / "pyproject.toml").write_text("[project]\nname='test'")
        (self.project / "src" / "main.py").write_text("def main(): pass")
        (self.project / "src" / "utils.py").write_text("def helper(): pass")
        (self.project / "node_modules" / "lodash" / "index.js").write_text("// stub")
        (self.project / ".git" / "HEAD").write_text("ref: refs/heads/main")
        (self.project / ".env").write_text("SECRET=1")

    def test_excludes_deny_list_dirs(self) -> None:
        files = walk.list_files(self.project)
        paths = {str(f) for f in files}
        self.assertIn("pyproject.toml", paths)
        self.assertIn("src/main.py", paths)
        node_files = [p for p in paths if "node_modules" in p]
        self.assertEqual(node_files, [])
        git_files = [p for p in paths if ".git" in p]
        self.assertEqual(git_files, [])
        env_files = [p for p in paths if ".env" in p]
        self.assertEqual(env_files, [])

    def test_returns_relative_paths(self) -> None:
        for f in walk.list_files(self.project):
            self.assertFalse(f.is_absolute())

    def test_sorted_output(self) -> None:
        files = walk.list_files(self.project)
        paths = [str(f) for f in files]
        self.assertEqual(paths, sorted(paths))

    def test_walk_files_excludes_denied(self) -> None:
        files = walk._walk_files(self.project)
        self.assertTrue(len(files) > 0)
        for f in files:
            for part in f.parts:
                self.assertNotIn(part, ["node_modules", ".git", ".env"])


if __name__ == "__main__":
    unittest.main()
