"""Build the Anatomy section of project memory.

Produces a markdown file tree and top-level symbol index by walking
the project and applying regex per detected language. The output is
hint-text for LLM agents, not a compiler-grade analysis.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from . import walk as _walk

# Maps file extension to regex patterns for top-level symbol detection.
# Each pattern has exactly one capturing group: the symbol name.
_SYMBOL_PATTERNS: dict[str, list[tuple[str, str]]] = {
    ".py": [
        ("class", r"^class\s+(\w+)"),
        ("func", r"^(?:async\s+)?def\s+(\w+)"),
    ],
    ".js": [
        ("class", r"^class\s+(\w+)"),
        ("func", r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)"),
        ("arrow", r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\("),
        ("export", r"^export\s+(?:const|let|var)\s+(\w+)"),
    ],
    ".ts": [
        ("class", r"^class\s+(\w+)"),
        ("func", r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)"),
        ("arrow", r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\("),
        ("export", r"^export\s+(?:const|let|var|type|interface)\s+(\w+)"),
    ],
    ".tsx": [
        ("component", r"^(?:export\s+)?(?:function|const)\s+(\w+[A-Z]\w*)"),
        ("export", r"^export\s+(?:const|let|var|type|interface)\s+(\w+)"),
    ],
    ".jsx": [
        ("component", r"^(?:export\s+)?(?:function|const)\s+(\w+[A-Z]\w*)"),
        ("export", r"^export\s+(?:const|let|var)\s+(\w+)"),
    ],
    ".go": [
        ("func", r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)"),
        ("type", r"^type\s+(\w+)"),
    ],
    ".rs": [
        ("fn", r"^(?:pub(?:\s*\(\s*crate\s*\))?\s+)?fn\s+(\w+)"),
        ("struct", r"^(?:pub\s+)?struct\s+(\w+)"),
        ("enum", r"^(?:pub\s+)?enum\s+(\w+)"),
        ("trait", r"^(?:pub\s+)?trait\s+(\w+)"),
    ],
    ".java": [
        ("class", r"^(?:public\s+)?class\s+(\w+)"),
        ("interface", r"^(?:public\s+)?interface\s+(\w+)"),
        ("method", r"^\s*(?:public|private|protected)\s+(?:\w+\s+)?(\w+)\s*\("),
    ],
    ".rb": [
        ("class", r"^class\s+(\w+)"),
        ("module", r"^module\s+(\w+)"),
        ("def", r"^\s*def\s+(\w+)"),
    ],
    ".tf": [
        ("resource", r'^resource\s+"([^"]+)"'),
        ("module", r'^module\s+"([^"]+)"'),
    ],
}


def build(project: Path, files: list[Path] | None = None) -> str:
    """Return the ## Anatomy markdown section."""
    if files is None:
        files = _walk.list_files(project)

    lines: list[str] = []
    _append_tree(lines, files)
    lines.append("")
    _append_symbols(lines, project, files)
    return "\n".join(lines)


# ---------------------------------------------------------------- tree


def _append_tree(lines: list[str], files: list[Path]) -> None:
    """Depth-2 file tree, files grouped under their directory."""
    by_dir: dict[str, list[str]] = defaultdict(list)
    for p in files:
        parts = p.parts
        if len(parts) == 1:
            by_dir["."].append(parts[0])
        else:
            by_dir[str(Path(*parts[:-1]))].append(parts[-1])

    lines.append("### File Tree")
    for d in sorted(by_dir):
        prefix = "  " if d == "." else ""
        lines.append(f"{prefix}{d}/")
        for fname in sorted(set(by_dir[d]))[:40]:
            lines.append(f"{prefix}  {fname}")
        shown = len(by_dir[d])
        if shown > 40:
            lines.append(f"{prefix}  ... +{shown - 40} more")


# ---------------------------------------------------------------- symbols


def _append_symbols(lines: list[str], project: Path, files: list[Path]) -> None:
    lines.append("### Key Symbols")
    found_any = False
    for p in files:
        ext = p.suffix
        patterns = _SYMBOL_PATTERNS.get(ext)
        if not patterns:
            continue
        try:
            text = _read_first_n(project / p, 200)
        except (OSError, UnicodeDecodeError):
            continue
        symbols: list[str] = []
        for _kind, pat in patterns:
            for m in re.finditer(pat, text, re.MULTILINE):
                symbols.append(m.group(1))

        if symbols:
            found_any = True
            lines.append(f"  {p}: {', '.join(symbols[:10])}")
    if not found_any:
        lines.append("  _(no top-level symbols detected)_")


def _read_first_n(path: Path, n: int) -> str:
    """Read first n lines of a file, ignoring binary content."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""
