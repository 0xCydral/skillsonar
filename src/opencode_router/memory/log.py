"""Dispatch log — per-subagent YAML entries for later distillation.

Each entry captures what an agent was asked to do, what files it
touched, and its final summary — observed by the router, not the agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import storage

_HEADER = "# opencode-router dispatch log\n"


def record_entry(
    project: Path,
    *,
    agent: str,
    task: str,
    files_touched: list[str],
    summary: str,
    duration_seconds: float,
) -> Path:
    """Write one YAML log entry. Returns the file path."""
    storage.ensure(project)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    name = f"{ts}-{agent}.yaml"
    path = storage.log_dir(project) / name

    lines = [
        f"agent: {_quote(agent)}",
        f"task: {_quote(task)}",
        f"timestamp: {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z",
        f"duration_seconds: {duration_seconds:.1f}",
        "files_touched:",
    ]
    for f in files_touched[:30]:
        lines.append(f"  - {_quote(f)}")
    lines.append("summary: |")
    for sline in summary.strip().splitlines():
        lines.append(f"  {sline}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def read_entries(project: Path) -> list[dict]:
    """Read all unarchived log entries, newest first."""
    ld = storage.log_dir(project)
    if not ld.is_dir():
        return []

    entries: list[dict] = []
    for path in sorted(ld.glob("*.yaml"), reverse=True):
        entry = _parse_entry(path)
        if entry:
            entries.append(entry)
    return entries


def archive(project: Path, paths: list[Path]) -> int:
    """Move processed entries to .archived/. Returns count moved."""
    archived = storage.log_dir(project) / ".archived"
    archived.mkdir(exist_ok=True)
    count = 0
    for p in paths:
        if p.is_file():
            p.rename(archived / p.name)
            count += 1
    return count


def _parse_entry(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    entry: dict = {"files_touched": [], "summary": ""}
    in_summary = False
    summary_lines: list[str] = []

    for line in text.splitlines():
        if in_summary:
            summary_lines.append(line[2:] if line.startswith("  ") else line)
            continue
        if line.startswith("summary: |"):
            in_summary = True
            continue
        if ": " in line:
            key, val = line.split(": ", 1)
            if key == "files_touched":
                continue
            entry[key] = val.strip()
        elif line.startswith("  - "):
            entry.setdefault("files_touched", []).append(line[4:].strip())

    if summary_lines:
        entry["summary"] = "\n".join(summary_lines).strip()

    if "agent" not in entry:
        return None
    return entry


def _quote(s: str) -> str:
    """YAML-safe quoting when the string needs it."""
    if any(c in s for c in ('"', "'", ":", "#", "\n")):
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s
