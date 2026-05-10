"""On-disk layout for project memory.

Creates .opencode-router/ in the project root, manages state.json
and memory.md paths, writes the bundled .gitignore.
"""

from __future__ import annotations

import json
from pathlib import Path

_DIRNAME = ".opencode-router"

DENY_LIST = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "*.pem",
        "*.key",
        "secrets",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        "build",
        ".next",
        ".turbo",
        ".git",
        ".svn",
        ".hg",
        ".opencode-router",
        ".hermes",
        ".wolf",
    }
)

_GITIGNORE_LINES = (
    "# opencode-router project memory\n",
    "log/\n",
    "state.json\n",
    "memory-index.json\n",
    "# memory.md is safe to commit if you want shared agent context\n",
)


def project_root(start_from: Path | None = None) -> Path | None:
    directory = Path(start_from).resolve() if start_from else Path.cwd()
    root = _git_root(directory)
    if root is not None:
        return root
    for ancestor in [directory, *directory.parents]:
        if _has_manifest(ancestor):
            return ancestor
        if ancestor == Path.home():
            break
    return None


def memory_dir(project: Path) -> Path:
    return project / _DIRNAME


def memory_file(project: Path) -> Path:
    return memory_dir(project) / "memory.md"


def state_file(project: Path) -> Path:
    return memory_dir(project) / "state.json"


def log_dir(project: Path) -> Path:
    return memory_dir(project) / "log"


def index_file(project: Path) -> Path:
    return memory_dir(project) / "memory-index.json"


def ensure(project: Path) -> Path:
    d = memory_dir(project)
    d.mkdir(parents=True, exist_ok=True)
    (log_dir(project)).mkdir(exist_ok=True)
    (log_dir(project) / ".archived").mkdir(exist_ok=True)
    _write_gitignore(d)
    return d


def read_state(project: Path) -> dict:
    path = state_file(project)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(project: Path, data: dict) -> None:
    ensure(project)
    state_file(project).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def is_denied(name: str) -> bool:
    if name in DENY_LIST:
        return True
    return any(name.endswith(p[1:]) for p in DENY_LIST if p.startswith("*."))


# ------------------------------------------------------------------ internals


def _git_root(path: Path) -> Path | None:
    try:
        import subprocess as sp

        result = sp.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()).resolve()
    except (FileNotFoundError, OSError, sp.TimeoutExpired):
        pass
    return None


def _has_manifest(directory: Path) -> bool:
    manifests = (
        "package.json",
        "pyproject.toml",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
        "pom.xml",
        "build.gradle",
        "Makefile",
    )
    return any((directory / m).is_file() for m in manifests)


def _write_gitignore(directory: Path) -> None:
    gi = directory / ".gitignore"
    if not gi.exists():
        gi.write_text("".join(_GITIGNORE_LINES), encoding="utf-8")
