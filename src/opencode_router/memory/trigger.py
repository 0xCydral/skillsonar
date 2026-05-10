"""Decide when to rebuild project memory.

Rebuild triggers: no memory yet, file changes, git HEAD moved,
24h elapsed, or explicit force flag.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from . import storage
from . import walk as _walk

_MIN_CHANGED_FILES = 10
_MIN_AGE_SECONDS = 86_400  # 24 hours


def should_rebuild(project: Path, *, force: bool = False) -> bool:
    """Return True if memory should be (re)built."""
    if not storage.memory_file(project).exists():
        return True
    if force:
        return True

    st = storage.read_state(project)
    if not st:
        return True

    if _files_changed(project, st):
        return True
    if _head_changed(project, st):
        return True
    if _too_old(st):
        return True

    return False


def _files_changed(project: Path, st: dict) -> bool:
    last_hash = st.get("file_mtime_hash", "")
    if not last_hash:
        return True
    try:
        current_hash = _mtime_hash(project)
    except OSError:
        return False
    if current_hash != last_hash:
        changed = _count_changed(project, st.get("mtime_snapshot", {}))
        return changed >= _MIN_CHANGED_FILES
    return False


def _head_changed(project: Path, st: dict) -> bool:
    try:
        import subprocess as sp

        result = sp.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return False
        return result.stdout.strip() != st.get("git_head", "")
    except (FileNotFoundError, OSError, sp.TimeoutExpired):
        return False


def _too_old(st: dict) -> bool:
    last_build = st.get("last_build", "")
    if not last_build:
        return True
    try:
        last = datetime.fromisoformat(last_build)
        return (datetime.now(timezone.utc) - last).total_seconds() > _MIN_AGE_SECONDS
    except ValueError:
        return True


def _mtime_hash(project: Path) -> str:
    files = _walk.list_files(project)
    hasher = hashlib.sha256()
    for p in sorted(files):
        fpath = project / p
        if fpath.is_file():
            mtime = os.path.getmtime(str(fpath))
            hasher.update(str(mtime).encode())
    return hasher.hexdigest()


def _count_changed(project: Path, snapshot: dict[str, int]) -> int:
    changed = 0
    for p in _walk.list_files(project):
        fpath = project / p
        if not fpath.is_file():
            continue
        current = os.path.getmtime(str(fpath))
        if snapshot.get(str(p)) != current:
            changed += 1
    return changed


def capture_snapshot(project: Path) -> dict:
    snapshot: dict[str, int] = {}
    for p in _walk.list_files(project):
        fpath = project / p
        if fpath.is_file():
            snapshot[str(p)] = os.path.getmtime(str(fpath))

    head = ""
    try:
        import subprocess as sp

        result = sp.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            head = result.stdout.strip()
    except (FileNotFoundError, OSError, sp.TimeoutExpired):
        pass

    return {
        "file_mtime_hash": _mtime_hash(project),
        "git_head": head,
        "mtime_snapshot": snapshot,
    }
