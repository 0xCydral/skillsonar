"""Infer project conventions from manifest files.

Reads package.json, pyproject.toml, Cargo.toml, go.mod, Makefile,
and CI configs to extract build commands, test framework, language
version, and coding style hints.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import walk as _walk

# Pyproject.toml is tricky without tomllib (Python 3.11+). We use a
# lightweight regex parser that extracts enough for conventions.
_TOML_SECTION_RE = re.compile(r"^\[(?:\w+\.)*(\w+)\]\s*$")
_TOML_KEYVAL_RE = re.compile(r'^(\w[\w_-]*)\s*=\s*(.+)$')


def build(project: Path, files: list[Path] | None = None) -> str:
    """Return the ## Conventions markdown section."""
    if files is None:
        files = _walk.list_files(project)

    lines: list[str] = []
    _detect_languages(lines, files)
    _detect_tools(lines, project, files)
    _detect_ci(lines, project, files)
    return "\n".join(lines)


# ---------------------------------------------------------------- languages


def _detect_languages(lines: list[str], files: list[Path]) -> None:
    ext_counts: dict[str, int] = {}
    ext_to_lang = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript (React)",
        ".jsx": "JavaScript (React)",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".rb": "Ruby",
        ".tf": "Terraform",
        ".css": "CSS",
        ".scss": "SCSS",
        ".sql": "SQL",
        ".sh": "Shell",
    }
    for p in files:
        ext = p.suffix
        if ext in ext_to_lang:
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

    primary = sorted(ext_counts, key=ext_counts.get, reverse=True)  # type: ignore[arg-type]
    if not primary:
        return

    detected = [ext_to_lang[e] for e in primary[:3] if e in ext_to_lang]
    lines.append("### Languages")
    lines.append(f"Primary: {', '.join(detected)}")


# ---------------------------------------------------------------- tools


def _detect_tools(lines: list[str], project: Path, files: list[Path]) -> None:
    file_set = {str(f) for f in files}

    if "package.json" in file_set:
        _read_package_json(lines, project / "package.json")
    if "pyproject.toml" in file_set:
        _read_pyproject_toml(lines, project / "pyproject.toml")
    if "Cargo.toml" in file_set:
        _read_cargo_toml(lines, project / "Cargo.toml")
    if "go.mod" in file_set:
        _read_go_mod(lines, project / "go.mod")
    if "Makefile" in file_set:
        _read_makefile(lines, project / "Makefile")
    if "tsconfig.json" in file_set:
        _read_tsconfig(lines, project / "tsconfig.json")
    if "Dockerfile" in file_set:
        _read_dockerfile(lines, project / "Dockerfile")


