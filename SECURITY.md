# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x   | ✅ |

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report vulnerabilities privately to the maintainers. Include:

- A clear description of the vulnerability
- Steps to reproduce
- Affected versions
- Any suggested mitigations

You should receive an initial response within 72 hours.

## Scope

This project's security model:

- No outbound network calls — the reranker hits a local Ollama endpoint only.
- `opencode.json` patching preserves existing keys and creates backups before writing.
- No telemetry, no analytics, no third-party network dependencies.
