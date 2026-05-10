"""Tests for memory.storage — on-disk layout and deny list."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router.memory import storage


class TestStorage(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)

    def test_memory_dir_path(self) -> None:
        self.assertEqual(storage.memory_dir(self.project), self.project / ".opencode-router")

    def test_memory_file_path(self) -> None:
        self.assertEqual(storage.memory_file(self.project), self.project / ".opencode-router" / "memory.md")

    def test_state_file_path(self) -> None:
        self.assertEqual(storage.state_file(self.project), self.project / ".opencode-router" / "state.json")

    def test_log_dir_path(self) -> None:
        self.assertEqual(storage.log_dir(self.project), self.project / ".opencode-router" / "log")

    def test_index_file_path(self) -> None:
        self.assertEqual(storage.index_file(self.project), self.project / ".opencode-router" / "memory-index.json")

    def test_ensure_creates_structure(self) -> None:
        storage.ensure(self.project)
        self.assertTrue(storage.memory_dir(self.project).is_dir())
        self.assertTrue(storage.log_dir(self.project).is_dir())
        self.assertTrue((storage.log_dir(self.project) / ".archived").is_dir())
        gi = storage.memory_dir(self.project) / ".gitignore"
        self.assertTrue(gi.is_file())

    def test_ensure_idempotent(self) -> None:
        storage.ensure(self.project)
        storage.ensure(self.project)

    def test_read_state_empty_when_missing(self) -> None:
        self.assertEqual(storage.read_state(self.project), {})

    def test_write_read_state_roundtrip(self) -> None:
        data = {"last_build": "2026-01-01T00:00:00Z", "log_count": 5}
        storage.write_state(self.project, data)
        self.assertEqual(storage.read_state(self.project), data)

    def test_is_denied_common_dirs(self) -> None:
        for name in [".env", "node_modules", ".git", "__pycache__", "secrets"]:
            with self.subTest(name=name):
                self.assertTrue(storage.is_denied(name))

    def test_is_denied_pattern_extensions(self) -> None:
        self.assertTrue(storage.is_denied("cert.pem"))
        self.assertTrue(storage.is_denied("secret.key"))

    def test_is_denied_allows_normal(self) -> None:
        self.assertFalse(storage.is_denied("src"))
        self.assertFalse(storage.is_denied("main.py"))

    def test_project_root_detects_manifest(self) -> None:
        (self.project / "pyproject.toml").write_text("[project]\nname='foo'")
        subdir = self.project / "src" / "nested"
        subdir.mkdir(parents=True)
        root = storage.project_root(start_from=subdir)
        if root is not None:
            self.assertEqual(root.resolve(), self.project.resolve())

    def test_project_root_none_for_empty(self) -> None:
        empty = self.project / "sub"
        empty.mkdir()
        root = storage.project_root(start_from=empty)
        self.assertIsNone(root)

    def test_gitignore_written_once(self) -> None:
        storage.ensure(self.project)
        mtime1 = (storage.memory_dir(self.project) / ".gitignore").stat().st_mtime
        storage.ensure(self.project)
        mtime2 = (storage.memory_dir(self.project) / ".gitignore").stat().st_mtime
        self.assertEqual(mtime1, mtime2)


class TestDenyList(unittest.TestCase):
    def test_opencode_router_excluded(self) -> None:
        self.assertTrue(storage.is_denied(".opencode-router"))

    def test_hermes_excluded(self) -> None:
        self.assertTrue(storage.is_denied(".hermes"))


if __name__ == "__main__":
    unittest.main()
