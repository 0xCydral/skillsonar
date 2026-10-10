"""Scan skill folders into a keyword index and score queries against it.

A skill is a directory holding a SKILL.md with YAML frontmatter (name, description). The index
keeps, per skill, the stemmed token set of its name, description and trigger text. A query is
scored by how many of its tokens a skill contains, with a bonus when a token is in the name.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Iterator
from pathlib import Path

from skillsonar.errors import SkillIndexError
from skillsonar.paths import display

# How much of a frontmatter description the index keeps. Descriptions in the wild run past 1,000
# characters; cutting them early hides the symptoms they list, which are what queries match.
DESC_CAP = 1200
SCAN_BYTES = 4000
BODY_BYTES = 250
INDEX_FILE = "index.json"

STOPWORDS = frozenset(
    "the and for with that this from into what when how why not are was were can has have had "
    "its our out you your any all but use used using get got just does did too very more some "
    "then than them they there their about after before over under again keeps keep".split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_KEY_RE = re.compile(r"^([a-z_]+):\s*(.*)$")
_BLOCK_SCALARS = ("|", ">", "|-", ">-", "|+", ">+")
_FIELDS = ("name", "description", "when_to_use")


def stem(word: str) -> str:
    """Minimal stemmer, applied to skills and queries alike: ing/ed/es/s, then a trailing e."""
    if len(word) >= 5:
        for suffix in ("ing", "ed", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                word = word[: -len(suffix)]
                break
        if word.endswith("e") and len(word) - 1 >= 4:
            word = word[:-1]
    return word


def tokenize(text: str) -> set[str]:
    text = _CAMEL_RE.sub(" ", text).lower()
    return {stem(t) for t in _TOKEN_RE.findall(text) if t not in STOPWORDS}


def split_frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter, body). Both are empty-safe: a file without frontmatter is all body."""
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return text[3:], ""
    return text[3:end], text[end + 4 :]


def parse_frontmatter(text: str) -> dict[str, str]:
    """Read name, description and when_to_use, including `|` and `>` block scalars.

    Indentation is data: an indented `key:` belongs to a nested field and is not top level, and
    a block scalar ends at the next line that starts in column zero.
    """
    lines = split_frontmatter(text)[0].splitlines()
    out: dict[str, str] = {}
    i = 0
    while i < len(lines):
        match = _KEY_RE.match(lines[i])
        i += 1
        if not match or match.group(1) not in _FIELDS:
            continue
        key, value = match.group(1), match.group(2).strip()
        if value in _BLOCK_SCALARS:
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i].strip())
                i += 1
            value = " ".join(part for part in block if part)
        out[key] = value.strip().strip("\"'")
    return out


def find_skill_dirs(root: Path) -> Iterator[Path]:
    """Every directory under root that holds a SKILL.md. Hidden directories are skipped."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d != "node_modules")
        if "SKILL.md" in filenames:
            yield Path(dirpath)


def read_head(path: Path, size: int) -> str:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as handle:
            return handle.read(size)
    except OSError:
        return ""


def make_entry(skill_dir: Path, source: str) -> dict | None:
    text = read_head(skill_dir / "SKILL.md", SCAN_BYTES)
    fields = parse_frontmatter(text)
    name = fields.get("name") or skill_dir.name
    desc = fields.get("description", "")[:DESC_CAP]
    extra = fields.get("when_to_use") or split_frontmatter(text)[1][:BODY_BYTES]
    tokens = tokenize(f"{name} {desc} {extra}")
    if not tokens:
        return None
    return {
        "name": name,
        "source": source,
        "path": str(skill_dir),
        "desc": desc,
        "tokens": sorted(tokens),
    }


def scan(roots: list[Path]) -> list[dict]:
    """Index every skill under the given roots. A skill reached twice is indexed once."""
    entries: list[dict] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        source = display(str(root.resolve()))
        for skill_dir in find_skill_dirs(root):
            resolved = skill_dir.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            entry = make_entry(resolved, source)
            if entry:
                entries.append(entry)
    return entries


def save_index(directory: Path, entries: list[dict]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / INDEX_FILE
    payload = {
        "version": 1,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "count": len(entries),
        "entries": entries,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return target


def load_index(directory: Path) -> dict:
    target = directory / INDEX_FILE
    if not target.is_file():
        raise SkillIndexError(
            f"no index at {target}. Build one first: skillsonar build "
            "(add --path DIR to choose skill folders)"
        )
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SkillIndexError(f"cannot read {target} ({exc}); rebuild with: skillsonar build") from exc


def keyword_rank(entries: list[dict], query: str) -> list[tuple[dict, float]]:
    """Every entry sharing a token with the query, best first. Ties keep index order."""
    terms = tokenize(query)
    scored = []
    for entry in entries:
        score = len(terms & set(entry["tokens"]))
        if score:
            if terms & tokenize(entry["name"]):
                score += 2
            scored.append((entry, float(score)))
    scored.sort(key=lambda pair: -pair[1])
    return scored
