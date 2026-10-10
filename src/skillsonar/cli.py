"""Command line: skillsonar build | search | stats | eval."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from skillsonar import __version__
from skillsonar.errors import SkillIndexError, SkillsonarError
from skillsonar.evaluate import evaluate, load_queries
from skillsonar.index import load_index, save_index, scan
from skillsonar.ollama import OllamaClient
from skillsonar.paths import display, index_dir, resolve_sources
from skillsonar.rerank import RerankClient
from skillsonar.search import MODES, POOL, Searcher
from skillsonar.semantic import EMBEDDINGS_FILE, build_embeddings, save_embeddings


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--path", action="append", default=[], metavar="DIR",
                        help="skill folder (repeatable). build indexes it; other commands only "
                             "return skills under it")
    common.add_argument("--index", metavar="DIR",
                        help="directory holding index.json and embeddings.json (default: user cache)")

    parser = argparse.ArgumentParser(prog="skillsonar", description="Find the right agent skill for a task.")
    parser.add_argument("--version", action="version", version=f"skillsonar {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", parents=[common], help="scan skill folders and write the index")
    build.add_argument("--embed", action="store_true", help="also build the embedding index (needs Ollama)")

    search = sub.add_parser("search", parents=[common], help="find skills for a task")
    search.add_argument("query")
    search.add_argument("--top", type=int, default=5)
    search.add_argument("--json", action="store_true")
    mode = search.add_mutually_exclusive_group()
    mode.add_argument("--semantic", action="store_true", help="rank by embedding similarity only")
    mode.add_argument("--hybrid", action="store_true", help="fuse keyword and embedding rankings")
    search.add_argument("--rerank", action="store_true", help="let a chat model reorder the shortlist")
    search.add_argument("--pool", type=int, default=POOL, help="shortlist size handed to --rerank")

    sub.add_parser("stats", parents=[common], help="show what the index holds")

    ev = sub.add_parser("eval", parents=[common], help="recall@k over a JSONL file of queries")
    ev.add_argument("queries", help='JSONL lines like {"query": "...", "expected": ["skill-name"]}')
    ev.add_argument("--k", type=int, default=5)
    ev.add_argument("--mode", choices=MODES, default="keyword")
    return parser


def restriction(flags: list[str]):
    """A filter for entries under the --path folders, or None when no folder was given."""
    roots = [Path(p).expanduser().resolve() for p in flags]
    if not roots:
        return None
    return lambda entry: any(Path(entry["path"]).is_relative_to(r) for r in roots)


def make_searcher(args) -> Searcher:
    directory = index_dir(args.index)
    entries = load_index(directory)["entries"]
    return Searcher(entries, directory, OllamaClient.from_env(), restriction(args.path))


def cmd_build(args) -> int:
    roots = resolve_sources(args.path)
    entries = scan(roots)
    if not entries:
        checked = ", ".join(display(str(r)) for r in roots) or "no default folders exist"
        raise SkillIndexError(f"no skills found (looked in: {checked}). Pass --path DIR.")
    directory = index_dir(args.index)
    target = save_index(directory, entries)
    print(f"indexed {len(entries)} skills from {len(roots)} folder(s) -> {display(str(target.resolve()))}")
    if args.embed:
        client = OllamaClient.from_env()

        def progress(done: int, total: int) -> None:
            print(f"\rembedding {done}/{total}", end="", file=sys.stderr, flush=True)

        payload = build_embeddings(entries, client, progress)
        print(file=sys.stderr)
        target = save_embeddings(directory, payload)
        print(f"embedded {payload['count']} skills with {payload['model']} -> {display(str(target.resolve()))}")
    return 0


def cmd_search(args) -> int:
    searcher = make_searcher(args)
    mode = "semantic" if args.semantic else "hybrid" if args.hybrid else "keyword"
    reranker = RerankClient.from_env() if args.rerank else None
    results = searcher.search(args.query, mode, args.top, reranker, args.pool)
    if args.json:
        rows = [{"name": e["name"], "score": round(s, 4), "source": e["source"],
                 "path": e["path"], "desc": e["desc"]} | ({"also": e["also"]} if e.get("also") else {})
                for e, s in results]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not results:
        print("no matches")
    for rank, (entry, score) in enumerate(results, 1):
        desc = " ".join(entry["desc"].split())
        shown = f"{score:.2f}" if mode == "keyword" else f"{score:.4g}"
        print(f"{rank}. {entry['name']}  (score {shown})")
        if desc:
            print(f"   {desc[:110]}{'...' if len(desc) > 110 else ''}")
        print(f"   {display(entry['path'])}")
        if entry.get("also"):
            print(f"   also in: {len(entry['also'])} other folder(s)")
    return 0


def cmd_stats(args) -> int:
    directory = index_dir(args.index)
    index = load_index(directory)
    print(f"index: {display(str((directory / 'index.json').resolve()))}")
    print(f"built: {index.get('built_at', 'unknown')}")
    print(f"skills: {index['count']}")
    print(f"duplicates collapsed: {sum(len(e.get('also', [])) for e in index['entries'])}")
    for source, count in sorted(Counter(e["source"] for e in index["entries"]).items()):
        print(f"  {source}: {count}")
    embeddings = directory / EMBEDDINGS_FILE
    if embeddings.is_file():
        data = json.loads(embeddings.read_text(encoding="utf-8"))
        print(f"embeddings: {data['model']}, {data['count']} vectors")
    else:
        print("embeddings: none (run: skillsonar build --embed)")
    return 0


def cmd_eval(args) -> int:
    searcher = make_searcher(args)
    report = evaluate(searcher, load_queries(Path(args.queries)), args.k, args.mode)
    hits = report.queries - len(report.misses)
    print(f"mode: {report.mode}   queries: {report.queries}   k: {report.k}")
    print(f"recall@{report.k}: {report.recall:.3f}   (every expected skill in top {report.k}: "
          f"{hits}/{report.queries}; top-1 correct: {report.first_hits}/{report.queries})")
    for miss in report.misses:
        print(f"  miss: {miss.query!r}\n        expected {miss.expected}, got {miss.got}")
    return 0


COMMANDS = {"build": cmd_build, "search": cmd_search, "stats": cmd_stats, "eval": cmd_eval}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except SkillsonarError as exc:
        print(f"skillsonar: {exc}", file=sys.stderr)
        return 1
