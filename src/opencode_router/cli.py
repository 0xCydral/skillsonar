"""Single CLI entry point for opencode-router."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, index, memory, ollama, opencode, orchestrate, profile, route
from .paths import AGENTS_DIR, CONFIG_FILE, INDEX_FILE, PROFILE_FILE

# ---------------------------------------------------------------------- helpers


def _print_route_table(result: route.RouteResult, top: int) -> None:
    print(f'\nQuery: "{result.query}"')
    if result.rerank_note:
        print(f"({result.rerank_note})")
    print()
    print(f'{"#":<3} {"score":<7} {"agent":<40} description')
    print("-" * 110)
    for i, c in enumerate(result.candidates[:top], 1):
        desc = c.description
        if len(desc) > 60:
            desc = desc[:57] + "..."
        marker = "★" if i == 1 else " "
        print(f'{marker}{i:<2} {c.score:<7.4f} {c.name:<40} {desc}')
    if result.candidates:
        print(f'\n→ Recommended: /agent {result.candidates[0].name}')


# ---------------------------------------------------------------------- commands


def cmd_route(args: argparse.Namespace) -> int:
    query = " ".join(args.query).strip()
    if not query:
        print("Error: query cannot be empty", file=sys.stderr)
        return 2
    result = route.route(query, shortlist=args.shortlist, rerank=args.rerank)
    if args.top_one:
        if not result.candidates:
            return 1
        print(result.candidates[0].name)
        return 0
    if args.json:
        payload = {
            "query": result.query,
            "reranked": result.reranked,
            "rerank_note": result.rerank_note,
            "results": [
                {
                    "name": c.name,
                    "score": round(c.score, 4),
                    "description": c.description,
                    "mode": c.mode,
                }
                for c in result.candidates[: args.top]
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    _print_route_table(result, args.top)
    return 0


def cmd_index_build(_args: argparse.Namespace) -> int:
    n = index.build()
    return 0 if n > 0 else 1


def cmd_register(_args: argparse.Namespace) -> int:
    n, backup = opencode.register()
    print(f"Registered {n} agents into {CONFIG_FILE}")
    if backup:
        print(f"Backup: {backup}")
    return 0


def cmd_models_apply(args: argparse.Namespace) -> int:
    summary = opencode.apply_models(profile_name=args.profile)
    print(f"Profile: {summary['profile']}")
    print(f"Updated {summary['changed']} of {summary['total']} agents.\n")
    print("Bucket distribution:")
    for b, n in sorted(summary["buckets"].items(), key=lambda x: -x[1]):
        print(f"  {n:>3}  {b}")
    print("\nModel distribution:")
    for m, n in sorted(summary["models"].items(), key=lambda x: -x[1]):
        print(f"  {n:>3}  {m}")
    return 0


def cmd_init(_args: argparse.Namespace) -> int:
    print("→ Registering agents from", AGENTS_DIR)
    n, backup = opencode.register()
    print(f"  Registered {n} agents")
    if backup:
        print(f"  Backup: {backup}")

    print("\n→ Applying model assignments")
    summary = opencode.apply_models()
    print(f"  Profile: {summary['profile']} — updated {summary['changed']}/{summary['total']}")

    print("\n→ Building embedding index")
    n_idx = index.build(verbose=False)
    print(f"  Indexed {n_idx} agents → {INDEX_FILE}")

    print("\n✓ Done. Open opencode and try a real task.")
    return 0


def cmd_profile_list(_args: argparse.Namespace) -> int:
    data = profile.load()
    profiles = data.get("profiles", {})
    if not profiles:
        print(f"No profiles configured at {PROFILE_FILE}")
        print("Seed one from examples/profiles/, or write your own.")
        return 1
    active = data.get("active")
    for name in sorted(profiles):
        marker = " (active)" if name == active else ""
        desc = profiles[name].get("description", "")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        print(f"  {name}{marker}\n      {desc}")
    return 0


def cmd_profile_current(_args: argparse.Namespace) -> int:
    name = profile.active_name()
    if not name:
        print("No active profile set.")
        return 1
    p = profile.get(name)
    print(name)
    for b in profile.CONVENTIONAL_BUCKETS:
        print(f"  {b:<12} {p.buckets.get(b)}")
    return 0


def cmd_profile_show(args: argparse.Namespace) -> int:
    p = profile.get(args.name)
    print(p.name)
    if p.description:
        print(f"  {p.description}\n")
    for b in profile.CONVENTIONAL_BUCKETS:
        print(f"  {b:<12} {p.buckets.get(b)}")
    return 0


def cmd_profile_set(args: argparse.Namespace) -> int:
    profile.set_active(args.name)
    print(f"Active profile set to: {args.name}")
    if args.no_apply:
        return 0
    print("\nApplying model assignments…")
    return cmd_models_apply(argparse.Namespace(profile=None))


def cmd_orchestrate(args: argparse.Namespace) -> int:
    task = " ".join(args.task).strip()
    if not task:
        print("Error: task cannot be empty", file=sys.stderr)
        return 2
    result = orchestrate.orchestrate(task, top_k=args.top_k)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if "error" not in result else 1


def cmd_doctor(_args: argparse.Namespace) -> int:
    issues: list[str] = []
    ok: list[str] = []

    # OpenCode config
    if CONFIG_FILE.exists():
        ok.append(f"opencode.json found at {CONFIG_FILE}")
    else:
        issues.append(f"opencode.json missing at {CONFIG_FILE}")

    # Agents directory
    if AGENTS_DIR.is_dir():
        n_agents = len(list(AGENTS_DIR.glob("*.md")))
        ok.append(f"agents/ has {n_agents} .md files")
        if n_agents == 0:
            issues.append("No agent .md files yet — write some or import a collection")
    else:
        issues.append(f"agents/ directory missing at {AGENTS_DIR}")

    # Profile
    if PROFILE_FILE.exists():
        active = profile.active_name() or "(none)"
        ok.append(f"profile config: active='{active}'")
        if not active:
            issues.append("No active profile selected")
    else:
        issues.append(f"profile config missing at {PROFILE_FILE} (seed from examples/)")

    # Index
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            ok.append(f"index has {data.get('count', 0)} agents (model={data.get('model')})")
        except Exception as exc:  # noqa: BLE001
            issues.append(f"index file unreadable: {exc}")
    else:
        issues.append(f"index missing at {INDEX_FILE} — run: opencode-router index build")

    # Ollama
    if ollama.is_running():
        ok.append(f"Ollama reachable at {ollama.DEFAULT_URL}")
    else:
        issues.append(f"Ollama not reachable at {ollama.DEFAULT_URL} — start it")

    print("OK:")
    for item in ok:
        print(f"  ✓ {item}")
    if issues:
        print("\nISSUES:")
        for item in issues:
            print(f"  ✗ {item}")
        return 1
    print("\nAll checks passed.")
    return 0


def cmd_memory_show(_args: argparse.Namespace) -> int:
    proj = memory.storage.project_root()
    if proj is None:
        print("No project found. Run from a project directory.", file=sys.stderr)
        return 1
    mem_path = memory.storage.memory_file(proj)
    if not mem_path.exists():
        print("No memory exists yet. Run: opencode-router memory rebuild")
        return 1
    print(mem_path.read_text(encoding="utf-8"))
    return 0


def cmd_memory_rebuild(args: argparse.Namespace) -> int:
    result = memory.rebuild(force=args.force)
    if result.get("status") == "skipped":
        print(f"Skipped: {result.get('reason')}")
        return 0
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1
    size_kb = result.get("size_bytes", 0) / 1024
    print(
        f"Memory built ({size_kb:.1f} KB, "
        f"{result.get('files_tracked', 0)} files tracked) → "
        f"{result['project']}/.opencode-router/memory.md"
    )
    return 0


def cmd_memory_clear(_args: argparse.Namespace) -> int:
    proj = memory.storage.project_root()
    if proj is None:
        print("No project found.", file=sys.stderr)
        return 1
    memory.clear(proj)
    print(f"Removed {proj}/.opencode-router/")
    return 0


def cmd_memory_inject(args: argparse.Namespace) -> int:
    task = " ".join(args.task).strip()
    brief = memory.inject(task)
    if brief:
        print(brief)
    else:
        print("(no memory — rebuild first: opencode-router memory rebuild)")
    return 0


# ---------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencode-router",
        description="Local-first agent routing for OpenCode.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    # init
    p_init = sub.add_parser("init", help="Register agents + apply models + build index")
    p_init.set_defaults(func=cmd_init)

    # register
    p_reg = sub.add_parser("register", help="Populate opencode.json `agent` block from agents/")
    p_reg.set_defaults(func=cmd_register)

    # models
    p_models = sub.add_parser("models", help="Apply role → bucket → model assignments")
    p_models_sub = p_models.add_subparsers(dest="action", required=True)
    p_models_apply = p_models_sub.add_parser("apply", help="Apply current rules + active profile")
    p_models_apply.add_argument("--profile", help="Override the active profile")
    p_models_apply.set_defaults(func=cmd_models_apply)

    # profile
    p_prof = sub.add_parser("profile", help="Manage provider profiles")
    p_prof_sub = p_prof.add_subparsers(dest="action", required=True)
    p_prof_sub.add_parser("list", help="List available profiles").set_defaults(func=cmd_profile_list)
    p_prof_sub.add_parser("current", help="Show active profile").set_defaults(func=cmd_profile_current)
    p_show = p_prof_sub.add_parser("show", help="Show one profile's bucket map")
    p_show.add_argument("name")
    p_show.set_defaults(func=cmd_profile_show)
    p_set = p_prof_sub.add_parser("set", help="Activate a profile (and re-apply models)")
    p_set.add_argument("name")
    p_set.add_argument("--no-apply", action="store_true", help="Don't auto-run models apply")
    p_set.set_defaults(func=cmd_profile_set)

    # index
    p_idx = sub.add_parser("index", help="Manage the embedding index")
    p_idx_sub = p_idx.add_subparsers(dest="action", required=True)
    p_idx_build = p_idx_sub.add_parser("build", help="Re-embed all agents")
    p_idx_build.set_defaults(func=cmd_index_build)

    # route
    p_route = sub.add_parser("route", help="Test the router on a query")
    p_route.add_argument("query", nargs="+")
    p_route.add_argument("--top", type=int, default=5)
    p_route.add_argument("--shortlist", type=int, default=10)
    p_route.add_argument("--no-rerank", dest="rerank", action="store_false")
    p_route.add_argument("--json", action="store_true")
    p_route.add_argument("--top-1", dest="top_one", action="store_true")
    p_route.set_defaults(func=cmd_route)

    # orchestrate
    p_orch = sub.add_parser(
        "orchestrate",
        help="Plan a multi-step DAG for a complex task (AgentSkillOS + agents)",
    )
    p_orch.add_argument("task", nargs="+")
    p_orch.add_argument("--top-k", type=int, default=5)
    p_orch.add_argument("--json", dest="as_json", action="store_true")
    p_orch.set_defaults(func=cmd_orchestrate)

    # memory
    p_mem = sub.add_parser("memory", help="Manage project memory")
    p_mem_sub = p_mem.add_subparsers(dest="action", required=True)
    p_mem_sub.add_parser("show", help="Print memory.md").set_defaults(func=cmd_memory_show)
    p_mem_rebuild = p_mem_sub.add_parser("rebuild", help="Rebuild project memory")
    p_mem_rebuild.add_argument("--force", action="store_true")
    p_mem_rebuild.set_defaults(func=cmd_memory_rebuild)
    p_mem_sub.add_parser("clear", help="Delete .opencode-router/").set_defaults(func=cmd_memory_clear)
    p_mem_inject = p_mem_sub.add_parser("inject", help="Print what would be injected (debug)")
    p_mem_inject.add_argument("task", nargs="+")
    p_mem_inject.set_defaults(func=cmd_memory_inject)

    # doctor
    p_doc = sub.add_parser("doctor", help="Diagnose configuration issues")
    p_doc.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
