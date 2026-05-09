"""Two-stage routing: embedding retrieval + LLM rerank."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from . import index, ollama


@dataclass(frozen=True)
class RouteResult:
    query: str
    candidates: list[index.Hit]
    rerank_note: str | None
    reranked: bool


_RERANK_PROMPT = """\
You route a task to the single best specialist agent from a catalog.

STEP 1 — Identify the task's PRIMARY OUTPUT:
  • Code to write/modify  → engineer/developer/architect
  • Code to review/audit  → reviewer/auditor
  • Written content       → writer/content-creator/strategist
  • Translation           → translator/localization specialist
  • Visual/UI design      → designer/UX specialist
  • Analysis/insight      → analyst/researcher
  • Plan/strategy doc     → strategist/planner/PM

STEP 2 — Identify the DOMAIN (databases, payments, frontend, security, etc.).

STEP 3 — Pick the candidate whose role+domain best matches both.

CRITICAL RULES:
  • Reject candidates that match only by surface keyword.
    (e.g. an "email-intelligence" agent is WRONG for a SQL query about
     a `users.email` column — that is a DATABASE task.)
  • For 'write a blog/social post' style tasks, pick a CONTENT agent,
    NEVER a domain engineer, even if the post is about that engineer's
    domain.
  • Platform-specific integration agents (Feishu, WeChat, Slack, etc.)
    are ONLY for those exact platforms — not generic webhooks.
  • Candidates are sorted by retrieval similarity (highest first). Treat
    rank as a SOFT signal — usually right, override when a lower-ranked
    candidate is a clearly better fit by role+domain.

TASK: {query}

CANDIDATES (sorted by similarity):
{candidates_block}

Respond ONLY with JSON: {{"choice": <candidate_number>, "reason": "<one short sentence>"}}
"""


def _build_prompt(query: str, candidates: list[index.Hit]) -> str:
    lines = []
    for i, c in enumerate(candidates, 1):
        desc = c.description or "(no description)"
        if len(desc) > 240:
            desc = desc[:237] + "..."
        lines.append(f"{i}. [{c.score:.3f}] {c.name} — {desc}")
    return _RERANK_PROMPT.format(query=query, candidates_block="\n".join(lines))


def _parse_choice(raw: str) -> tuple[int | None, str]:
    try:
        parsed = json.loads(raw)
        return int(parsed.get("choice")) - 1, str(parsed.get("reason", "")).strip()
    except (ValueError, TypeError, json.JSONDecodeError):
        match = re.search(r"\d+", raw)
        return (int(match.group(0)) - 1, "") if match else (None, "")


def _rerank(
    query: str,
    candidates: list[index.Hit],
    *,
    model: str | None = None,
) -> tuple[list[index.Hit], str | None]:
    if len(candidates) < 2:
        return candidates, None

    raw = ollama.generate(
        _build_prompt(query, candidates),
        model=model,
        json_format=True,
        think=False,
        temperature=0.0,
        num_predict=120,
    )
    idx_, reason = _parse_choice(raw)
    if idx_ is not None and 0 <= idx_ < len(candidates):
        chosen = candidates[idx_]
        reordered = [chosen] + [c for j, c in enumerate(candidates) if j != idx_]
        note = f"reranked top-{len(candidates)}"
        if reason:
            note += f" — {reason}"
        return reordered, note
    return candidates, f"rerank failed, fell back to cosine: {raw[:80]}"


def route(
    query: str,
    *,
    shortlist: int = 10,
    rerank: bool = True,
) -> RouteResult:
    candidates = index.search(query, k=shortlist)
    if rerank:
        reordered, note = _rerank(query, candidates)
        return RouteResult(
            query=query,
            candidates=reordered,
            rerank_note=note,
            reranked=True,
        )
    return RouteResult(query=query, candidates=candidates, rerank_note=None, reranked=False)
