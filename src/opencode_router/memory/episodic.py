"""Distill dispatch logs into an episodic memory section.

Reads log entries, calls the local LLM (qwen3.5:4b) with a tight
JSON-mode prompt, and returns bullet points of reusable patterns,
decisions, and gotchas. Capped at 50 bullets or 5k tokens.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from opencode_router import ollama

from . import log

_MAX_BULLETS = 50
_MAX_TOKENS = 5_000  # ~2.5 words per token for qwen
_MIN_ENTRIES = 5

_DISTILL_PROMPT = """You receive task logs from previous agent runs in a software project.
Extract reusable patterns, decisions, and gotchas for future agents.

Output ONLY a JSON array of strings. Example:
["auth uses JWT in middleware/auth.py", "prefer select_related over prefetch for 1:1"]

Rules:
- Max 10 items, each ≤120 characters.
- Focus on: recurring conventions, decided tradeoffs, non-obvious gotchas.
- Skip: trivia, status updates, "I read X then edited Y" narratives.
- If logs contain no reusable knowledge, output [].
"""


def distill(project: Path) -> str | None:
    """Return an episodic section string, or None if nothing to distill."""
    entries = log.read_entries(project)
    if len(entries) < _MIN_ENTRIES:
        return None

    prompt = _build_prompt(entries)
    raw = ollama.generate(
        prompt,
        model=ollama.DEFAULT_RERANK_MODEL,
        json_format=True,
        think=False,
        temperature=0.0,
        num_predict=300,
        timeout=120,
    )

    bullets = _parse_distill_output(raw)
    if not bullets:
        return None

    return _format_section(bullets)


def estimate_tokens(text: str) -> int:
    """Rough token count: ~2.5 chars per token for English."""
    return len(text) // 3  # conservative


# ---------------------------------------------------------------- internals


def _build_prompt(entries: list[dict]) -> str:
    lines: list[str] = [_DISTILL_PROMPT, "", "## Log entries", ""]
    for e in entries[:20]:
        lines.append(f"Agent: {e.get('agent', '?')}")
        lines.append(f"Task: {e.get('task', '?')}")
        summary = e.get("summary", "")
        if len(summary) > 300:
            summary = summary[:297] + "..."
        lines.append(f"Summary: {summary}")
        files = e.get("files_touched", [])
        if files:
            lines.append(f"Files: {', '.join(files[:10])}")
        lines.append("")
    return "\n".join(lines)


def _parse_distill_output(raw: str) -> list[str]:
    # Try JSON array first
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(b) for b in parsed if str(b).strip()]
    except json.JSONDecodeError:
        pass

    # Try JSON object — collect from list or string values
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            result: list[str] = []
            for _key, val in obj.items():
                if isinstance(val, list):
                    result.extend(str(b) for b in val)
                elif isinstance(val, str) and val.strip():
                    result.append(val.strip())
            if result:
                return result
        except json.JSONDecodeError:
            pass

    # Fallback: extract bullet-like lines
    bullets = re.findall(r'^[-*]\s*(.*)', raw, re.MULTILINE)
    return [b.strip() for b in bullets if len(b.strip()) > 10][:10]


def _format_section(bullets: list[str]) -> str:
    limited = bullets[:_MAX_BULLETS]
    total = 0
    kept: list[str] = []
    for b in limited:
        t = estimate_tokens(b)
        if total + t > _MAX_TOKENS:
            break
        kept.append(b)
        total += t

    lines = ["## Episodic", ""]
    for b in kept:
        lines.append(f"- {b}")
    return "\n".join(lines) + "\n"
