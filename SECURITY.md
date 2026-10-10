# Security Policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's private vulnerability reporting on this repository
("Security" tab, "Report a vulnerability"). Include a description, steps to reproduce and the
affected version. You should get a first reply within 72 hours.

## What the tool does with your data

- `build` and `search` read `SKILL.md` files and write the index to your user cache directory.
- Network calls happen only when you ask for them. `build --embed`, `--semantic` and `--hybrid`
  send skill text and queries to the server named by `OLLAMA_HOST` (a local Ollama by default).
  `--rerank` sends the query and the shortlisted skill names and descriptions to the endpoint in
  `SKILLSONAR_RERANK_BASE_URL`, with `SKILLSONAR_RERANK_API_KEY` as the bearer token when set.
- No telemetry and no update checks.