def _read_package_json(lines: list[str], path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    scripts = data.get("scripts", {})
    if scripts:
        lines.append("### Build / Scripts")
        for name in ("build", "dev", "start", "test", "lint", "format", "typecheck"):
            cmd = scripts.get(name)
            if cmd:
                lines.append(f"- `npm run {name}`: {cmd[:80]}")

    deps = dict(data.get("dependencies", {}))
    deps.update(data.get("devDependencies", {}))
    deps.update(data.get("peerDependencies", {}))
    dep_keys = set(deps)

    lines.append("### Frameworks / Libraries")
    framework = _detect_js_framework(dep_keys)
    if framework:
        lines.append(f"- Framework: {framework}")
    if "typescript" in dep_keys:
        lines.append("- Language: TypeScript")
    if "jest" in dep_keys:
        lines.append("- Test runner: Jest")
    if "vitest" in dep_keys:
        lines.append("- Test runner: Vitest")
    if "prettier" in dep_keys or any("prettier" in s for s in scripts.values()):
        lines.append("- Formatter: Prettier")
    if "eslint" in dep_keys or any("eslint" in s for s in scripts.values()):
        lines.append("- Linter: ESLint")

    # Detect test runner from scripts.test command
    test_cmd = scripts.get("test", "")
    if "jest" in test_cmd:
        lines.append("- Test runner: Jest")
    elif "vitest" in test_cmd:
        lines.append("- Test runner: Vitest")
    elif "pytest" in test_cmd:
        lines.append("- Test runner: pytest")


def _read_pyproject_toml(lines: list[str], path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return

    deps: list[str] = []
    build_system: dict[str, str] = {}
    ruff_line_length: str | None = None
    current_section = ""

    for line in text.splitlines():
        m = _TOML_SECTION_RE.match(line)
        if m:
            current_section = m.group(1)
            continue
        m = _TOML_KEYVAL_RE.match(line)
        if not m:
            continue
        key, val = m.group(1), _strip_quotes(m.group(2).strip())

        # Handle list values like dependencies = ["a", "b"]
        deps_sections = ("dependencies", "dev-dependencies", "optional-dependencies")
        if current_section in deps_sections or current_section == "project":
            _extract_list_items(val, deps)

        if current_section == "project" and key == "dependencies":
            _extract_list_items(val, deps)
        if current_section == "build-system":
            build_system[key] = val
        if current_section == "ruff" and key == "line-length":
            ruff_line_length = val

    lines.append("### Build / Scripts")
    backend = build_system.get("build-backend", "")
    if "poetry" in backend:
        lines.append("- Build: Poetry")
    elif "hatchling" in backend:
        lines.append("- Build: Hatchling")
    elif "setuptools" in backend:
        lines.append("- Build: Setuptools")

    lines.append("### Frameworks / Libraries")
    dep_set = set(deps)
    if "pytest" in dep_set:
        lines.append("- Test runner: pytest")
    if "django" in dep_set:
        lines.append("- Framework: Django")
    if "fastapi" in dep_set:
        lines.append("- Framework: FastAPI")
    if "flask" in dep_set:
        lines.append("- Framework: Flask")
    if "pydantic" in dep_set:
        lines.append("- Validation: Pydantic")
    if "ruff" in dep_set:
        if ruff_line_length:
            lines.append(f"- Linter: Ruff (line-length: {ruff_line_length})")
        else:
            lines.append("- Linter: Ruff")


def _read_cargo_toml(lines: list[str], path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    edition = re.search(r'edition\s*=\s*["\'](\d+)["\']', text)
    lines.append("### Build / Scripts")
    if edition:
        lines.append(f"- Rust edition: {edition.group(1)}")
    if "tokio" in text:
        lines.append("- Async runtime: Tokio")
    if "actix" in text:
        lines.append("- Framework: Actix")
    if "axum" in text:
        lines.append("- Framework: Axum")


def _read_go_mod(lines: list[str], path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    mod = re.search(r"^module\s+(\S+)", text, re.MULTILINE)
    go_ver = re.search(r"^go\s+(\S+)", text, re.MULTILINE)
    lines.append("### Build / Scripts")
    if mod:
        lines.append(f"- Module: {mod.group(1)}")
    if go_ver:
        lines.append(f"- Go version: {go_ver.group(1)}")


def _read_makefile(lines: list[str], path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    targets = re.findall(r"^(\w[\w_-]*)\s*:", text, re.MULTILINE)
    if targets:
        shown = targets[:6]
        lines.append("### Makefile targets")
        lines.append(f"{', '.join(shown)}")


def _read_tsconfig(lines: list[str], path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    compiler = data.get("compilerOptions", {})
    strict = compiler.get("strict", False)
    target = compiler.get("target", "")
    if strict:
        lines.append("- TypeScript strict mode: enabled")
    if target:
        lines.append(f"- TypeScript target: {target}")


def _read_dockerfile(lines: list[str], path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    base = re.search(r"^FROM\s+(\S+)", text, re.MULTILINE)
    if base:
        lines.append(f"- Base image: {base.group(1)}")


# ---------------------------------------------------------------- CI


def _detect_ci(lines: list[str], project: Path, files: list[Path]) -> None:
    ci_files = [
        f
        for f in files
        if ".github/workflows" in str(f) and str(f).endswith((".yml", ".yaml"))
    ]
    if not ci_files:
        return
    lines.append("### CI/CD")
    for cf in ci_files[:4]:
        lines.append(f"- {cf.name}")
        try:
            text = (project / cf).read_text(encoding="utf-8")
        except OSError:
            continue
        runs = re.findall(r"^\s*run:\s*\|?\s*(.*)", text, re.MULTILINE)
        for r in runs[:3]:
            r = r.strip().replace("|", "").strip()
            if r and len(r) < 80:
                lines.append(f"  `{r}`")


# ---------------------------------------------------------------- helpers


def _detect_js_framework(deps: set[str]) -> str | None:
    if "next" in deps:
        return "Next.js"
    if "react" in deps:
        return "React"
    if "vue" in deps:
        return "Vue.js"
    if "svelte" in deps or "@sveltejs/kit" in deps:
        return "Svelte"
    if "@angular/core" in deps:
        return "Angular"
    if "express" in deps:
        return "Express"
    if "fastify" in deps:
        return "Fastify"
    if "nuxt" in deps:
        return "Nuxt.js"
    return None


def _strip_quotes(v: str) -> str:
    """Remove surrounding quotes from a TOML string value."""
    for q in ('"', "'"):
        if v.startswith(q) and v.endswith(q):
            v = v[1:-1]
            break
    return v


def _extract_list_items(val: str, deps: list[str]) -> None:
    """Extract items from a TOML value: list like ['a','b'] or single string."""
    val = val.strip()
    # List value: ["item1", "item2"]
    if val.startswith("[") and "]" in val:
        items = re.findall(r'"([^"]+)"', val)
        deps.extend(items)
        return
    # Single quoted value
    unquoted = val.strip().strip('"').strip("'")
    if unquoted and unquoted != val:
        deps.append(unquoted)
