"""Tests for memory.conventions — manifest parsing."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opencode_router.memory import conventions


class TestConventionsPython(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n\n'
            '[project]\nname = "myapp"\ndependencies = ["django", "pydantic"]\n\n'
            '[project.optional-dependencies]\ndev = ["pytest", "ruff"]\n\n'
            '[tool.ruff]\nline-length = 100\n'
        )
        (self.project / "src").mkdir()
        (self.project / "src" / "main.py").write_text("print('hello')")
        self.files = [Path("pyproject.toml"), Path("src/main.py")]

    def test_detects_python(self) -> None:
        result = conventions.build(self.project, self.files)
        self.assertIn("Python", result)

    def test_detects_django(self) -> None:
        result = conventions.build(self.project, self.files)
        self.assertIn("Django", result)

    def test_detects_pytest(self) -> None:
        result = conventions.build(self.project, self.files)
        self.assertIn("pytest", result)

    def test_detects_ruff_with_line_length(self) -> None:
        result = conventions.build(self.project, self.files)
        self.assertIn("Ruff", result)
        self.assertIn("100", result)


class TestConventionsNode(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "package.json").write_text(
            json.dumps({
                "name": "myapp",
                "scripts": {"build": "next build", "test": "jest --coverage"},
                "dependencies": {"next": "^14", "react": "^18"},
                "devDependencies": {"typescript": "^5", "prettier": "^3"},
            })
        )
        (self.project / "src" / "index.ts").mkdir(parents=True)
        self.files = [Path("package.json"), Path("src/index.ts")]

    def test_detects_nextjs(self) -> None:
        result = conventions.build(self.project, self.files)
        self.assertIn("Next.js", result)

    def test_detects_typescript(self) -> None:
        result = conventions.build(self.project, self.files)
        self.assertIn("TypeScript", result)

    def test_detects_jest(self) -> None:
        result = conventions.build(self.project, self.files)
        self.assertIn("Jest", result)


class TestConventionsCI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        wf_dir = self.project / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        wf_dir.joinpath("ci.yml").write_text("jobs:\n  test:\n    steps:\n      - run: npm test\n")
        (self.project / "src" / "app.py").mkdir(parents=True)
        self.files = [Path(".github/workflows/ci.yml"), Path("src/app.py")]

    def test_detects_ci_workflow(self) -> None:
        result = conventions.build(self.project, self.files)
        self.assertIn("CI/CD", result)
        self.assertIn("ci.yml", result)


if __name__ == "__main__":
    unittest.main()
