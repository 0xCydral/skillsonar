# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-10-10

Renamed from `opencode-router` to `skillsonar`. The project is now a skill search tool.

### Added
- `skillsonar` command (also `python -m skillsonar`) with `build`, `search`, `stats` and `eval`.
- Keyword index over any folder tree containing `SKILL.md`, with a small stemmer and stopword list.
  Parses `description: |` and `description: >` block scalars. Each shared word is weighted by its
  rarity across the catalog (IDF, log(1 + N / df)) and counts three times when it is in the skill's
  name, so common words do not decide the order. Scores are decimals, printed with two places.
- Optional embeddings through Ollama (`bge-m3` by default) and hybrid ranking by reciprocal rank
  fusion (`search --semantic`, `search --hybrid`, `build --embed`).
- Optional rerank through any OpenAI-compatible chat endpoint (`search --rerank`).
- `eval` command that prints recall@k for a JSONL file of queries, and a public query set in
  `evals/queries.jsonl`.
- Index stored in the user cache directory, overridable with `--index`.
- Skill folders from `--path`, `SKILLSONAR_PATHS`, or the usual Claude Code, OpenCode and shared
  agent skill directories.
- Skills with the same name in several folders are collapsed to the first one found. The other
  locations are kept as `also` (shown as `also in: N other folder(s)`, listed in `search --json`),
  and `stats` reports how many duplicates were collapsed.

### Removed
- Agent routing, rules, provider profiles, the `opencode.json` patcher, DAG orchestration,
  project memory, `install.sh`, example agents and the related docs. Routing was dropped because it
  did not earn its complexity in daily use.
- The `opencode-router` console script. Use `skillsonar`.

## [0.3.3] — 2026-05-11

### Added
- `opencode-router memory record --agent --task --summary [--files] [--duration]`
  CLI command so the router prompt can log completed dispatches.
- Updated router prompt (`examples/router-prompts/default.md`) with memory-aware
  workflow: build memory, route with context, dispatch, record completion.

## [0.3.2] — 2026-05-10

### Added
- **Retrieval injection** for large projects (>9k chars / ~3k tokens).
  Memory is chunked by section, embedded with mxbai-embed-large, and
  cosine-searched by task relevance. Returns always-on header + top-5
  chunks — up to 89% token savings vs verbatim injection.
- `retrieval.py` with build_index(), chunking, and semantic search.
- Individual embedding failures don't block index builds — graceful skip.
- 12 new tests (retrieval module), 108 total.

## [0.3.1] — 2026-05-10

### Added
- Episodic memory distillation — dispatch logs are analyzed by LLM to extract
  reusable patterns, decisions, and gotchas for future agents.
- `memory.record()` public API for logging completed subagent dispatches.
- `opencode-router memory log [--tail N]` CLI.
- Distillation runs during rebuild when 5+ new log entries exist.
- 18 new tests (log + episodic), 96 total.

## [0.3.0] — 2026-05-10

### Added
- **Project memory** — persistent codebase context injected on subagent dispatch.
  Agents get a preamble with file tree, symbols, and conventions so they skip
  the exploration phase.
- `opencode-router memory {show,rebuild,clear,inject}` CLI subcommands.
- Symbol detection (7 languages), convention inference (8 manifest types).
- User-notes and episodic section preservation across rebuilds.
- 55 unit tests across 6 new test modules.

## [0.2.0] — 2026-05-09

### Added
- `opencode-router orchestrate "<task>"` — multi-step DAG planning that combines
  skill discovery (118 tree seeds + 105K token-indexed catalog) with agent routing
  (233 specialists) and LLM-based task decomposition.
- Skill catalog ingestion pipeline (`scripts/import-skills.py`) with security
  scanning — rejects curl injection, prompt override, and data exfiltration
  patterns. 105K clean skills imported from astra-skills.
- Tokenized skill index for fast search over large catalogs (~40 MB, cached).
- AgentSkillOS integration — tree search + token index for discovering relevant
  skills from the 200K+ ecosystem before routing to agents.
- Router prompt now supports two-tier dispatch: single-step (route) and
  multi-step (orchestrate) with automatic detection.
- Full architecture documentation with Mermaid diagram in `docs/architecture.md`.

### Changed
- Router agent prompt simplified to 40 lines — aggressive guard against doing
  work directly.
- Stderr from AgentSkillOS imports now suppressed to avoid confusing the router.
- Orchestrate bash calls include 120s timeout for API call headroom.

### Removed
- Deprecated `contrib/agentskillos/` engine (Claude SDK-based, replaced by
  native OpenCode execution via `orchestrate` subcommand).

## [0.1.0] — 2026-05-07

Initial release.

### Added
- Two-stage routing pipeline: `mxbai-embed-large` retrieval + `qwen3.5:4b` LLM rerank, both via Ollama.
- `opencode-router` CLI with subcommands: `init`, `register`, `route`, `index build`, `models apply`, `profile {list,current,show,set}`, `doctor`.
- Provider profile system mapping six abstract role buckets (`pro`, `flash`, `coding`, `visual`, `chinese`, `translation`) to concrete model paths.
- User-overridable role-pattern → bucket rules at `~/.config/opencode/orchestration-rules.json`.
- Default router agent prompt (`examples/router-prompts/default.md`) with explicit no-fabrication and default-save-deliverables policies.
- Four starter provider profiles: `ollama-local`, `ollama-cloud`, `nvidia-nim`, `deepseek-official`.
- Two example agent files: `code-reviewer`, `content-writer`.
- Documentation: architecture, installation, configuration, agent authoring, profiles, routing rules, FAQ.
- Idempotent `install.sh`.
- Unit test suite for agent parsing, rules engine, profile management, cosine similarity.

[Unreleased]: https://github.com/0xCydral/skillsonar/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/0xCydral/skillsonar/releases/tag/v0.4.0
[0.1.0]: https://github.com/0xCydral/opencode-router/releases/tag/v0.1.0
