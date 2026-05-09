"""
Router engine for AgentSkillOS.

Replaces generic skill execution with opencode-router's agent dispatch:
  1. Receives a task from the AgentSkillOS DAG pipeline.
  2. Routes it via `opencode-router route` to find the best specialist agent.
  3. Loads that agent's system prompt from ~/.config/opencode/agents/<name>.md.
  4. Executes the task via AgentSkillOS's SkillClient (Claude SDK) with the
     agent's expertise injected into the prompt.

Install:
    bash contrib/agentskillos/install.sh

Requires:
    - AgentSkillOS installed and importable
    - opencode-router installed and on PATH
    - ~/.config/opencode/agents/ populated with specialist agents
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Optional

from config import get_config
from loguru import logger as _logger
from logging_config import add_file_sink, map_level
from orchestrator.base import EngineMeta, EngineRequest, ExecutionResult
from orchestrator.registry import register_engine
from orchestrator.runtime.client import SkillClient
from orchestrator.runtime.prompts import build_direct_executor_prompt
from orchestrator.runtime.run_context import RunContext

UI_CONTRIBUTION = {
    "id": "router",
    "partials": {
        "execute": "modules/orchestrator_direct/direct-execute.html",
    },
    "scripts": [
        "modules/orchestrator_direct/direct-execute.js",
    ],
    "modals": [
        "modules/orchestrator_dag/node-log-modal.html",
    ],
}

AGENTS_DIR = Path.home() / ".config" / "opencode" / "agents"
ROUTE_CMD = ["opencode-router", "route", "--top-1", "--json"]


def _parse_frontmatter(text: str) -> str:
    """Extract the body content after YAML frontmatter."""
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1 :])
    return text


def _load_agent_prompt(name: str) -> str | None:
    """Load an agent's system prompt from its .md file."""
    path = AGENTS_DIR / f"{name}.md"
    if not path.exists():
        return None
    return _parse_frontmatter(path.read_text(encoding="utf-8"))


def _route_task(task: str) -> dict:
    """Call opencode-router to find the best agent for a task.

    Returns a dict with keys: name, score, description, mode.
    """
    try:
        result = subprocess.run(
            [*ROUTE_CMD, task],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ},
        )
        if result.returncode != 0:
            return {"name": "unknown", "error": result.stderr.strip()}
        data = json.loads(result.stdout)
        results = data.get("results", [])
        if not results:
            return {"name": "unknown", "error": "no match found"}
        return results[0]
    except subprocess.TimeoutExpired:
        return {"name": "unknown", "error": "routing timed out"}
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return {"name": "unknown", "error": str(e)}


def _build_agent_task(agent_name: str, agent_prompt: str, task: str) -> str:
    """Build the task description that includes the agent's expertise."""
    brief = agent_prompt.strip()
    if len(brief) > 1200:
        cutoff = brief.rfind("\n\n", 800, 1200)
        brief = brief[:cutoff] if cutoff != -1 else brief[:1200]
    return (
        f"You are acting as the **{agent_name}** specialist.\n\n"
        f"Your expertise and responsibilities:\n{brief}\n\n"
        "---\n\n"
        f"TASK: {task}\n\n"
        "Apply your specialist knowledge to complete this task. "
        "Save deliverables to appropriate file paths in the project."
    )


