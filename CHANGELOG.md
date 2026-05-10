# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Project memory** — persistent codebase context injected on subagent dispatch.
  Agents now receive a preamble with the project file tree, top-level symbols,
  detected conventions (language, framework, test runner, formatter, CI
  commands), and distilled episodic patterns — so they skip the exploration
  phase. Built on first dispatch, refreshed when files change, git HEAD moves,
  or 24h elapses.
- `opencode-router memory {show,rebuild,clear,inject}` CLI subcommands for
  manual memory management and debugging.
- Memory walks respect `.gitignore` via `git ls-files` when available, falls
  back to `os.walk` with a built-in deny list.
- Symbol detection via regex for Python, JavaScript/TypeScript, Go, Rust,
  Java, Ruby, and Terraform.
- Convention inference from package.json, pyproject.toml, Cargo.toml, go.mod,
  Makefile, Dockerfile, tsconfig.json, and CI workflows.
- User-notes preservation: rebuilds preserve text below
  `<!-- user-notes -->` in memory.md.
- Episodic memory preservation: existing `## Episodic` sections survive
  rebuilds.
- `memory/` module with modular architecture (`storage`, `walk`, `anatomy`,
  `conventions`, `trigger`) and public API: `inject()`, `rebuild()`, `clear()`.
- 55 unit tests for the memory subsystem across 6 test modules.

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

[Unreleased]: https://github.com/AdrianCsT/opencode-router/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AdrianCsT/opencode-router/releases/tag/v0.1.0
