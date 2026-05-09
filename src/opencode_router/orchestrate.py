"""Multi-step task orchestration — AgentSkillOS skill discovery + opencode-router agent dispatch + DAG planning.

Usage:
    opencode-router orchestrate "build a bug diagnosis report"
    opencode-router orchestrate --json "create a feature PRD"
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from . import index, ollama

AGENTSKILLOS_SRC: Optional[Path] = None
for candidate in [
    Path.home() / "AgentSkillOS" / "src",
    Path.home() / "agent-skillos" / "src",
]:
    if candidate.is_dir():
        AGENTSKILLOS_SRC = candidate
        break

PLANNER_PROMPT = """You are a workflow planner. Given a task and available agents, produce a DAG execution plan.

## Available agents
{agents_block}

## Output format
```json
{{
  "plan": {{
    "name": "Plan name",
    "description": "Strategy description",
    "steps": [
      {{
        "id": "step-1",
        "name": "Human-readable step name",
        "agent": "agent-name-from-list",
        "depends_on": [],
        "purpose": "What this step does",
        "task": "Specific instructions for the agent, self-contained"
      }},
      {{
        "id": "step-2",
        "name": "Another step",
        "agent": "another-agent",
        "depends_on": ["step-1"],
        "purpose": "What this step does, referencing outputs from step-1",
        "task": "Self-contained instructions referencing step-1 outputs"
      }}
    ]
  }}
}}
```

## Rules
1. Each step MUST use an agent from the available agents list exactly.
2. Dependencies: reference step IDs in depends_on. Steps with no deps run first.
3. The task field must be complete and self-contained per agent.
4. Prefer 2-5 steps. Don't over-decompose.
5. Output ONLY the JSON block, no other text."""


def _discover_skills(task: str) -> list[str]:
    """Try AgentSkillOS skill discovery. Returns [] if unavailable."""
    if AGENTSKILLOS_SRC is None:
        return []
    try:
        # Load env vars from AgentSkillOS .env so its config module picks them up
        env_path = AGENTSKILLOS_SRC.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

        _saved = sys.path.copy()
        sys.path.insert(0, str(AGENTSKILLOS_SRC))
        from workflow.service import discover_skills  # type: ignore[import-untyped]

        result = discover_skills(task, skill_group="skill_seeds")
        sys.path = _saved
        return result
    except Exception as exc:
        if os.environ.get("OPENCODE_ROUTER_DEBUG"):
            print(f"[orchestrate] skill discovery failed: {exc}", file=sys.stderr)
        return []


def _plan(task: str, agents_block: str) -> dict:
    prompt = PLANNER_PROMPT.format(agents_block=agents_block)
    prompt += f"\n\nTASK: {task}\n\nPLAN:"

    raw = ollama.generate(
        prompt, model=ollama.DEFAULT_RERANK_MODEL, json_format=True,
        think=False, temperature=0.0, num_predict=500,
    )
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        brace = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace:
            return json.loads(brace.group(0))
        return {"error": "failed to parse plan", "raw": raw[:500]}


def orchestrate(task: str, *, top_k: int = 5) -> dict:
    """Produce a complete execution plan for a task.

    Returns {task, skills, agents, plan: {name, description, steps: [...]}}.
    """
    # 1. AgentSkillOS skill discovery (optional)
    skills = _discover_skills(task)

    # 2. Route to find candidate agents
    candidates = index.search(task, k=top_k)

    # 3. Build agents block for the planner
    agent_lines = []
    agent_names = []
    for c in candidates:
        agent_lines.append(f"- **{c.name}**: {c.description[:150]}")
        agent_names.append(c.name)

    # Add agents matched from discovered skills
    for skill in skills[:5]:
        sc_list = index.search(skill, k=2)
        for sc in sc_list:
            if sc.name not in agent_names:
                agent_lines.append(
                    f"- **{sc.name}** (via skill '{skill}'): {sc.description[:120]}"
                )
                agent_names.append(sc.name)

    if not agent_lines:
        return {"error": "no agents available", "task": task}

    # 4. Plan the DAG via LLM
    plan = _plan(task, "\n".join(agent_lines))

    return {
        "task": task,
        "skills_discovered": skills[:10],
        "candidate_agents": [
            {"name": c.name, "score": round(c.score, 4), "description": c.description[:120]}
            for c in candidates
        ],
        "plan": plan.get("plan", plan),
    }
