# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