@register_engine("router")
class RouterEngine:
    """Dispatch each DAG node to the best specialist agent from the
    opencode-router catalog, then execute with that agent's expertise."""

    ui_contribution = UI_CONTRIBUTION
    meta = EngineMeta(
        label="Router (Agent Dispatch)",
        description=(
            "Routes each task to the best specialist agent from a 230+ "
            "catalog using local semantic search + LLM rerank, then executes "
            "with that agent's domain expertise."
        ),
        folder_mode="router",
        aliases=("agent-router", "specialist"),
    )

    @classmethod
    def create(cls, *, run_context, log_callback=None, allowed_tools=None, **kw):
        return cls(
            run_context=run_context,
            log_callback=log_callback,
            allowed_tools=allowed_tools,
        )

    def __init__(
        self,
        run_context: RunContext,
        log_callback: Optional[Callable[[str, str], None]] = None,
        allowed_tools: Optional[list[str]] = None,
    ):
        self.run_context = run_context
        self.log_callback = log_callback
        self.allowed_tools = allowed_tools
        cfg = get_config()
        self._runtime = cfg.orchestrator_config("no-skill").runtime

    async def run(self, request: EngineRequest) -> ExecutionResult:
        viz = request.visualizer

        # 1. Route the task to find the best agent
        route = _route_task(request.task)
        agent_name = route.get("name", "unknown")
        agent_desc = route.get("description", "")

        if viz:
            auto_node = {
                "id": agent_name,
                "name": agent_name,
                "type": "primary",
                "depends_on": [],
                "purpose": f"Dispatched to {agent_name} — {agent_desc[:120]}",
                "outputs_summary": f"Work done by the {agent_name} specialist",
            }
            await viz.set_nodes([auto_node], [[auto_node["id"]]])
            await viz.update_status(agent_name, "running")

        # 2. Load the agent's system prompt
        agent_prompt = (
            _load_agent_prompt(agent_name) if agent_name != "unknown" else None
        )

        # 3. Execute
        result = await self._execute(
            task=request.task,
            files=request.files,
            agent_name=agent_name,
            agent_prompt=agent_prompt,
        )

        if viz:
            status = "completed" if result.status == "completed" else "failed"
            await viz.update_status(agent_name, status)

        return result

    async def _execute(
        self,
        task: str,
        files: Optional[list[str]],
        agent_name: str,
        agent_prompt: Optional[str],
    ) -> ExecutionResult:
        run_context = self.run_context

        await run_context.async_setup([], run_context.run_dir, copy_all=False)
        if files:
            await run_context.async_copy_files(files)
        await run_context.async_save_meta(task, "router", [agent_name])

        cwd = str(run_context.exec_dir)
        output_dir = run_context.workspace_dir

        if agent_prompt:
            prompt = _build_agent_task(agent_name, agent_prompt, task)
        else:
            prompt = build_direct_executor_prompt(
                task=task,
                output_dir=str(output_dir),
                working_dir=cwd,
            )

        sink_key = f"router-{run_context.run_id}"
        sink_id = add_file_sink(
            run_context.get_log_path("execution"), filter_key=sink_key
        )
        execution_logger = _logger.bind(sink_key=sink_key)
        execution_logger.info(
            f"{'='*60}\nTask: router dispatch → {agent_name}\n{'='*60}"
        )
        execution_logger.info(f"Agent: {agent_name}")

        def _log_callback(message: str, level: str = "info") -> None:
            execution_logger.log(map_level(level), message)
            if self.log_callback:
                self.log_callback(message, level)

        try:
            client_kwargs = {
                "session_id": f"router-{run_context.run_id}",
                "cwd": cwd,
                "log_callback": _log_callback,
                "model": self._runtime.model,
            }
            if self.allowed_tools is not None:
                client_kwargs["allowed_tools"] = self.allowed_tools

            async with SkillClient(**client_kwargs) as client:
                coro = client.execute(prompt)
                if self._runtime.execution_timeout > 0:
                    response = await asyncio.wait_for(
                        coro, timeout=self._runtime.execution_timeout
                    )
                else:
                    response = await coro

                sdk_metrics = client.last_result_metrics
                metrics_dict = sdk_metrics.to_dict() if sdk_metrics else None

                max_len = self._runtime.summary_max_length
                result = ExecutionResult(
                    status="completed",
                    summary=response[:max_len] if response else "",
                    metadata={
                        "response": response,
                        "sdk_metrics": metrics_dict,
                        "agent": agent_name,
                        "agent_prompt_loaded": agent_prompt is not None,
                    },
                )

            execution_logger.success(f"Status: {result.status}")

            await run_context.async_save_result(
                {
                    "status": result.status,
                    "agent": agent_name,
                    "response": response,
                    "sdk_metrics": metrics_dict,
                }
            )

            return result
        finally:
            await run_context.async_finalize()
            _logger.remove(sink_id)
