"""Tests for memory.anatomy — file tree and symbol extraction."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router.memory import anatomy


class TestAnatomyPython(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "src").mkdir()
        (self.project / "src" / "models.py").write_text("class User:\n    pass\nclass Order:\n    pass\n")
        (self.project / "src" / "views.py").write_text("def list_view(request):\n    pass\n")
        (self.project / "src" / "utils.py").write_text("async def fetch_data(url):\n    pass\n")
        self.files = [Path("src/models.py"), Path("src/views.py"), Path("src/utils.py")]

    def test_build_returns_string(self) -> None:
        result = anatomy.build(self.project, self.files)
        self.assertIsInstance(result, str)

    def test_detects_classes(self) -> None:
        result = anatomy.build(self.project, self.files)
        self.assertIn("User", result)
        self.assertIn("Order", result)

    def test_detects_functions(self) -> None:
        result = anatomy.build(self.project, self.files)
        self.assertIn("list_view", result)

    def test_detects_async_functions(self) -> None:
        result = anatomy.build(self.project, self.files)
        self.assertIn("fetch_data", result)

    def test_includes_file_tree(self) -> None:
        result = anatomy.build(self.project, self.files)
        self.assertIn("src/", result)

    def test_empty_files_graceful(self) -> None:
        result = anatomy.build(self.project, [])
        self.assertIn("File Tree", result)

    def test_single_root_file(self) -> None:
        (self.project / "app.py").write_text("def main():\n    pass\n")
        result = anatomy.build(self.project, [Path("app.py")])
        self.assertIn("./", result)
        self.assertIn("app.py", result)


class TestAnatomyJS(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "index.js").write_text("export function hello() {}\nclass App {}\n")
        self.files = [Path("index.js")]

    def test_detects_js(self) -> None:
        result = anatomy.build(self.project, self.files)
        self.assertIn("hello", result)
        self.assertIn("App", result)


class TestAnatomyGo(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "main.go").write_text("package main\nfunc main() {}\nfunc helper() {}\ntype Config struct {}\n")
        self.files = [Path("main.go")]

    def test_detects_go(self) -> None:
        result = anatomy.build(self.project, self.files)
        self.assertIn("main", result)
        self.assertIn("Config", result)


class TestAnatomyRust(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "lib.rs").write_text("pub fn init() {}\npub struct App {}\npub trait Runner {}\n")
        self.files = [Path("lib.rs")]

    def test_detects_rust(self) -> None:
        result = anatomy.build(self.project, self.files)
        self.assertIn("init", result)
        self.assertIn("App", result)
        self.assertIn("Runner", result)


if __name__ == "__main__":
    unittest.main()
