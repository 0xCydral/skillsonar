"""Walk project files for memory building.

Prefer git ls-files when available (respects .gitignore for free).
Fall back to os.walk with a built-in deny list.
"""

from __future__ import annotations

import os
from pathlib import Path

from .storage import is_denied


def list_files(project: Path) -> list[Path]:
    """Return relative file paths suitable for anatomy building."""
    git_files = _git_list_files(project)
    if git_files is not None:
        return git_files
    return _walk_files(project)


def _git_list_files(project: Path) -> list[Path] | None:
    try:
        import subprocess as sp

        result = sp.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        files: list[Path] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            fpath = project / line
            if fpath.is_file() and not _has_denied_component(fpath):
                files.append(Path(line))
        return files
    except (FileNotFoundError, OSError, sp.TimeoutExpired):
        return None


def _walk_files(project: Path) -> list[Path]:
    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(str(project)):
        dirnames[:] = [d for d in dirnames if not is_denied(d)]
        dirnames.sort()
        root = Path(dirpath)
        for fname in sorted(filenames):
            if is_denied(fname):
                continue
            fpath = root / fname
            if fpath.is_file():
                paths.append(fpath.relative_to(project))
    return paths


def _has_denied_component(path: Path) -> bool:
    for part in path.parts:
        if is_denied(part):
            return True
    return False
