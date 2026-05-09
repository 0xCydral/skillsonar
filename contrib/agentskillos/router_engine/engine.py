"""
Router engine for AgentSkillOS — OpenCode edition.

Replaces generic skill execution with opencode-router's agent dispatch:
  1. Receives a task from the AgentSkillOS DAG pipeline.
  2. Routes it via `opencode-router route` to find the best specialist agent.
  3. Loads that agent's system prompt + model from ~/.config/opencode/.
  4. Executes the task via `opencode run` (headless) with the agent's model
     and expertise injected.

Zero Claude SDK dependencies. Uses OpenCode for all execution.

Install:
    bash contrib/agentskillos/install.sh

Requires:
    - AgentSkillOS installed (for the engine protocol + registry)
    - opencode CLI on PATH
    - opencode-router installed and on PATH
    - ~/.config/opencode/agents/ populated with specialist agents
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Optional

from loguru import logger as _logger
from logging_config import add_file_sink, map_level
from orchestrator.base import EngineMeta, EngineRequest, ExecutionResult
from orchestrator.registry import register_engine
from orchestrator.runtime.run_context import RunContext

UI_CONTRIBUTION = {
    "id": "router",
    "partials": {"execute": "modules/orchestrator_direct/direct-execute.html"},
    "scripts": ["modules/orchestrator_direct/direct-execute.js"],
    "modals": ["modules/orchestrator_dag/node-log-modal.html"],
}

AGENTS_DIR = Path.home() / ".config" / "opencode" / "agents"
CONFIG_FILE = Path.home() / ".config" / "opencode" / "opencode.json"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> str:
    m = _FRONTMATTER_RE.match(text)
    return text[m.end() :] if m else text


def _load_agent(name: str) -> dict | None:
    """Load an agent's prompt and model from the filesystem."""
    path = AGENTS_DIR / f"{name}.md"
    if not path.exists():
        return None
    prompt = _parse_frontmatter(path.read_text(encoding="utf-8")).strip()
    model = None
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        model = cfg.get("agent", {}).get(name, {}).get("model")
    except (json.JSONDecodeError, OSError):
        pass
    return {"name": name, "prompt": prompt, "model": model}


def _route_task(task: str) -> dict:
    """Call opencode-router to find the best agent."""
    try:
        result = subprocess.run(
            ["opencode-router", "route", "--top-1", "--json", task],
            capture_output=True, text=True, timeout=30,
            env={**os.environ},
        )
        if result.returncode != 0:
            return {"name": "unknown", "error": result.stderr.strip()}
        data = json.loads(result.stdout)
        results = data.get("results", [])
        return results[0] if results else {"name": "unknown", "error": "no match"}
    except subprocess.TimeoutExpired:
        return {"name": "unknown", "error": "routing timed out"}
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return {"name": "unknown", "error": str(e)}


def _build_prompt(agent_name: str, agent_prompt: str, task: str) -> str:
    brief = agent_prompt
    if len(brief) > 1500:
        cutoff = brief.rfind("\n\n", 1000, 1500)
        brief = brief[:cutoff] if cutoff != -1 else brief[:1500]
    return (
        f"You are the **{agent_name}** specialist.\n\n"
        f"Your expertise:\n{brief}\n\n"
        f"---\n\nTASK:\n{task}\n\n"
        "Complete this task thoroughly. Save deliverables to appropriate "
        "file paths in the project."
    )


async def _run_opencode(
    prompt: str, *, model: str | None, cwd: str, timeout: int = 600,
) -> tuple[str, int]:
    cmd = ["opencode", "run", "--format", "json"]
    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)

    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ},
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        return "Execution timed out", -1

    text = stdout.decode("utf-8", errors="replace")
    if not text and stderr:
        text = stderr.decode("utf-8", errors="replace")
    return text, proc.returncode


@register_engine("router")
class RouterEngine:
    """Dispatch DAG nodes to specialist OpenCode agents via opencode-router."""

    ui_contribution = UI_CONTRIBUTION
    meta = EngineMeta(
        label="OpenCode Router",
        description=(
            "Routes each task to the best specialist agent from your OpenCode "
            "catalog, then executes with that agent's model + expertise via "
            "`opencode run`."
        ),
        folder_mode="router",
        aliases=("agent-router", "specialist", "opencode-agent"),
    )

    @classmethod
    def create(cls, *, run_context, log_callback=None, **kw):
        return cls(run_context=run_context, log_callback=log_callback)

    def __init__(
        self,
        run_context: RunContext,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.run_context = run_context
        self.log_callback = log_callback

    async def run(self, request: EngineRequest) -> ExecutionResult:
        viz = request.visualizer
        rc = self.run_context

        # 1. Route
        route = _route_task(request.task)
        agent_name = route.get("name", "unknown")
        agent_desc = route.get("description", "")
        score = route.get("score", 0)

        # 2. Load agent
        agent = _load_agent(agent_name) if agent_name != "unknown" else None

        if viz:
            node = {
                "id": agent_name, "name": agent_name, "type": "primary",
                "depends_on": [],
                "purpose": f"→ {agent_name} (score={score:.2f})",
                "outputs_summary": f"{agent_name}: {agent_desc[:120]}",
            }
            await viz.set_nodes([node], [[node["id"]]])
            await viz.update_status(agent_name, "running")

        # 3. Workspace
        await rc.async_setup([], rc.run_dir, copy_all=False)
        if request.files:
            await rc.async_copy_files(request.files)
        await rc.async_save_meta(request.task, "router", [agent_name])

        cwd = str(rc.exec_dir)

        if agent:
            prompt = _build_prompt(agent["name"], agent["prompt"], request.task)
            model = agent.get("model")
        else:
            prompt = request.task
            model = None

        # 4. Log
        sk = f"router-{rc.run_id}"
        sid = add_file_sink(rc.get_log_path("execution"), filter_key=sk)
        elog = _logger.bind(sink_key=sk)
        elog.info(f"Agent: {agent_name} | Model: {model or 'default'}")

        def _log_cb(msg: str, lvl: str = "info") -> None:
            elog.log(map_level(lvl), msg)
            if self.log_callback:
                self.log_callback(msg, lvl)

        try:
            _log_cb(
                f"opencode run --model {model or 'default'} → {agent_name}",
                "send",
            )
            output, exit_code = await _run_opencode(
                prompt, model=model, cwd=cwd,
            )
            _log_cb(output[:2000], "recv")

            status = "completed" if exit_code == 0 else "failed"
            result = ExecutionResult(
                status=status,
                summary=output[:2000] if output else "(no output)",
                metadata={
                    "agent": agent_name, "model": model,
                    "route_score": score, "exit_code": exit_code,
                },
            )
            elog.success(f"Status: {status}")
            await rc.async_save_result(
                {"status": status, "agent": agent_name, "model": model,
                 "exit_code": exit_code},
            )
            if viz:
                await viz.update_status(agent_name, status)
            return result
        except Exception as exc:
            elog.error(f"Failed: {exc}")
            if viz:
                await viz.update_status(agent_name, "failed")
            return ExecutionResult(
                status="failed", error=str(exc),
                metadata={"agent": agent_name},
            )
        finally:
            await rc.async_finalize()
            _logger.remove(sid)
