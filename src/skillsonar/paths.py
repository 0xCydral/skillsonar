"""Where skills are read from and where the index is stored."""

from __future__ import annotations

import os
from pathlib import Path


def cache_dir() -> Path:
    """User cache directory for the index: LOCALAPPDATA on Windows, XDG cache elsewhere."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "skillsonar"


def default_sources(cwd: Path | None = None) -> list[Path]:
    """Skill folders that exist on this machine, plus the project-local ones under cwd."""
    cwd = cwd or Path.cwd()
    home = Path.home()
    candidates = [
        home / ".claude" / "skills",
        home / ".agents" / "skills",
        home / ".config" / "opencode" / "skills",
        cwd / ".claude" / "skills",
        cwd / ".opencode" / "skills",
    ]
    return [p for p in candidates if p.is_dir()]


def resolve_sources(flags: list[str], env: str | None = None) -> list[Path]:
    """Explicit --path flags and SKILLSONAR_PATHS replace the defaults when either is set."""
    env = os.environ.get("SKILLSONAR_PATHS", "") if env is None else env
    explicit = [Path(p).expanduser() for p in [*flags, *env.split(os.pathsep)] if p]
    return explicit if explicit else default_sources()


def index_dir(flag: str | None) -> Path:
    """The directory holding index.json and embeddings.json."""
    return Path(flag).expanduser() if flag else cache_dir()


def display(path: str, cwd: Path | None = None) -> str:
    """Shorten a path for output: relative to cwd when inside it, ~ for the home directory."""
    p = Path(path)
    cwd = cwd or Path.cwd()
    if p.is_relative_to(cwd):
        return p.relative_to(cwd).as_posix() or "."
    home = Path.home()
    if p.is_relative_to(home):
        return "~/" + p.relative_to(home).as_posix()
    return p.as_posix()
