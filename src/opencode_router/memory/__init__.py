"""Project memory — persistent codebase context for subagent dispatch.

Public API:
    inject(task, project) -> str       # Build preamble for agent dispatch
    rebuild(project, *, force) -> dict # Build/update memory.md
    clear(project) -> None             # Remove .opencode-router/
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import anatomy, conventions, episodic, log, retrieval, storage, trigger


def inject(task: str, project: Path | None = None) -> str:
    """Return the memory preamble for a task dispatch.

    Small projects (< ~3k tokens) get verbatim injection.
    Large projects get header + top-5 retrieval chunks.
    """
    proj = project or storage.project_root()
    if proj is None or not storage.memory_file(proj).exists():
        return ""
    return retrieval.inject(task, proj)


def record(
    agent: str,
    task: str,
    files_touched: list[str],
    summary: str,
    duration_seconds: float = 0.0,
    *,
    project: Path | None = None,
) -> Path | None:
    """Record a completed subagent dispatch for future distillation."""
    proj = project or storage.project_root()
    if proj is None:
        return None
    return log.record_entry(
        proj,
        agent=agent,
        task=task,
        files_touched=files_touched,
        summary=summary,
        duration_seconds=duration_seconds,
    )


def rebuild(project: Path | None = None, *, force: bool = False) -> dict:
    """Build or refresh project memory. Returns summary dict."""
    proj = project or storage.project_root()
    if proj is None:
        return {"error": "no project found", "project": str(project or Path.cwd())}

    if not trigger.should_rebuild(proj, force=force):
        return {"status": "skipped", "reason": "no changes", "project": str(proj)}

    storage.ensure(proj)
    files = _walk(proj)

    anat = anatomy.build(proj, files)
    conv = conventions.build(proj, files)

    # Distill new log entries into episodic section
    try:
        distilled = episodic.distill(proj)
        epis = distilled if distilled else _read_existing_episodic(proj)
        if distilled:
            _archive_processed(proj)
    except Exception:
        epis = _read_existing_episodic(proj)
    user_notes = _read_user_notes(proj)

    header = (
        f"# Project Memory\n"
        f"_Last built: {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z_\n\n"
    )
    content = header + "## Anatomy\n\n" + anat + "\n\n## Conventions\n\n" + conv

    if epis:
        content += "\n\n" + epis

    if user_notes:
        content += "\n\n<!-- user-notes -->\n" + user_notes

    content += "\n"

    storage.memory_file(proj).write_text(content, encoding="utf-8")

    # Build retrieval index for large projects
    try:
        retrieval.build_index(proj)
    except Exception:
        pass

    state = trigger.capture_snapshot(proj)
    state["last_build"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    storage.write_state(proj, state)

    return {
        "status": "built",
        "project": str(proj),
        "files_tracked": len(files),
        "size_bytes": storage.memory_file(proj).stat().st_size,
    }


def clear(project: Path | None = None) -> None:
    """Remove .opencode-router/ from the project directory."""
    proj = project or storage.project_root()
    if proj is None:
        return
    d = storage.memory_dir(proj)
    if d.exists():
        shutil.rmtree(d)


# ---------------------------------------------------------------- internals


def _walk(project: Path) -> list[Path]:
    from . import walk

    return walk.list_files(project)


def _read_header(project: Path) -> str:
    path = storage.memory_file(project)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    split = text.split("<!-- user-notes -->")
    return split[0].strip()


def _read_episodic(project: Path) -> str:
    path = storage.memory_file(project)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    marker = "## Episodic"
    idx = text.find(marker)
    if idx == -1:
        return ""
    rest = text[idx:]
    end = rest.find("\n## ", 2)
    if end > 0:
        return rest[:end].strip()
    un = rest.find("<!-- user-notes -->")
    if un > 0:
        return rest[:un].strip()
    return rest.strip()


def _read_existing_episodic(project: Path) -> str:
    path = storage.memory_file(project)
    if not path.exists():
        return ""
    return _read_episodic(project)


def _archive_processed(project: Path) -> None:
    entries = log.read_entries(project)
    if not entries:
        return
    # Archive entries that were read (all unarchived ones)
    ld = storage.log_dir(project)
    paths = sorted(ld.glob("*.yaml"))
    log.archive(project, paths)


def _read_user_notes(project: Path) -> str:
    path = storage.memory_file(project)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    marker = "<!-- user-notes -->"
    idx = text.find(marker)
    if idx == -1:
        return ""
    return text[idx + len(marker):].strip()
